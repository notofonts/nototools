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
from nototools import lang_data
from nototools import notoconfig
from nototools import tool_utils
from nototools import unicode_data

# The '[xxx]' syntax is used to get the noto-xxx value from notoconfig.
NOTO_FONT_PATHS = [
    '[fonts]/hinted', '[fonts]/unhinted', '[fonts]/alpha', '[emoji]', '[cjk]']


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

# NotoFont maps a font path to information we assume the font to have, based on Noto
# path and naming conventions:
# - filepath: the path name from which we derived the information
# - family: family name, e.g. 'Arimo', 'Noto'
# - style: type style, e.g. 'Sans', 'Serif', might be None
# - script: four-letter script code or 'private use' code like 'Aran', 'LGC', 'HST'
# - variant: script variant like 'UI' or Syriac variants like 'Estrangela'
# - weight: weight name
# - slope: slope name ('Italic') or None
# - fmt: 'ttf' or 'otf' or 'otc'
# - license_type: 'sil' or 'apache'
# - is_hinted: boolean, true if hinted
# - is_mono: boolean, true if monospace (currently only CJK Latin range)
# - is_UI: boolean, true if has UI metrics
# - is_cjk: boolean, true if a CJK font (from Adobe)
# - subset: name of cjk subset (KR, JA, SC, TC) for reduced-charset fonts targetted at these
#     languages
NotoFont = collections.namedtuple(
    'NotoFont',
    'filepath, family, style, script, variant, weight, slope, fmt, license_type, '
    'is_hinted, is_mono, is_UI, is_cjk, subset')

_NOTO_FONT_NAME_REGEX = re.compile(
    '(Arimo|Cousine|Tinos|Noto)'
    '(Sans|Serif|Naskh|Kufi|Nastaliq|Emoji)?'
    '(Mono)?'
    '(.*?)'
    '(UI|Eastern|Estrangela|Western)?'
    '-'
    '(|Black|Bold|DemiLight|Light|Medium|Regular|Thin)'
    '(Italic)?'
    '\.(ttf|ttc|otf)')

_EXT_REGEX = re.compile(r'.*\.(?:ttf|ttc|otf)$')

def get_noto_font(filepath):
  """Return a NotoFont if filepath points to a noto font, or None if we can't
  process the path."""

  filedir, filename = os.path.split(filepath)
  match = _NOTO_FONT_NAME_REGEX.match(filename)
  if match:
    family, style, mono, script, variant, weight, slope, fmt = match.groups()
  else:
    if _EXT_REGEX.match(filename):
      print '%s did not match font regex' % filename
    return None

  is_cjk = filedir.endswith('noto-cjk')

  license_type = 'sil' if is_cjk else 'apache'

  if script in ['JP', 'KR', 'TC', 'SC']:
    subset = script
  else:
    subset = None

  # Special-case emoji style
  if style == 'Emoji':
    script = 'Qaae'

  if not script:
    script = 'LGC'
  elif script == 'Urdu':
    # Currently, this code uses 'Aran' as the stand-in script for Arabic written
    # using Nastaliq.  The font naming uses 'Urdu' which is not a script, but
    # a language. Not clear which is better, we should just decide on one.
    # For now, we remap.
    assert family == 'Noto' and style == 'Nastaliq'
    script = 'Aran'
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

  is_mono = mono == 'Mono'

  is_UI = variant == 'UI'
  if is_UI:
    variant = None

  if is_cjk:
    is_hinted = True
  elif filedir.endswith('alpha') or filedir.endswith('emoji'):
    is_hinted = False
  else:
    hint_status = path.basename(filedir)
    assert hint_status in ['hinted', 'unhinted']
    is_hinted = hint_status == 'hinted'

  return NotoFont(filepath, family, style, script, variant, weight, slope, fmt, license_type,
                  is_hinted, is_mono, is_UI, is_cjk, subset)


def script_key_to_scripts(script_key):
  """First script in list is the 'default' script."""
  if script_key == 'LGC':
    return ['Latn', 'Grek', 'Cyrl']
  elif script_key == 'Aran':
    return ['Arab']
  elif script_key == 'HST':
    raise ValueError('!do not know scripts for HST script key')
  else:
    if script_key not in lang_data.scripts():
      raise ValueError('!not a script: %s' % script_key)
    return [script_key]


