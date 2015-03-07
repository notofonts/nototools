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

import argparse
import array
import os
from os import path
import re
import sys

from fontTools import ttLib

from nototools import font_data
import notoconfig

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


def fix_vendor_id(font):
    """Fix the vendor ID of the font."""
    if font['OS/2'].achVendID != 'GOOG':
        font['OS/2'].achVendID = 'GOOG'
        print 'Changed font vendor ID to GOOG'
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

TRADEMARK_LINE = u'Noto is a trademark of Google Inc.'

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

    if name_records[7] != TRADEMARK_LINE:
      font_data.set_name_record(font, 7, TRADEMARK_LINE)
      modified = True
      print 'Updated name table record 7 to "%s"' % TRADEMARK_LINE

    if name_records.has_key(16):
        font_data.set_name_record(font, 16, None)
        print 'Name table record #16 dropped'
        modified = True

    return modified


def fix_attachlist(font):
    """Fix duplicate attachment points in GDEF table."""
    modified = False
    try:
        attach_points = font['GDEF'].table.AttachList.AttachPoint
    except (KeyError, AttributeError):
        attach_points = []

    for attach_point in attach_points:
        points = sorted(set(attach_point.PointIndex))
        if points != attach_point.PointIndex:
            attach_point.PointIndex = points
            attach_point.PointCount = len(points)
            modified = True

    if modified:
        print 'Fixed GDEF.AttachList'

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

def fix_font(src_file, dst_file, is_hinted, save_unmodified):
    """Fix font in src_file and write to dst_file.  If is_hinted is false,
    strip hints.  If unmodified, don't write destination unless save_unmodified
    is true."""

    print 'Font file: %s' % src_file
    font = ttLib.TTFont(src_file)
    modified = False

    modified |= fix_revision(font)
    modified |= fix_fstype(font)
    modified |= fix_vendor_id(font)
    modified |= fix_name_table(font)
    modified |= fix_attachlist(font)

    tables_to_drop = TABLES_TO_DROP
    if not is_hinted:
        modified |= drop_hints(font)
        tables_to_drop += ['fpgm', 'prep', 'cvt']

    modified |= drop_tables(font, tables_to_drop)
    if not modified:
        print 'No modification necessary'
    if modified or save_unmodified:
        # wait until we need it before we create the dest directory
        dst_dir = path.dirname(dst_file)
        if not path.isdir(dst_dir):
            os.makedirs(dst_dir)
        font.save(dst_file)
        print 'Wrote %s' % dst_file

def fix_fonts(src_root, dst_root, name_pat, save_unmodified):
    src_root = path.abspath(src_root)
    dst_root = path.abspath(dst_root)
    name_rx = re.compile(name_pat)
    for root, dirs, files in os.walk(src_root):
        for file in files:
            src_file = path.join(root, file)
            rel_path = src_file[len(src_root)+1:] # +1 to ensure no leading slash.
            if not name_rx.search(rel_path):
                continue
            dst_file = path.join(dst_root, rel_path)
            is_hinted = root.endswith('/hinted') or '_hinted' in file
            fix_font(src_file, dst_file, is_hinted, save_unmodified)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name_pat', help='regex for files to fix, '
                        'searches relative path from root')
    parser.add_argument('--src_root', help='root of src files',
                        default=notoconfig.values.get('alpha'))
    parser.add_argument('--dst_root', help='root of destination',
                        default=notoconfig.values.get('autofix'))
    parser.add_argument('--save_unmodified', help='save even unmodified files',
                        action='store_true')
    args = parser.parse_args()

    if not args.src_root:
        # not on command line and not in user's .notoconfig
        print 'no src root specified.'
        return
    if not path.isdir(args.src_root):
        print '%s does not exist or is not a directory' % args.src_root
        return

    if not args.dst_root:
        # not on command line and not in user's .notoconfig
        args.dst_root = path.join(path.dirname(args.src_root), 'modified')
    if not path.isdir(args.dst_root):
        if path.exists(args.dst_root):
            print '%s exists and is not a directory' % args.dst_root
            return

    fix_fonts(args.src_root, args.dst_root, args.name_pat, args.save_unmodified)


if __name__ == '__main__':
    main()
