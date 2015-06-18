#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generate data files for the Noto website."""

from __future__ import division

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'

import argparse
import codecs
import collections
import csv
import json
import locale
import os
from os import path
import re
import shutil
import subprocess
import xml.etree.cElementTree as ElementTree

from fontTools import ttLib

from nototools import cldr_data
from nototools import coverage
from nototools import create_image
from nototools import extra_locale_data
from nototools import font_data
from nototools import notoconfig
from nototools import tool_utils
from nototools import unicode_data

TOOLS_DIR = notoconfig.values['noto_tools']
FONTS_DIR = notoconfig.values['noto_fonts']
CJK_DIR = notoconfig.values['noto_cjk']

CLDR_DIR = path.join(TOOLS_DIR, 'third_party', 'cldr')

LAT_LONG_DIR = path.join(TOOLS_DIR, 'third_party', 'dspl')
SAMPLE_TEXT_DIR = path.join(TOOLS_DIR, 'sample_texts')

APACHE_LICENSE_LOC = path.join(FONTS_DIR, 'LICENSE')
SIL_LICENSE_LOC = path.join(CJK_DIR, 'LICENSE')

ODD_SCRIPTS = {
  'CJKjp': 'Jpan',
  'CJKkr': 'Kore',
  'CJKsc': 'Hans',
  'CJKtc': 'Hant',
  'JP': 'Jpan',
  'KR': 'Kore',
  'SC': 'Hans',
  'TC': 'Hant',
  'NKo': 'Nkoo',
  'SumeroAkkadianCuneiform': 'Xsux',
  'Symbols': 'Zsym',
  'Emoji': 'Qaae',
}

def convert_to_four_letter(script_name):
  """Converts a script name from a Noto font file name to ISO 15924 code."""
  if not script_name:
    raise ValueError('empty script name')
  if script_name in ODD_SCRIPTS:
      return ODD_SCRIPTS[script_name]
  return unicode_data.web_script_code(script_name)


NotoInfo = collections.namedtuple(
    'NotoInfo',
    'family, script, variant, weight, slope, fmt, hint_status, is_cjk, subset')

_NOTO_FONT_NAME_REGEX = re.compile(
    'Noto'
    '(Sans|Serif|Naskh|Kufi|Nastaliq|Emoji)'
    '(Mono)?'
    '(.*?)'
    '(UI|Eastern|Estrangela|Western)?'
    '-'
    '(|Black|Bold|DemiLight|Light|Medium|Regular|Thin)'
    '(Italic)?'
    '\.(ttf|ttc|otf)')

def noto_font_path_to_info(font_path):
  """Return NotoInfo if font_path points to a noto font."""

  filedir, filename = os.path.split(font_path)
  match = _NOTO_FONT_NAME_REGEX.match(filename)
  if match:
    family, mono, script, variant, weight, slope, fmt = match.groups()
  elif filename == 'NotoNastaliqUrduDraft.ttf':
    family, mono, script, variant, weight, slope, fmt = (
        'Nastaliq', None, 'Aran', None, 'Regular', None, 'ttf')
  else:
    if filename not in ['NotoSansCJK.ttc.zip']:
      print '%s did not match font regex' % filename
    return None

  if family == 'Emoji':
    family = 'Sans'
    script = 'Emoji'

  is_cjk = filedir.endswith('noto-cjk')

  if script in ['JP', 'KR', 'TC', 'SC']:
    subset = script
  else:
    subset = None

  script_name = script
  if not script:
    script = 'LGC'
    script_name = 'LGC'
  elif script == 'Historic':
    script = 'HST'
  elif script == 'CJK':
    # leave script as-is
    pass
  else:
    try:
      script = convert_to_four_letter(script)
    except ValueError:
      print 'unknown script: %s for %s' % (script, filename)
      return

  if weight == '':
    weight = 'Regular'

  if mono and variant:
    raise ValueError('mono and variant')
  elif mono:
    variant = mono

  if is_cjk:
    hint_status = 'hinted'
  elif filedir.endswith('alpha'):
    hint_status = 'unhinted'
  else:
    hint_status = path.basename(filedir)
    assert hint_status in ['hinted', 'unhinted']

  return NotoInfo(family, script, variant, weight, slope, fmt, hint_status, is_cjk, subset)


Font = collections.namedtuple(
    'Font',
    'filepath, hint_status, key, family, script, variant, weight, slope, '
    'license_type, is_cjk, fmt')

def get_noto_fonts():
  """Scan Noto dirs for fonts, and create a Font object for each one that we will use
  in the web site.  Return a list of these Font objects."""

  all_fonts = []

  font_dirs = [
    path.join(FONTS_DIR, 'hinted'),
    path.join(FONTS_DIR, 'unhinted'),
    path.join(FONTS_DIR, 'alpha'),
    CJK_DIR]

  for font_dir in font_dirs:
    for filename in os.listdir(font_dir):
      if not filename.startswith('Noto'):
        continue
      filepath = path.join(font_dir, filename)
      notoinfo = noto_font_path_to_info(filepath)
      if not notoinfo:
        if not (filename == 'NotoSansCJK.ttc.zip' or
                filename.endswith('.ttx')):
          raise ValueError("unexpected filename in %s: '%s'." %
                           (font_dir, filename))
        continue

      if notoinfo.variant == 'Mono':
        continue

      if notoinfo.script in {'CJK', 'HST'}:
        continue

      if notoinfo.subset:
        continue

      if notoinfo.is_cjk:
        license_type = 'sil'
      else:
        license_type = 'apache'

      family = 'Noto ' + notoinfo.family

      key = family.replace(' ', '-')
      if notoinfo.script != 'LGC':
        key += '-' + notoinfo.script
      if notoinfo.variant not in {None, 'UI', 'Mono'}:
        key += '-' + notoinfo.variant
      key = key.lower()[5:] # strip 'noto-' from head of key, they all start with it

      font = Font(filepath, notoinfo.hint_status, key,
                  family, notoinfo.script, notoinfo.variant, notoinfo.weight,
                  notoinfo.slope, license_type, notoinfo.is_cjk, notoinfo.fmt)
      all_fonts.append(font)

  return all_fonts


