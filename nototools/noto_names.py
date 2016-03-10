#!/usr/bin/python
# Copyright 2016 Google Inc. All rights reserved.
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

"""Determine how the names of members of noto families should be
represented.

There are two groups of routines, and a tool api.  One set of routines
generates information about family names from a collection of noto
fonts.  This information looks at all the subfamilies of a family and
generates a FamilyNameInfo object representing general information
about that family.  For instance, families with only regular/bold,
normal/italic subfamilies can use the original opentype name fields
and don't require preferred names or wws names.  These routines
also read/write an xml version of this data.

The other set of routines generates name information for a noto font,
using the family name info.  The family name info is required.  For
example, familes whose subfamilies have more weights than regular/bold
will have limit_original set, and so will not include the weight in the
original subfamily name, even if a particular font instance (not knowing
about the structure of the entire family) could.

The tool api lets you generate the family info file, and/or use it to
show how one or more fonts' names would be generated.

This of necessity incorporates noto naming conventions-- it expects
file namess that follow noto conventions, and generates the corresponding
name table names.  So it is not useful for non-noto fonts.
"""

import argparse
import collections
import datetime
import glob
from os import path
import re
import sys

from nototools import cldr_data
from nototools import noto_fonts
from nototools import tool_utils
from nototools import unicode_data

from xml.etree import ElementTree as ET

# Standard values used in Noto fonts.

# Regex values returned in NameTableData must start with ^ and end with $,
# since lint uses this to understand the value is a regex.

GOOGLE_COPYRIGHT_RE = r'^Copyright 20\d\d Google Inc. All Rights Reserved\.$'

ADOBE_COPYRIGHT_RE = (
    u"^Copyright \u00a9 2014(?:, 20\d\d)? Adobe Systems Incorporated "
    u"\(http://www.adobe.com/\)\.$")

NOTO_URL = "http://www.google.com/get/noto/"

SIL_LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This Font Software is distributed on an \"AS IS\" "
    "BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express "
    "or implied. See the SIL Open Font License for the specific language, "
    "permissions and limitations governing your use of this Font Software.")

SIL_LICENSE_URL = "http://scripts.sil.org/OFL"

APACHE_LICENSE = "Licensed under the Apache License, Version 2.0"

APACHE_LICENSE_URL = "http://www.apache.org/licenses/LICENSE-2.0"

# default files where we store family name info
FAMILY_NAME_INFO_FILE='family_name_info.xml'
PHASE_2_FAMILY_NAME_INFO_FILE = 'family_name_info_p2.xml'
PHASE_3_FAMILY_NAME_INFO_FILE = 'family_name_info_p3.xml'

# Represents what and how we write family names in the name table.
# If limit_original is true, weights become part of the family name,
# otherwise the family only has Bold and Regular weights so they
# remain in the subfamily.
# if use_preferred is true, there are subfamilies that don't fit into
# Regular Bold BoldItalic Italic, so generate the preferred names.
# if use_wws is true, there are subfamilies that don't fit into wws,
# so generate the wws names.
FamilyNameInfo = collections.namedtuple(
    'FamilyNameInfo',
    'limit_original, use_preferred, use_wws')

# Represents expected name table data for a font.
# Fields expected to be empty are None.  Fields that are expected
# to be present but have any value are '-'.
NameTableData = collections.namedtuple(
    'NameTableData',
    'copyright_re, original_family, original_subfamily, unique_id, '
    'full_name, version_re, postscript_name, trademark, manufacturer, '
    'designer, description_re, vendor_url, designer_url, license_text, '
    'license_url, preferred_family, preferred_subfamily, wws_family, '
    'wws_subfamily')

_SCRIPT_KEY_TO_FONT_NAME = {
    'Aran': 'Urdu',
    'HST': 'Historic',
    'LGC': None,
    'Zsye': None,
}


# copied from noto_lint, we should have a better place for it.
def preferred_script_name(script_key):
  try:
    return unicode_data.human_readable_script_name(script_key)
  except KeyError:
    return cldr_data.get_english_script_name(script_key)


# copied from cmap_data, it has a dependency on lint, lint has one
# on this, and python gives an unhelpful error message when there's
# circular dependencies.
def _prettify(root, indent=''):
  """Pretty-print the root element if it has no text and children
     by adding to the root text and each child's tail."""
  if not root.text and len(root):
    indent += '  '
    sfx = '\n' + indent
    root.text = sfx
    for elem in root:
      elem.tail = sfx
      _prettify(elem, indent)
    elem.tail = sfx[:-2]


