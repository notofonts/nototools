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
import sys

from fontTools import ttLib

from nototools import cldr_data
from nototools import coverage
from nototools import font_data
from nototools import lang_data
from nototools import notoconfig
from nototools import noto_data
from nototools import tool_utils
from nototools import unicode_data

# The '[xxx]' syntax is used to get the noto-xxx value from notoconfig.
# for now we exclude alpha, the phase 3 fonts are here but we don't use
# them yet.
NOTO_FONT_PATHS = [
    '[fonts]/hinted', '[fonts]/unhinted', '[emoji]/fonts', '[cjk]']


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
  'Emoji': 'Zsye',
}


def convert_to_four_letter(script_name):
  """Converts a script name from a Noto font file name to ISO 15924 code."""
  if not script_name:
    raise ValueError('empty script name')
  if script_name in ODD_SCRIPTS:
    return ODD_SCRIPTS[script_name]
  script_code = unicode_data.script_code(script_name)
  if script_code == 'Zzzz':
    if len(script_name) != 4:
      raise ValueError('no script for %s' % script_name)
    print >> sys.stderr, 'defaulting script for %s' % script_name
    script_code = script_name
  return script_code


def preferred_script_name(script_key):
  try:
    return unicode_data.human_readable_script_name(script_key)
  except:
    return cldr_data.get_english_script_name(script_key)


_script_key_to_report_name = {
    'Aran': '(Urdu)',  # phase 2 usage
    'HST': '(Historic)',
    'LGC': '(LGC)',
    'SYM2': 'Symbols2'
}
def script_name_for_report(script_key):
    return (_script_key_to_report_name.get(script_key, None) or
            preferred_script_name(script_key))


# NotoFont maps a font path to information we assume the font to have, based
# on Noto path and naming conventions:
# - filepath: the path name from which we derived the information
# - family: family name, e.g. 'Arimo', 'Noto'
# - style: type style, e.g. 'Sans', 'Serif', might be None
# - script: four-letter script code or 'private use' code like 'Aran', 'LGC',
#     'HST'
# - variant: script variant like 'UI' or Syriac variants like 'Estrangela'
# - width: width name ('Condensed') or None
# - weight: weight name
# - slope: slope name ('Italic') or None
# - fmt: 'ttf', 'otf', or 'otc'
# - manufacturer: 'Adobe', 'Google', 'Khmertype', or 'Monotype'
# - license_type: 'sil' or 'apache'
# - is_hinted: boolean, true if hinted
# - is_mono: boolean, true if monospace (currently CJK Latin range, or legacy
#     LGC Mono)
# - is_display: boolean, true if display
# - is_UI: boolean, true if has UI in the name
# - is_UI_metrics: boolean true if must have UI metrics
# - is_cjk: boolean, true if a CJK font (from Adobe)
# - subset: name of cjk subset (KR, JA, SC, TC) for reduced-charset fonts
#     targeted at these languages
NotoFont = collections.namedtuple(
    'NotoFont',
    'filepath, family, style, script, variant, width, weight, slope, '
    'fmt, manufacturer, license_type, is_hinted, is_mono, is_UI, is_UI_metrics, '
    'is_display, is_cjk, subset')


WEIGHTS = {
    'Thin': 100,
    'ExtraLight': 200,
    'Light': 300,
    'DemiLight': 350,
    'Regular': 400,
    'Medium': 500,
    'SemiBold': 600,
    'Bold': 700,
    'ExtraBold': 800,
    'Black': 900
}


_FONT_NAME_REGEX = (
    # family should be prepended - this is so Roboto can be used with unittests
    # that use this regex to parse.
    '(Sans|Serif|Naskh|Kufi|Nastaliq|Emoji|ColorEmoji)?'
    '(Mono(?:space)?)?'
    '(.*?)'
    '(Eastern|Estrangela|Western|Slanted|New|Unjoined)?'
    '(UI)?'
    '(Display)?'
    '-?'
    '((?:Semi|Extra)?Condensed)?'
    '(|%s)?' % '|'.join(WEIGHTS.keys()) +
    '(Italic)?'
    '\.(ttf|ttc|otf)')


_EXT_REGEX = re.compile(r'.*\.(?:ttf|ttc|otf)$')