Family = collections.namedtuple(
    'Family',
    'name, rep_member, charset, hinted_members, unhinted_members')

def get_families(fonts):
  """Group fonts into families, group by hinted and unhinted, select representative."""
  families = {}
  all_keys = set([font.key for font in fonts])
  for key in all_keys:
    members = {font for font in fonts
               if font.key == key and font.variant != 'UI' and font.fmt in {'ttf', 'otf'}}

    if not members:
      mbrs = {font for font in fonts if font.key == key}
      raise ValueError("no members for %s from %s" % (key, [f.filepath for f in mbrs]))

    hinted_members = []
    unhinted_members = []
    rep_member = None
    for font in members:
      if font.hint_status == 'hinted':
        hinted_members.append(font)
      else:
        unhinted_members.append(font)
      if not rep_member:
        if font.weight == 'Regular' and font.slope is None:
          # We assume here that there's no difference between a hinted or unhinted
          # rep_member in terms of what we use it for
          rep_member = font

    if not rep_member:
      raise ValueError('Family %s does have a representative font.' % key)

    if hinted_members and not len(hinted_members) in [1, 2, 4, 7]:
      raise ValueError('Family %s has %d hinted_members (%s)' % (
          key, len(hinted_members), [font.name for font in hinted_members]))

    if unhinted_members and not len(unhinted_members) in [1, 2, 4, 7]:
      raise ValueError('Family %s has %d unhinted_members (%s)' % (
          key, len(unhinted_members), [font.name for font in unhinted_members]))

    if hinted_members and unhinted_members and len(hinted_members) != len(unhinted_members):
      raise ValueError('Family %s has %d hinted members but %d unhinted memberts' % (
          key, len(hinted_members), len(unhinted_members)))

    name = get_font_family_name(rep_member.filepath)

    if rep_member.fmt in {'ttf', 'otf'}:
      charset = coverage.character_set(rep_member.filepath)
    else:
      charset = NotImplemented

    families[key] = Family(name, rep_member, charset, hinted_members, unhinted_members)

  return families


def get_script_to_family_ids(family_map):
  """The keys in the returned map are all the supported scripts."""
  script_to_family_ids = collections.defaultdict(set)
  for key in family_map:
    script = family_map[key].rep_member.script
    if script == 'LGC':
      for script in ['Latn', 'Grek', 'Cyrl']:
        script_to_family_ids[script].add(key)
    else:
      script_to_family_ids[script].add(key)
  return script_to_family_ids


def get_used_lang_data(supported_scripts):
  """Returns a mapping from lang to a tuple of:
  - a set of scripts used in some region
  - a set of scripts not used in any region"""

  # Get additional scripts for a lang by using get_likely_subtags from script to
  # lang.  This might not be the same as the likely script for a lang, but it does
  # indicate the language can be written in the script, or so we assume.
  lang_to_additional_script = {}
  for script in supported_scripts:
    lang = cldr_data.get_likely_subtags('und-' + script)[0]
    if lang != 'und':
      lang_to_additional_script[lang] = script

  unsupported_scripts = set()
  lang_data = {}
  used_lang_scripts = collections.defaultdict(set)
  for region in cldr_data.known_regions():
    lang_scripts = cldr_data.region_to_lang_scripts(region)
    for lang_script in lang_scripts:
      lang, script = lang_script.split('-')
      if script == 'Kana':
        print 'remap %s to use Jpan' % lang_script
        script = 'Jpan'
      if script not in supported_scripts:
        unsupported_scripts.add(script)
      used_lang_scripts[lang].add(script)

  if unsupported_scripts:
    print 'used scripts that are not supported: %s' % ', '.join(sorted(unsupported_scripts))

  known_langs = set(cldr_data.known_langs())
  for lang in lang_to_additional_script:
    if not lang in known_langs:
      print 'lang %s not in known langs' % lang
      known_langs.add(lang)

  for lang in known_langs:
    if lang in ['ryu', 'ain']:
      all_scripts = set(['Jpan'])
    else:
      all_scripts = set(cldr_data.lang_to_scripts(lang))

    # add additional scripts for lang
    if lang in lang_to_additional_script:
      script = lang_to_additional_script[lang]
      if script not in all_scripts:
        print 'cldr data does not have script %s for lang %s' % (script, lang)
        all_scripts.add(script)

    if not all_scripts & supported_scripts:
      print 'no supported scripts among %s for lang %s' % (all_scripts, lang)
      continue

    used_scripts = used_lang_scripts[lang]
    if not used_scripts:
      script = cldr_data.get_likely_script(lang)
      if script != 'Zzzz':
        used_scripts = set([script])

    unused_scripts = all_scripts - used_scripts
    lang_data[lang] = (used_scripts, unused_scripts)

  # Patch out langs whose sample data Noto doesn't support
  # A bunch of these resolve to the same sample.  Would be easier to check if I just had
  # sample names independent of language names, but then harder to remove the languages.
  for lang in ['abq', 'ady', 'aii-Cyrl', 'av', 'bua', 'chm']:
    if not lang in lang_data:
      print 'patched out lang %s not present' % lang
    else:
      print 'patch out lang %s' % lang
      del lang_data[lang]

  return lang_data