def _preferred_cjk_parts(noto_font):
  # CJK treats mono as part of the family name.  This is odd
  # but we will go with the current Adobe naming.
  family_parts = [
      noto_font.family,
      noto_font.style,
      'Mono' if noto_font.is_mono else None]
  if noto_font.subset:
    family_parts.append(noto_font.subset)
  else:
    family_parts.append('CJK')
    cjk_script_to_name = {
        'Jpan': 'JP',
        'Kore': 'KR',
        'Hans': 'SC',
        'Hant': 'TC'
        }
    family_parts.append(cjk_script_to_name[noto_font.script])

  subfamily_parts = [
      noto_font.weight,
      noto_font.slope]
  return family_parts, subfamily_parts


def _preferred_non_cjk_parts(noto_font):
  """Return a tuple of preferred_family, preferred_subfamily).

  The preferred family is based on the family, style, script, and variant, the
  preferred_subfamily is based on the remainder.
  """

  family_parts = [
      noto_font.family,
      'Color' if noto_font.variant == 'color' else None,
      noto_font.style]

  script = noto_font.script
  if script in _SCRIPT_KEY_TO_FONT_NAME:
    # special case script key portion of name
    family_parts.append(_SCRIPT_KEY_TO_FONT_NAME[script])
  else:
    family_parts.append(preferred_script_name(script))
  if noto_font.variant != 'color':
    family_parts.append(noto_font.variant)

  include_weight = (noto_font.weight != 'Regular' or
    (not noto_font.width and not noto_font.slope))

  subfamily_parts = [
      'Mono' if noto_font.is_mono else None,
      'UI' if noto_font.is_UI else None,
      'Display' if noto_font.is_display else None,
      noto_font.width,
      noto_font.weight if include_weight else None,
      noto_font.slope]
  return family_parts, subfamily_parts


def _preferred_parts(noto_font):
  if noto_font.is_cjk:
    parts_pair = _preferred_cjk_parts(noto_font)
  else:
    parts_pair = _preferred_non_cjk_parts(noto_font)
  return filter(None, parts_pair[0]), filter(None, parts_pair[1])


def _shift_parts(family_parts, subfamily_parts, stop_fn):
  """Iterate over subfamily parts, removing from
  subfamily and appending to family, until stop_fn(part)
  returns true.  If subfamily_parts is empty, add
  'Regular'.  This works because for both original and
  wws subfamilies the order of parts is such that all
  parts that fail the stop_fn precede any that pass.
  Does not modify the input parts lists."""

  result_family_parts = family_parts[:]
  limit = len(subfamily_parts)
  i = 0
  while i < limit:
    part = subfamily_parts[i]
    if stop_fn(part):
      break
    result_family_parts.append(part)
    i += 1
  result_subfamily_parts = subfamily_parts[i:]
  if not result_subfamily_parts:
    result_subfamily_parts.append('Regular')
  return result_family_parts, result_subfamily_parts


_WWS_RE = re.compile('(?:Condensed|Italic|%s)$' % '|'.join(noto_fonts.WEIGHTS))
def _is_wws_part(part):
  return _WWS_RE.match(part)


def _wws_parts(family_parts, subfamily_parts):
  return _shift_parts(family_parts, subfamily_parts, _is_wws_part)


_ORIGINAL_RE = re.compile('(?:Bold|Italic|Regular)$')
def _is_original_part(part):
    return _ORIGINAL_RE.match(part)


_LIMITED_ORIGINAL_RE = re.compile('(?:Italic)$')
def _is_limited_original_part(part):
  return _LIMITED_ORIGINAL_RE.match(part)


def _original_parts(family_parts, subfamily_parts, limited=False):
  """Set limited to true if weight should be in the family and not
  the subfamily."""
  stop_fn = _is_limited_original_part if limited else _is_original_part
  return _shift_parts(family_parts, subfamily_parts, stop_fn)


def _names(family_parts, subfamily_parts):
  return (' '.join(family_parts), ' '.join(subfamily_parts))


def _preferred_names(preferred_family, preferred_subfamily, use_preferred):
  if use_preferred:
    return _names(preferred_family, preferred_subfamily)
  return None, None


