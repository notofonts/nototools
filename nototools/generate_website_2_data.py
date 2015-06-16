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
  if not match:
    return None

  family, mono, script, variant, weight, slope, fmt = match.groups()

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
                filename == 'NotoNastaliqUrduDraft.ttf' or
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

  DEBUG_LANGS = ['tab', 'yrk', 'xum', 'ude', 'mro', 'syi',
                 'lzh', 'ryu', 'syl', 'ain', 'pra', 'bh']

  # we rely on the lang to script mapping, and its a problem if we
  # can map scripts to langs and not have the inverse map, so let's
  # catch those.
  default_lang_to_script = {}
  for script in supported_scripts:
    lang = cldr_data.get_likely_subtags('und-' + script)[0]
    if lang != 'und':
      default_lang_to_script[lang] = script
      if lang in DEBUG_LANGS:
        print 'likely subtags: lang %s has likely script %s' % (lang, script)

  unsupported_scripts = set()
  lang_data = {}
  used_lang_scripts = collections.defaultdict(set)
  for region in cldr_data.known_regions():
    if region == 'ZZ':
      continue
    lang_scripts = cldr_data.region_to_lang_scripts(region)
    if not lang_scripts:
      print 'region %s has no lang_script info' % region
    else:
      for lang_script in lang_scripts:
        lang, script = lang_script.split('-')
        if script == 'Kana':
          print 'remap %s to use Jpan' % lang_script
          script = 'Jpan'
        if lang in DEBUG_LANGS:
          print 'region lang_scr: lang %s has script %s' % (lang, script)
        if script not in supported_scripts:
          if script not in unsupported_scripts:
            print 'used script %s is not supported' % script
            unsupported_scripts.add(script)
        used_lang_scripts[lang].add(script)

  for lang in cldr_data.known_langs():
    all_scripts = set(cldr_data.lang_to_scripts(lang))
    if lang in DEBUG_LANGS:
      print 'known lang_scr: lang %s has script %s' % (lang, all_scripts)
    old_all_scripts = set(all_scripts)

    all_scripts &= supported_scripts
    if lang in ['ryu', 'ain']:
      all_scripts.add('Jpan')

    # sanity check
    if lang in default_lang_to_script:
      script = default_lang_to_script[lang]
      if script not in all_scripts:
        print 'cldr data does not have script %s for lang %s' % (script, lang)
        all_scripts.add(script)

    if not all_scripts:
      print 'no supported scripts among %s for lang %s' % (old_all_scripts, lang)
      continue

    used_scripts = used_lang_scripts[lang]
    if not used_scripts:
      script = cldr_data.get_likely_script(lang)
      used_scripts = set([script])

    unused_scripts = all_scripts - used_scripts
    lang_data[lang] = (used_scripts, unused_scripts)

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
        tag = lang + '-' + script if add_script else leng
        lang_tag_to_family_ids[tag].update(family_ids)

  return lang_tag_to_family_ids