def get_lang_tag_to_family_ids(used_lang_data, script_to_family_ids):
  lang_tag_to_family_ids = collections.defaultdict(set)
  for lang in used_lang_data:
    used_scripts, unused_scripts = used_lang_data[lang]
    add_script = len(used_scripts) > 1
    default_script = iter(used_scripts).next() if len(used_scripts) == 1 else None
    for script in used_scripts:
      if not script in script_to_family_ids:
        print 'unsupported script %s for lang %s' % (script, lang)
      else:
        family_ids = script_to_family_ids[script]
        tag = lang + '-' + script if add_script else lang
        lang_tag_to_family_ids[tag].update(family_ids)
    add_script = add_script or len (used_scripts | unused_scripts) > 1
    for script in unused_scripts:
      if not script in script_to_family_ids:
        print 'unsupported unused script %s for lang %s' % (script, lang)
      else:
        family_ids = script_to_family_ids[script]
        tag = lang + '-' + script if add_script else lang
        lang_tag_to_family_ids[tag].update(family_ids)

  # Map thsese to Nastaliq
  for lang_tag in ['bal', 'hnd', 'hno', 'ks', 'lah', 'pa-Arab', 'skr', 'ur']:
    if not lang_tag in lang_tag_to_family_ids:
      print 'Map nastaliq: %s not found' % lang_tag
    else:
      lang_tag_to_family_ids[lang_tag].add('nastaliq-aran')

  # Kufi patches:
  # - Kufi is broken for Urdu Heh goal (issue #34)
  # - Kufi doesn't support all characters needed for Khowar
  # - Kufi doesn't support all characters needed for Kashmiri
  for lang_tag in ['ur', 'khw', 'ks', 'ks-Arab']:
    if not lang_tag in lang_tag_to_family_ids:
      print 'patch kufi: %s not found' % lang_tag
    else:
      lang_tag_to_family_ids[lang_tag] -= {'kufi-arab'}
      if not lang_tag_to_family_ids:
        print 'patched kufi: %s, no fonts remaining' % lang_tag
        del lang_tag_to_family_ids[lang_tag]
      else:
        print 'patched kufi: %s -> %s' % (lang_tag, lang_tag_to_family_ids[lang_tag])

  return lang_tag_to_family_ids


def get_region_to_family_ids(script_to_family_ids):
  region_to_family_ids = collections.defaultdict(set)
  for region in cldr_data.known_regions():
    if region == 'ZZ':
      continue
    if len(region) > 2:
      print 'skipping region %s' % region
      continue
    lang_scripts = cldr_data.region_to_lang_scripts(region)
    for lang_script in lang_scripts:
      lang, script = lang_script.split('-')
      if script == 'Kana':
        print 'remap %s to use Jpan script' % lang_script
        script = 'Jpan'
      if not script in script_to_family_ids:
        print 'unsupported script %s for lang %s in region %s' % (script, lang, region)
      else:
        families = script_to_family_ids[script]
        region_to_family_ids[region].update(families)
  return region_to_family_ids


def get_lang_tag_sort_order(lang_tags):
  """Return a sort order for lang_tags based on the english name, but clustering related
  languages."""
  def lang_key(lang_tag):
    name = cldr_data.get_english_language_name(lang_tag)
    if name.endswith (' script)'):
      ix = name.rfind('(') - 1
      script_sfx = ' ' + name[ix + 2: len(name) - 8]
      name = name[:ix]
    else:
      script_sfx = ''

    key = name
    for prefix in ['Ancient', 'Central', 'Eastern', 'Lower', 'Middle', 'North',
                   'Northern', 'Old', 'Southern', 'Southwestern', 'Upper',
                   'West', 'Western']:
      if name.startswith(prefix + ' '):
        key = name[len(prefix) + 1:] + ' ' + name[:len(prefix)]
        break

    for cluster in ['Arabic', 'French', 'Chinese', 'English', 'German', 'Hindi',
                    'Malay', 'Nahuatl', 'Tamazight', 'Thai']:
      if name.find(cluster) != -1:
        key = cluster + '-' + name
        break

    return key + script_sfx

  sorted_tags = list(lang_tags)
  sorted_tags.sort(key=lang_key)
  n = 0
  tag_order = {}
  for tag in sorted_tags:
    print '%10s: %s' % (tag, cldr_data.get_english_language_name(tag))
    tag_order[tag] = n
    n += 1
  return tag_order


def get_family_id_to_lang_tags(lang_tag_to_family_ids, families):
  family_id_to_lang_tags = {}
  for family_id in families:
    family_id_to_lang_tags[family_id] = set()
  for lang_tag, family_ids in lang_tag_to_family_ids.iteritems():
    for family_id in family_ids:
      family_id_to_lang_tags[family_id].add(lang_tag)
  return family_id_to_lang_tags


def get_family_id_to_regions(region_to_family_ids, families):
  family_id_to_regions = {}
  for family_id in families:
    family_id_to_regions[family_id] = set()
  for region, family_ids in region_to_family_ids.iteritems():
    for family_id in family_ids:
      family_id_to_regions[family_id].add(region)
  return family_id_to_regions


def get_charset_info(charset):
  """Returns an encoding of the charset as pairs of lengths of runs of chars to skip and
  chars to include.  Each length is written as length - 1 in hex-- except when length ==
  1, which is written as the empty string-- and separated from the next length by a comma.
  Thus successive commas indicate a length of 1, a 1 indicates a length of 2, and so on.
  Since the minimum representable length is 1, the base is -1 so that the first run (a
  skip) of 1 can be output as a comma to then start the first included character at 0 if
  need be.  Only as many pairs of values as are needed to encode the last run of included
  characters."""

  ranges = coverage.convert_set_to_ranges(charset)
  prev = -1
  range_list = []
  for start, end in ranges:
    range_len = start - 1 - prev
    if range_len > 0:
      range_list.append('%x' % range_len)
    else:
      range_list.append('')
    range_len = end - start
    if range_len > 0:
      range_list.append('%x' % range_len)
    else:
      range_list.append('')
    prev = end + 1
  return ','.join(range_list)