def _wws_names(preferred_family, preferred_subfamily, use_wws):
  if use_wws:
    return _names(*_wws_parts(preferred_family, preferred_subfamily))
  return None, None


def _original_names(preferred_family, preferred_subfamily, limited):
  return _names(*_original_parts(
      preferred_family, preferred_subfamily, limited=limited))


def _copyright_re(noto_font):
  # See comment at top of file about regex values
  if noto_font.manufacturer == 'Adobe':
    return ADOBE_COPYRIGHT_RE
  else:
    return GOOGLE_COPYRIGHT_RE


def _full_name(preferred_family, preferred_subfamily, keep_regular):
  wws_family, wws_subfamily = _wws_parts(preferred_family, preferred_subfamily)
  result = wws_family[:]
  for n in wws_subfamily:
    if n not in result and (keep_regular or n != 'Regular'):
      result.append(n)
  return ' '.join(result)


def _postscript_name(preferred_family, preferred_subfamily, keep_regular):
  wws_family, wws_subfamily = _wws_parts(preferred_family, preferred_subfamily)
  # fix for names with punctuation
  punct_re = re.compile("[\s'-]")
  result = ''.join(punct_re.sub('', p) for p in wws_family)
  tail = [n for n in wws_subfamily if
          n not in wws_family and (keep_regular or n != 'Regular')]
  if tail:
    result += '-' + ''.join(tail)

  # fix for CJK
  def repl_fn(m):
    return 'CJK' + m.group(1).lower()
  result = re.sub('CJK(JP|KR|SC|TC)', repl_fn, result)

  if len(result) > 63:
    print >> sys.stderr, 'postscript name longer than 63 characters:\n"%s"' % (
        result)
  return result


def _version_re(noto_font):
  # See comment at top of file about regex values
  if noto_font.manufacturer == 'Adobe':
    sub_len = 3
    hint_ext = ''
  elif noto_font.manufacturer == 'Google':
    sub_len = 2
    hint_ext = '' # no 'uh' suffix for unhinted Color Emoji font
  else:
    sub_len = 2
    hint_ext = '' if noto_font.is_hinted else ' uh'
  return r'^Version ([0-2])\.(\d{%d})%s(?:;.*)?$' % (sub_len, hint_ext)


def _trademark(noto_font):
  return '%s is a trademark of Google Inc.' % noto_font.family


def _manufacturer(noto_font):
  if noto_font.manufacturer == 'Adobe':
    return 'Adobe Systems Incorporated'
  if noto_font.manufacturer == 'Monotype':
    return 'Monotype Imaging Inc.'
  if noto_font.manufacturer == 'Khmertype':
    return 'Danh Hong'
  if noto_font.manufacturer == 'Google':
    return 'Google, Inc.'
  raise ValueError('unknown manufacturer "%s"' % noto_font.manufacturer)


def _designer(noto_font):
  if noto_font.manufacturer == 'Adobe':
    return '-'
  if noto_font.manufacturer == 'Monotype':
    if noto_font.family == 'Noto':
      if noto_font.style == 'Serif' and noto_font.script in [
          'Beng', 'Gujr', 'Knda', 'Mlym', 'Taml', 'Telu']:
        return 'Indian Type Foundry'
      return 'Monotype Design Team'
    if noto_font.family in ['Arimo', 'Cousine', 'Tinos']:
      return 'Steve Matteson'
    raise ValueError('unknown family "%s"' % noto_font.family)
  if noto_font.manufacturer == 'Khmertype':
    return 'Danh Hong'
  if noto_font.manufacturer == 'Google':
    return 'Google, Inc.'
  raise ValueError('unknown manufacturer "%s"' % noto_font.manufacturer)


def _designer_url(noto_font):
  if noto_font.manufacturer == 'Adobe':
    return 'http://www.adobe.com/type/'
  if noto_font.manufacturer == 'Monotype':
    return 'http://www.monotype.com/studio'
  if noto_font.manufacturer == 'Khmertype':
    return 'http://www.khmertype.org'
  if noto_font.manufacturer == 'Google':
    return 'http://www.google.com/get/noto/'
  raise ValueError('unknown manufacturer "%s"' % noto_font.manufacturer)