def noto_font_to_family_id(notofont):
  # exclude 'noto-' from head of key, they all start with it except
  # arimo, cousine, and tinos, and we can special-case those.
  # For cjk with subset we ignore script and use 'cjk' plus the subset.
  tags = []
  if notofont.family != 'Noto':
    tags.append(notofont.family)
  if notofont.style:
    tags.append(notofont.style)
  if notofont.is_cjk and notofont.subset:
    tags.append('cjk')
    tags.append(notofont.subset)
  else:
    tags.append(notofont.script)
  if notofont.variant:
    tags.append(notofont.variant)
  key = '-'.join(tags)
  return key.lower()


def get_noto_fonts(paths=NOTO_FONT_PATHS):
  """Scan paths for fonts, and create a NotoFont for each one, returning a list
  of these.  'paths' defaults to the standard noto font paths, using notoconfig."""

  font_dirs = filter(None, [tool_utils.resolve_path(p) for p in paths])
  print 'Getting fonts from: %s' % font_dirs

  all_fonts = []
  for font_dir in font_dirs:
    for filename in os.listdir(font_dir):
      if not _EXT_REGEX.match(filename):
        continue

      filepath = path.join(font_dir, filename)
      font = get_noto_font(filepath)
      if not font:
        raise ValueError('bad font filename in %s: \'%s\'.' %
                         (font_dir, filename))

      all_fonts.append(font)

  return all_fonts


def get_font_family_name(font_file):
    font = ttLib.TTFont(font_file, fontNumber=0)
    name_record = font_data.get_name_records(font)
    try:
      name = name_record[16]
    except KeyError:
      name = name_record[1]
      if name.endswith('Regular'):
        name = name.rsplit(' ', 1)[0]
    return name


# NotoFamily provides additional information about related Noto fonts.  These fonts have
# weight/slope/other variations but have the same cmap, script support, etc. Most of
# this information is held in a NotoFont that is the representative member.  Fields are:
# - name: name of the family
# - family_id: a family_id for the family
# - rep_member: the representative member, some of its data is common to all members
# - charset: the character set, must the the same for all members
# - hinted_members: list of members that are hinted
# - unhinted_members: list of members that are unhinted
# When both hinted_members and unhinted_members are present, they correspond.
NotoFamily = collections.namedtuple(
    'NotoFamily',
    'name, family_id, rep_member, charset, hinted_members, unhinted_members')

def get_families(fonts):
  """Group fonts into families, separate into hinted and unhinted, select representative."""
  family_id_to_fonts = collections.defaultdict(set)
  families = {}
  for font in fonts:
    family_id = noto_font_to_family_id(font)
    family_id_to_fonts[family_id].add(font)

  for family_id, fonts in family_id_to_fonts.iteritems():
    hinted_members = []
    unhinted_members = []
    rep_member = None
    rep_backup = None  # used in case all fonts are ttc fonts
    for font in fonts:
      if font.is_hinted:
        hinted_members.append(font)
      else:
        unhinted_members.append(font)
      if not rep_member:
        if font.weight == 'Regular' and font.slope is None and not font.is_mono:
          # We assume here that there's no difference between a hinted or unhinted
          # rep_member in terms of what we use it for.  The other filters are to ensure
          # the fontTools font name is a good stand-in for the family name.
          if font.fmt == 'ttc' and not rep_backup:
            rep_backup = font
          else:
            rep_member = font

    rep_member = rep_member or rep_backup
    if not rep_member:
      raise ValueError('Family %s does not have a representative font.' % family_id)

    name = get_font_family_name(rep_member.filepath)

    if rep_member.fmt in {'ttf', 'otf'}:
      charset = coverage.character_set(rep_member.filepath)
    else:
      # was NotImplemented, but bool(NotImplemented) is True
      charset = None

    families[family_id] = NotoFamily(
        name, family_id, rep_member, charset, hinted_members, unhinted_members)

  return families


def get_family_filename(family):
  """Returns a filename to use for a family zip of hinted/unhinted members.  This
     is basically the postscript name with weight/style removed.
  """
  font = ttLib.TTFont(family.rep_member.filepath, fontNumber=0)
  name_record = font_data.get_name_records(font)
  try:
    name = name_record[6]
    ix = name.find('-')
    if ix >= 0:
      name = name[:ix]
  except KeyError:
    name = name_record[1]
    if name.endswith('Regular'):
      name = name.rsplit(' ', 1)[0]
    name = name.replace(' ', '')
  return name
