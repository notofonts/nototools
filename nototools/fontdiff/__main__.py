# Copyright 2016 Google Inc. All Rights Reserved.
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


"""Provides the command-line utility `fontdiff`.

Leverages GposDiffFinder or ShapeDiffFinder, depending on what's given via the
`diff_type` argument. Can compare multiple font pairs via the `match` argument.
For shaping comparisons, all results are sorted together and the largest
differences from all pairs are shown first. For GPOS the pairs are still
compared separately.
"""


import argparse
import glob
import os

from nototools.fontdiff import gpos_diff, shape_diff


def shape(path_a, path_b, stats):
    cur_stats = []
    diff_finder = shape_diff.ShapeDiffFinder(
        path_a, path_b, output_lines=-1, ratio_diffs=True)

    diff_finder.find_area_diffs(cur_stats)

    basename = os.path.basename(path_a)
    stats.extend(s[0:2] + (basename,) + s[2:] for s in cur_stats)


def gpos(path_a, path_b, out_lines):
    print '-- %s --' % os.path.basename(path_a)
    print
    diff_finder = gpos_diff.GposDiffFinder(path_a, path_b, 3, out_lines)
    print diff_finder.find_kerning_diffs()
    print diff_finder.find_mark_class_diffs()
    print diff_finder.find_positioning_diffs()
    print diff_finder.find_positioning_diffs(mark_type='mark')
    print


def run_multiple(func, filematch, dir_a, dir_b, *args):
    for path_a in glob.glob(os.path.join(dir_a, filematch)):
        path_b = path_a.replace(dir_a, dir_b)
        func(path_a, path_b, *args)


def main():
    parser = argparse.ArgumentParser(description='Compare fonts or ttxn output '
                                     'pointed to by PATH_A and PATH_B.')
    parser.add_argument('path_a', metavar='PATH_A')
    parser.add_argument('path_b', metavar='PATH_B')
    parser.add_argument('-t', '--diff_type', default='shape',
                        help='type of comparison to run, "shape" or "gpos" '
                        '(defaults to "shape"), if "gpos" is provided the '
                        'input paths should point to ttxn output')
    parser.add_argument('-m', '--match',
                        help='if provided, compares all matching files found '
                        'in PATH_A with respective matches in PATH_B')
    parser.add_argument('-l', '--out_lines', type=int, default=20,
                        help='number of differences to print (default 20)')
    parser.add_argument('-w', '--whitelist', nargs='+',
                        help='list of one or more glyph names to ignore')
    args = parser.parse_args()

    if args.diff_type == 'shape':
        stats = []
        if args.match:
            run_multiple(shape, args.match, args.path_a, args.path_b, stats)
        else:
            shape(args.path_a, args.path_b, stats)

        if not stats:
            print 'No shape differences found.'
            return

        if args.whitelist:
            stats = [s for s in stats if s[1] not in args.whitelist]
        stats.sort()
        stats.reverse()
        for diff, glyph, font, val_a, val_b in stats[:args.out_lines]:
            print '%s %s %s (%s vs %s)' % (font, glyph, diff, val_a, val_b)

    else:
        if args.match:
            run_multiple(gpos, args.match, args.path_a, args.path_b,
                         args.out_lines)
        else:
            gpos(args.path_a, args.path_b, args.out_lines)


if __name__ == '__main__':
    main()
