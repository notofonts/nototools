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

SPREADSHEET_NAME = 'GoogleChrome_WeeklyScriptStatus - ReworkStatus.csv'

import argparse
import csv
import os
from os import path

from nototools import noto_fonts
"""
{'Styles': 'Sans Regular', 'Status': 'QA approved 4/17/2014', 'Version Tested': '1.01', 'SCRIPT': 'Brahmi', 'Xiangye Report dated 4/17/2015 - # of issues': 'PASSED', 'Note': '', 'Google Acceptance Date': '6/6/2014', 'ISSUE\xc2\xa0REPORT FILE NAME (internal)': '_Brahmi_IssueReport.xlsx', 'Date Delivered to Google': '4/17/2014'}
"""

# map script/style combo to what we'd actually expect to see
FIXES = {
    ('Emoji', 'Sans Regular'): ('', 'Emoji Regular'),
    ('Kufi', 'Regular'): ('Arabic', 'Kufi Regular'),
    ('Kufi', 'Bold'): ('Arabic', 'Kufi Bold'),
    ('Kufi', 'Sans UI Regular'): ('Latin', 'Sans UI Regular'),
    ('Kufi', 'Sans UI Italic'): ('Latin', 'Sans UI Italic'),
    ('Kufi', 'Sans UI Bold'): ('Latin', 'Sans UI Bold'),
    ('Kufi', 'Sans UI Bold Italic'): ('Latin', 'Sans UI Bold Italic'),
    ('Mongolian', 'Bold'): ('Mongolian', 'Sans Bold'),
    ('Naskh Arabic', 'Sans Regular'): ('Arabic', 'Naskh Regular'),
    ('Naskh Arabic', 'Sans Bold'): ('Arabic', 'Naskh Bold'),
    ('Naskh Arabic', 'Sans UI Regular'): ('Arabic', 'Naskh UI Regular'),
    ('Naskh Arabic', 'Sans UI Bold'): ('Arabic', 'Naskh UI Bold'),
    ('Nastaliq', 'Regular'): ('Arabic', 'Nastaliq Regular'),
    ('Syriac Estrangelo', 'Sans Regular'): ('Syriac Estrangela', 'Sans Regular'),
    }

def check_spreadsheet(src_file):
  filenames = set()
  prev_script_name = None
  with open(src_file) as csvfile:
    reader = csv.DictReader(csvfile)
    for index, row in enumerate(reader):
      script_name = row['SCRIPT'].replace('\u00a0', ' ')
      if script_name == 'SERIF INDICS':
        # ignore serifs, not delivered yet
        break

      style_name = row['Styles'].replace('\u00a0', ' ')
      if not style_name:
        # assume blank row
        continue

      if not script_name:
        script_name = prev_script_name
      else:
        prev_script_name = script_name

      if (script_name, style_name) in FIXES:
        script_name, style_name = FIXES[(script_name, style_name)]

      # handle script + variant, i.e. Syriac
      script_name = script_name.replace(' ', '')

      style_parts = style_name.split(' ')
      style = style_parts[0]
      variant = ''
      if len(style_parts) == 1:
        print '--> bad styles info "%s"' % style_name
        continue

      if len(style_parts) == 2:
        weight_slope = style_parts[1]
      else:
        if style_parts[-2] == 'Bold' and style_parts[-1] == 'Italic':
          style_parts = style_parts[:-2]
          style_parts.append('BoldItalic')
        if len(style_parts) == 2:
          weight_slope = style_parts[1]
        elif len(style_parts) == 3:
          variant = style_parts[1]
          weight_slope = style_parts[2]
        else:
          print '--> bad styles info "%s"' % style_name
          continue

      deliver_date = row['Date Delivered to Google']
      accept_date = row['Google Acceptance Date']
      note = row['Note']
      version_tested = row['Version Tested']

      file_script_name = ('' if script_name == 'Latin' else
                          'Urdu' if script_name == 'Arabic' and style == 'Nastaliq' else
                          script_name)
      filename = 'Noto%s%s%s-%s.ttf' % (style, file_script_name, variant, weight_slope)
      print ','.join([str(index + 2),script_name, style_name, filename])
      if filename in filenames:
        print 'already have file named %s' % filename
      else:
        filenames.add(filename)

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
