#!/usr/bin/python
#
# Copyright 2014 Google Inc. All rights reserved.
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

"""Fix some issues in Noto fonts before releasing them."""

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'

import array
from os import path
import re
import sys

from fontTools import ttLib

from nototools import font_data


def fix_revision(font):
    """Fix the revision of the font to match its version."""
    version = font_data.font_version(font)
    match = re.match(r'Version (\d{1,5})\.(\d{1,5})', version)
    major_version = match.group(1)
    minor_version = match.group(2)

    accuracy = len(minor_version)
    font_revision = font_data.printable_font_revision(font, accuracy)
    expected_font_revision = major_version+'.'+minor_version
    if font_revision != expected_font_revision:
        font['head'].fontRevision = float(expected_font_revision)
        print 'Fixed fontRevision to %s' % expected_font_revision
        return True

    return False


def fix_fstype(font):
    """Fix the fsType of the font."""
    if font['OS/2'].fsType != 0:
        font['OS/2'].fsType = 0
        print 'Updated fsType to 0'
        return True
    return False


# Reversed name records in Khmer and Lao fonts
NAME_CORRECTIONS = {
    'Sans Kufi': 'Kufi',
    'SansKufi': 'Kufi',
    'UI Khmer': 'Khmer UI',
    'UIKhmer': 'KhmerUI',
    'UI Lao': 'Lao UI',
    'UILao': 'LaoUI',
}

def fix_name_table(font):
    """Fix copyright and reversed values in the 'name' table."""
    modified = False
    name_records = font_data.get_name_records(font)

    copyright_data = name_records[0]
    years = re.findall('20[0-9][0-9]', copyright_data)
    year = min(years)
    copyright_data = u'Copyright %s Google Inc. All Rights Reserved.' % year

    if copyright_data != name_records[0]:
        print 'Updated copyright message to "%s"' % copyright_data
        font_data.set_name_record(font, 0, copyright_data)
        modified = True

    for name_id in [1, 3, 4, 6]:
        record = name_records[name_id]
        for source in NAME_CORRECTIONS:
            if source in record:
                record = record.replace(source, NAME_CORRECTIONS[source])
        if record != name_records[name_id]:
            font_data.set_name_record(font, name_id, record)
            print 'Updated name table record #%d to "%s"' % (
                name_id, record)
            modified = True

    return modified


def drop_hints(font):
    """Drops a font's hint."""
    modified = False
    glyf_table = font['glyf']
    for glyph_index in range(len(glyf_table.glyphOrder)):
        glyph_name = glyf_table.glyphOrder[glyph_index]
        glyph = glyf_table[glyph_name]
        if glyph.numberOfContours > 0:
            if glyph.program.bytecode:
                glyph.program.bytecode = array.array('B')
                modified = True
                print 'Dropped hints from glyph "%s"' % glyph_name
    return modified


def drop_tables(font, tables):
    """Drops the listed tables from a font."""
    modified = False
    for table in tables:
        if table in font:
            modified = True
            print 'Dropped table "%s"' % table
            modified = True
            del font[table]
    return modified


TABLES_TO_DROP = [
    # FontForge internal tables
    'FFTM', 'PfEd',
    # Microsoft VOLT internatl tables
    'TSI0', 'TSI1', 'TSI2', 'TSI3',
    'TSI5', 'TSID', 'TSIP', 'TSIS',
    'TSIV',
]

def main(argv):
    """Fix all fonts provided in the command line."""
    for font_file in argv[1:]:
        print 'Font file: %s' % font_file
        font = ttLib.TTFont(font_file)
        modified = False

        modified |= fix_revision(font)
        modified |= fix_fstype(font)
        modified |= fix_name_table(font)

        is_hinted = '/hinted' in font_file or '_hinted' in font_file
        if not is_hinted:
            modified |= drop_hints(font)

        tables_to_drop = TABLES_TO_DROP
        if not is_hinted:
            tables_to_drop += ['fpgm', 'prep', 'cvt']
        modified |= drop_tables(font, tables_to_drop)

        target_file = (
            path.dirname(font_file) +
            '/modified/' +
            path.basename(font_file))
        if modified:
            font.save(target_file)
        else:
            print 'No modification necessary'
        print


if __name__ == '__main__':
    main(sys.argv)
