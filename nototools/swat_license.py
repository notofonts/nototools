#!/usr/bin/python
#
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

"""Swat copyright, bump version."""


import argparse
import os
from os import path
import re

from nototools import cldr_data
from nototools import font_data
from nototools import noto_fonts

from fontTools import ttLib
from fontTools import misc

_VERSION_ID = 5
_LICENSE_ID = 13
_LICENSE_URL_ID = 14

_SIL_LICENSE = ("This Font Software is licensed under the SIL Open Font License, "
                "Version 1.1. This Font Software is distributed on an \"AS IS\" "
                "BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express "
                "or implied. See the SIL Open Font License for the specific language, "
                "permissions and limitations governing your use of this Font Software.")

_SIL_LICENSE_URL = "http://scripts.sil.org/OFL"

_SCRIPT_KEYS = {
    'Aran': 'Urdu',
    'HST': 'Historic',
    'LGC': ''
}

_FAMILY_KEYS = {
  'Arimo': 'a',
  'Cousine':'b',
  'Tinos': 'c',
  'Noto': 'd',
}

def _swat_fonts(dst_root, dry_run):
  def family_key(family):
      return _FAMILY_KEYS[family]
  def script_key(script):
      return _SCRIPT_KEYS.get(script, None) or cldr_data.get_english_script_name(script)
  def compare_key(font):
    return (font.family,
            font.style,
            script_key(font.script),
            'a' if font.is_hinted else '',
            font.variant if font.variant else '',
            'UI' if font.is_UI else '',
            '' if font.weight == 'Regular' else font.weight,
            font.slope or '',
            font.fmt)
  fonts = noto_fonts.get_noto_fonts()
  for font in sorted(fonts, key=compare_key):
    _swat_font(font, dst_root, dry_run)

def _swat_font(noto_font, dst_root, dry_run):
  filepath = noto_font.filepath
  basename, ext = path.splitext(path.basename(filepath))
  if noto_font.is_cjk:
    print '# Skipping cjk font %s' % basename
    return

  ttfont = ttLib.TTFont(filepath, fontNumber=0)

  names = font_data.get_name_records(ttfont)

  print '-----\nUpdating %s' % filepath
  # create relative root path
  x = filepath.find('noto-fonts')
  if x == -1:
    x = filepath.find('noto-cjk')
    if x == -1:
      x = filepath.find('noto-emoji')
  if x == -1:
    print 'Could not identify noto root'
    return

  dst_file = path.join(dst_root, filepath[x:])

  version = names[_VERSION_ID]
  m = re.match(r'Version (\d{1,5})\.(\d{1,5})(.*)', version)
  if not m:
    print '! Could not match version string (%s)' % version
    return

  major_version = m.group(1)
  minor_version = m.group(2)
  version_remainder = m.group(3)
  accuracy = len(minor_version)
  print_revision = font_data.printable_font_revision(ttfont, accuracy)
  # sanity check
  expected_revision = major_version + '.' + minor_version
  if expected_revision != print_revision:
    print '! Expected revision \'%s\' but got revision \'%s\'' % (
        expected_revision, print_revision)
    return

  # bump the minor version keeping significant digits:
  new_minor_version = str(int(minor_version) + 1).zfill(accuracy)
  new_revision = major_version + '.' + new_minor_version
  print 'Update revision from  \'%s\' to \'%s\'' % (
      expected_revision, new_revision)
  # double check we are going to properly round-trip this value
  float_revision = float(new_revision)
  fixed_revision = misc.fixedTools.floatToFixed(float_revision, 16)
  rt_float_rev = misc.fixedTools.fixedToFloat(fixed_revision, 16)
  rt_float_rev_int = int(rt_float_rev)
  rt_float_rev_frac = int(round((rt_float_rev - rt_float_rev_int) * 10 ** accuracy))
  rt_new_revision = str(rt_float_rev_int) + '.' + str(rt_float_rev_frac).zfill(accuracy)
  if new_revision != rt_new_revision:
    print '! Could not update new revision, expected \'%s\' but got \'%s\'' % (
        new_revision, rt_new_revision)
    return

  new_version_string = 'Version ' + new_revision;
  if not noto_font.is_hinted:
    new_version_string += ' uh'
  if version_remainder != ' uh':
    print '# omitting version remainder \'%s\'' % version_remainder

  print '%s: %s' % ('Would write' if dry_run else 'Writing', dst_file)

  # vendor url
  NOTO_URL = "http://www.google.com/get/noto/"

  # trademark message
  TRADEMARK = "%s is a trademark of Google Inc." % family

  # description field - should be set.  Roozbeh has note, make sure design field has
  # information on whether the font is hinted.
  # Missing in Lao and Khmer, default in Cham.
  if noto_font.script in ['Lao', 'Khmer', 'Cham']:
    decription = (
        'Data %shinted. Noto %s is a humanist %s serif typeface designed for user interfaces '
        'and electronic communication.' % (
            '' if hinted else 'un',
            'Sans' if sans else 'Serif',
            'sans ' if sans else ''))
  elif noto_font.vendor is 'Monotype':
    description = (
      'Data %shinted. Designed by Monotype design team.' % '' if hinted else 'un'))
  else:
    print '# could not generate description'
    description = None

  # Designer name

  if dry_run:
    return

  font_data.set_name_record(ttfont, _LICENSE_ID, _SIL_LICENSE)
  font_data.set_name_record(ttfont, _LICENSE_URL_ID, _SIL_LICENSE_URL)
  font_data.set_name_record(ttfont, _VERSION_ID, new_version_string)
  font_data.set_name_record(ttfont, _VENDOR_URL, NOTO_URL)
  font_data.set_name_record(ttfont, _TRADMARK, TRADEMARK)
  if description:
    font_data.set_name_record(ttfont, _DESCRIPTION, description)

  ttfont['head'].fontRevision = float_revision

  dst_dir = path.dirname(dst_file)
  if not path.isdir(dst_dir):
    os.makedirs(dst_dir)
  ttfont.save(dst_file)
  print 'Wrote file.'


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-n', '--dry_run', help='Do not write fonts', action='store_true')
  parser.add_argument('--dst_root', help='root of destination', default='/tmp/swat')
  args = parser.parse_args()

  _swat_fonts(args.dst_root, args.dry_run)


if __name__ == "__main__":
    main()
