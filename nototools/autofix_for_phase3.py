#!/usr/bin/env python
#
# Copyright 2017 Google Inc. All rights reserved.
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

"""Autofix phase 3 binaries, and autohint.

Quick tool to make fixes to some fonts that are 'ok for release' but
still have issues.  Main goal here is to autohint fonts that can be
hinted.  We also put more info into the version string.
"""

# TODO: ideally, we don't autofix at all, but if we continue to do this
# it would be better to unify the lint checks and the autofix code to
# ensure they agree in their expectations.

import argparse
import datetime
import glob
import os
from os import path
import re
import subprocess

from fontTools import ttLib

from nototools import font_data
from nototools import noto_data
from nototools import noto_fonts
from nototools import tool_utils

_version_info_re = re.compile(
    r'GOOG;noto-fonts:(\d{4})(\d{2})(\d{2}):([0-9a-f]{12})')

def _check_version_info(version_info):
  """ensure version info looks reasonable, for example:
  'GOOG;noto-fonts:20170220:a8a215d2e889'.  Raise an exception
  if it does not."""
  m = _version_info_re.match(version_info)
  if not m:
    raise Exception('did not match version info "%s"' % version_info)
  year = int(m.group(1))
  month = int(m.group(2))
  day = int(m.group(3))
  commit_hash = m.group(4)
  today = datetime.date.today()
  if 2017 <= year:
    try:
      encoded_date = datetime.date(year, month, day)
    except Exception as e:
      raise Exception(
          '%04d-%02d-%02d in %s is not a valid date' % (
              year, month, day, version_info))
    if encoded_date > today:
      raise Exception('%s in %s is after the current date' % (
          encoded_date, version_info))
  else:
    raise Exception('date in %s appears too far in the past' % version_info)


def _check_autohint(script):
  if script and not(
      script in ['no-script'] or script in noto_data.HINTED_SCRIPTS):
    raise Exception('not a hintable script: "%s"' % script)


def autofix_fonts(font_names, dstdir, version_info, autohint, dry_run):
  dstdir = tool_utils.ensure_dir_exists(dstdir)

  _check_version_info(version_info)
  _check_autohint(autohint)

  font_names.sort()
  print 'Processing\n  %s' % '\n  '.join(font_names)
  print 'Dest dir: %s' % dstdir
  if dry_run:
    print '*** dry run %s***' % ('(autohint) ' if autohint else '')
  for f in font_names:
    fix_font(f, dstdir, version_info, autohint, dry_run)


version_re = re.compile(r'Version (\d+\.\d{2,3})')
def get_revision(font, fname):
  if 'Armenian' in fname:
    # special case phase 2 version string >= 2.0
    return '2.040'

  # sometimes the fontRevision and version string don't match, and the
  # fontRevision is bad, so we prefer the version string.

  version_string = font_data.font_version(font)
  m = version_re.match(version_string)
  if not m:
    raise Exception('could not match "%s"' % version_string)
  revision = m.group(1)
  if float(revision) < 2.0:
    return '2.000'

  original_revision = revision
  chars = [cp for cp in revision]
  index = len(chars) - 1
  while index >= 0 and chars[index] != '.':
    if chars[index] < '9':
      chars[index] = chr(ord(revision[index]) + 1)
      return ''.join(chars)
    else:
      chars[index] = '0'
    index -= 1

  raise Exception('unable to increment revision "%s"' % original_revision)


def _get_font_info(f):
  font_info = noto_fonts.get_noto_font(f)
  if not font_info:
    raise Exception('not a noto font: "%s"' % f)
  return font_info

def _is_ui_metrics(f):
  return _get_font_info(f).is_UI_metrics


def _autohint_code(f, script):
  """Return 'not-hinted' if we don't hint this, else return the ttfautohint
  code, which might be None if ttfautohint doesn't support the script.
  Note that LGC and MONO return None."""

  if script == 'no-script':
    return script
  if not script:
    script = noto_fonts.script_key_to_primary_script(_get_font_info(f).script)
  return noto_data.HINTED_SCRIPTS.get(script, 'not-hinted')