def get_exemplar(lang_scr):
  locl = lang_scr
  # don't use exemplars encoded without script if the requested script is not
  # the default
  _, script = lang_scr.split('-')
  while locl != 'root':
    for directory in ['common', 'seed', 'exemplars']:
      exemplar = get_exemplar_from_file(
          path.join(directory, 'main', locl.replace('-', '_') + '.xml'))
      if exemplar:
        return exemplar, 'ex-' + directory + '-' + locl
    locl = cldr_data.parent_locale(locl)
    if locl == 'root' or cldr_data.get_likely_subtags(locl)[1] != script:
      break
  return None, None


def get_sample_from_sample_file(lang_scr):
  filepath = path.join(SAMPLE_TEXT_DIR, lang_scr + '.txt')
  if path.exists(filepath):
    return unicode(open(filepath).read().strip(), 'UTF-8')
  return None


ATTRIBUTION_DATA = {}

def get_attribution(lang_scr):
  if not ATTRIBUTION_DATA:
    attribution_path = path.join(TOOLS_DIR, 'sample_texts', 'attributions.txt')
    with open(attribution_path, 'r') as f:
      data = f.readlines()
    for line in data:
      line = line.strip()
      if not line or line[0] == '#':
        continue
      tag, attrib = line.split(':')
      ATTRIBUTION_DATA[tag.strip()] = attrib.strip()
  try:
    return ATTRIBUTION_DATA[lang_scr]
  except KeyError:
    print 'no attribution for %s' % lang_scr
    return 'none'


EXEMPLAR_CUTOFF_SIZE = 50

def sample_text_from_exemplar(exemplar):
  exemplar = [c for c in exemplar
                if unicode_data.category(c[0])[0] in 'LNPS']
  exemplar = exemplar[:EXEMPLAR_CUTOFF_SIZE]
  return ' '.join(exemplar)


def get_sample_and_attrib(lang_scr):
  """Return a tuple of:
  - a short sample text string
  - an attribution key, one of
    UN: official UN translation, needs attribution
    other: not an official UN translation, needs non-attribution
    original: public domain translation, does not need attribution
    none: we have no attribution info on this, does not need attribution
  - source key"""
  assert '-' in lang_scr
  DEBUG = lang_scr.startswith('tab-')

  sample_text = get_sample_from_sample_file(lang_scr)
  if sample_text is not None:
    attr = get_attribution(lang_scr)
    src_key = 'txt-' + lang_scr
    return sample_text, attr, src_key

  exemplar, src_key = get_exemplar(lang_scr)
  if exemplar is not None:
    return sample_text_from_exemplar(exemplar), 'none', src_key

  _, script = lang_scr.split('-')
  src_key = 'und-' + script
  sample_text = get_sample_from_sample_file(src_key)
  if sample_text is not None:
    return sample_text, 'none', src_key

  print 'No sample for %s' % lang_scr
  return '', 'none', 'none'


def ensure_script(lang_tag):
  """If lang_tag has no script, use get_likely_script to add one.
  If that fails, return an empty tag."""
  if '-' in lang_tag:
    return lang_tag
  try:
    script = cldr_data.get_likely_script(lang_tag)
  except KeyError:
    print 'no likely script for lang %s' % lang_tag
    return ''
  return lang_tag + '-' + script


def get_family_id_to_default_lang_tag(family_id_to_lang_tags):
  """Return a mapping from family id to default lang tag, for families
  that have multiple lang tags.  This is based on likely subtags and
  the script of the family (Latn for LGC).
  """
  # TODO(dougfelt): this reintroduces language tags that we'd previously filtered
  # out.  We should not be doing this here.  Figure out a better way to handle this.

  family_id_to_default_lang_tag = {}
  for family_id, lang_tags in family_id_to_lang_tags.iteritems():
    parts = family_id.split('-')
    if len(parts) == 1:
      # 'sans' or 'serif'
      script = 'Latn'
    else:
      script = parts[1].capitalize()
    lang = cldr_data.get_likely_subtags('und-' + script)[0]
    # CLDR has no names for these, and two are collectives, so it's simpler to omit them.
    if script in ['Kthi', 'Khar', 'Brah']:
      print 'likely lang for %s is %s, replace with und' % (script, lang)
      lang = 'und'

    if lang == 'und':
      # special case
      if script == 'Latn':
        lang_tag = 'en'
      elif script == 'Aran':
        lang_tag = 'ur'
      else:
        lang_tag = 'und' + '-' + script
    elif lang not in lang_tags:
      lang_tag = lang + '-' + script
      if lang_tag not in lang_tags:
        print 'Akk, lang and lang_scr \'%s\' not listed for family %s' % (
            lang_tag, family_id)
    else:
      lang_tag = lang
    family_id_to_default_lang_tag[family_id] = lang_tag
  return family_id_to_default_lang_tag


def get_used_lang_tags(family_langs, default_langs):
  return set(family_langs) | set(default_langs)


def get_lang_tag_to_sample_data(used_lang_tags):
  """Return a mapping from lang tag to tuple of:
    - rtl
    - sample text
    - attribution
  """
  lang_tag_to_sample_data = {}
  for lang_tag in used_lang_tags:
    rtl = cldr_data.is_rtl(lang_tag)
    sample, attrib, src_key = get_sample_and_attrib(ensure_script(lang_tag))
    lang_tag_to_sample_data[lang_tag] = (rtl, sample, attrib, src_key)
  return lang_tag_to_sample_data


lat_long_data = {}

