#!/usr/bin/env python
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
#
"""Utilities for working with .ttc files."""

import argparse
import collections
from os import path
import struct
import subprocess

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._n_a_m_e import table__n_a_m_e as NameTable
from fontTools.ttLib.ttCollection import TTCollection

from nototools import tool_utils

TableEntry = collections.namedtuple("TableEntry", "tag,offset,length")


_EXTRACT_TOOL_PATH = "[afdko]/FDK/Tools/linux/otc2otf"
_BUILD_TOOL_PATH = "[afdko]/FDK/Tools/linux/otf2otc"


class TTCFile(object):
    """Holds some information from the sfnt headers in a .ttc file.

    - fonts is a list of FontEntry objects, in order.  It holds
    the format ('ttf' or 'otf') and a list of indices into the
    tables list.
    - tables is the list of TableEntry objects, in order. Each holds
    the table tag, offset, and length.  Offsets are relative to
    the very start of the data.  There is one entry for each unique
    table in the ttc.
    """

    def __init__(self, data=None):
        if data:
            self._build(data)
        else:
            self.fonts = []
            self.tables = []

    def _build(self, data):
        tag, version, font_count = struct.unpack(_ttcHeader, data[:_ttcHeaderSize])
        if tag not in [b"ttcf"]:
            raise ValueError("not a font collection")
        if version not in [0x10000, 0x20000]:
            raise ValueError("unrecognized version %s" % version)

        self.fonts = []
        self.tables = []
        for i in range(font_count):
            pos = _ttcHeaderSize + i * 4
            offset = struct.unpack(">L", data[pos : pos + 4])[0]
            self._build_font_entry(data, offset)

    def _build_font_entry(self, data, offset):
        limit = offset + _sfntHeaderSize
        version, num_tables = struct.unpack(_sfntHeader, data[offset:limit])[:2]
        if version == 0x10000:
            version_str = "1.0"
            font_fmt = "ttf"
        elif version == 0x4F54544F:
            version_str = "OTTO"
            font_fmt = "otf"
        else:
            raise ValueError("unrecognized sfnt version %x" % version)

        font_table_indices = []
        for j in range(num_tables):
            entry_pos = limit + j * _sfntHeaderEntrySize
            font_table_indices.append(self._build_table_entry(data, entry_pos))

        self.fonts.append(FontEntry(font_fmt, font_table_indices))

    def _build_table_entry(self, data, offset):
        limit = offset + _sfntHeaderEntrySize
        tag, checksum, offset, length = struct.unpack(
            _sfntHeaderEntry, data[offset:limit]
        )
        entry = TableEntry(tag, offset, length)
        for i, e in enumerate(self.tables):
            if e == entry:
                return i
        self.tables.append(entry)
        return len(self.tables) - 1


def ttcfile_dump(ttcfile):
    """Reads the file and dumps the information."""
    ttc = TTCollection(ttcfile)
    ttc_dump(ttc)


def ttc_dump(ttc):
    """Dumps the ttc information.

    It provides a likely filename for each file, and lists the tables, providing
    either the TableEntry data, or the table tag and index of the file that first
    referenced the table.
    """
    names = ttc_filenames(ttc)

    table_map = {}
    for font_index, font in enumerate(ttc):
        print("[%2d] %s" % (font_index, names[font_index]))
        for table_index, (tag, table) in enumerate(font.reader.tables.items()):
            table_entry = TableEntry(tag, table.offset, table.length)
            if table_entry not in table_map:
                table_map[table_entry] = (font_index, table_index)
                print(
                    "  [%2d] %s %8d %8d"
                    % (table_index, table.tag, table.offset, table.length)
                )
            else:
                table_from = table_map[table_entry]
                print(
                    "  [%2d] %s @%d.%d"
                    % (table_index, table.tag, table_from[0], table_from[1])
                )


def ttcfile_filenames(ttcfile):
    """Reads the file and returns the filenames."""
    ttc = TTCollection(ttcfile)
    return ttc_filenames(ttc)


def ttc_filenames(ttc):
    """Returns likely filenames for each ttc file.

    The filenames are based on the postscript name from the name table for each
    font.  When there is no information, the string '<unknown x>' is provided with
    either 'ttf' or 'otf' in place of 'x' depending on the info in the sfnt
    header.
    """
    names = []
    for font in ttc.fonts:
        file_name = ttfont_filename(font)
        names.append(file_name or ("<unknown %s>" % ttfont_format_as_extension(font)))
    return names


def ttfont_filename(font):
    name_table = font.get("name")
    if name_table:
        ps_name = name_table.getDebugName(6)
        if ps_name:
            file_name = ps_name
            if "-" not in ps_name:
                file_name += "-Regular"
            font_fmt = ttfont_format_as_extension(font)
            file_name += "." + font_fmt
            return file_name
    return None


