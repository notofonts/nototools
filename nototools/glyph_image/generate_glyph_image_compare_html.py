#!/usr/bin/env python
#
# Copyright 2017 Google Inc. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import print_function

"""Generate html that lets you browse the results from glyph_image_compare.

The glyph image compare tool takes information on two sets of glyphs from
two versions of the same font, attempts to find related glyphs, and generates
images representing the differences.  This turns that information into a web
page so the images can be easily browsed.

Basic usage is:

1) use make to create glyph_image from glyph_image.c:
$ make

2) run glyph_image on two versions of a font, e.g.
$ glyph_image srcdir1/some_font_file.ttf 128 > dstdir/out1.txt
$ glyph_image srcdir2/some_font_file.ttf 128 > dstdir/out2.txt

The generated files are text files and embed the glyph image
bitmaps as ascii hex values, so they're large, usually 500K or more.

3) run glyph_image_compare to generate a directory containing
comparison images and data.  glyph_image_compare uses glyph_image_pair
to pair up glyphs from the two fonts, first based on direct mapping
to unicode code points, then based on the similarity between the pixel
data.  It then generates images from these pairs that highlight the
differences.  E.g.:
$ ./glyph_image_compare.py -b dstdir/out1.txt -t dstdir/out2.txt -o compdir

4) run generate_glyph_image_compare_html to create a directory and
html files to browse this data.  The images are copied to this directory
and an html file is created along with supporting .js and .css files.
$ ./generate_glyph_image_compare_html.py -i compdir -o htmldir/filename.html
"""

import argparse
import shutil
from os import path
from string import Template

from nototools import tool_utils

from nototools.glyph_image import glyph_image_compare

_TEMPLATE = """<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset="utf-8">
  <title>$title</title>
  <link href="glyph_image_compare.css" rel="stylesheet">
  <script type="text/javascript">
    var image_data = [
      $image_data
      ];
    var cp_data = {
      $cp_data
      };
    var image_dir = "$image_dir"
  </script>
  <script type="text/javascript" src="glyph_image_compare.js"></script>
</head>
<body onload="init()">
<div id='header'>
<div id='fdata'>
<h3>$name</h3>
<table>
$ftable
</table>
<div id='switch'>
  <label>Filter
    <input id='filter' type='number' value=100 size=4 min=1 max=100 step=1>
  </label>
  <label>Sort
    <select id='sort'>
      <option value=0>Codepoint then glyph</option>
      <option value=1>Similarity</option>
    </select>
  </label>
  <input id='sort_order' type='button' value='Asc'>
  <span id='count_msg'>&nbsp;</span>
</div>
</div>
<div id='ref'></div>
</div>
<div id='frame' style="margin-top: ${header_height}px">
<div id='main'></div>
</div>
</body>
</html>
"""


def generate_font_table(compare_data):
    lines = []

    def write_lines(key, fdata):
        lines.append(
            '<tr><td><div class="box %s">&nbsp;</div><td><b>File</b> %s'
            % (key, fdata.file[pfx_len:])
        )

        version = fdata.version
        if version.startswith("Version "):
            version = version[len("Version ") :]
        lines.append("<tr><td><td><b>Version</b> %s" % version)

        lines.append(
            "<tr><td><td><b>Upem</b> %d, <b>Ascent</b> %d, <b>Descent</b> %d, "
            "<b>Glyphs</b> %d, <b>CPs</b> %d"
            % (
                fdata.upem,
                fdata.ascent,
                fdata.descent,
                fdata.num_glyphs,
                fdata.codepoints,
            )
        )

    pfx, paths = tool_utils.commonpathprefix(
        (compare_data.base_fdata.file, compare_data.target_fdata.file)
    )
    pfx_len = len(pfx)

    write_lines("b", compare_data.base_fdata)
    write_lines("t", compare_data.target_fdata)
    return "\n".join(lines)


def generate_image_data(compare_data):
    import json
    from nototools import unicode_data

    bdata = compare_data.base_gdata
    tdata = compare_data.target_gdata

    # name, sim, b_ix, b_adv, b_cp, b_name, t_ix, t_adv, t_cp, t_name
    cp_map = {}

    def add_cp(cp):
        if cp != -1 and cp not in cp_map:
            try:
                name = unicode_data.name(cp)
            except:
                name = "u%04X" % cp
            cp_map[cp] = name

    pair_lines = []
    no_data = (0, -1, "")
    for name, b, t, similarity in compare_data.pair_data.pair_data:
        bd = bdata[b] if b != -1 else no_data
        td = tdata[t] if t != -1 else no_data
        pair_lines.append(json.dumps((name + ".png", similarity, b) + bd + (t,) + td))
        add_cp(bdata[b][1])
        add_cp(tdata[t][1])
    cp_lines = ['%s: "%s"' % t for t in sorted(cp_map.items())]
    return ",\n      ".join(pair_lines), ",\n      ".join(cp_lines)


def generate_report(title, input_dir, compare_data, output_path):
    """The html file is output_path.  The image data goes in a folder
    with the same name as output_path without the extension.  .css
    and .js files are written as siblings of the html file."""

    if compare_data is None:
        compare_data = glyph_image_compare.read_compare_data(
            path.join(input_dir, "compare_data.txt")
        )

    output_path = path.abspath(output_path)
    root = path.dirname(output_path)
    image_dir = path.splitext(path.basename(output_path))[0]

    # Do not clean this directory, so we can write multiple html files
    # files to it.
    tool_utils.ensure_dir_exists(root)

    # Copy supporting js/css files, they are always the same.
    filedir = tool_utils.resolve_path("[tools]/nototools/glyph_image")
    for name in ["glyph_image_compare.js", "glyph_image_compare.css"]:
        shutil.copy2(path.join(filedir, name), path.join(root, name))

    # Clean subdir for this html, then copy image files to it
    full_image_dir = tool_utils.ensure_dir_exists(path.join(root, image_dir), True)
    for name in [t[0] + ".png" for t in compare_data.pair_data.pair_data]:
        shutil.copy2(path.join(input_dir, name), path.join(full_image_dir, name))

    bname = compare_data.base_fdata.name
    tname = compare_data.target_fdata.name
    name = bname if bname == tname else bname + " / " + tname

    image_data, cp_data = generate_image_data(compare_data)

    ftable = generate_font_table(compare_data)

    header_height = max(250, compare_data.pair_data.max_frame.h + 20)

    # generate html
    with open(output_path, "w") as f:
        f.write(
            Template(_TEMPLATE).substitute(
                title=title,
                ftable=ftable,
                header_height=header_height,
                image_dir=image_dir,
                image_data=image_data,
                cp_data=cp_data,
                name=name,
            )
        )
    print("wrote %s" % output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input_dir",
        help="directory containing glyph image compare data",
        metavar="dir",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output_path",
        help="path of output html file",
        metavar="file",
        required=True,
    )
    parser.add_argument(
        "-t", "--title", help="title of report", metavar="str", required=True
    )

    args = parser.parse_args()

    generate_report(args.title, args.input_dir, None, args.output_path)


if __name__ == "__main__":
    main()
