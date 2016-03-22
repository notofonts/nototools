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

Leverages various DiffFinder classes, depending on what's given via the
`diff_type` argument. Can compare multiple font pairs via the `match` argument.
For shaping comparisons, all results are sorted together and the largest
differences from all pairs are shown first. For GPOS the pairs are still
compared separately.
"""


import argparse
import glob
import os

from nototools import gpos_diff, gsub_diff, shape_diff


def _shape(path_a, path_b, stats, diff_type, render_path):
    """Do a shape comparison (glyph area or rendered) and add results to stats.

    path_a and b refer to binary font files (OTF or TTF). stats should be a
    list (possibly empty) of <diff, glyph-name, font-name> tuples, for sorting.
    diff_type and render_path are passed through from the original call to
    fontdiff.
    """

    cur_stats = []
    diff_finder = shape_diff.ShapeDiffFinder(
        path_a, path_b, output_lines=-1, ratio_diffs=True)

    if diff_type == 'area':
        diff_finder.find_area_diffs(stats=cur_stats)
    else:
        diff_finder.find_rendered_diffs(stats=cur_stats,
                                        render_path=render_path)

    basename = os.path.basename(path_a)
    stats.extend(s[0:2] + (basename,) + s[2:] for s in cur_stats)


def _dump_shape_stats(stats, whitelist, out_lines, diff_type, multiple_fonts):
    """Dump stats accumulated from calls to _shape.

    Members of stats are passed in with sortable ordering, but are re-ordered
    for printing. whitelist, out_lines, and diff_type are passed through from
    the original call to fontdiff. multiple_fonts designates whether these stats
    have been accumulated from multiple calls or just one; if multiple then the
    font names from each stats member will be printed as well.
    """

    if not stats:
        print 'No differences found.'
        return

    if whitelist:
        stats = [s for s in stats if s[1] not in whitelist]
    stats.sort()
    stats.reverse()

    stat_format = '%s %s'

    # include individual font names if multiple pairs of fonts were compared
    if multiple_fonts:
        stat_format = '%s ' + stat_format

    # include actual area values if areas were compared
    if diff_type == 'area':
        stat_format += ' (%s vs %s)'

    for stat in stats[:out_lines]:

        # print <font> <glyph> <vals>; stats are sorted in reverse priority
        stat = tuple(list(reversed(stat[:3])) + list(stat[3:]))

        # ignore font name if just one pair of fonts was compared
        if not multiple_fonts:
            stat = stat[1:]
        print stat_format % stat


def _gpos(path_a, path_b, error_bound, out_lines, print_font=False):
    """Do a GPOS table comparison and print results.

    path_a and b refer to plaintext files containing ttxn output. print_font
    is a boolean flag designating whether to print path_a (useful if _gpos is
    being called multiple times in succession).
    """

    if print_font:
        print '-- %s --' % os.path.basename(path_a)
        print
    diff_finder = gpos_diff.GposDiffFinder(path_a, path_b, error_bound,
                                           out_lines)
    print diff_finder.find_kerning_diffs()
    print diff_finder.find_mark_class_diffs()
    print diff_finder.find_positioning_diffs()
    print diff_finder.find_positioning_diffs(mark_type='mark')
    print


def _gsub(path_a, path_b, out_lines, print_font=False):
    """Do a GSUB table comparison and print results.

    path_a and b refer to plaintext files containing ttxn output. print_font
    is a boolean flag designating whether to print path_a (useful if _gsub is
    being called multiple times in succession).
    """

    if print_font:
        print '-- %s --' % os.path.basename(path_a)
    diff_finder = gsub_diff.GsubDiffFinder(path_a, path_b, out_lines)
    print diff_finder.find_gsub_diffs()
    print


def _run_multiple(func, filematch, dir_a, dir_b, *args):
    """Run a comparison function (probably _shape or _gpos) multiple times.

    Runs the given function "func" for each file in dir_a matching filematch,
    comparing it with a respective file of the same name in dir_b. Variable
    arguments are passed through when calling func.
    """

    for path_a in glob.glob(os.path.join(dir_a, filematch)):
        path_b = path_a.replace(dir_a, dir_b)
        func(path_a, path_b, *args)


def main():
    parser = argparse.ArgumentParser(description='Compare fonts or ttxn output '
                                     'pointed to by PATH_A and PATH_B.')
    parser.add_argument('path_a', metavar='PATH_A')
    parser.add_argument('path_b', metavar='PATH_B')
    parser.add_argument('-t', '--diff-type', default='area',
                        choices=('area', 'rendered', 'gpos', 'gsub'),
                        help='type of comparison to run (defaults to "area"), '
                        'if "gpos" is provided the input paths should point to '
                        'ttxn output')
    parser.add_argument('-m', '--match',
                        help='if provided, compares all matching files found '
                        'in PATH_A with respective matches in PATH_B')
    parser.add_argument('-l', '--out-lines', type=int, default=20,
                        help='number of differences to print (default 20)')
    parser.add_argument('-w', '--whitelist', nargs='+',
                        help='list of one or more glyph names to ignore')
    parser.add_argument('--render-path', help='if provided and DIFF_TYPE is '
                        '"rendered", saves comparison renderings here')
    parser.add_argument('--gpos-bound', type=int, default=3,
                        help='error bound to allow for gpos differences, '
                        'anything below is not printed (default 3)')
    args = parser.parse_args()

    if args.diff_type in ['area', 'rendered']:
        stats = []
        if args.match:
            _run_multiple(_shape, args.match, args.path_a, args.path_b, stats,
                          args.diff_type, args.render_path)
        else:
            _shape(args.path_a, args.path_b, stats, args.diff_type,
                   args.render_path)
        _dump_shape_stats(stats, args.whitelist, args.out_lines, args.diff_type,
                          multiple_fonts=bool(args.match))

    elif args.diff_type == 'gpos':
        if args.match:
            _run_multiple(_gpos, args.match, args.path_a, args.path_b,
                          args.gpos_bound, args.out_lines, True)
        else:
            _gpos(args.path_a, args.path_b, args.gpos_bound, args.out_lines)

    elif args.diff_type == 'gsub':
        if args.match:
            _run_multiple(_gsub, args.match, args.path_a, args.path_b,
                          args.out_lines, True)
        else:
            _gsub(args.path_a, args.path_b, args.out_lines)

    else:
        assert 0, 'Got unhandled diff type "%s"' % args.diff_type


if __name__ == '__main__':
    main()
