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


"""Provides ShapeDiffFinder, which finds differences in OTF/TTF glyph shapes.

ShapeDiffFinder takes in two paths, to font binaries. It then provides methods
which compare these fonts, returning a report string and optionally adding to a
report dictionary. These methods are `find_area_diffs`, which compares glyph
areas, and `find_rendered_diffs` which compares harfbuzz output using image
magick.

Neither comparison is ideal. Glyph areas can be the same even if the shapes are
wildly different. Image comparison is usually either slow (hi-res) or inaccurate
(lo-res), and can be easily hindered when one glyph's image is a pixel larger
than another's. Still, these are usually useful for raising red flags and
catching large errors.
"""


import os
import subprocess

from fontTools.ttLib import TTFont
from nototools.pens.glyph_area_pen import GlyphAreaPen


class ShapeDiffFinder:
    """Provides methods to report diffs in glyph shapes between OT Fonts."""

    def __init__(self, file_a, file_b, output_lines=6, ratio_diffs=False):
        self.paths = file_a, file_b
        self.fonts = [TTFont(f) for f in self.paths]
        self.out_lines = output_lines
        self.ratio_diffs = ratio_diffs
        self.report = []

    def find_area_diffs(self, stats=None):
        """Report differences in glyph areas."""

        self.build_names()

        glyph_sets =[f.getGlyphSet() for f in self.fonts]
        glyph_set_a, glyph_set_b = glyph_sets
        pen_a, pen_b = [GlyphAreaPen(glyph_set) for glyph_set in glyph_sets]

        mismatched = {}
        for name in self.names:
            glyph_set_a[name].draw(pen_a)
            area_a = pen_a.unload()
            glyph_set_b[name].draw(pen_b)
            area_b = pen_b.unload()
            if area_a != area_b:
                mismatched[name] = (area_a, area_b)

        report = self.report
        report.append('%d differences in glyph areas' % len(mismatched))
        mismatched = self._sorted_by(
            mismatched.items(),
            self._calc_ratio if self.ratio_diffs else self._calc_diff)
        for diff, name, (area1, area2) in mismatched[:self.out_lines]:
            report.append('%s: %s vs %s' % (name, area1, area2))
            if stats is not None:
                stats.append((diff, name, area1, area2))
        report.append('')

    def find_rendered_diffs(self, font_size=24, stats=None):
        """Find diffs of glyphs as rendered by harfbuzz."""

        self.build_names()
        self.build_reverse_cmap()

        path_a, path_b = self.paths
        ordered_names = list(self.names)
        a_png = 'tmp_a.png'
        b_png = 'tmp_b.png'
        cmp_png = 'tmp_cmp.png'
        diffs_filename = 'tmp_diffs.txt'

        with open(diffs_filename, 'w') as ofile:
            for name in ordered_names:

                # ignore null character, and characters without unicode values
                unival = self.reverse_cmap.get(name, 0)
                if unival == 0:
                    continue

                strin = unichr(unival)
                subprocess.call([
                    'hb-view', '--font-size=%d' % font_size,
                    '--output-file=%s' % a_png, path_a, strin])
                subprocess.call([
                    'hb-view', '--font-size=%d' % font_size,
                    '--output-file=%s' % b_png, path_b, strin])
                subprocess.call(
                    ['compare', '-metric', 'AE', a_png, b_png, cmp_png],
                    stderr=ofile)

        with open(diffs_filename) as ifile:
            diffs = ifile.readlines()

        os.remove(a_png)
        os.remove(b_png)
        os.remove(cmp_png)
        os.remove(diffs_filename)

        mismatched = {}
        img_size_diffs = []
        for name, diff in zip(ordered_names, diffs):
            if 'image widths or heights differ' in diff:
                img_size_diffs.append(name)
            elif int(diff) != 0:
                mismatched[name] = int(diff)

        report = self.report
        report.append('%d differences in rendered glyphs' % len(mismatched))
        mismatched = self._sorted_by(
            mismatched.items(), self._pass_val)
        for _, name, diff in mismatched[:self.out_lines]:
            report.append('%s: %s' % (name, diff))
            if stats is not None:
                stats.append((diff, name))
        report.append('')

        report.append('%d differences in glyph img size' % len(img_size_diffs))
        img_size_diffs.sort()
        for name in img_size_diffs[:self.out_lines]:
            report.append(name)
        report.append('')

    def build_names(self):
        """Build a list of glyph names shared between the fonts."""

        if hasattr(self, 'names'):
            return

        report = self.report
        names_a, names_b = [set(f.getGlyphOrder()) for f in self.fonts]
        if names_a != names_b:
            report.append("Glyph coverage doesn't match")
            report.append('  in A but not B: %s' % list(names_a - names_b))
            report.append('  in B but not A: %s' % list(names_b - names_a))
            report.append('')
        self.names = names_a & names_b

    def build_reverse_cmap(self):
        """Build a map from glyph names to unicode values for the fonts."""

        if hasattr(self, 'reverse_cmap'):
            return

        report = self.report
        reverse_cmaps = [
            dict((n, v) for v, n in f['cmap'].tables[1].cmap.items())
            for f in self.fonts]
        mismatched = {}
        for name in self.names:
            unival_a, unival_b = [m.get(name) for m in reverse_cmaps]
            if unival_a != unival_b:
                mismatched[name] = (unival_a, unival_b)
        if mismatched:
            report.append("Glyph unicode values don't match")
            for name, univals in mismatched.items():
                univals = [(('0x%04X' % v) if v else str(v)) for v in univals]
                report.append('  %s: %s in A, %s in B' %
                              (name, univals[0], univals[1]))
            report.append('')
        self.reverse_cmap = reverse_cmaps[0]

    def dump(self):
        """Return the results of run diffs."""
        return '\n'.join(self.report)

    def _sorted_by(self, items, diff_calc):
        """Return items, sorted by diff_calc with calculated diff included."""

        items = list(items)
        items.sort(lambda lhs, rhs: self._compare(lhs, rhs, diff_calc))
        return [(diff_calc(vals), name, vals) for name, vals in items]

    def _compare(self, left, right, diff_calc):
        """Compare glyph area diffs by magnitude then glyph name.

        Args:
            left, right: Tuples each containing a glyph name and then an
                argument to diff_calc (usually the argument would be a tuple
                containing two areas for the glyph from different fonts).
            diff_calc: A function which calculates an area diff for a glyph. For
                now this either calculates the difference of two areas, or the
                ratio, or just passes through a pre-computed diff.

        Returns:
            An integer value for use in a sorting function.
        """

        (lname, lvals), (rname, rvals) = left, right
        dl = diff_calc(lvals)
        dr = diff_calc(rvals)
        return -1 if dl > dr else 1 if dr > dl else cmp(lname, rname)

    def _pass_val(self, val):
        """Pass through a pre-computed area diff."""

        return val

    def _calc_diff(self, vals):
        """Calculate an area difference."""

        return abs(vals[0] - vals[1])

    def _calc_ratio(self, vals):
        """Calculate an area ratio."""

        a, b = vals
        if not (a or b):
            return 0
        if abs(a) > abs(b):
            a, b = b, a
        ratio = (a / b) if (a and b) else 0
        return (1 - ratio)