def get_region_to_family_ids(script_to_family_ids):
  region_to_family_ids = collections.defaultdict(set)
  for region in cldr_data.known_regions():
    if region == 'ZZ':
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
  while locl != 'root':
    for directory in ['common', 'seed', 'exemplars']:
      exemplar = get_exemplar_from_file(
          path.join(directory, 'main', locl.replace('-', '_') + '.xml'))
      if exemplar:
        return exemplar
    locl = cldr_data.parent_locale(locl)
  return None


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
    none: we have no attribution info on this, does not need attribution"""
  assert '-' in lang_scr

  sample_text = get_sample_from_sample_file(lang_scr)
  if sample_text is not None:
    attr = get_attribution(lang_scr)
    return sample_text, attr

  exemplar = get_exemplar(lang_scr)
  if exemplar is not None:
    return sample_text_from_exemplar(exemplar), 'none'

  _, script = lang_scr.split('-')
  sample_text = get_sample_from_sample_file('und-' + script)
  if sample_text is not None:
    return sample_text, 'none'

  print 'No sample for %s' % lang_scr
  return '', 'none'


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
  family_id_to_default_lang_tag = {}
  for family_id, lang_tags in family_id_to_lang_tags.iteritems():
    parts = family_id.split('-')
    if len(parts) == 1:
      # 'sans' or 'serif'
      script = 'Latn'
    else:
      script = parts[1].capitalize()
    lang = cldr_data.get_likely_subtags('und-' + script)[0]
    if lang == 'und':
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
    sample, attrib = get_sample_and_attrib(ensure_script(lang_tag))
    lang_tag_to_sample_data[lang_tag] = (rtl, sample, attrib)
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


def sorted_langs(langs):
  return sorted(
    set(langs),
    key=lambda code: locale.strxfrm(
        get_english_language_name(code).encode('UTF-8')))


all_used_lang_scrs = set()

def create_regions_object():
    if not lat_long_data:
        read_lat_long_data()
    regions = {}
    for territory in territory_info:
        region_obj = {}
        region_obj['name'] = english_territory_name[territory]
        region_obj['lat'], region_obj['lng'] = lat_long_data[territory]
        region_obj['langs'] = sorted_langs(territory_info[territory])
        all_used_lang_scrs.update(territory_info[territory])
        regions[territory] = region_obj

    return regions


def charset_supports_text(charset, text):
    if charset is NotImplemented:
        return False
    needed_codepoints = {ord(char) for char in set(text)}
    return needed_codepoints <= charset


family_to_langs = collections.defaultdict(set)

def create_langs_object():
    langs = {}
    for lang_scr in sorted(set(written_in_scripts) | all_used_lang_scrs):
        lang_object = {}
        if '-' in lang_scr:
            language, script = lang_scr.split('-')
        else:
            language = lang_scr
            try:
                script = find_likely_script(language)
            except KeyError:
                print "no likely script for %s" % language
                continue

        lang_object['name'] = get_english_language_name(lang_scr)
        native_name = get_native_language_name(lang_scr)
        if native_name is not None:
            lang_object['nameNative'] = native_name

        lang_object['rtl'] = is_script_rtl(script)

        if script == 'Kana':
            script = 'Jpan'

        if script not in supported_scripts:
            # Scripts we don't have fonts for yet
            print('No font supports the %s script (%s) needed for the %s language.'
                  % (english_script_name[script], script, lang_object['name']))
            assert script in {
                'Bass',  # Bassa Vah
                'Lina',  # Linear A
                'Mani',  # Manichaean
                'Merc',  # Meroitic Cursive
                'Narb',  # Old North Arabian
                'Orya',  # Oriya
                'Plrd',  # Miao
                'Sora',  # Sora Sompeng
                'Thaa',  # Thaana
                'Tibt',  # Tibetan
            }

            lang_object['families'] = []
        else:
            sample_text = get_sample_text(language, script)
            lang_object['sample'] = sample_text

            if script in {'Latn', 'Grek', 'Cyrl'}:
                query_script = ''
            else:
                query_script = script

            # FIXME(roozbeh): Figure out if the language is actually supported
            # by the font + Noto LGC. If it's not, don't claim support.
            fonts = [font for font in fonts if font.script == query_script]

            # For certain languages of Pakistan, add Nastaliq font
            if lang_scr in {'bal', 'hnd', 'hno', 'ks-Arab', 'lah',
                            'pa-Arab', 'skr', 'ur'}:
                fonts += [font for font in fonts if font.script == 'Aran']

            family_keys = set([font.key for font in fonts])

            lang_object['families'] = sorted(family_keys)
            for family in family_keys:
                family_to_langs[family].add(lang_scr)

        langs[lang_scr] = lang_object
    return langs


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


def charset_to_ranges(font_charset):
    # Ignore basic common characters
    charset = font_charset - {0x00, 0x0D, 0x20, 0xA0, 0xFEFF}
    ranges = coverage.convert_set_to_ranges(charset)

    output_list = []
    for start, end in ranges:
        output_list.append(('%04X' % start, '%04X' % end))
    return output_list


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


def fonts_are_basically_the_same(font1, font2):
    """Returns true if the fonts are the same, except perhaps hint or platform.
    """
    return (font1.family == font2.family and
            font1.script == font2.script and
            font1.variant == font2.variant and
            font1.weight == font2.weight and
            font1.style == font2.style)


def compress_png(pngpath):
    subprocess.call(['optipng', '-o7', '-quiet', pngpath])


def compress(filepath, compress_function):
    print 'Compressing %s.' % filepath
    oldsize = os.stat(filepath).st_size
    compress_function(filepath)
    newsize = os.stat(filepath).st_size
    print 'Compressed from {0:,}B to {1:,}B.'.format(oldsize, newsize)


zip_contents_cache = {}

def create_zip(major_name, target_platform, fonts):
    # Make sure no file name repeats
    assert len({path.basename(font.filepath) for font in fonts}) == len(fonts)

    all_hint_statuses = {font.hint_status for font in fonts}
    if len(all_hint_statuses) == 1:
        hint_status = list(all_hint_statuses)[0]
    else:
        hint_status = 'various'

    if target_platform == 'other':
        if hint_status == 'various':
            # This may only be the comprehensive package
            assert len(fonts) > 50
            suffix = ''
        elif hint_status == 'unhinted':
            suffix = '-unhinted'
        else:  # hint_status == 'hinted'
            suffix = '-hinted'
    elif target_platform == 'windows':
        if hint_status in ['various', 'hinted']:
            if 'windows' in {font.platform for font in fonts}:
                suffix = '-windows'
            else:
                suffix = '-hinted'
        else:  # hint_status == 'unhinted':
            suffix = '-unhinted'
    else:  # target_platform == 'linux'
        if len(fonts) > 50 or hint_status in ['various', 'hinted']:
            suffix = '-hinted'
        else:
            suffix = '-unhinted'

    zip_basename = '%s%s.zip' % (major_name, suffix)

    zippath = path.join(OUTPUT_DIR, 'pkgs', zip_basename)
    frozen_fonts = frozenset(fonts)
    if path.isfile(zippath):  # Skip if the file already exists
        # When continuing, we assume that if it exists, it is good
        if zip_basename not in zip_contents_cache:
            print("Continue: assuming built %s is valid" % zip_basename)
            zip_contents_cache[zip_basename] = frozen_fonts
        else:
            assert zip_contents_cache[zip_basename] == frozen_fonts
        return zip_basename
    else:
        assert frozen_fonts not in zip_contents_cache.values()
        zip_contents_cache[zip_basename] = frozen_fonts
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
    return zip_basename


def copy_font(source_file):
    source_dir, source_basename = path.split(source_file)
    target_dir = path.join(OUTPUT_DIR, 'fonts')
    if source_dir.endswith('/hinted'):
        target_dir = path.join(target_dir, 'hinted')
    shutil.copy(source_file, path.join(OUTPUT_DIR, target_dir))
    return '../fonts/' + source_basename


def create_css(key, family_name, fonts):
    csspath = path.join(OUTPUT_DIR, 'css', 'fonts', key + '.css')
    with open(csspath, 'w') as css_file:
        for font in fonts:
            font_url = copy_font(font.filepath)
            css_file.write(
                '@font-face {\n'
                '  font-family: "%s";\n'
                '  font-weight: %d;\n'
                '  font-style: %s;\n'
                '  src: url(%s) format("truetype");\n'
                '}\n' % (
                    family_name,
                    css_weight(font.weight),
                    css_style(font.slope),
                    font_url)
            )
    return '%s.css' % key


def create_families_object(target_platform):
    all_keys = set([font.key for font in all_fonts])
    families = {}
    all_font_files = set()
    for key in all_keys:
        family_object = {}
        members = {font for font in all_fonts
                   if font.key == key and font.variant != 'UI'
                                      and font.filepath.endswith('tf')}

        if not members:
            mbrs = {font for font in all_fonts if font.key == key}
            raise ValueError("no members for %s from %s" % (key, [f.filepath for f in mbrs]))

        members_to_drop = set()
        for font in members:
            if font.platform == target_platform:
                # If there are any members matching the target platform, they
                # take priority: drop alternatives
                members_to_drop.update(
                    {alt for alt in members
                     if fonts_are_basically_the_same(font, alt) and
                        font.platform != alt.platform})
            elif font.platform is not None:
                # This is a font for another platform
                members_to_drop.add(font)
        members -= members_to_drop

        if target_platform in ['windows', 'linux']:
            desired_hint_status = 'hinted'
        else:
            desired_hint_status = 'unhinted'

        # If there are any members matching the desired hint status, they take
        # priority: drop alternatives
        members_to_drop = set()
        for font in members:
            if font.hint_status == desired_hint_status:
                members_to_drop.update(
                    {alt for alt in members
                     if fonts_are_basically_the_same(font, alt) and
                        font.hint_status != alt.hint_status})
        members -= members_to_drop

        all_font_files |= members

        rep_members = {font for font in members
                        if font.weight == 'Regular' and font.style is None}

        if len(rep_members) != 1:
            raise ValueError("Do not have a single regular font (%s) for key: %s (from %s)." %
                             (len(rep_members), key, [f.filepath for f in members]))
        rep_member = rep_members.pop()

        font_family_name = get_font_family_name(rep_member.filepath)
        if font_family_name.endswith('Regular'):
            font_family_name = font_family_name.rsplit(' ', 1)[0]
        family_object['name'] = font_family_name

        family_object['pkg'] = create_zip(
            font_family_name.replace(' ', ''), target_platform, members)

        family_object['langs'] = sorted_langs(family_to_langs[rep_member.key])

        family_object['category'] = get_css_generic_family(rep_member.family)
        family_object['css'] = create_css(key, font_family_name, members)
        family_object['ranges'] = charset_to_ranges(rep_member.charset)

        font_list = []
        for font in members:
            font_list.append({
                'style': css_style(font.style),
                'weight': css_weight(font.weight),
            })
        if len(font_list) not in [1, 2, 4, 7]:
            print key, font_list
        assert len(font_list) in [1, 2, 4, 7]
        family_object['fonts'] = font_list

        families[key] = family_object
    return families, all_font_files


def generate_ttc_zips_with_7za():
    """Generate zipped versions of the ttc files and put in pkgs directory."""

    # The font family code skips the ttc files, but we want them in the
    # package directory. Instead of mucking with the family code to add the ttcs
    # and then exclude them from the other handling, we'll just handle them
    # separately.
    # For now at least, the only .ttc fonts are the CJK fonts

    pkg_dir = path.join(OUTPUT_DIR, 'pkgs')
    tool_utils.ensure_dir_exists(pkg_dir)
    filenames = [path.basename(f) for f in os.listdir(CJK_DIR) if f.endswith('.ttc')]
    for filename in filenames:
        zip_basename = filename + '.zip'
        zip_path = path.join(pkg_dir, zip_basename)
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


def generate_sample_images(data_object):
    image_dir = path.join(OUTPUT_DIR, 'images', 'samples')
    for family_key in data_object['family']:
        family_obj = data_object['family'][family_key]
        font_family_name = family_obj['name']
        print 'Generating images for %s...' % font_family_name
        is_cjk_family = (
            family_key.endswith('-hans') or
            family_key.endswith('-hant') or
            family_key.endswith('-jpan') or
            family_key.endswith('-kore'))
        for lang_scr in family_obj['langs']:
            lang_obj = data_object['lang'][lang_scr]
            sample_text = lang_obj['sample']
            is_rtl = lang_obj['rtl']
            for instance in family_obj['fonts']:
                weight, style = instance['weight'], instance['style']
                image_file_name = path.join(
                    image_dir,
                    '%s_%s_%d_%s.png' % (family_key, lang_scr, weight, style))
                if is_cjk_family:
                    family_suffix = ' ' + css_weight_to_string(weight)
                else:
                    family_suffix = ''
                image_location = path.join(image_dir, image_file_name)
                if path.isfile(image_location):
                    # Don't rebuild images when continuing.
                    print "Continue: assuming image file '%s' is valid." % image_location
                    continue
                create_image.create_png(
                    sample_text,
                    image_location,
                    family=font_family_name+family_suffix,
                    language=lang_scr,
                    rtl=is_rtl,
                    weight=weight, style=style)
                compress(image_location, compress_png)


def create_package_object(fonts, target_platform):
    comp_zip_file = create_zip('Noto', target_platform, fonts)

    package = {}
    package['url'] = comp_zip_file
    package['size'] = os.stat(
        path.join(OUTPUT_DIR, 'pkgs', comp_zip_file)).st_size
    return package


# ==========================

class WebGen(object):

  def __init__(self, target, clean, pretty_json):
    self.target = target
    self.clean = clean
    self.pretty_json = pretty_json

    self.pkgs = path.join(target, 'pkgs')
    self.fonts = path.join(target, 'fonts')
    self.fonts_hinted = path.join(target, 'fonts', 'hinted')
    self.css_fonts = path.join(target, 'css', 'fonts')
    self.images_samples = path.join(target, 'images', 'samples')
    self.js = path.join(target, 'js')

  def clean_target_dir(self):
    if path.exists(self.target):
        print 'Removing the old website directory from %s...' % self.target
        shutil.rmtree(self.target)

  def write_json(self, obj, name):
    filepath = path.join(self.js, name + '.json')
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
      json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))

    filepath = path.join(self.js, 'pretty', name + '-pretty.json')
    with codecs.open(filepath, 'w', encoding='UTF-8') as f:
      json.dump(obj, f, ensure_ascii=False, separators=(',', ': '),
                     indent=4, sort_keys=True)

  def ensure_target_dirs_exist(self):
    def mkdirs(p):
      if not path.exists(p):
        os.makedirs(p)
    mkdirs(self.target)
    mkdirs(self.pkgs)
    mkdirs(self.fonts_hinted)
    mkdirs(self.css_fonts)
    mkdirs(self.images_samples)
    mkdirs(self.js)
    if self.pretty_json:
      mkdirs(path.join(self.js, 'pretty'))

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

  def build_family_css(self, key, family):
    fonts = family.hinted_members or family.unhinted_members
    css_name = key + '.css'
    csspath = path.join(self.css_fonts, css_name)
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
    data_obj = {}
    families_obj = {}
    for k, family in families.iteritems():
      family_obj = {}
      family_obj['name'] = family.name

      name, hinted_size, unhinted_size = family_zip_info[k]
      pkg_obj = {}
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

    langs_obj = {}
    for lang in sorted(lang_tag_to_family_ids):
      lang_obj = {}
      lang_obj['name'] = cldr_data.get_english_language_name(lang)
      lang_obj['families'] = sorted(lang_tag_to_family_ids[lang])
      native_name = cldr_data.get_native_language_name(lang)
      if native_name:
        lang_obj['keywords'] = [native_name]
      langs_obj[lang] = lang_obj
    data_obj['lang'] = langs_obj

    regions_obj = {}
    for region in sorted(region_to_family_ids):
      region_obj = {}
      region_obj['families'] = sorted(region_to_family_ids[region])
      region_obj['keywords'] = [cldr_data.get_english_region_name(region)]
      regions_obj[region] = region_obj
    data_obj['region'] = regions_obj

    pkg_obj = {
      'hinted': universal_zip_info[1],
      'unhinted': universal_zip_info[2]
    }
    data_obj['pkgSize'] = pkg_obj

    self.write_json(data_obj, 'data')

  def build_family_json(self, family_id, family, lang_tags, regions, css_info,
                        default_lang_tag):
    family_obj = {}
    category = get_css_generic_family(family.name)
    if category:
      family_obj['category'] = category
    if lang_tags:
      family_obj['langs'] = sorted(lang_tags)
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
      fonts_obj.append({
        'style': css_style(font.slope),
        'weight': css_weight(font.weight)
      })
    family_obj['fonts'] = fonts_obj
    family_obj['fontSize'] = css_info
    self.write_json(family_obj, family_id)

  def build_families_json(self, families, family_id_to_lang_tags,
                          family_id_to_default_lang_tag,
                          family_id_to_regions, family_css_info):
    result = {}
    for k, v in families.iteritems():
      lang_tags = family_id_to_lang_tags[k]
      default_lang_tag = family_id_to_default_lang_tag[k]
      regions = family_id_to_regions[k]
      css_info = family_css_info[k]
      self.build_family_json(k, v, lang_tags, regions, css_info, default_lang_tag)

  def build_misc_json(self, sample_data, region_data):
    lang_info = sample_data
    meta_obj = {}
    langs_obj = {}
    for lang in sorted(lang_info):
      rtl, sample, attrib = lang_info[lang]
      lang_obj = {
          'sample' : sample,
          'attrib' : attrib
          }
      if rtl:
        lang_obj['rtl'] = rtl
      langs_obj[lang] = lang_obj
    meta_obj['lang'] = langs_obj

    # don't need much accuracy for our map UI use case
    def trim_decimals(num):
      return float('%1.2f' % num)

    regions_obj = {}
    for region in region_data:
      lat, lng = region_data[region]
      lat = trim_decimals(lat)
      lng = trim_decimals(lng)
      region_obj = {
          'lat': lat,
          'lng': lng
      }
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
      image_location = path.join(self.images_samples, image_file_name)
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
          font_size=20,
          line_spacing=32,
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
        is_rtl, sample_text, attrib = lang_tag_to_sample_info[lang_tag]
        self.build_family_images(family, lang_tag, is_rtl, sample_text, attrib)

  def generate(self):
    if self.clean:
      self.clean_target_dir()
    self.ensure_target_dirs_exist()

    fonts = get_noto_fonts()
    families = get_families(fonts)

    script_to_family_ids = get_script_to_family_ids(families)

    supported_scripts = set(script_to_family_ids.keys())
    used_lang_data = get_used_lang_data(supported_scripts)

    langs_to_delete = []
    for lang in used_lang_data.keys():
      if not cldr_data.get_english_language_name(lang):
        langs_to_delete.append(lang)
    for lang in langs_to_delete:
      del used_lang_data[lang]

    lang_tag_to_family_ids = get_lang_tag_to_family_ids(used_lang_data, script_to_family_ids)

    # kufi hot patches:
    # - Kufi is broken for Urdu Heh goal (issue #34)
    # - Kufi doesn't support all characters needed for Khowar
    # - Kufi doesn't support all characters needed for Kashmiri
    for lang in ['ur', 'khw', 'ks-Arab', 'ks']:
      if not lang in lang_tag_to_family_ids:
        print 'patch kufi: %s not found' % lang
      else:
        lang_tag_to_family_ids[lang] -= {'kufi-arab'}
        if not lang_tag_to_family_ids:
          print 'patched kufi: %s, no fonts remaining'
          del lang_tag_to_family_ids[lang]
        else:
          print 'patched kufi: %s -> %s' % (lang, lang_tag_to_family_ids[lang])

    region_to_family_ids = get_region_to_family_ids(script_to_family_ids)

    family_id_to_lang_tags = get_family_id_to_lang_tags(lang_tag_to_family_ids, families)
    family_id_to_regions = get_family_id_to_regions(region_to_family_ids, families)

    family_id_to_default_lang_tag = get_family_id_to_default_lang_tag(
        family_id_to_lang_tags)
    used_lang_tags = get_used_lang_tags(
        lang_tag_to_family_ids.keys(), family_id_to_default_lang_tag.values())
    lang_tag_to_sample_data = get_lang_tag_to_sample_data(used_lang_tags)
    region_data = get_region_lat_lng_data(region_to_family_ids.keys())

    # build outputs
    family_zip_info = self.build_zips(families)
    universal_zip_info = self.build_universal_zips(families)

    family_css_info = self.build_css(families)

    self.build_data_json(families, family_zip_info, universal_zip_info,
                         family_id_to_lang_tags, family_id_to_regions,
                         lang_tag_to_family_ids, region_to_family_ids)

    self.build_families_json(families, family_id_to_lang_tags,
                             family_id_to_default_lang_tag,
                             family_id_to_regions, family_css_info)

    self.build_misc_json(lang_tag_to_sample_data, region_data)

    self.build_images(families, family_id_to_lang_tags,
                      family_id_to_default_lang_tag, lang_tag_to_sample_data)


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
    return


    # for target_platform in ['windows', 'linux', 'other']:
    # debug
    for target_platform in ['linux']:
        print 'Target platform %s:' % target_platform

        output_object = {}
        print 'Generating data objects and CSS...'
        output_object['region'] = create_regions_object()
        output_object['lang'] = create_langs_object()

        output_object['family'], all_font_files = create_families_object(
            target_platform)

        print 'Creating comprehensive zip file...'
        output_object['pkg'] = create_package_object(
            all_font_files, target_platform)

        ############### Hot patches ###############
        # Kufi is broken for Urdu Heh goal
        # See issue #34
        output_object['lang']['ur']['families'].remove('noto-kufi-arab')
        output_object['family']['noto-kufi-arab']['langs'].remove('ur')

        # Kufi doesn't support all characters needed for Khowar
        output_object['lang']['khw']['families'].remove('noto-kufi-arab')
        output_object['family']['noto-kufi-arab']['langs'].remove('khw')

        # Kufi doesn't support all characters needed for Kashmiri
        output_object['lang']['ks-Arab']['families'].remove('noto-kufi-arab')
        output_object['family']['noto-kufi-arab']['langs'].remove('ks-Arab')
        ############### End of hot patches ########

        # Debug
        if False and target_platform == 'linux':
            generate_sample_images(output_object)


        if target_platform == 'other':
            json_file_name = 'data.json'
        else:
            json_file_name = 'data-%s.json' % target_platform
        json_path = path.join(OUTPUT_DIR, 'js', json_file_name)
        with codecs.open(json_path, 'w', encoding='UTF-8') as json_file:
            json.dump(output_object, json_file,
                      ensure_ascii=False, separators=(',', ':'))

    # Compress the ttc files.  Requires 7za on the build machine.
    # debug
    # generate_ttc_zips_with_7za()


if __name__ == '__main__':
    locale.setlocale(locale.LC_COLLATE, 'en_US.UTF-8')
    main()
