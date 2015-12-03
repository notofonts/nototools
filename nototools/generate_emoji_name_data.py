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

"""Generate name data for emoji resources. Currently in json format."""

import argparse
import collections
import glob
import os
from os import path
from nototools import unicode_data


REGIONAL_INDICATOR_A = 0x1f1e6
REGIONAL_INDICATOR_Z = 0x1f1ff


def is_regional_indicator(cp):
  return cp >= REGIONAL_INDICATOR_A and cp <= REGIONAL_INDICATOR_Z


def is_ascii_digit(cp):
  return cp >= ord('0') and cp <= ord('9')


def keep_sequence(cps):
  if len(cps) > 1:
    return True
  cp = cps[0]
  if (unicode_data.is_private_use(cp) or
      unicode_data.category(cp)[0] not in ['L', 'P', 'S'] or
      is_regional_indicator(cp) or
      is_ascii_digit(cp) or
      cp == ord('#')):
    return False
  return True


def is_flag_sequence(cps):
  if len(cps) != 2:
    return False
  for cp in cps:
    if cp < REGIONAL_INDICATOR_A or cp > REGIONAL_INDICATOR_Z:
      return False
  return True


def flag_sequence_name(cps):
  return ''.join(unichr(cp - REGIONAL_INDICATOR_A + ord('A')) for cp in cps)


_NAME_FIXES = {
    'Oclock': "O'Clock",
    'Mans': "Man's",
    'Womans': "Woman's",
    'Mens': "Men's",
    'Womens': "Women's"
}

def unicode_name(cp):
  name = unicode_data.name(cp).title()
  for k, v in _NAME_FIXES.iteritems():
    name = name.replace(k, v)
  return name


def generate_names(srcdir, outfile, force):
  if not path.isdir(srcdir):
    print '%s is not a directory' % srcdir
    return

  if path.exists(outfile):
    if not force:
      print '%s already exists' % outfile
      return
    if not path.isfile(outfile):
      print '%s is not a file' % outfile
      return
  else:
    parent = path.dirname(outfile)
    if parent and not os.path.exists(parent):
      os.makedirs(parent)

  output = {}
  skipped = []
  for f in glob.glob(path.join(srcdir, 'emoji_u*.png')):
    fname = path.basename(f)
    parts = fname[7:-4].split('_')
    # Omit emoji presentation variation selector, it should not be necessary.
    cps = [int(part, 16) for part in parts if part != 'fe0f']
    if not keep_sequence(cps):
      skipped.append(cps)
      continue

    sequence = ''.join('&#x%x;' % cp for cp in cps)
    if len(cps) == 1:
      name = unicode_name(cps[0])
    elif is_flag_sequence(cps):
      name = flag_sequence_name(cps)
    else:
      name = ''
    output[tuple(cps)] = (fname, sequence, name)

  with open(outfile, 'w') as f:
    f.write('[\n')
    for k in sorted(output):
      f.write('  {"image":"%s", "sequence":"%s", "name":"%s"},\n' % output[k])
    f.write(']\n')
  print 'wrote %s' % outfile

  if skipped:
    print 'skipped %d images:' % len(skipped)
    for cps in sorted(skipped):
      print '  %s (%s)' % (
          '_'.join('%04x' % cp for cp in cps),
          ','.join(unicode_data.name(cp, '') for cp in cps))


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--srcdir', help='directory containing images',
                      metavar='dir', required = True)
  parser.add_argument('-o', '--outfile', help='name of output file (default '
                      '"emoji_names.json"',
                      metavar='fname', default='emoji_names.json')
  parser.add_argument('-f', '--force', help='overwrite output file if it '
                      'exists', default=False, action='store_true')
  args = parser.parse_args()
  generate_names(args.srcdir, args.outfile, args.force)


if __name__ == "__main__":
    main()