def _description_re(noto_font):
  # See comment at top of file about regex values
  if noto_font.manufacturer == 'Adobe':
    return '-'
  if noto_font.manufacturer == 'Monotype':
    if noto_font.family == 'Noto':
      return ('^Data %shinted. Designed by Monotype design team.$' %
              ('' if noto_font.is_hinted else 'un'))
    # Arimo, Tinos, and Cousine don't currently mention hinting in their
    # descriptions, but they probably should.
    # TODO(dougfelt): swat them to fix this.
    return '-'
  if noto_font.manufacturer == 'Google' and noto_font.variant == 'color':
    return 'Color emoji font using CBDT glyph data.'
  if noto_font.is_hinted:
    return '^Data hinted\.(?:\s.*)?$'
  return '^Data unhinted\.(?:\s.*)?$'


def _license_text(noto_font):
  if noto_font.license_type == 'sil':
    return SIL_LICENSE
  if noto_font.license_type == 'apache':
    return APACHE_LICENSE
  raise ValueError('unknown license type "%s"' % noto_font.license_type)


def _license_url(noto_font):
  if noto_font.license_type == 'sil':
    return SIL_LICENSE_URL
  if noto_font.license_type == 'apache':
    return APACHE_LICENSE_URL
  raise ValueError('unknown license type "%s"' % noto_font.license_type)


def name_table_data(noto_font, family_to_name_info):
  """Returns a NameTableData for this font given the family_to_name_info."""
  family_parts, subfamily_parts = _preferred_parts(noto_font)
  family_key = ' '.join(family_parts)
  try:
    info = family_to_name_info[family_key]
  except KeyError:
    print >> sys.stderr, 'no family name info for "%s"' % family_key
    return None

  if not info.use_preferred and subfamily_parts not in [
      ['Regular'],
      ['Bold'],
      ['Italic'],
      ['Bold', 'Italic']]:
    print >> sys.stderr, (
        'Error in family name info: %s requires preferred names, but info '
        'says none are required.' % path.basename(noto_font.filepath))
    print >> sys.stderr, subfamily_parts
    return None

  ofn, osfn = _original_names(
      family_parts, subfamily_parts, info.limit_original)
  # If we limit the original names (to put weights into the original family)
  # then we need a preferred name to undo this.  When info is read or generated,
  # the code should ensure use_preferred is set.
  pfn, psfn = _preferred_names(
      family_parts, subfamily_parts, info.use_preferred)
  wfn, wsfn = _wws_names(family_parts, subfamily_parts, info.use_wws)
  if wfn and wfn == pfn:
    wfn = None
  if wsfn and wsfn == psfn:
    wsfn = None
  if pfn and pfn == ofn:
    pfn = None
  if psfn and psfn == osfn:
    psfn = None

  return NameTableData(
      copyright_re=_copyright_re(noto_font),
      original_family=ofn,
      original_subfamily=osfn,
      unique_id='-',
      full_name=_full_name(family_parts, subfamily_parts, noto_font.is_cjk),
      version_re=_version_re(noto_font),
      postscript_name=_postscript_name(
          family_parts, subfamily_parts, noto_font.is_cjk),
      trademark=_trademark(noto_font),
      manufacturer=_manufacturer(noto_font),
      designer=_designer(noto_font),
      description_re=_description_re(noto_font),
      vendor_url=NOTO_URL,
      designer_url=_designer_url(noto_font),
      license_text=_license_text(noto_font),
      license_url=_license_url(noto_font),
      preferred_family=pfn,
      preferred_subfamily=psfn,
      wws_family=wfn,
      wws_subfamily=wsfn)


def _create_family_to_subfamilies(noto_fonts):
  """Return a map from preferred family name to set of preferred subfamilies."""
  family_to_subfamilies = collections.defaultdict(set)
  for noto_font in noto_fonts:
    family, subfamily = _names(*_preferred_parts(noto_font))
    family_to_subfamilies[family].add(subfamily)
  return family_to_subfamilies


_NON_ORIGINAL_WEIGHT_PARTS = frozenset(
    w for w in noto_fonts.WEIGHTS
    if w not in ['Bold', 'Regular'])
_ORIGINAL_PARTS = frozenset(['Bold', 'Regular', 'Italic'])
_WWS_PARTS = frozenset(['Condensed', 'Italic'] + list(noto_fonts.WEIGHTS))

