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

"""Process a family description file.

You can check the file, and generate a list of font file names from it.
This list can be passed to noto_names to generate the name data.

The file is a list of Noto family names (see noto_fonts.py) interspersed with
definitions of what WWS style combinations apply to that file.  See
_get_stylenames() for the format.  Each style definition applies to each
following family until the next style definition."""

import argparse
import re

from nototools import noto_fonts

_style_re = re.compile(r'--\s+(.*)\s+--')
_extended_style_re = re.compile(r'^([TRBH]+)(?:/([CR]+)(?:/([RI]+))?)?$')

# Below we use the longest names we intend, so that the noto_names code can
# identify which families need extra short abbreviations.  The style of
# abbreviation is based on the longest names in the family.

_WEIGHT_NAMES = {
    'T': 'Thin',
    'R': 'Regular',
    'B': 'Bold',
    'H': 'ExtraBold' # Nee 'Heavy'. Not 'Black' because 'ExtraBold' is longer.
}

_WIDTH_NAMES = {
    'C': 'SemiCondensed', # We use this since it is longer. We don't expect to
                          # use ExtraCondensed.
    'R': ''
}

_ITALIC_NAMES = {
    'I': 'Italic',
    'R': '',
}

def _get_stylenames(styles):
  """Returns the list of style names for the encoded styles.  These are the
  (master-ish) style names encoded as weights / widths/ italic, where weights
  is any of 'T', 'R', 'B', or 'H', widths any of 'C' or 'R', and italic 'I'.
  If there's not an italic then the italic is omitted, if there's only
  regular width and no italic then widths are omitted."""
  m = _extended_style_re.match(styles)
  assert m
  weights = m.group(1)
  widths = m.group(2) or 'R'
  slopes = m.group(3) or 'R'

  names = []
  for wd in widths:
    width_name = _WIDTH_NAMES[wd]
    for wt in weights:
      weight_name = _WEIGHT_NAMES[wt]
      for it in slopes:
        italic_name = _ITALIC_NAMES[it]
        final_weight_name = weight_name
        if wt == 'R' and (width_name or italic_name):
          final_weight_name = ''
        names.append(width_name + final_weight_name + italic_name)
  return names


def check_familyname(name, styles):
  notofont = noto_fonts.get_noto_font('unhinted/' + name + '-Regular.ttf')
  if not notofont:
    print 'Error: could not parse', name
    return False
  print name, noto_fonts.noto_font_to_wws_family_id(notofont), styles
  return True


def generate_family_filenames(name, styles):
  """Name is the family name portion of a Noto filename.  Styles is the
  encoding of the styles, see _get_stylenames."""
  stylenames = _get_stylenames(styles)
  return [name + '-' + s + '.ttf' for s in stylenames]


def _for_all_familynames(namefile, fn):
  """Call fn passing the family name and style descriptor for
  all families in namefile. '#' is a comment to eol, blank lines are
  ignored."""
  styles = None
  with open(namefile, 'r') as f:
    for name in f:
      ix = name.find('#')
      if ix >= 0:
        name = name[:ix]
      name = name.strip()
      if not name:
        continue

      m = _style_re.match(name)
      if m:
        styles = m.group(1)
        continue

      # Catch a common error in which an intended style tag didn't match the
      # regex.
      if name[0] == '-':
        raise ValueError('Looks like a bad style tag: "%s"' % name)
      if styles == None:
        raise ValueError('Styles must be set before first familyname.')

      fn(name, styles)


def check_familynames(namefile):
  passed = [True]
  def fn(name, styles):
    name_passed = check_familyname(name, styles)
    passed[0] &= name_passed
  _for_all_familynames(namefile, fn)
  return passed[0]


def generate_filenames(namefile, outfile):
  namelist = []
  def fn(name, styles):
    namelist.extend(generate_family_filenames(name, styles))
  _for_all_familynames(namefile, fn)
  allnames = '\n'.join(namelist)
  if outfile:
    with open(outfile, 'w') as f:
      f.write(allnames)
      f.write('\n')
  else:
    print allnames


def main():
  DEFAULT_NAMEDATA = 'familyname_and_styles.txt'

  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-f', '--familynamedata', help='file containing family name/style data'
      ' (default %s)' % DEFAULT_NAMEDATA, metavar='file',
      default=DEFAULT_NAMEDATA)
  parser.add_argument(
      '-c', '--check', help='check family name/style data', action='store_true')
  parser.add_argument(
      '-w', '--write', help='write filenames, default stdout', nargs='?',
      const='stdout', metavar='file')
  args = parser.parse_args()

  if args.check:
    passed = check_familynames(args.familynamedata)
    if not passed:
      print 'Check failed, some files had errors.'
      return
    print 'Check succeeded.'

  if args.write:
    outfile = None if args.write == 'stdout' else args.write
    if not outfile and args.check:
      print
    generate_filenames(args.familynamedata, outfile)
    if outfile:
      print 'Wrote', outfile


if __name__ == '__main__':
  main()