def read_lat_long_data():
  with open(path.join(LAT_LONG_DIR, 'countries.csv')) as lat_long_file:
    for row in csv.reader(lat_long_file):
      region, latitude, longitude, _ = row
      if region == 'country':
          continue  # Skip the header
      if not latitude:
          continue  # Empty latitude
      latitude = float(latitude)
      longitude = float(longitude)
      lat_long_data[region] = (latitude, longitude)

  # From the English Wikipedia and The World Factbook at
  # https://www.cia.gov/library/publications/the-world-factbook/fields/2011.html
  lat_long_data.update({
      'AC': (-7-56/60, -14-22/60),  # Ascension Island
      'AX': (60+7/60, 19+54/60),  # Åland Islands
      'BL': (17+54/60, -62-50/60),  # Saint Barthélemy
      'BQ': (12+11/60, -68-14/60),  # Caribbean Netherlands
      'CP': (10+18/60, -109-13/60),  # Clipperton Island
      'CW': (12+11/60, -69),  # Curaçao
      'DG': (7+18/60+48/3600, 72+24/60+40/3600),  # Diego Garcia
       # Ceuta and Melilla, using Ceuta
      'EA': (35+53/60+18/3600, -5-18/60-56/3600),
      'IC': (28.1, -15.4),  # Canary Islands
      'MF': (18+4/60+31/3600, -63-3/60-36/3600),  # Saint Martin
      'SS': (8, 30),  # South Sudan
      'SX': (18+3/60, -63-3/60),  # Sint Maarten
      'TA': (-37-7/60, -12-17/60),  # Tristan da Cunha
       # U.S. Outlying Islands, using Johnston Atoll
      'UM': (16+45/60, -169-31/60),
  })


def get_region_lat_lng_data(regions):
  if not lat_long_data:
    read_lat_long_data()
  return lat_long_data


# ==========================

def read_character_at(source, pointer):
    assert source[pointer] not in ' -{}'
    if source[pointer] == '\\':
        if source[pointer+1] == 'u':
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

    return_list = []
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
            return_list.append(multi_char)
            pointer = mc_ptr+1
        elif exstr[pointer] == '-':
            previous = return_list[-1]
            assert len(previous) == 1  # can't have ranges with strings
            previous = ord(previous)

            pointer, last = read_character_at(exstr, pointer+1)
            assert last not in [' ', '\\', '{', '}', '-']
            last = ord(last)
            return_list += [unichr(code) for code in range(previous+1, last+1)]
        else:
            pointer, char = read_character_at(exstr, pointer)
            return_list.append(char)

    return return_list


exemplar_from_file_cache = {}

def get_exemplar_from_file(cldr_file_path):
    try:
        return exemplar_from_file_cache[cldr_file_path]
    except KeyError:
        pass

    data_file = path.join(CLDR_DIR, cldr_file_path)
    try:
        root = ElementTree.parse(data_file).getroot()
    except IOError:
        exemplar_from_file_cache[cldr_file_path] = None
        return None
    for tag in root.iter('exemplarCharacters'):
        if 'type' in tag.attrib:
            continue
        exemplar_from_file_cache[cldr_file_path] = exemplar_string_to_list(
            tag.text)
        return exemplar_from_file_cache[cldr_file_path]
    return None


def get_font_family_name(font_file):
    font = ttLib.TTFont(font_file)
    name_record = font_data.get_name_records(font)
    try:
      name = name_record[16]
    except KeyError:
      name = name_record[1]
      if name.endswith('Regular'):
        name = name.rsplit(' ', 1)[0]
    return name


# ==========================

def get_css_generic_family(family):
    if family in {'Noto Naskh', 'Noto Serif', 'Tinos'}:
        return 'serif'
    if family in {'Arimo', 'Noto Kufi', 'Noto Sans'}:
        return 'sans-serif'
    if family == 'Cousine':
        return 'monospace'
    return None


CSS_WEIGHT_MAPPING = {
    'Thin': 250,
    'Light': 300,
    'DemiLight': 350,
    'Regular': 400,
    'Medium': 500,
    'Bold': 700,
    'Black': 900,
}

def css_weight(weight_string):
    return CSS_WEIGHT_MAPPING[weight_string]


CSS_WEIGHT_TO_STRING = {s:w for w, s in CSS_WEIGHT_MAPPING.items()}

def css_weight_to_string(weight):
    return CSS_WEIGHT_TO_STRING[weight]


def css_style(style_value):
    if style_value is None:
        return 'normal'
    else:
        assert style_value == 'Italic'
        return 'italic'


