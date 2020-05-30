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


import tempfile
import unittest

from nototools.gpos_diff import GposDiffFinder
from hb_input_test import make_font


class GposDiffFinderText(unittest.TestCase):
    def _expect_kerning_diffs(self, source_a, source_b, pairs, values):
        font_a = make_font("feature kern {\n%s\n} kern;" % source_a)
        font_b = make_font("feature kern {\n%s\n} kern;" % source_b)
        file_a = tempfile.NamedTemporaryFile()
        file_b = tempfile.NamedTemporaryFile()
        font_a.save(file_a.name)
        font_b.save(file_b.name)
        finder = GposDiffFinder(file_a.name, file_b.name, 0, 100)

        diffs = finder.find_kerning_diffs()
        self.assertIn("%d differences in kerning pairs" % len(pairs), diffs)
        for pair_diff in pairs:
            self.assertIn("%s pos %s %s %s" % pair_diff, diffs)
        self.assertIn("%d differences in kerning values" % len(values), diffs)
        for value_diff in values:
            self.assertIn("pos %s %s: %s vs %s" % value_diff, diffs)

    def _expect_mark_positioning_diffs(self, source_a, source_b, values):
        font_a = make_font("feature mark {\n%s\n} mark;" % source_a)
        font_b = make_font("feature mark {\n%s\n} mark;" % source_b)
        file_a = tempfile.NamedTemporaryFile()
        file_b = tempfile.NamedTemporaryFile()
        font_a.save(file_a.name)
        font_b.save(file_b.name)
        finder = GposDiffFinder(file_a.name, file_b.name, 0, 100)

        diffs = finder.find_positioning_diffs()
        self.assertIn(
            "%d differences in mark-to-base positioning rule values" % len(values),
            diffs,
        )
        for value_diff in values:
            self.assertIn("<%s %s> vs <%s %s>" % value_diff, diffs)

    def test_kern_simple(self):
        self._expect_kerning_diffs(
            """
                pos a b -10;
                pos a c -20;
            """,
            """
                pos a b -30;
                pos a d -40;
            """,
            [("-", "a", "c", [-20]), ("+", "a", "d", [-40])],
            [("a", "b", [-10], [-30])],
        )

    def test_kern_multiple_rules(self):
        self._expect_kerning_diffs(
            """
                @a_b = [a b];
                pos a d -10;
                pos @a_b d -20;
            """,
            """
                pos a d -30;
            """,
            [("-", "b", "d", [-20])],
            [("a", "d", [-10, -20], [-30])],
        )

    def test_kern_single_vs_class(self):
        self._expect_kerning_diffs(
            """
                pos a d -10;
            """,
            """
                @a_b = [a b];
                pos @a_b d -20;
            """,
            [("+", "b", "d", [-20])],
            [("a", "d", [-10], [-20])],
        )

    def test_mark_positioning_diffs_simple(self):
        """Find position differences for a single mark and single base glyph"""
        self._expect_mark_positioning_diffs(
            """
                markClass acute <anchor 150 -10> @TOP_MARKS;

                position base a <anchor 250 450> mark @TOP_MARKS;
            """,
            """
                markClass acute <anchor 150 -10> @TOP_MARKS;

                position base a <anchor 0 0> mark @TOP_MARKS;
            """,
            [(250, 450, 0, 0)],
        )

    def test_mark_positioning_diffs_on_groups(self):
        """Find position differences for groups"""
        self._expect_mark_positioning_diffs(
            """
                markClass [acute grave] <anchor 150 -10> @TOP_MARKS;

                position base [a e o u] <anchor 250 450> mark @TOP_MARKS;
            """,
            """
                markClass [acute grave] <anchor 150 -50> @TOP_MARKS;

                position base [a e o u] <anchor 0 0> mark @TOP_MARKS;
            """,
            [(250, 450, 0, 0), (250, 450, 0, 0), (250, 450, 0, 0), (250, 450, 0, 0)],
        )

    def test_mark_positioning_diffs_on_classes(self):
        """Find position differences on classes"""
        self._expect_mark_positioning_diffs(
            """
                @top = [acute grave];
                @base_glyphs = [a e o u];

                markClass @top <anchor 150 -10> @TOP_MARKS;

                position base @base_glyphs <anchor 250 450> mark @TOP_MARKS;
            """,
            """
                @top = [acute grave];
                @base_glyphs = [a e o u];

                markClass @top <anchor 150 -50> @TOP_MARKS;

                position base @base_glyphs <anchor 0 0> mark @TOP_MARKS;
            """,
            [(250, 450, 0, 0), (250, 450, 0, 0), (250, 450, 0, 0), (250, 450, 0, 0)],
        )

    def test_mark_positioning_diffs_mark_on_mark(self):
        """Find positions differences on mark to mark positions"""
        self._expect_mark_positioning_diffs(
            """
            @top = [acute grave];

            markClass @top <anchor 150 -10> @TOP_MARKS;

            position base @top <anchor 250 450> mark @TOP_MARKS;
        """,
            """
            @top = [acute grave];

            markClass @top <anchor 150 -50> @TOP_MARKS;

            position base @top <anchor 0 0> mark @TOP_MARKS;
        """,
            [(250, 450, 0, 0), (250, 450, 0, 0)],
        )


if __name__ == "__main__":
    unittest.main()
