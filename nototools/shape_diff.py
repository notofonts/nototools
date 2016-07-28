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
which compare these fonts, storing results in a report dictionary. These methods
are `find_area_diffs`, which compares glyph areas, and `find_rendered_diffs`
which compares harfbuzz output using image magick.

Neither comparison is ideal. Glyph areas can be the same even if the shapes are
wildly different. Image comparison is usually either slow (hi-res) or inaccurate
(lo-res). Still, these are usually useful for raising red flags and catching
large errors.
"""


import os
import re
import subprocess
import tempfile

from fontTools.ttLib import TTFont
from nototools.glyph_area_pen import GlyphAreaPen

from nototools import hb_input

GDEF_UNDEF = 0
GDEF_MARK = 3
GDEF_LABELS = ['no class', 'base', 'ligature', 'mark', 'component']


class ShapeDiffFinder:
    """Provides methods to report diffs in glyph shapes between OT Fonts."""

    def __init__(self, file_a, file_b, stats, ratio_diffs=False):
        self.path_a = file_a
        self.font_a = TTFont(self.path_a)
        self.glyph_set_a = self.font_a.getGlyphSet()
        self.gdef_a = {}
        if 'GDEF' in self.font_a:
            self.gdef_a = self.font_a['GDEF'].table.GlyphClassDef.classDefs

        self.path_b = file_b
        self.font_b = TTFont(self.path_b)
        self.glyph_set_b = self.font_b.getGlyphSet()
        self.gdef_b = {}
        if 'GDEF' in self.font_b:
            self.gdef_b = self.font_b['GDEF'].table.GlyphClassDef.classDefs

        stats['compared'] = []
        stats['untested'] = []
        stats['unmatched'] = []
        stats['unicode_mismatch'] = []
        stats['gdef_mark_mismatch'] = []
        stats['zero_width_mismatch'] = []
        stats['input_mismatch'] = []
        self.stats = stats

        self.ratio_diffs = ratio_diffs
        self.basepath = os.path.basename(file_a)

    def find_area_diffs(self):
        """Report differences in glyph areas."""

        self.build_names()

        pen_a = GlyphAreaPen(self.glyph_set_a)
        pen_b = GlyphAreaPen(self.glyph_set_b)

        mismatched = {}
        for name in self.names:
            self.glyph_set_a[name].draw(pen_a)
            area_a = pen_a.pop()
            self.glyph_set_b[name].draw(pen_b)
            area_b = pen_b.pop()
            if area_a != area_b:
                mismatched[name] = (area_a, area_b)

        stats = self.stats['compared']
        calc = self._calc_ratio if self.ratio_diffs else self._calc_diff
        for name, areas in mismatched.items():
            stats.append((calc(areas), name, self.basepath, area[0], area[1]))

    def find_rendered_diffs(self, font_size=256, render_path=None):
        """Find diffs of glyphs as rendered by harfbuzz + image magick."""

        hb_input_generator_a = hb_input.HbInputGenerator(self.font_a)
        hb_input_generator_b = hb_input.HbInputGenerator(self.font_b)

        a_png_file = tempfile.NamedTemporaryFile()
        a_png = a_png_file.name
        b_png_file = tempfile.NamedTemporaryFile()
        b_png = b_png_file.name
        cmp_png_file = tempfile.NamedTemporaryFile()
        cmp_png = cmp_png_file.name
        diffs_file = tempfile.NamedTemporaryFile()
        diffs_filename = diffs_file.name

        self.build_names()
        for name in self.names:
            class_a = self.gdef_a.get(name, GDEF_UNDEF)
            class_b = self.gdef_b.get(name, GDEF_UNDEF)
            if GDEF_MARK in (class_a, class_b) and class_a != class_b:
                self.stats['gdef_mark_mismatch'].append((
                    self.basepath, name, GDEF_LABELS[class_a],
                    GDEF_LABELS[class_b]))
                continue

            width_a = self.glyph_set_a[name].width
            width_b = self.glyph_set_b[name].width
            zwidth_a = width_a == 0
            zwidth_b = width_b == 0
            if zwidth_a != zwidth_b:
                self.stats['zero_width_mismatch'].append((
                    self.basepath, name, width_a, width_b))
                continue

            hb_args_a = hb_input_generator_a.input_from_name(name, pad=zwidth_a)
            hb_args_b = hb_input_generator_b.input_from_name(name, pad=zwidth_b)
            if hb_args_a != hb_args_b:
                self.stats['input_mismatch'].append((
                    self.basepath, name, hb_args_a, hb_args_b))
                continue

            # ignore unreachable characters
            if not hb_args_a:
                self.stats['untested'].append((self.basepath, name))
                continue

            features, text = hb_args_a

            # ignore null character
            if unichr(0) in text:
                continue

            with open(diffs_filename, 'a') as ofile:
                ofile.write('%s\n' % name)

            subprocess.call([
                'hb-view', '--font-size=%d' % font_size,
                '--output-file=%s' % a_png,
                '--features=%s' % ','.join(features), self.path_a, text])
            subprocess.call([
                'hb-view', '--font-size=%d' % font_size,
                '--output-file=%s' % b_png,
                '--features=%s' % ','.join(features), self.path_b, text])

            img_info = subprocess.check_output(['identify', a_png]).split()
            assert img_info[0] == a_png and img_info[1] == 'PNG'
            subprocess.call([
                'convert', '-gravity', 'center', '-background', 'black',
                '-extent', img_info[2], b_png, b_png])

            if render_path:
                glyph_filename = re.sub(r'([A-Z_])', r'\1_', name) + '.png'
                output_png = os.path.join(render_path, glyph_filename)
                # see for a discussion of this rendering technique:
                # https://github.com/googlei18n/nototools/issues/162#issuecomment-175885431
                subprocess.call([
                    'convert',
                    '(', a_png, '-colorspace', 'gray', ')',
                    '(', b_png, '-colorspace', 'gray', ')',
                    '(', '-clone', '0-1', '-compose', 'darken', '-composite', ')',
                    '-channel', 'RGB', '-combine', output_png])

            with open(diffs_filename, 'a') as ofile:
                subprocess.call(
                    ['compare', '-metric', 'AE', a_png, b_png, cmp_png],
                    stderr=ofile)
                ofile.write('\n')

        with open(diffs_filename) as ifile:
            lines = [l.strip() for l in ifile.readlines() if l.strip()]
        diffs = [(lines[i], lines[i + 1]) for i in range(0, len(lines), 2)]

        mismatched = {}
        for name, diff in diffs:
            if int(diff) != 0:
                mismatched[name] = int(diff)

        stats = self.stats['compared']
        for name, diff in mismatched.items():
            stats.append((diff, name, self.basepath))

    def build_names(self):
        """Build a list of glyph names shared between the fonts."""

        if hasattr(self, 'names'):
            return

        stats = self.stats['unmatched']
        names_a = set(self.font_a.getGlyphOrder())
        names_b = set(self.font_b.getGlyphOrder())
        if names_a != names_b:
            stats.append((self.basepath, names_a - names_b, names_b - names_a))
        self.names = names_a & names_b

        stats = self.stats['unicode_mismatch']
        reverse_cmap_a = hb_input.build_reverse_cmap(self.font_a)
        reverse_cmap_b = hb_input.build_reverse_cmap(self.font_b)
        mismatched = {}
        for name in self.names:
            unival_a = reverse_cmap_a.get(name)
            unival_b = reverse_cmap_b.get(name)
            if unival_a != unival_b:
                mismatched[name] = (unival_a, unival_b)
        if mismatched:
            stats.append((self.basepath, mismatched.items()))
            self.names -= set(mismatched.keys())

    @staticmethod
    def dump(stats, whitelist, out_lines, include_vals, multiple_fonts):
        """Return the results of run diffs.

        Args:
            stats: List of tuples with diff data which is sorted and printed.
            whitelist: Names of glyphs to exclude from report.
            out_lines: Number of diff lines to print.
            include_vals: Include the values which have been diffed in report.
            multiple_fonts: Designates whether stats have been accumulated from
                multiple fonts, if so then font names will be printed as well.
        """

        report = []

        compared = sorted(
            s for s in stats['compared'] if s[1] not in whitelist)
        compared.reverse()
        fmt = '%s %s'
        if include_vals:
            fmt += ' (%s vs %s)'
        if multiple_fonts:
            fmt = '%s ' + fmt
        report.append('%d differences in glyph shape' % len(compared))
        for line in compared[:out_lines]:
            # print <font> <glyph> <vals>; stats are sorted in reverse priority
            line = tuple(reversed(line[:3])) + tuple(line[3:])
            # ignore font name if just one pair of fonts was compared
            if not multiple_fonts:
                line = line[1:]
            report.append(fmt % line)
        report.append('')

        for font, set_a, set_b in stats['unmatched']:
            report.append("Glyph coverage doesn't match in %s" % font)
            report.append('  in A but not B: %s' % sorted(set_a))
            report.append('  in B but not A: %s' % sorted(set_b))
        report.append('')

        for font, mismatches in stats['unicode_mismatch']:
            report.append("Glyph unicode values don't match in %s" % font)
            for name, univals in sorted(mismatches):
                univals = [(('0x%04X' % v) if v else str(v)) for v in univals]
                report.append('  %s: %s in A, %s in B' %
                              (name, univals[0], univals[1]))
        report.append('')

        ShapeDiffFinder._add_simple_report(
            report, stats['gdef_mark_mismatch'],
            '%s: Mark class mismatch for %s (%s vs %s)')
        ShapeDiffFinder._add_simple_report(
            report, stats['zero_width_mismatch'],
            '%s: Zero-width mismatch for %s (%d vs %d)')
        ShapeDiffFinder._add_simple_report(
            report, stats['input_mismatch'],
            '%s: Harfbuzz input mismatch for %s (%s vs %s)')
        ShapeDiffFinder._add_simple_report(
            report, stats['untested'],
            '%s: %s not tested (unreachable?)')

        return '\n'.join(report)

    @staticmethod
    def _add_simple_report(report, stats, fmt):
        for stat in sorted(stats):
            report.append(fmt % stat)
        if stats:
            report.append('')

    def _calc_diff(self, vals):
        """Calculate an area difference."""

        a, b = vals
        return abs(a - b)

    def _calc_ratio(self, vals):
        """Calculate an area ratio."""

        a, b = vals
        if not (a or b):
            return 0
        return 1 - min(a, b) / max(a, b)