def ttfont_format_as_extension(font):
    sfnt_version = font.reader.sfntVersion
    if sfnt_version == b"\x00\x01\x00\x00":
        return "ttf"
    if sfnt_version == b"OTTO":
        return "otf"
    raise ValueError("unrecognized sfnt version '%s'" % sfnt_version.decode("ascii"))


def ttcfile_build(output_ttc_path, fontpath_list):
    """Build a .ttc from a list of font files."""
    tool_utils.ensure_dir_exists(path.dirname(output_ttc_path))
    ttc = TTCollection()
    for fontpath in fontpath_list:
        font = TTFont(fontpath)
        ttc.fonts.append(font)
    ttc.save(output_ttc_path)


def ttc_namesfile_name(ttc_path):
    return path.splitext(path.basename(ttc_path))[0] + "_names.txt"


def ttcfile_build_from_namesfile(output_ttc_path, file_dir, namesfile_name=None):
    """Read names of files from namesfile and pass them to build_ttc to build
    a .ttc file.  The names file will default to one named after output_ttc and
    located in file_dir."""

    output_ttc_path = tool_utils.resolve_path(output_ttc_path)
    if not namesfile_name:
        namesfile_name = ttc_namesfile_name(output_ttc_path)

    namesfile_path = path.join(file_dir, namesfile_name)
    if not path.isfile(namesfile_path):
        raise ValueError("could not find names file %s" % namesfile_path)

    filenames = tool_utils.read_lines(namesfile_path)
    with tool_utils.temp_chdir(file_dir):
        # resolve filenames relative to file_dir
        fontpath_list = [tool_utils.resolve_path(n) for n in filenames]
    missing = [n for n in fontpath_list if not path.isfile(n)]
    if missing:
        raise ValueError(
            "%d files were missing:\n  %s" % (len(missing), "\n  ".join(missing))
        )
    ttcfile_build(output_ttc_path, fontpath_list)


def ttcfile_extract(input_ttc_path, output_dir):
    """Extract .ttf/.otf fonts from a .ttc file, and return a list of the names of
    the extracted fonts."""
    input_ttc_path = tool_utils.resolve_path(input_ttc_path)
    output_dir = tool_utils.ensure_dir_exists(output_dir)
    ttc = TTCollection(input_ttc_path)
    filenames = []
    for font in ttc:
        filename = ttfont_filename(font)
        font.save(path.join(output_dir, filename))
        filenames.append(filename)
    return filenames


def ttcfile_extract_and_write_namesfile(
    input_ttc_path, output_dir, namesfile_name=None
):
    """Call ttcfile_extract and in addition write a file to output dir containing
    the names of the extracted files.  The name of the names file will default to
    one based on the basename of the input path. It is written to output_dir."""
    names = ttcfile_extract(input_ttc_path, output_dir)
    if not namesfile_name:
        namesfile_name = ttc_namesfile_name(input_ttc_path)
    tool_utils.write_lines(names, path.join(output_dir, namesfile_name))


def main():
    epilog = """
  names (default action)
    print just the name of each font in the ttc, in order.
  dump
    print, in order, the name of each font in the ttc followed by a list
    of its tables and where they come from-- either an offset in the ttc
    and length, or "@xx.yy" where xx is the index of the font that first
    referenced that table data, and yy the index of the table in that font.
  extract
    extract the contents of the .ttc to a directory.  An additional file
    named after the .ttc with a suffix of '_names.txt' lists the file
    names in the order in which they were in the .ttc.
  build
    build the .ttc using the contents of a directory.  The name of the
    .ttc is used to look in the directory for a list of font file names
    (like that built by 'extract'); these fonts are included in the .ttc
    in the listed order.
  """

    parser = argparse.ArgumentParser(
        description="Use afdko to operate on ttc files.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-f", "--ttcfile", help="ttc file to operate on", metavar="ttc", required=True
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="filedir",
        help="directory for individual files",
        metavar="dir",
        default=".",
    )
    parser.add_argument(
        "-o",
        "--op",
        help="operation to perform (names, dump, extract, build)",
        metavar="op",
        choices="names dump extract build".split(),
        default="names",
    )
    args = parser.parse_args()

    if args.op == "dump":
        ttcfile_dump(args.ttcfile)
    elif args.op == "names":
        print("\n".join(ttcfile_filenames(args.ttcfile)))
    elif args.op == "extract":
        ttcfile_extract_and_write_namesfile(args.ttcfile, args.filedir)
    elif args.op == "build":
        ttcfile_build_from_namesfile(args.ttcfile, args.filedir)


if __name__ == "__main__":
    main()