def create_family_to_name_info(noto_fonts):
  family_to_parts = collections.defaultdict(set)
  for noto_font in noto_fonts:
    family_parts, subfamily_parts = _preferred_parts(noto_font)
    family_key = ' '.join(family_parts)
    family_to_parts[family_key].update(subfamily_parts)
  result = {}
  for key, part_set in family_to_parts.iteritems():
    # Even through CJK mono fonts are in their own families and have only
    # bold and regular weights, they behave like they have more weights like
    # the rest of CJK.
    limit_original = 'CJK' in key or bool(part_set & _NON_ORIGINAL_WEIGHT_PARTS)
    # If we limit original, then we automatically use_preferred.
    use_preferred = limit_original or bool(part_set - _ORIGINAL_PARTS)
    use_wws = bool(part_set - _WWS_PARTS)
    result[key] = FamilyNameInfo(limit_original, use_preferred, use_wws)
  return result


def _build_info_element(family, info):
  attrs = {'family': family}
  for attr in FamilyNameInfo._fields:
    if getattr(info, attr):
      attrs[attr] = 't'
  # Don't have to write it out since limit_original implies use_preferred
  if 'limit_original' in attrs and 'use_preferred' in attrs:
    del attrs['use_preferred']
  return ET.Element('info', attrs)


def _build_tree(family_to_name_info, pretty=False):
  date = str(datetime.date.today())
  root = ET.Element('family_name_data', date=date)
  for family in sorted(family_to_name_info):
    info = family_to_name_info[family]
    root.append(_build_info_element(family, info))
  if pretty:
    _prettify(root)
    root.tail='\n'
  return ET.ElementTree(element=root)


def _read_info_element(info_node):
  def bval(attr):
    return bool(info_node.get(attr, False))
  # limit_original implies use_preferred
  return FamilyNameInfo(
      bval('limit_original'),
      bval('limit_original') or bval('use_preferred'),
      bval('use_wws'))


def _read_tree(root):
  family_to_name_info = {}
  for node in root:
    if node.tag != 'info':
      raise ValueError('unknown node in tree: "%s"' % node.tag)
    family = node.get('family').strip()
    family_to_name_info[family] = _read_info_element(node)
  return family_to_name_info


def write_family_name_info_file(family_to_name_info, filename, pretty=False):
  _build_tree(family_to_name_info, pretty).write(
      filename, encoding='utf8', xml_declaration=True)


def write_family_name_info(family_to_name_info, pretty=False):
  return ET.tostring(
      _build_tree(family_to_name_info, pretty).getroot(),
      encoding='utf-8')


_PHASE_TO_NAME_INFO_CACHE = {}
_PHASE_TO_FILENAME = {
    2: PHASE_2_FAMILY_NAME_INFO_FILE,
    3: PHASE_3_FAMILY_NAME_INFO_FILE
}
def family_to_name_info_for_phase(phase):
  """Phase is an int, either 2 or 3."""
  result = _PHASE_TO_NAME_INFO_CACHE.get(phase, None)
  if not result and phase in _PHASE_TO_FILENAME:
    result = read_family_name_info_file(_PHASE_TO_FILENAME[phase])
    _PHASE_TO_NAME_INFO_CACHE[phase] = result
  return result


def read_family_name_info_file(filename):
  """Returns a map from preferred family name to FontNameInfo."""
  return _read_tree(ET.parse(filename).getroot())


def read_family_name_info(text):
  """Returns a map from preferred family name to FontNameInfo."""
  return _read_tree(ET.fromstring(text))


def _create_family_to_faces(noto_fonts, name_fn):
  """Noto_fonts is a collection of NotoFonts.  Return a map from
  preferred family to a list of preferred subfamily."""

  family_to_faces = collections.defaultdict(set)
  for noto_font in noto_fonts:
    if noto_font.fmt == 'ttc':
      continue
    family, subfamily = name_fn(noto_font)
    family_to_faces[family].add(subfamily)
  return family_to_faces


def _dump_family_to_faces(family_to_faces):
  for family in sorted(family_to_faces):
    print '%s:\n  %s' % (
        family, '\n  '.join(sorted(family_to_faces[family])))


def _dump_name_data(name_data):
  if not name_data:
    print '  Error: no name data'
    return
  for attr in NameTableData._fields:
    value = getattr(name_data, attr)
    if value:
      print '  %20s: %s' % (attr, value)
    else:
      print '  %20s: <none>' % attr


