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
# test reading bitmap dump

from __future__ import absolute_import
from __future__ import print_function

"""Generate comparison data for two glyph image files.

This takes two sets of glyph image data, creates pairs of images, and
writes those image comparisons to an output dir."""

import argparse
import collections
import re
from datetime import datetime
from os import path

from fontTools import ttLib

from nototools import font_data
from nototools import tool_utils

from nototools.glyph_image import glyph_image_pair
from nototools.glyph_image import glyph_image


def select_named_pairs(pair_data):
    """Returns a list of name, base id, target id tuples
    for the codepoint and primary pairs in pair_data.
    Generates a name for each selected pair.  If the pair is matched
    by codepoint, use the 'u(ni)XXXX' name of the codepoint.  Else use
    a name formed from the glyph id(s). This handles unmatched
    pairs (where one glyph id is -1)."""

    named_pairs = []
    if pair_data.cp_pairs is not None:
        for b, t, cp in pair_data.cp_pairs:
            name = "%s%04X" % ("uni" if cp < 0x10000 else "u", cp)
            named_pairs.append((name, b, t))
    if pair_data.pri_pairs is not None:
        for b, t, _ in pair_data.pri_pairs:
            if b == t:
                name = "g_%05d" % b
            elif t == -1:
                name = "g_b%05d" % b
            elif b == -1:
                name = "g_t%05d" % t
            else:
                name = "g_b%05d_t%05d" % (b, t)
            named_pairs.append((name, b, t))
    return named_pairs


GlyphImageCompareData = collections.namedtuple(
    "GlyphImageCompareData", "base_fdata target_fdata base_gdata target_gdata pair_data"
)
GlyphImageFontData = collections.namedtuple(
    "GlyphImageFontData", glyph_image.FileHeader._fields + ("codepoints", "version")
)
GlyphImagePairData = collections.namedtuple(
    "GlyphImagePairData", "max_frame, pair_data"
)


def create_compare_data(
    base_collection, target_collection, named_pairs, similarities, max_frame
):
    def create_font_data(font, collection):
        cps = len(font_data.get_cmap(font))
        version = font_data.font_version(font)
        return GlyphImageFontData._make(collection.file_header + (cps, version))

    def create_glyph_data(font, collection):
        glyphorder = font.getGlyphOrder()
        data = [None] * len(glyphorder)
        name_to_index = {g: i for i, g in enumerate(glyphorder)}
        cmap = font_data.get_cmap(font)
        # if different cps map to the same glyph, this uses the last one
        index_to_cp = {name_to_index[cmap[cp]]: cp for cp in cmap}

        for i, g in enumerate(glyphorder):
            cp = index_to_cp.get(i, -1)
            name = "" if (i == 0 or cp >= 0 or g == "glyph%05d" % i) else g
            adv = collection.image_dict[i].adv.int
            data[i] = (adv, cp, name)
        return data

    def create_pair_data():
        image_data = []
        for (name, b, t), similarity in zip(named_pairs, similarities):
            image_data.append((name, b, t, similarity))
        return GlyphImagePairData(max_frame, image_data)

    base_font = ttLib.TTFont(base_collection.file_header.file)
    target_font = ttLib.TTFont(target_collection.file_header.file)

    base_fdata = create_font_data(base_font, base_collection)
    target_fdata = create_font_data(target_font, target_collection)

    base_gdata = create_glyph_data(base_font, base_collection)
    target_gdata = create_glyph_data(target_font, target_collection)

    pair_data = create_pair_data()
    return GlyphImageCompareData(
        base_fdata, target_fdata, base_gdata, target_gdata, pair_data
    )


def write_compare_data(gic_data, fd):
    def write_font_data(label, fdata):
        print("> %s: [" % label, file=fd)
        for k in GlyphImageFontData._fields:
            print("> %s: %s" % (k, getattr(fdata, k)), file=fd)
        print("]", file=fd)

    def write_glyph_data(label, gdata):
        print("> %s: %d" % (label, len(gdata)), file=fd)
        print("# index advance cp name", file=fd)
        for i, (adv, cp, g) in enumerate(gdata):
            print(
                "%d;%d;%s;%s" % (i, adv, "%04x" % cp if cp >= 0 else "", g or ""),
                file=fd,
            )

    def write_pair_data(label, pdata):
        print("> %s:" % label, file=fd)
        print("> max_frame: %d %d %d %d" % pdata.max_frame, file=fd)
        print("> pairs: %d" % len(pdata.pair_data), file=fd)
        print("# image_name base target similarity (pct)", file=fd)
        for name, base, target, similarity in pdata.pair_data:
            base_str = "%d" % base if base >= 0 else ""
            target_str = "%d" % target if target >= 0 else ""
            print("%s;%s;%s;%s" % (name, base_str, target_str, similarity), file=fd)

    time = datetime.now()
    print("# %s" % time.strftime("%Y-%m-%d %H:%M:%S"), file=fd)
    write_font_data("base_fdata", gic_data.base_fdata)
    write_font_data("target_fdata", gic_data.target_fdata)
    write_glyph_data("base_gdata", gic_data.base_gdata)
    write_glyph_data("target_gdata", gic_data.target_gdata)
    write_pair_data("pair_data", gic_data.pair_data)
    print("# EOF", file=fd)