def get_noto_font(filepath, family_name='Arimo|Cousine|Tinos|Noto',
                  phase=3):
  """Return a NotoFont if filepath points to a noto font, or None if we can't
  process the path."""

  filedir, filename = os.path.split(filepath)
  if not filedir:
    filedir = os.getcwd()
  match = match_filename(filename, family_name)
  if match:
    (family, style, mono, script, variant, ui, display, width, weight,
     slope, fmt) = match.groups()
  else:
    if _EXT_REGEX.match(filename):
      print >> sys.stderr, '%s did not match font regex' % filename
    return None

  is_cjk = filedir.endswith('noto-cjk')

  license_type = 'sil'

  if script in ['JP', 'KR', 'TC', 'SC']:
    subset = script
  else:
    subset = None

  # Special-case emoji style
  # (style can be None for e.g. Cousine, causing 'in' to fail, so guard)
  if style and 'Emoji' in style:
    script = 'Zsye'
    if style == 'ColorEmoji':
      style = 'Emoji'
      variant = 'color'

  is_mono = mono == 'Mono'

  if width not in [None, '', 'Condensed', 'SemiCondensed', 'ExtraCondensed']:
    print >> sys.stderr, 'noto_fonts: Unexpected width "%s"' % width
    if width in ['SemiCond', 'Narrow']:
      width = 'SemiCondensed'
    elif width == 'Cond':
      width = 'Condensed'
    else:
      width = '#'+ width + '#'

  if not script:
    if is_mono:
      script = 'MONO'
    else:
      script = 'LGC'
  elif script == 'Urdu':
    # Use 'Aran' for languages written in the Nastaliq Arabic style, like Urdu.
    # The font naming uses 'Urdu' which is not a script, but a language.
    assert family == 'Noto' and style == 'Nastaliq'
    script = 'Aran'
  elif script == 'Historic':
    script = 'HST'
  elif script == 'CJK':
    # leave script as-is
    pass
  elif script == 'Symbols2':
    script = 'SYM2'
  else:
    try:
      script = convert_to_four_letter(script)
    except ValueError:
      print >> sys.stderr, 'unknown script: %s for %s' % (script, filename)
      return None

  if not weight:
    weight = 'Regular'

  is_UI = ui == 'UI'
  is_UI_metrics = is_UI or style == 'Emoji' or (
      style == 'Sans' and script in noto_data.DEEMED_UI_SCRIPTS_SET)

  is_display = display == 'Display'
  if is_cjk:
    is_hinted = True
  elif filedir.endswith('alpha') or 'emoji' in filedir:
    is_hinted = False
  else:
    hint_status = path.basename(filedir)
    if (hint_status not in ['hinted', 'unhinted']
        and 'noto-source' not in filedir):
      # print >> sys.stderr, (
      #    'unknown hint status for %s, defaulting to unhinted') % filedir
      pass
    is_hinted = hint_status == 'hinted'

  manufacturer = (
      'Adobe' if is_cjk
      else 'Google' if script == 'Zsye' and variant == 'color'
      else 'Khmertype' if phase < 3 and script in ['Khmr', 'Cham', 'Laoo']
      else 'Monotype')

  return NotoFont(
      filepath, family, style, script, variant, width, weight, slope, fmt,
      manufacturer, license_type, is_hinted, is_mono, is_UI, is_UI_metrics,
      is_display, is_cjk, subset)


def match_filename(filename, family_name):
    """Match just the file name."""
    return re.match('(%s)' % family_name + _FONT_NAME_REGEX, filename)


def parse_weight(name):
    """Parse the weight specifically from a name."""
    match = re.search('|'.join(WEIGHTS.keys()), name)
    if not match:
        return 'Regular'
    return match.group(0)


def script_key_to_scripts(script_key):
  """Return a set of scripts for a script key.  The script key is used by
  a font to define the set of scripts it supports.  Some keys are ours,
  e.g. 'LGC', and some are standard script codes that map to multiple
  scripts, like 'Jpan'.  In either case we need to be able to map a script
  code (either unicode character script code, or more general iso script
  code) to a font, and we do so by finding it in the list returned here."""
  if script_key == 'LGC':
    return frozenset(['Latn', 'Grek', 'Cyrl'])
  elif script_key == 'Aran':
    return frozenset(['Arab'])
  elif script_key == 'HST':
    raise ValueError('!do not know scripts for HST script key')
  elif script_key == 'MONO':
    # TODO: Mono doesn't actually support all of Latn, we need a better way
    # to deal with pseudo-script codes like this one.
    return frozenset(['Latn'])
  else:
    return lang_data.script_includes(script_key)