def _dump_family_names(noto_fonts, family_to_name_info):
  for font in sorted(noto_fonts, key=lambda f: f.filepath):
    name_data = name_table_data(font, family_to_name_info)
    print font.filepath
    _dump_name_data(name_data)


def _dump(fonts, info_file):
  """Display information about fonts, using name info from info_file."""
  family_to_name_info = read_family_name_info_file(info_file)
  _dump_family_names(fonts, family_to_name_info)


def _write(fonts, info_file):
  """Build family name info from font_paths and write to info_file.
  Write to stdout if info_file is None."""
  family_to_name_info =  create_family_to_name_info(fonts)
  if info_file:
    write_family_name_info_file(family_to_name_info, info_file, pretty=True)
  else:
    print write_family_name_info(family_to_name_info, pretty=True)


def _test(fonts):
  """Build name info from font_paths and dump the names for them."""
  family_to_name_info = create_family_to_name_info(fonts)
  print write_family_name_info(family_to_name_info, pretty=True)
  _dump_family_names(fonts, family_to_name_info)


def _info(fonts):
  """Group fonts into families and list the subfamilies for each."""
  family_to_subfamilies = _create_family_to_subfamilies(fonts)
  for family in sorted(family_to_subfamilies):
    print '%s:\n  %s' % (
        family, '\n  '.join(sorted(family_to_subfamilies[family])))


def _collect_paths(dirs, files):
  paths = []
  if dirs:
    for d in dirs:
      d = tool_utils.resolve_path(d)
      paths.extend(n for n in glob.glob(path.join(d, '*')))
  if files:
    paths.extend(tool_utils.resolve_path(f) for f in files)
  return paths


def _get_noto_fonts(font_paths):
  FMTS = frozenset(['ttf', 'otf'])
  SCRIPTS = frozenset(['CJK', 'HST'])
  fonts = []
  for p in font_paths:
    font = noto_fonts.get_noto_font(p)
    if font and font.fmt in FMTS and font.script not in SCRIPTS:
      fonts.append(font)
  return fonts


def main():
  CMDS = ['dump', 'write', 'test', 'info']
  HELP = """
  dump  - read the family info file, and display the names to generate
          for some fonts.
  write - collect all the names of the provided fonts, and write a family name
          info file if one was provided (via -i or -p), else write to stdout.
  test  - collect all the names of the provided fonts, show the family name
          info file that would be generated, and show the names to generate
          for those fonts.
  info  - collect the preferred names of the provided fonts, and display them.
  """

  parser = argparse.ArgumentParser(
      epilog=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
      '-i', '--info_file', metavar='fname',
      help='name of xml family info file, overrides name based on phase')
  parser.add_argument(
      '-p', '--phase', metavar = 'phase', type=int,
      help='determine info file name by phase (2 or 3)')
  parser.add_argument(
      '-d', '--dirs', metavar='dir', help='font directories to examine '
      '(use "[noto]" for noto fonts/cjk/emoji font dirs)', nargs='+')
  parser.add_argument(
      '-f', '--files', metavar='fname', help='fonts to examine', nargs='+')
  parser.add_argument(
      'cmd', metavar='cmd', help='operation to perform (%s)' % ', '.join(CMDS),
      choices=CMDS)
  args = parser.parse_args()

  if args.dirs:
    for i in range(len(args.dirs)):
      if args.dirs[i] == '[noto]':
        args.dirs[i] = None
        args.dirs.extend(noto_fonts.NOTO_FONT_PATHS)
        args.dirs = filter(None, args.dirs)
        break

  paths = _collect_paths(args.dirs, args.files)
  fonts = _get_noto_fonts(paths)
  if not fonts:
    print 'Please specify at least one directory or file'
    return

  if not args.info_file:
    if args.phase:
      args.info_file = _PHASE_TO_FILENAME[args.phase]
      print 'using info file: "%s"' % args.info_file

  if args.cmd == 'dump':
    if not args.info_file:
      print 'must specify an info file to dump'
      return
    if not path.exists(args.info_file):
      print '"%s" does not exist.' % args.info_file
      return
    _dump(fonts, args.info_file)
  elif args.cmd == 'write':
    _write(fonts, args.info_file)
  elif args.cmd == 'test':
    _test(fonts)
  elif args.cmd == 'info':
    _info(fonts)


if __name__ == "__main__":
    main()
