#!/usr/bin/python
# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generates script-specific samples (collections of chars) using cldr
exemplar data for languages written in a script."""

import argparse
import codecs
import collections
import locale
import os
from os import path
import re
import shutil
import xml.etree.cElementTree as ElementTree

from nototools import create_image
from nototools import extra_locale_data
from nototools import notoconfig
from nototools import tool_utils
from nototools import unicode_data

from icu import Locale, Collator

NOTO_DIR = path.abspath(path.join(path.dirname(__file__), os.pardir))

CLDR_DIR = path.join(NOTO_DIR, 'third_party', 'cldr')

_VERBOSE = False

def read_character_at(source, pointer):
  while pointer < len(source) and source[pointer] == ' ':
    pointer += 1

  if pointer >= len(source):
    raise IndexError('pointer %d out of range 0-%d' % (pointer, len(source)))

  if source[pointer] == '\\':
    if source[pointer+1].upper() == 'U':
      end_of_hex = pointer+2
      while (end_of_hex < len(source)
           and source[end_of_hex].upper() in '0123456789ABCDEF'):
        end_of_hex += 1
      assert end_of_hex-(pointer+2) in {4, 5, 6}
      hex_code = source[pointer+2:end_of_hex]
      return end_of_hex, unichr(int(hex_code, 16))
    else:
      return pointer+2, source[pointer+1]
  else:
    return pointer+1, source[pointer]


def exemplar_string_to_list(exstr):
  assert exstr[0] == '['
  exstr = exstr[1:]
  if exstr[-1] == ']':
    exstr = exstr[:-1]

  exemplar_list = []
  pointer = 0
  while pointer < len(exstr):
    if exstr[pointer] in ' ':
      pointer += 1
    elif exstr[pointer] == '{':
      multi_char = ''
      mc_ptr = pointer+1
      while exstr[mc_ptr] != '}':
        mc_ptr, char = read_character_at(exstr, mc_ptr)
        multi_char += char
      exemplar_list.append(multi_char)
      pointer = mc_ptr+1
    elif exstr[pointer] == '-':
      while pointer + 1 < len(exstr) and exstr[pointer + 1] == ' ':
        continue
      if pointer + 1 == len(exstr): # hyphen before ']' is special
        exemplar_list.append('-')
        break
      previous = exemplar_list[-1]
      assert len(previous) == 1  # can't have ranges with strings
      previous = ord(previous)

      pointer, last = read_character_at(exstr, pointer+1)
      assert last not in [' ', '\\', '{', '}', '-']
      last = ord(last)
      exemplar_list += [unichr(code) for code in range(previous+1, last+1)]
    else:
      pointer, char = read_character_at(exstr, pointer)
      exemplar_list.append(char)

  return exemplar_list


_exemplar_from_file_cache = {}

def get_exemplar_from_file_cache(cldr_file_path):
  try:
    return _exemplar_from_file_cache[cldr_file_path]
  except KeyError:
    pass

  exemplar_list = get_exemplar_from_file(cldr_file_path)
  if exemplar_list:
    _exemplar_from_file_cache[cldr_file_path] = exemplar_list
    return exemplar_list
  return None


def get_exemplar_from_file(cldr_file_path):
  data_file = path.join(CLDR_DIR, cldr_file_path)
  try:
    root = ElementTree.parse(data_file).getroot()
  except IOError:
    return None

  for tag in root.iter('exemplarCharacters'):
    if 'type' in tag.attrib:
      if _VERBOSE:
        print 'type defined, skip chars %s in %s' % (tag.attrib, cldr_file_path)
      continue
    try:
      return exemplar_string_to_list(tag.text)
    except (ValueError, IndexError) as e:
      print 'error reading exemplar from \'%s\':\n  %s' % (cldr_file_path, e)

  return None


_exemplar_from_extra_data_cache = {}

def get_exemplar_from_extra_data_cache(loc_tag):
  try:
    return _exemplar_from_extra_data_cache[loc_tag]
  except KeyError:
    pass

  try:
    exemplar_string = extra_locale_data.EXEMPLARS[loc_tag]
    exemplars = exemplar_string_to_list(exemplar_string)
    _exemplar_from_extra_data_cache[loc_tag] = exemplars
    return exemplars
  except KeyError:
    pass
  return None


def find_parent_locale(locl):
  if locl in parent_locale:
    return parent_locale[locl]
  if '-' in locl:
    return locl[:locl.rindex('-')]
  if locale == 'root':
    return None
  return 'root'


def get_exemplar(language, script):
  locl = language + '-' + script
  while locl != 'root':
    for directory in ['common', 'seed', 'exemplars']:
      exemplar = get_exemplar_from_file_cache(
        path.join(directory, 'main', locl.replace('-', '_')+'.xml'))
      if exemplar:
        return exemplar
    exemplar = get_exemplar_from_extra_data_cache(locl)
    if exemplar:
      return exemplar
    locl = find_parent_locale(locl)
  return None


likely_subtag_data = {}

def parse_likely_subtags():
    data_file = path.join(
        CLDR_DIR, 'common', 'supplemental', 'likelySubtags.xml')
    tree = ElementTree.parse(data_file)

    for tag in tree.findall('likelySubtags/likelySubtag'):
        from_tag = tag.get('from').replace('_', '-')
        to_tag = tag.get('to').split('_')
        likely_subtag_data[from_tag] = to_tag

    likely_subtag_data.update(extra_locale_data.LIKELY_SUBTAGS)


def find_likely_script(language):
    if not likely_subtag_data:
        parse_likely_subtags()
    return likely_subtag_data[language][1]


# technically, language tags are case-insensitive, but the CLDR data is cased
LSRV_RE = re.compile(r'^([a-z]{2,3})(?:[_-]([A-Z][a-z]{3}))?'
                     r'(?:[_-]([A-Z]{2}|\d{3}))?(?:[_-]([A-Z]{5,8}))?$')

def get_lsrv(locale):
  m = LSRV_RE.match(locale)
  if not m:
    print 'regex did not match locale \'%s\'' % locale
    return None
  lang = m.group(1)
  script = m.group(2)
  region = m.group(3)
  variant = m.group(4)

  if not script:
    tag = lang
    if region:
      tag += '-' + region
    try:
      script = find_likely_script(tag)
    except KeyError:
      try:
        script = find_likely_script(lang)
      except KeyError:
        pass
  return (lang, script, region, variant)


loc_to_lit_pop = {}

def _collect_lit_pops():
    data_file = path.join(
        CLDR_DIR, 'common', 'supplemental', 'supplementalData.xml')
    root = ElementTree.parse(data_file).getroot()

    for territory in root.findall('territoryInfo/territory'):
      region = territory.attrib['type']
      population = int(territory.attrib['population'])
      lit_percent = float(territory.attrib['literacyPercent']) / 100.0
      for lang_pop in territory.findall('languagePopulation'):
        lang = lang_pop.attrib['type']
        pop_percent = float(lang_pop.attrib['populationPercent']) / 100.0
        if 'writingPercent' in lang_pop.attrib:
          lang_lit_percent = float(lang_pop.attrib['writingPercent']) / 100.0
        else:
          lang_lit_percent = lit_percent

        locale = get_lsrv(lang + '_' + region)
        loc_tag = '_'.join([locale[0], locale[1]])

        lit_pop = int(population * pop_percent * lang_lit_percent)
        if loc_tag in loc_to_lit_pop:
          loc_to_lit_pop[loc_tag] += lit_pop
        else:
          loc_to_lit_pop[loc_tag] = lit_pop


def get_locs_by_lit_pop():
  if not loc_to_lit_pop:
    _collect_lit_pops()
  return sorted([(v, k) for k, v in loc_to_lit_pop.iteritems()])


def get_lit_pop(loc_tag):
  if not loc_to_lit_pop:
    _collect_lit_pops()
  return loc_to_lit_pop.get(loc_tag, 0)


def loc_to_tag(loc):
  return '-'.join([tag for tag in loc if tag])


def get_script_to_exemplar_data_map():
  """Return a map from script to 3-tuples of:
    - locale tuple (lang, script, region, variant)
    - cldr_relative path to src of exemplar data
    - tuple of the exemplar chars"""

  script_map = collections.defaultdict(dict)
  for directory in ['common', 'seed', 'exemplars']:
    data_dir = path.join(directory, 'main')
    for filename in os.listdir(path.join(CLDR_DIR, data_dir)):
      if not filename.endswith('.xml'):
        continue

      exemplar_list = get_exemplar_from_file_cache(path.join(data_dir, filename))
      if not exemplar_list:
        continue

      lsrv = get_lsrv(filename[:-4])
      if not lsrv:
        continue
      src = path.join(directory, filename)
      script = lsrv[1]
      if not script:
        continue

      loc_tag = loc_to_tag(lsrv)
      loc_to_exemplar_info = script_map[script]
      if loc_tag in loc_to_exemplar_info:
        if _VERBOSE:
          print 'skipping %s, already have exemplars for %s from %s' % (
              src, loc_tag, loc_to_exemplar_info[loc_tag][1])
        continue

      # fix exemplars that look incorrect
      if script == 'Arab' and 'd' in exemplar_list:
        if _VERBOSE:
          print 'found \'d\' in %s for %s' % (src, lsrv)
        no_latin = True
      else:
        no_latin = False
      # exclude exemplar strings, and restrict to letters and digits
      filtered_exemplar_list = [cp for cp in exemplar_list if len(cp) == 1 and
                                (unicode_data.category(cp)[0] in 'L' or
                                 unicode_data.category(cp) == 'Nd') and
                                not (cp in 'df' and no_latin)]

      # some exemplar lists don't surround strings with curly braces, and end up
      # with duplicate characters.  Flag these
      exemplar_chars = set()
      dup_chars = set()
      fixed_exemplar_list = []
      for cp in filtered_exemplar_list:
        if cp in exemplar_chars:
          dup_chars.add(cp)
        else:
          exemplar_chars.add(cp)
          fixed_exemplar_list.append(cp)
      if len(dup_chars) > 0 and _VERBOSE:
        print 'duplicate exemplars in %s: %s' % (
            src, ', '.join([u'\u200e%s\u200e (%x)' % (cp, ord(cp)) for cp in dup_chars]))
      loc_to_exemplar_info[loc_tag] = (lsrv, src, tuple(fixed_exemplar_list))

  # supplement with extra locale data
  for loc_tag in extra_locale_data.EXEMPLARS:
    exemplar_list = get_exemplar_from_extra_data_cache(loc_tag)
    lang, script = loc_tag.split('-')
    lsrv = (lang, script, None, None)
    loc_to_exemplar_info = script_map[script]
    src = '[extra locale data]/%s' % loc_tag
    if loc_tag in loc_to_exemplar_info:
      if _VERBOSE:
        print 'skipping %s, already have exemplars for %s from %s' % (
            src, loc_tag, loc_to_exemplar_info[loc_tag][1])
      continue

    # restrict to letters
    filtered_exemplar_list = [cp for cp in exemplar_list if unicode_data.category(cp)[0] in 'L'
                              or unicode_data.category(cp) in 'Nd']
    if len(filtered_exemplar_list) != len(exemplar_list) and _VERBOSE:
      print 'filtered some characters from %s' % src
    loc_to_exemplar_info[loc_tag] = (lsrv, src, tuple(filtered_exemplar_list))

  return script_map


def show_rarely_used_char_info(script, loc_map, char_to_lang_map):
  # let's list chars unique to each language
  for loc_tag in sorted(loc_map):
    unique_chars = []
    dual_chars = []
    dual_shared_with = set()
    triple_chars = []
    triple_shared_with = set()
    info = loc_map[loc_tag]
    exemplars = info[2]
    for cp in exemplars:
      num_common_langs = len(char_to_lang_map[cp])
      if num_common_langs == 1:
        unique_chars.append(cp)
      elif num_common_langs == 2:
        dual_chars.append(cp)
        for shared_loc_tag in char_to_lang_map[cp]:
          if shared_loc_tag != loc_tag:
            dual_shared_with.add(shared_loc_tag)
      elif num_common_langs == 3:
        triple_chars.append(cp)
        for shared_loc_tag in char_to_lang_map[cp]:
          if shared_loc_tag != loc_tag:
            triple_shared_with.add(shared_loc_tag)

    script_tag = '-' + script
    if unique_chars:
      print '%s has %d unique chars: %s%s' % (
          loc_tag, len(unique_chars), ' '.join(unique_chars[:100]),
          '...' if len(unique_chars) > 100 else '')
    if dual_chars:
      print '%s shares %d chars (%s%s) with 1 other lang: %s' % (
          loc_tag, len(dual_chars), ' '.join(dual_chars[:20]),
          '...' if len(dual_chars) > 20 else '',
          ', '.join(sorted([loc.replace(script_tag, '') for loc in dual_shared_with])))
    if triple_chars:
      print '%s shares %d chars (%s%s) with 2 other langs: %s' % (
          loc_tag, len(triple_chars), ' '.join(triple_chars[:20]),
          '...' if len(triple_chars) > 20 else '',
          ', '.join(sorted([loc.replace(script_tag, '') for loc in triple_shared_with])))
    if not (unique_chars or dual_chars or triple_chars):
      print '%s shares all chars with 3+ other langs' % loc_tag


def get_char_to_lang_map(loc_map):
  char_to_lang_map = collections.defaultdict(list)
  for loc_tag in sorted(loc_map):
    info = loc_map[loc_tag]
    exemplars = info[2]
    for cp in exemplars:
      if loc_tag in char_to_lang_map[cp]:
        print 'loc %s (from %s) already in char_to_lang_map for %s (%x)' % (
            loc_tag, info[1], cp, ord(cp))
      else:
        char_to_lang_map[cp].append(loc_tag)
  return char_to_lang_map


def char_lang_info(num_locales, char_to_lang_map):
  """Returns a tuple containing
  - characters ordered by the number of langs that use them
  - a list mapping number of shared langs to number of chars shared by those langs"""

  freq_list = []
  hist = [0] * (num_locales + 1)
  for cp in char_to_lang_map:
    num_shared_langs = len(char_to_lang_map[cp])
    if num_shared_langs >= len(hist):
      for shared_lang in char_to_lang_map[cp]:
        if shared_lang not in loc_map:
          print 'loc map does not have \'%s\'!' % shared_lang

    freq_list.append((num_shared_langs, cp))
    if num_shared_langs >= len(hist):
      print 'num shared langs is %d but size of hist is %d' % (num_shared_langs, len(hist))
    hist[num_shared_langs] += 1
  freq_list.sort()
  return [cp for nl, cp in freq_list], hist


def show_char_use_info(script, chars_by_num_langs, char_to_lang_map):
  script_tag = '-' + script
  for cp in chars_by_num_langs:
    langs = char_to_lang_map[cp]
    count = len(langs)
    print u'char %s\u200e (%x): %d %s%s' % (
        cp, ord(cp), count, ', '.join(sorted(
            [loc.replace(script_tag, '') for loc in langs[:12]])),
        '...' if count > 12 else '')
  print 'total chars listed: %d' % len(char_to_lang_map)


def show_shared_langs_hist(hist):
  # histogram - number of chars per number of shared languages
  for i in range(1, len(hist)):
    print '[%3d] %3d %s' % (i, hist[i], 'x' * hist[i])


def get_upper_case_list(char_list):
  """Return the upper case versions where they differ.
  If no char in the list is a lower case variant, the result is empty."""
  # keep in same order as input list.
  upper_case_chars = []
  for cp in char_list:
    upcp = unicode_data.to_upper(cp)
    if upcp != cp:
      upper_case_chars.append(upcp)
  return upper_case_chars


def show_tiers(char_list, num_tiers, tier_size):
  for tier in range(1, num_tiers + 1):
    if tier == 1:
      subset = char_list[-tier_size:]
    else:
      subset = char_list[tier * -tier_size:(tier-1) * -tier_size]
    if not subset:
      break
    tier_chars = sorted(subset)
    print 'tier %d: %s' % (tier, ' '.join(tier_chars))

    upper_case_chars = get_upper_case_list(tier_chars)
    if upper_case_chars:
      print ' upper: ' + ' '.join(upper_case_chars)


def get_rare_char_info(char_to_lang_map, shared_lang_threshold):
  """Returns a tuple of:
  - a set of 'rare_chars' (those used threshold langs or fewer),
  - a mapping from each locale with rare chars to a set of its rare chars"""

  rare_chars = set()
  locs_with_rare_chars = collections.defaultdict(set)
  for cp in char_to_lang_map:
    num_shared_langs = len(char_to_lang_map[cp])
    if num_shared_langs <= shared_lang_threshold:
      rare_chars.add(cp)
      for lang_tag in char_to_lang_map[cp]:
        locs_with_rare_chars[lang_tag].add(cp)
  return rare_chars, locs_with_rare_chars


_lang_for_script_map = {}

def _init_lang_for_script_map():
  locs_by_lit_pop = [t[1] for t in get_locs_by_lit_pop()]
  locs_by_lit_pop.reverse()
  for t in locs_by_lit_pop:
    lsrv = get_lsrv(t)
    script = lsrv[1]
    if script not in _lang_for_script_map:
      lang = lsrv[0]
      # print '%s lang => %s' % (script, lang)
      _lang_for_script_map[script] = lang


def lang_for_script(script):
  """Return the most common language for a script based on literate population."""
  # should use likely subtag data for this.
  # the current code assumes all we want is lang -> script, I'd have to change
  # it to map locale->locale. Right now I dont' get Hant -> zh_Hant, only
  # Hant -> zh, which isn't good enough I think.
  if not _lang_for_script_map:
    _init_lang_for_script_map()
  return _lang_for_script_map.get(script)


def select_rare_chars_for_loc(script, locs_with_rare_chars, shared_lang_threshold,
                              char_to_lang_map):
  """Return a list of 2-tuples of loc and selected rare chars,
  ordered by decreasing literate population of the locale."""

  rarity_threshold_map = {}
  for lang_tag in locs_with_rare_chars:
    rarity_threshold_map[lang_tag] = shared_lang_threshold

  selected = []
  locs_by_lit_pop = [t[1] for t in get_locs_by_lit_pop()]
  locs_by_lit_pop.reverse()
  # examine locales in decreasing order of literate population
  for loc_tag in locs_by_lit_pop:
    if script not in loc_tag:
      continue
    loc_tag = loc_tag.replace('_', '-')
    if loc_tag not in locs_with_rare_chars:
      continue
    most_specific_chars = set()
    most_specific_chars_count = rarity_threshold_map[loc_tag]
    # From the rare chars for this locale, select those that
    # are most specific to this language. In most cases they
    # are unique to this language.
    for cp in locs_with_rare_chars[loc_tag]:
      num_chars = len(char_to_lang_map[cp])
      if num_chars <= most_specific_chars_count:
        if num_chars < most_specific_chars_count:
          most_specific_chars = set()
        most_specific_chars.add(cp)
        most_specific_chars_count = num_chars
    if most_specific_chars:
      selected.append((loc_tag, most_specific_chars))
      for cp in most_specific_chars:
        for tag in char_to_lang_map[cp]:
          if rarity_threshold_map[tag] > most_specific_chars_count:
            rarity_threshold_map[tag] = most_specific_chars_count
  return selected


def show_selected_rare_chars(selected):
  print 'langs with rare chars by lang pop:'
  for lang_tag, chars in selected:
    print '%10s: %s' % (lang_tag, ', '.join(sorted(chars)))


def sort_for_script(cp_list, script):
  lang = lang_for_script(script)
  if not lang:
    print 'cannot sort for script, no lang for %s' % script
    return cp_list
  loc = Locale(lang + '_' + script)
  col = Collator.createInstance(loc)
  return sorted(cp_list, cmp=col.compare)


def addcase(sample, script):
  cased_sample = []
  for cp in sample:
    ucp = unicode_data.to_upper(cp)
    if ucp != cp and ucp not in sample: # Copt has cased chars paired in the block
      cased_sample.append(ucp)
  if cased_sample:
    cased_sample = ' '.join(cased_sample)
    if _VERBOSE:
      print 'add case for %s' % script
    return sample + '\n' + cased_sample
  return sample


def generate_sample_for_script(script, loc_map):
  num_locales = len(loc_map)

  if num_locales == 1:
    tag, info = loc_map.iteritems().next()
    exemplars = info[2]
    ex_len = len(exemplars)
    info = '%s (1 locale)\nfrom exemplars for %s (%s%d chars)' % (
        script, tag, 'first 60 of ' if ex_len > 60 else '', ex_len)
    # don't sort, rely on exemplar order
    sample = ' '.join(exemplars[:60])
    sample = addcase(sample, script)
    return sample, info

  script_tag = '-' + script

  char_to_lang_map = get_char_to_lang_map(loc_map)
  if len(char_to_lang_map) <= 60:
    info = '%s (%d locales)\nfrom merged exemplars (%d chars) from %s' % (
        script, num_locales, len(char_to_lang_map),
        ', '.join([loc.replace(script_tag, '') for loc in loc_map]))
    sample = ' '.join(sort_for_script(list(char_to_lang_map), script))
    sample = addcase(sample, script)
    return sample, info

  # show_rarely_used_char_info(script, loc_map, char_to_lang_map)

  chars_by_num_langs, num_langs_to_num_chars = char_lang_info(
      num_locales, char_to_lang_map)

  # show_char_use_info(chars_by_num_langs, char_to_lang_map)

  # show_shared_langs_hist(num_langs_to_num_chars)

  # show_tiers(chars_by_num_langs, 3, 40)

  shared_lang_threshold = min(7, num_locales)
  rare_chars, locs_with_rare_chars = get_rare_char_info(
      char_to_lang_map, shared_lang_threshold)

  selected = select_rare_chars_for_loc(script,
      locs_with_rare_chars, shared_lang_threshold, char_to_lang_map)

  # show_selected_rare_chars(selected)

  chosen_chars = list(chars_by_num_langs)[-60:]
  rare_extension = []
  for _, chars in selected:
    avail_chars = [cp for cp in chars if cp not in chosen_chars and
                   cp not in rare_extension]
    rare_extension.extend(sorted(avail_chars)[:4]) # vietnamese dominates latin otherwise
    if len(rare_extension) > 20:
      break
  chosen_chars = chosen_chars[:60 - len(rare_extension)]
  chosen_chars.extend(rare_extension)
  info = ('%s (%d locales)\n'
         'from most common exemplars plus chars specific to most-read languages' % (
             script, num_locales))
  sample = ' '.join(sort_for_script(chosen_chars, script))
  sample = addcase(sample, script)
  return sample, info


def generate_samples(dstdir, imgdir, summary):
  if imgdir:
    imgdir = tool_utils.ensure_dir_exists(imgdir)
    print 'writing images to %s' % imgdir

  if dstdir:
    dstdir = tool_utils.ensure_dir_exists(dstdir)
    print 'writing files to %s' % dstdir

  verbose = summary
  script_map = get_script_to_exemplar_data_map()
  for script in sorted(script_map):
    sample, info = generate_sample_for_script(script, script_map[script])
    if summary:
      print
      print info
      print sample

    if imgdir:
      path = os.path.join(imgdir, '%s.png' % script)
      print 'writing image %s.png' % script
      rtl = script in['Hebr', 'Arab']
      create_image.create_png(sample, path, font_size=34, line_spacing=40, width=800, rtl=rtl)

    if dstdir:
      filename = 'und-%s.txt' % script
      print 'writing data %s' % filename
      filepath = os.path.join(dstdir, filename)
      with codecs.open(filepath, 'w', 'utf-8') as f:
        f.write(sample + '\n')


def main():
  noto = notoconfig.values.get('noto')
  default_dstdir = os.path.join(noto, 'sample_texts')

  parser = argparse.ArgumentParser()
  parser.add_argument('--dstdir', help='where to write samples (default %s)' %
                      default_dstdir, default=default_dstdir, metavar='dir')
  parser.add_argument('--imgdir', help='if defined, generate images in this dir',
                      metavar='dir')
  parser.add_argument('--save', help='write sample files in dstdir', action='store_true')
  parser.add_argument('--summary', help='output list of samples and how they were generated',
                      action='store_true')
  parser.add_argument('--verbose', help='print warnings and extra info', action='store_true')
  args = parser.parse_args()

  if not args.save and not args.imgdir and not args.summary:
    print 'nothing to do.'
    return

  if args.verbose:
    global _VERBOSE
    _VERBOSE = True

  generate_samples(args.dstdir if args.save else None, args.imgdir, args.summary)


if __name__ == '__main__':
  locale.setlocale(locale.LC_COLLATE, 'en_US.UTF-8')
  main()