class WebGen(object):

  def __init__(self, target, clean, pretty_json):
    self.target = target
    self.clean = clean
    self.pretty_json = pretty_json

    self.pkgs = path.join(target, 'pkgs')
    self.fonts = path.join(target, 'fonts')
    self.css = path.join(target, 'css')
    self.samples = path.join(target, 'samples')
    self.data = path.join(target, 'data')

  def clean_target_dir(self):
    if path.exists(self.target):
        print 'Removing the old website directory from %s...' % self.target
        shutil.rmtree(self.target)

  def write_json(self, obj, name):
    filepath = path.join(self.data, name + '.json')
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
      json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))

    if self.pretty_json:
      filepath = path.join(self.data, 'pretty', name + '-pretty.json')
      with codecs.open(filepath, 'w', encoding='UTF-8') as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ': '),
                       indent=4)

  def ensure_target_dirs_exist(self):
    def mkdirs(p):
      if not path.exists(p):
        os.makedirs(p)
    mkdirs(self.target)
    mkdirs(self.pkgs)
    mkdirs(self.css)
    mkdirs(self.fonts)
    mkdirs(self.samples)
    mkdirs(self.data)
    if self.pretty_json:
      mkdirs(path.join(self.data, 'pretty'))

  def create_zip(self, name, fonts):
    zipname = name + '.zip'
    zippath = path.join(self.pkgs, zipname)
    if path.isfile(zippath):
      print('Assuming %s is valid.' % zipname)
    else:
      pairs = []
      license_types = set()
      for font in fonts:
        pairs.append((font.filepath, path.basename(font.filepath)))
        license_types.add(font.license_type)
      if 'apache' in license_types:
        pairs.append((APACHE_LICENSE_LOC, 'LICENSE.txt'))
      if 'sil' in license_types:
        pairs.append((SIL_LICENSE_LOC, 'LICENSE_CJK.txt'))
      tool_utils.generate_zip_with_7za_from_filepairs(pairs, zippath)
      print 'Created zip %s' % zippath
    return os.stat(zippath).st_size

  def build_family_zips(self, key, family):
    zip_name = family.name.replace(' ', '')
    hinted_size = 0
    unhinted_size = 0
    if family.hinted_members:
      hinted_size = self.create_zip(zip_name + '-hinted', family.hinted_members)
    if family.unhinted_members:
      unhinted_size = self.create_zip(zip_name + '-unhinted', family.unhinted_members)
    return zip_name, hinted_size, unhinted_size

  def build_zips(self, families):
    zip_info = {}
    for key, family_data in families.iteritems():
      zip_info[key] = self.build_family_zips(key, family_data)
    return zip_info

  def build_universal_zips(self, families):
    hinted_fonts = []
    unhinted_fonts = []
    for family_data in families.values():
      hinted_fonts.extend(family_data.hinted_members or family_data.unhinted_members)
      unhinted_fonts.extend(family_data.unhinted_members or family_data.hinted_members)
    hinted_size = self.create_zip('Noto-hinted', hinted_fonts)
    unhinted_size = self.create_zip('Noto-unhinted', unhinted_fonts)
    return 'Noto', hinted_size, unhinted_size

  def copy_font(self, fontpath):
    basename = path.basename(fontpath)
    dst = path.join(self.fonts, basename)
    shutil.copy(fontpath, dst)
    return basename

  def build_family_css(self, key, family):
    fonts = family.hinted_members or family.unhinted_members
    css_name = key + '.css'
    csspath = path.join(self.css, css_name)
    font_size = 0
    with open(csspath, 'w') as css_file:
      for font in fonts:
        font_name = self.copy_font(font.filepath)
        font_size = max(font_size, os.stat(font.filepath).st_size)
        css_file.write(
          '@font-face {\n'
          '  font-family: "%s";\n'
          '  font-weight: %d;\n'
          '  font-style: %s;\n'
          '  src: url(../fonts/%s) format("truetype");\n'
          '}\n' % (
              family.name,
              css_weight(font.weight),
              css_style(font.slope),
              font_name)
          )
    return font_size

  def build_css(self, families):
    css_info = {}
    for key, family_data in families.iteritems():
      css_info[key] = self.build_family_css(key, family_data)
    return css_info

  def build_data_json(self, families, family_zip_info, universal_zip_info,
                      family_id_to_lang_tags, family_id_to_regions,
                      lang_tag_to_family_ids, region_to_family_ids):

    data_obj = collections.OrderedDict()
    families_obj = collections.OrderedDict()
    # Sort families by English name, except 'Noto Sans' and 'Noto Serif' come first
    family_ids = [family_id for family_id in families if family_id != 'sans' and family_id != 'serif']
    family_ids = sorted(family_ids, key=lambda f: families[f].name)
    sorted_ids = ['sans', 'serif']
    sorted_ids.extend(family_ids)
    for k in sorted_ids:
      family = families[k]
      family_obj = {}
      family_obj['name'] = family.name

      name, hinted_size, unhinted_size = family_zip_info[k]
      pkg_obj = collections.OrderedDict()
      if hinted_size:
        pkg_obj['hinted'] = hinted_size
      if unhinted_size:
        pkg_obj['unhinted'] = unhinted_size
      family_obj['pkgSize'] = pkg_obj

      family_obj['fonts'] = len(family.hinted_members or family.unhinted_members)
      family_obj['langs'] = len(family_id_to_lang_tags[k])
      family_obj['regions'] = len(family_id_to_regions[k])

      families_obj[k] = family_obj
    data_obj['family'] = families_obj

    data_obj['familyOrder'] = sorted_ids

    langs_obj = collections.OrderedDict()
    # Dont list 'und-' lang tags, these are for default samples and not listed in the UI
    lang_tags = [lang for lang in lang_tag_to_family_ids if not lang.startswith('und-')]

    lang_tags = sorted(lang_tags, key=lambda l: cldr_data.get_english_language_name(l))
    for lang in lang_tags:
      lang_obj = collections.OrderedDict()
      english_name = cldr_data.get_english_language_name(lang)
      lang_obj['name'] = english_name
      lang_obj['families'] = sorted(lang_tag_to_family_ids[lang])
      native_name = cldr_data.get_native_language_name(lang)
      if native_name and native_name != english_name:
        lang_obj['keywords'] = [native_name]
      langs_obj[lang] = lang_obj
    data_obj['lang'] = langs_obj

    regions_obj = collections.OrderedDict()
    for region in sorted(region_to_family_ids,
                         key=lambda r: cldr_data.get_english_region_name(r)):
      region_obj = collections.OrderedDict()
      region_obj['families'] = sorted(region_to_family_ids[region])
      region_obj['keywords'] = [cldr_data.get_english_region_name(region)]
      regions_obj[region] = region_obj
    data_obj['region'] = regions_obj

    pkg_obj = collections.OrderedDict()
    pkg_obj['hinted'] = universal_zip_info[1]
    pkg_obj['unhinted'] = universal_zip_info[2]
    data_obj['pkgSize'] = pkg_obj

    self.write_json(data_obj, 'data')

  def build_family_json(self, family_id, family, lang_tags, regions, css_info,
                        default_lang_tag):
    family_obj = collections.OrderedDict()
    category = get_css_generic_family(family.name)
    if category:
      family_obj['category'] = category
    if lang_tags:
       # maintain provided sort order
      family_obj['langs'] = lang_tags
    if default_lang_tag:
      family_obj['defaultLang'] = default_lang_tag
    if regions:
      family_obj['regions'] = sorted(regions)
    if family.charset:
      family_obj['ranges'] = get_charset_info(family.charset)
    fonts_obj = []
    members = []
    members.extend(family.hinted_members or family.unhinted_members)
    members.sort(key=lambda f: str(css_weight(f.weight)) + '-' +
                                   ('b' if css_style(f.slope) == 'italic' else 'a'))
    for font in members:
      weight_style = collections.OrderedDict()
      weight_style['weight'] = css_weight(font.weight)
      weight_style['style'] = css_style(font.slope)
      fonts_obj.append(weight_style)
    family_obj['fonts'] = fonts_obj
    family_obj['fontSize'] = css_info
    self.write_json(family_obj, family_id)

  def build_families_json(self, families, family_id_to_lang_tags,
                          family_id_to_default_lang_tag,
                          family_id_to_regions, family_css_info,
                          lang_sort_order):
    for k, v in families.iteritems():
      lang_tags = list(family_id_to_lang_tags[k])
      lang_tags.sort(key=lambda l: lang_sort_order[l])
      default_lang_tag = family_id_to_default_lang_tag[k]
      regions = family_id_to_regions[k]
      css_info = family_css_info[k]
      self.build_family_json(k, v, lang_tags, regions, css_info, default_lang_tag)

  def build_misc_json(self, sample_data, region_data):
    lang_info = sample_data
    meta_obj = collections.OrderedDict()

    langs_obj = collections.OrderedDict()
    for lang in sorted(lang_info):
      rtl, sample, attrib, sample_key = lang_info[lang]
      lang_obj = collections.OrderedDict()
      lang_obj['sample'] = sample
      lang_obj['attrib'] = attrib
      if rtl:
        lang_obj['rtl'] = rtl
      langs_obj[lang] = lang_obj
    meta_obj['lang'] = langs_obj

    # don't need much accuracy for our map UI use case
    def trim_decimals(num):
      return float('%1.2f' % num)

    regions_obj = collections.OrderedDict()
    for region in sorted(region_data):
      lat, lng = region_data[region]
      lat = trim_decimals(lat)
      lng = trim_decimals(lng)
      region_obj = collections.OrderedDict()
      region_obj['lat'] = lat
      region_obj['lng'] = lng
      regions_obj[region] = region_obj

    meta_obj['region'] = regions_obj

    self.write_json(meta_obj, 'meta')

  def build_family_images(self, family, lang_tag, is_rtl, sample_text, attrib):
    family_id = family.rep_member.key
    is_cjk = family.rep_member.is_cjk
    for font in family.hinted_members or family.unhinted_members:
      weight = css_weight(font.weight)
      style = css_style(font.slope)
      image_file_name = '%s_%s_%d_%s.svg' % (family_id, lang_tag, weight, style)
      if is_cjk:
        family_suffix = ' ' + font.weight
      else:
        family_suffix = ''
      image_location = path.join(self.samples, image_file_name)
      if path.isfile(image_location):
        # Don't rebuild images when continuing.
        print "Continue: assuming image file '%s' is valid." % image_location
        continue
      print 'create %s' % image_file_name
      create_image.create_svg(
          sample_text,
          image_location,
          family=family.name + family_suffix,
          language=lang_tag,
          rtl=is_rtl,
          width=685,
          # text is coming out bigger than we expect, perhaps this is why?
          font_size=int(20 * (72.0/96.0)),
          line_spacing=int(32 * (72.0/96.0)),
          weight=weight,
          style=style)

  def build_images(self, families, family_id_to_lang_tags, family_id_to_default_lang_tag,
                   lang_tag_to_sample_info):
    for family_id, family in families.iteritems():
      print 'Generating images for %s...' % family.name
      default_lang = family_id_to_default_lang_tag[family_id]
      lang_tags = family_id_to_lang_tags[family_id]
      if not default_lang in lang_tags:
        print 'build extra default image for lang %s' % default_lang
        lang_tags = list(lang_tags)
        lang_tags.append(default_lang)
      for lang_tag in lang_tags:
        is_rtl, sample_text, attrib, sample_key = lang_tag_to_sample_info[lang_tag]
        self.build_family_images(family, lang_tag, is_rtl, sample_text, attrib)

  def build_ttc_zips(self):
    """Generate zipped versions of the ttc files and put in pkgs directory."""

    # The font family code skips the ttc files, but we want them in the
    # package directory. Instead of mucking with the family code to add the ttcs
    # and then exclude them from the other handling, we'll just handle them
    # separately.
    # For now at least, the only .ttc fonts are the CJK fonts

    filenames = [path.basename(f) for f in os.listdir(CJK_DIR) if f.endswith('.ttc')]
    for filename in filenames:
      zip_basename = filename + '.zip'
      zip_path = path.join(self.pkgs, zip_basename)
      if path.isfile(zip_path):
          print("Continue: assuming built %s is valid." % zip_basename)
          continue
      oldsize = os.stat(path.join(CJK_DIR, filename)).st_size
      pairs = [(path.join(CJK_DIR, filename), filename),
               (SIL_LICENSE_LOC, 'LICENSE_CJK.txt')]
      tool_utils.generate_zip_with_7za_from_filepairs(pairs, zip_path)
      newsize = os.stat(zip_path).st_size
      print "Wrote " + zip_path
      print 'Compressed from {0:,}B to {1:,}B.'.format(oldsize, newsize)

  def generate(self):
    if self.clean:
      self.clean_target_dir()
    self.ensure_target_dirs_exist()

    # debug/print
    # ['families', 'script_to_family_ids', 'used_lang_data',
    #  'family_id_to_lang_tags', 'family_id_to_default_lang_tag']
    debug = frozenset([])

    fonts = get_noto_fonts()
    families = get_families(fonts)

    if 'families' in debug:
      print '\nfamilies'
      for family_id, family in sorted(families.iteritems()):
        print family_id, family.rep_member.script

    script_to_family_ids = get_script_to_family_ids(families)
    if 'script_to_family_ids' in debug:
      print '\nscript to family ids'
      for script, family_ids in sorted(script_to_family_ids.iteritems()):
        print script, family_ids

    supported_scripts = set(script_to_family_ids.keys())
    used_lang_data = get_used_lang_data(supported_scripts)
    if 'used_lang_data' in debug:
      print '\nused lang data'
      for lang, data in sorted(used_lang_data.iteritems()):
        used = ', '.join(data[0])
        unused = ', '.join(data[1])
        if unused:
          unused = '(' + unused + ')'
          if used:
            unused = ' ' + unused
        print '%s: %s%s' % (lang, used, unused)

    langs_to_delete = []
    for lang in used_lang_data.keys():
      if not cldr_data.get_english_language_name(lang):
        langs_to_delete.append(lang)
    if langs_to_delete:
      print 'deleting languages with no english name: %s' % langs_to_delete
      for lang in langs_to_delete:
        del used_lang_data[lang]

    lang_tag_to_family_ids = get_lang_tag_to_family_ids(used_lang_data, script_to_family_ids)

    region_to_family_ids = get_region_to_family_ids(script_to_family_ids)

    family_id_to_lang_tags = get_family_id_to_lang_tags(lang_tag_to_family_ids, families)
    if 'family_id_to_lang_tags' in debug:
      print '\nfamily id to lang tags'
      for family_id, lang_tags in sorted(family_id_to_lang_tags.iteritems()):
        print '%s: %s' % (family_id, ','.join(sorted(lang_tags)))

    family_id_to_regions = get_family_id_to_regions(region_to_family_ids, families)

    family_id_to_default_lang_tag = get_family_id_to_default_lang_tag(
        family_id_to_lang_tags)
    if 'family_id_to_default_lang_tag' in debug:
      print '\nfamily id to default lang tag'
      for family_id, lang_tag in family_id_to_default_lang_tag.iteritems():
        print family_id, lang_tag

    used_lang_tags = get_used_lang_tags(
        lang_tag_to_family_ids.keys(), family_id_to_default_lang_tag.values())
    lang_tag_to_sample_data = get_lang_tag_to_sample_data(used_lang_tags)

    # find the samples that can't be displayed.
    tested_keys = set()
    failed_keys = set()
    family_langs_to_remove = {}
    for lang_tag in sorted(lang_tag_to_sample_data):
      sample_info = lang_tag_to_sample_data[lang_tag]
      sample = sample_info[1]
      sample_key = sample_info[3]

      for family_id in sorted(lang_tag_to_family_ids[lang_tag]):
        full_key = sample_key + '-' + family_id
        if full_key in tested_keys:
          if full_key in failed_keys:
            print 'failed sample %s lang %s' % (full_key, lang_tag)
            if family_id not in family_langs_to_remove:
              family_langs_to_remove[family_id] = set()
            family_langs_to_remove[family_id].add(lang_tag)
          continue

        failed_cps = set()
        tested_keys.add(full_key)
        charset = families[family_id].charset
        for cp in sample:
          if ord(cp) in [0xa, 0x28, 0x29, 0x2c, 0x2d, 0x2e, 0x3b, 0x5b, 0x5d, 0x2010]:
            continue
          if ord(cp) not in charset:
            failed_cps.add(ord(cp))
        if failed_cps:
          print 'sample %s cannot be displayed in %s (lang %s):\n  %s' % (
              sample_key, family_id, lang_tag,
              '\n  '.join('%04x (%s)' % (cp, unichr(cp)) for cp in sorted(failed_cps)))
          failed_keys.add(full_key)
          if family_id not in family_langs_to_remove:
            family_langs_to_remove[family_id] = set()
          family_langs_to_remove[family_id].add(lang_tag)

    for family_id in sorted(family_langs_to_remove):
      langs_to_remove = family_langs_to_remove[family_id]
      print 'remove from %s: %s' % (family_id, ','.join(sorted(langs_to_remove)))

      family_id_to_lang_tags[family_id] -= langs_to_remove
      default_lang_tag = family_id_to_default_lang_tag[family_id]
      if default_lang_tag in langs_to_remove:
        print '!removing default lang tag %s for family %s' % (
            default_lang_tag, family_id)
      for lang in langs_to_remove:
        lang_tag_to_family_ids[lang] -= set([family_id])

    region_data = get_region_lat_lng_data(region_to_family_ids.keys())

    lang_tag_sort_order = get_lang_tag_sort_order(lang_tag_to_family_ids.keys())

    # build outputs
    family_zip_info = self.build_zips(families)
    universal_zip_info = self.build_universal_zips(families)
    family_css_info = self.build_css(families)

    self.build_data_json(families, family_zip_info, universal_zip_info,
                         family_id_to_lang_tags, family_id_to_regions,
                         lang_tag_to_family_ids, region_to_family_ids)

    self.build_families_json(families, family_id_to_lang_tags,
                             family_id_to_default_lang_tag,
                             family_id_to_regions, family_css_info,
                             lang_tag_sort_order)

    self.build_misc_json(lang_tag_to_sample_data, region_data)

    self.build_images(families, family_id_to_lang_tags,
                      family_id_to_default_lang_tag, lang_tag_to_sample_data)

    # build outputs not used by the json but linked to from the web page
    self.build_ttc_zips()


def main():
    """Outputs data files for the noto website."""

    default_target = '/tmp/website2'

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clean',  help='clean target directory',
                        action='store_true')
    parser.add_argument('-t', '--target', help='target dir, default %s' %
                        default_target, default=default_target, metavar='dir')
    parser.add_argument('-pj', '--pretty_json', help='generate additional pretty json',
                        action='store_true')
    args = parser.parse_args();

    webgen = WebGen(args.target, args.clean, args.pretty_json)
    webgen.generate()


if __name__ == '__main__':
    locale.setlocale(locale.LC_COLLATE, 'en_US.UTF-8')
    main()
