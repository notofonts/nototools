# Copyright 2015 Google Inc. All rights reserved.
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

"""Some utilities to identify Noto fonts and collect them into families"""

import argparse
import collections
import os
from os import path
import re

from fontTools import ttLib

from nototools import coverage
from nototools import font_data
from nototools import notoconfig
from nototools import unicode_data

FONTS_DIR = notoconfig.values['noto_fonts']
CJK_DIR = notoconfig.values['noto_cjk']

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
    # Currently, this code uses 'Aran' as the stand-in script for Arabic written
    # using Nastaliq.  The font naming uses 'Urdu' which is not a script, but
    # a language. Not clear which is better, we should just decide on one.
    # For now, we remap.
    if family == 'Nastaliq' and script == 'Urdu':
      script = 'Aran'
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
        pass

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

    if hinted_members and not len(hinted_members) in [1, 2, 4, 7, 9]: # 9 adds the two Mono variants
      raise ValueError('Family %s has %d hinted_members (%s)' % (
          key, len(hinted_members), [path.basename(font.filepath) for font in hinted_members]))

    if unhinted_members and not len(unhinted_members) in [1, 2, 4, 7, 9]:
      raise ValueError('Family %s has %d unhinted_members (%s)' % (
          key, len(unhinted_members), [path.basename(font.filepath) for font in unhinted_members]))

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
