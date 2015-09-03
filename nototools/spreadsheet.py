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

"""Get information from the status spreadsheet with MTI"""

SPREADSHEET_NAME = 'Noto Project Status (Phase II)- go-noto - Unicode-Monotype.csv'

import argparse
import csv
import os
from os import path
import re

from nototools import noto_fonts


def check_spreadsheet(src_file):
  filenames = set()
  prev_script_name = None
  with open(src_file) as csvfile:
    reader = csv.DictReader(csvfile)
    for index, row in enumerate(reader):

      fonts = row['Fonts'].replace('\u00a0', ' ')
      hinting = row['Hinting']
      status = row['Status']
      accepted_version = row['Accepted Version']
      eta = row['ETA']
      note = row['Note']

      # family script style (variant UI) weight, mostly
      if not re.match(r'Noto ((?:Arabic (?:Kufi|Naskh))|Color Emoji|Emoji|Sans|Serif|Urdu Nastaliq)'
                      r'(.*?)(:? (UI))? (Thin|Light|DemiLight|Regular|Medium|Bold|Black|Italic|Bold Italic)', fonts):
        print 'Did not match "%s"' % fonts
  return

  fonts = noto_fonts.get_noto_fonts()
  noto_filenames = set([path.basename(font.filepath) for font in fonts
                        if not font.is_cjk and font.family == 'Noto'])

  unknown_fonts = filenames - noto_filenames
  missing_fonts = noto_filenames - filenames
  if unknown_fonts:
    print 'There are %d unknown font names' % len(unknown_fonts)
    print '  ' + '\n  '.join(sorted(unknown_fonts))
  if missing_fonts:
    print 'There are %d missing font names' % len(missing_fonts)
    print '  ' + '\n  '.join(sorted(missing_fonts))


def main():
  default_file = path.expanduser(path.join('~/Downloads', SPREADSHEET_NAME))

  parser = argparse.ArgumentParser()
  parser.add_argument('-sf', '--src_file', help='path to tracking spreadsheet csv',
                      metavar='fname', default=default_file)

  args = parser.parse_args()
  check_spreadsheet(args.src_file)

if __name__ == "__main__":
    main()