def read_compare_data(filepath):
    def check_match(regex, it):
        line = next(it)
        m = re.match(regex, line)
        if not m:
            raise Exception('regex "%s" failed to match "%s"' % (regex, line))
        return m

    def read_fdata(label, it):
        check_match(r">\s*%s:\s*\[\s*$" % label, it)

        def get_val(k):
            m = check_match(r">\s*%s:\s*(.*)\s*$" % k, it)
            val = m.group(1)
            if k not in ["name", "file", "version"]:
                val = int(val)
            return val

        vals = [get_val(k) for k in GlyphImageFontData._fields]
        assert next(it).strip() == "]"

        return GlyphImageFontData._make(vals)

    def read_gdata(label, it):
        m = check_match(r">\s*%s:\s*(\d+)\s*$" % label, it)
        count = int(m.group(1))
        data = [None] * count
        for i in range(count):
            ix, adv, cp, name = (v.strip() for v in next(it).split(";"))
            adv = int(adv)
            cp = int(cp, 16) if cp != "" else -1
            data[i] = (adv, cp, name)
        return data

    def read_pairdata(label, it):
        check_match(r">\s*%s:\s*$" % label, it)

        m = check_match(r">\s*max_frame:\s*(.+)\s*$", it)
        max_frame = glyph_image.Frame._make(
            [int(n.strip()) for n in m.group(1).split()]
        )

        m = check_match(r">\spairs:\s(\d+)\s*$", it)
        count = int(m.group(1))

        def get_pairdata(line):
            name, b, t, similarity = line.split(";")
            b = -1 if b == "" else int(b)
            t = -1 if t == "" else int(t)
            similarity = int(similarity)
            return name, b, t, similarity

        pair_data = [None] * count
        for i in range(count):
            pair_data[i] = get_pairdata(next(it))

        return GlyphImagePairData(max_frame, pair_data)

    with open(filepath, "r") as f:
        it = glyph_image.LineStripper(f)
        base_fdata = read_fdata("base_fdata", it)
        target_fdata = read_fdata("target_fdata", it)
        base_gdata = read_gdata("base_gdata", it)
        target_gdata = read_gdata("target_gdata", it)
        pair_data = read_pairdata("pair_data", it)
        return GlyphImageCompareData(
            base_fdata, target_fdata, base_gdata, target_gdata, pair_data
        )


def write_compare_data_to_dir(gic_data, output_dir, name="compare_data.txt"):
    data_file = path.join(output_dir, name)
    with open(data_file, "w") as f:
        write_compare_data(gic_data, f)


def compare_collections(base_collection, target_collection, pair_data, output_dir):
    """Compares two glyph image collections, writing the result to output_dir.
    If pair data is provided, uses it, else uses glyph_image_pair to pair the
    glyphs in the two collections."""

    base_header = base_collection.file_header
    target_header = target_collection.file_header

    # Font names must be the same.  This might be too restrictive.
    if base_header.name != target_header.name:
        print(
            'base name is "%s" but target name is "%s"'
            % (base_header.name, target_header.name)
        )
        print("aborting compare.")
        return

    # Image sizes must be the same.
    if base_header.size != target_header.size:
        print(
            "base font size is %d but target font size is %d"
            % (base_header.size, target_header.size)
        )
        print("aborting compare.")
        return

    # Use glyph_image_pair to generate pair data if none was provided.
    if pair_data is None:
        pair_data = glyph_image_pair.get_collection_pairs(
            base_collection, target_collection
        )

    named_pairs = select_named_pairs(pair_data)

    max_frame = glyph_image.union_frames(
        [base_collection.common_frame(True), target_collection.common_frame(True)]
    )
    # only use height
    tall_frame = glyph_image.Frame(0, max_frame.t, 0, max_frame.h)

    output_dir = tool_utils.ensure_dir_exists(output_dir, clean=True)

    # Generate comparison images and write to output dir.  Collect match
    # percentages as we go.
    match_pcts = []
    for name, base_ix, target_ix in named_pairs:
        bg = base_collection.image_dict.get(base_ix)
        tg = target_collection.image_dict.get(target_ix)
        frame = glyph_image.compute_frame(bg, tg, include_metrics=True)
        # ensure frame extends to max glyph ascent/descent, and add padding
        frame = glyph_image.pad_frame(glyph_image.union_frames([frame, tall_frame]), 5)
        image, match_pct = glyph_image.create_compare_image(bg, tg, frame, True)
        image_path = path.join(output_dir, name + ".png")
        image.save(image_path)
        match_pcts.append(match_pct)

    max_frame = glyph_image.pad_frame(max_frame, 5)

    return create_compare_data(
        base_collection, target_collection, named_pairs, match_pcts, max_frame
    )


def compare_files(base_file, target_file, image_dir):
    """Reads the two glyph image files, then calls compare_collections.
    No pairing info is provided."""

    if not path.isfile(base_file):
        raise Exception("base file %s does not exist" % base_file)
    if not path.isfile(target_file):
        raise Exception("target file %s does not exist" % target_file)

    base_collection = glyph_image.read_file(base_file)
    target_collection = glyph_image.read_file(target_file)
    return compare_collections(base_collection, target_collection, None, image_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b", "--base", help="base glyph image file", metavar="file", required=True
    )
    parser.add_argument(
        "-t", "--target", help="target glyph image file", metavar="file", required=True
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        help="directory to write output into",
        metavar="dir",
        required=True,
    )
    args = parser.parse_args()

    gic_data = compare_files(args.base, args.target, args.output_dir)
    write_compare_data_to_dir(gic_data, args.output_dir)


if __name__ == "__main__":
    # print(read_compare_data('/tmp/gujarati/compare_data.txt'))
    main()
