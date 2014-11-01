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

"""Get high-level font data from a font object."""

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'


def get_name_records(font):
    """Get a font's 'name' table records as a dictionary of Unicode strings."""
    name_table = font['name']
    names = {}
    for record in name_table.names:
        name_ids = (record.platformID, record.platEncID, record.langID)
        if name_ids != (3, 1, 0x409):
            continue
        names[record.nameID] = unicode(record.string, 'UTF-16BE')
    return names


def set_name_record(font, record_id, value):
    """Sets a record in the 'name' table to a given string.

    If the value is None, the name record is dropped."""
    records_to_drop = set()
    names = font['name'].names
    for record_number, record in enumerate(names):
        name_ids = (record.platformID, record.platEncID, record.langID)
        if name_ids != (3, 1, 0x409):
            continue
        if record.nameID == record_id:
            if value is None:
                records_to_drop.add(record_number)
            else:
                record.string = value.encode('UTF-16BE')
    if records_to_drop:
        font['name'].names = [
            record for record_number, record in enumerate(names)
            if record_number not in records_to_drop]


def font_version(font):
    """Returns the font version from the 'name' table."""
    names = get_name_records(font)
    return names[5]


def font_name(font):
    """Returns the font name from the 'name' table."""
    names = get_name_records(font)
    return names[4]


def printable_font_revision(font, accuracy=2):
    """Returns the font revision as a string from the 'head' table."""
    font_revision = font['head'].fontRevision
    font_revision_int = int(font_revision)
    font_revision_frac = int(
        round((font_revision - font_revision_int) * 10**accuracy))

    font_revision_int = str(font_revision_int)
    font_revision_frac = str(font_revision_frac).zfill(accuracy)
    return font_revision_int+'.'+font_revision_frac


def get_cmap(font):
    """Get the cmap dictionary of a font."""
    cmap_table = font['cmap']
    cmaps = {}
    for table in cmap_table.tables:
        if (table.format, table.platformID, table.platEncID) in [
            (4, 3, 1), (12, 3, 10)]:
            cmaps[table.format] = table.cmap
    if 12 in cmaps:
        return cmaps[12]
    elif 4 in cmaps:
        return cmaps[4]
    return {}


UNICODE_CMAPS = {(4, 0, 3), (4, 3, 1), (12, 3, 10)}

def delete_from_cmap(font, chars):
    """Delete all characters in a list from the cmap tables of a font."""
    cmap_table = font['cmap']
    for table in cmap_table.tables:
        if (table.format, table.platformID, table.platEncID) in UNICODE_CMAPS:
            for char in chars:
                del table.cmap[char]


def add_to_cmap(font, mapping):
    """Adds a codepoint to glyph mapping to a font's cmap."""
    cmap_table = font['cmap']
    for table in cmap_table.tables:
        if (table.format, table.platformID, table.platEncID) in UNICODE_CMAPS:
            for code, glyph in mapping.iteritems():
                table.cmap[code] = glyph