def script_key_to_primary_script(script_key):
  """We need a default script for a font, and fonts using a 'script key' support
  multiple fonts.  This lets us pick a default sample for a font based on it.
  The sample is named with a script that can include 'Jpan' so 'Jpan' should be
  the primary script in this case."""
  if script_key == 'LGC':
    return 'Latn'
  if script_key == 'Aran':
    return 'Arab'
  if script_key == 'HST':
    raise ValueError('!do not know scripts for HST script key')
  if script_key == 'MONO':
    return 'Latn'
  if script_key not in lang_data.scripts():
    raise ValueError('!not a script key: %s' % script_key)
  return script_key


def noto_font_to_family_id(notofont):
  # exclude 'noto-' from head of key, they all start with it except
  # arimo, cousine, and tinos, and we can special-case those.
  # For cjk with subset we ignore script and use 'cjk' plus the subset.
  tags = []
  if notofont.family != 'Noto':
    tags.append(notofont.family)
  if notofont.style:
    tags.append(notofont.style)
  if notofont.is_mono and not notofont.is_cjk:
    tags.append('mono')
  if notofont.is_cjk and notofont.subset:
    tags.append('cjk')
    tags.append(notofont.subset)
  else:
    tags.append(notofont.script)
  if notofont.variant:
    tags.append(notofont.variant)
  key = '-'.join(tags)
  return key.lower()


def noto_font_to_wws_family_id(notofont):
  """Return an id roughly corresponding to the wws family.  Used to identify
  naming rules for the corresponding fonts. Compare to noto_font_to_family_id,
  which corresponds to a preferred family and is used to determine the language
  support for those fonts.  For example, 'Noto Sans Devanagari UI' and
  'Noto Sans Devanagari' support the same languages (e.g. have the same cmap)
  but have different wws family names and different name rules (names for the
  UI variant use very short abbreviations)."""
  id = noto_font_to_family_id(notofont)
  if notofont.is_UI:
    id += '-ui'
  if notofont.is_display:
    id += '-display'
  return id


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
        print >> sys.stderr, 'bad font filename in %s: \'%s\'.' % (
            (font_dir, filename))
        continue

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


# NotoFamily provides additional information about related Noto fonts.  These
# fonts have weight/slope/other variations but have the same cmap, script
# support, etc. Most of this information is held in a NotoFont that is the
# representative member.  Fields are:

# - name: name of the family
# - family_id: a family_id for the family
# - rep_member: the representative member, some of its data is common to all
#     members
# - charset: the character set, must the the same for all members
# - hinted_members: list of members that are hinted
# - unhinted_members: list of members that are unhinted
# When both hinted_members and unhinted_members are present, they correspond.
NotoFamily = collections.namedtuple(
    'NotoFamily',
    'name, family_id, rep_member, charset, hinted_members, unhinted_members')

def get_families(fonts):
  """Group fonts into families, separate into hinted and unhinted, select
  representative."""

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
        if font.weight == 'Regular' and font.slope is None and not (
            font.is_cjk and font.is_mono) and not font.is_UI:
          # We assume here that there's no difference between a hinted or
          # unhinted rep_member in terms of what we use it for.  The other
          # filters are to ensure the fontTools font name is a good stand-in
          # for the family name.
          if font.fmt == 'ttc' and not rep_backup:
            rep_backup = font
          else:
            rep_member = font

    rep_member = rep_member or rep_backup
    if not rep_member:
      raise ValueError(
          'Family %s does not have a representative font.' % family_id)

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
  """Returns a filename to use for a family zip of hinted/unhinted members.
     This is basically the postscript name with weight/style removed.
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


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-d', '--dirs', help='list of directories to find fonts in',
      metavar='dir', nargs='+',default=NOTO_FONT_PATHS)
  args = parser.parse_args()
  fonts = get_noto_fonts(paths=args.dirs)
  for font in fonts:
    print font.filepath
    for attr in font._fields:
      print '  %15s: %s' % (attr, getattr(font, attr))


if __name__ == "__main__":
    main()