def autohint_font(src, dst, script, dry_run):
  code = _autohint_code(src, script)
  if code == 'not-hinted':
    print 'Warning: no hinting information for %s, script %s' % (src, script)
    return

  if code == None:
    print 'Warning: unable to autohint %s' % src
    return

  if code == 'no-script':
    args = ['ttfautohint', '-t', '-W', src, dst]
  else:
    args = ['ttfautohint', '-t', '-W', '-f', code, src, dst]
  if dry_run:
    print 'dry run would autohint:\n  "%s"' % ' '.join(args)
    return

  hinted_dir = tool_utils.ensure_dir_exists(path.dirname(dst))
  subprocess.check_call(args)

  print 'wrote autohinted %s using %s' % (dst, code)


def _alert(val_name, cur_val, new_val):
  if isinstance(cur_val, basestring):
    tmpl = 'update %s\n  from: "%s"\n    to: "%s"'
  else:
    tmpl = 'update %s\n  from: %4d\n    to: %4d'
  print  tmpl % (val_name, cur_val, new_val)


def _alert_and_check(val_name, cur_val, new_val, max_diff):
  _alert(val_name, cur_val, new_val)
  if abs(cur_val - new_val) > max_diff:
    raise Exception(
        'unexpectedly large different in expected and actual %s' % val_name)

def fix_font(f, dstdir, version_info, autohint, dry_run):
  print '\n-----\nfont:', f
  font = ttLib.TTFont(f)
  fname = path.basename(f)
  expected_font_revision = get_revision(font, fname)
  if expected_font_revision != None:
    font_revision = font_data.printable_font_revision(font, 3)
    if font_revision != expected_font_revision:
      _alert('revision', font_revision, expected_font_revision)
      font['head'].fontRevision = float(expected_font_revision)

    names = font_data.get_name_records(font)
    NAME_ID = 5
    font_version = names[NAME_ID]
    expected_version = (
        'Version %s;%s' % (expected_font_revision, version_info))
    if font_version != expected_version:
      _alert('version string', font_version, expected_version)
      font_data.set_name_record(font, NAME_ID, expected_version)

  expected_upem = 2048
  upem = font['head'].unitsPerEm
  if upem != expected_upem:
    print 'expected %d upem but got %d upem' % (expected_upem, upem)

  if _is_ui_metrics(fname):
    if upem == 2048:
      expected_ascent = 2163
      expected_descent = -555
    elif upem == 1000:
      expected_ascent = 1069
      expected_descent = -293
    else:
      raise Exception('no expected ui ascent/descent for upem: %d' % upem)

    font_ascent = font['hhea'].ascent
    font_descent = font['hhea'].descent
    if font_ascent != expected_ascent:
      _alert_and_check('ascent', font_ascent, expected_ascent, 2)
      font['hhea'].ascent = expected_ascent
      font['OS/2'].sTypoAscender = expected_ascent
      font['OS/2'].usWinAscent = expected_ascent

    if font_descent != expected_descent:
      _alert_and_check('descent', font_descent, expected_descent, 2)
      font['hhea'].descent = expected_descent
      font['OS/2'].sTypoDescender = expected_descent
      font['OS/2'].usWinDescent = -expected_descent

  tool_utils.ensure_dir_exists(path.join(dstdir, 'unhinted'))

  dst = path.join(dstdir, 'unhinted', fname)
  if dry_run:
    print 'dry run would write:\n  "%s"' % dst
  else:
    font.save(dst)
    print 'wrote %s' % dst

  if autohint:
    autohint_font(dst, path.join(dstdir, 'hinted', fname), autohint, dry_run)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-d', '--dest_dir', help='directory into which to write swatted fonts',
      metavar='dir', default='swatted')
  parser.add_argument(
      '-f', '--fonts', help='paths of fonts to swat', nargs='+',
      metavar='font')
  parser.add_argument(
      '-i', '--version_info', help='version info string', required=True,
      metavar='str')
  parser.add_argument(
      '-a', '--autohint', help='autohint fonts (using script if provided)',
      nargs='?', const='no-script', metavar='code')
  parser.add_argument(
      '-n', '--dry_run', help='process checks but don\'t fix',
      action='store_true')
  args = parser.parse_args()

  autofix_fonts(
      args.fonts, args.dest_dir, args.version_info, args.autohint, args.dry_run)


if __name__ == '__main__':
  main()
