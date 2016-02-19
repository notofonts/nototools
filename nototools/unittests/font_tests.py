# coding=UTF-8
#
# Copyright 2015 Google Inc. All Rights Reserved.
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


import glob
from os import path
import unittest

from fontTools import ttLib
import freetype

from nototools import coverage
from nototools import font_data
from nototools import noto_fonts
from nototools import unicode_data
from nototools.pens.glyph_area_pen import GlyphAreaPen
from nototools.unittests import layout


def get_rendered_char_height(font_filename, font_size, char, target='mono'):
    if target == 'mono':
        render_params = freetype.FT_LOAD_TARGET_MONO
    elif target == 'lcd':
        render_params = freetype.FT_LOAD_TARGET_LCD
    render_params |= freetype.FT_LOAD_RENDER

    face = freetype.Face(font_filename)
    face.set_char_size(font_size*64)
    face.load_char(char, render_params)
    return face.glyph.bitmap.rows


def load_fonts(patterns, expected_count=None, font_class=None):
    """Load all fonts specified in the patterns.

    Also assert that the number of the fonts found is exactly the same as
    expected_count."""

    if font_class is None:
        font_class = ttLib.TTFont

    all_font_files = []
    for pattern in patterns:
        all_font_files += glob.glob(pattern)
    all_fonts = [font_class(font) for font in all_font_files]
    if expected_count:
        assert len(all_font_files) == expected_count
    return all_font_files, all_fonts


class FontTest(unittest.TestCase):
    """Parent class for all font tests."""
    loaded_fonts = None


class TestItalicAngle(FontTest):
    """Test the italic angle of fonts."""

    def setUp(self):
        _, self.fonts = self.loaded_fonts

    def test_italic_angle(self):
        """Tests the italic angle of fonts to be correct."""
        for font in self.fonts:
            post_table = font['post']
            if 'Italic' in font_data.font_name(font):
                expected_angle = self.expected_italic_angle
            else:
                expected_angle = 0.0
            self.assertEqual(post_table.italicAngle, expected_angle)


class TestMetaInfo(FontTest):
    """Test various meta information."""

    mark_heavier_as_bold = False
    mark_italic_as_oblique = False

    def setUp(self):
        _, self.fonts = self.loaded_fonts

    def parse_metadata(self, font):
        """Parse font name to infer weight and slope."""

        font_name = font_data.font_name(font)
        bold = ('Bold' in font_name) or (
            self.mark_heavier_as_bold and 'Black' in font_name)
        italic = 'Italic' in font_name
        return bold, italic

    def test_mac_style(self):
        """Tests the macStyle of the fonts to be correct."""

        for font in self.fonts:
            bold, italic = self.parse_metadata(font)
            expected_mac_style = (italic << 1) | bold
            self.assertEqual(font['head'].macStyle, expected_mac_style)

    def test_fs_selection(self):
        """Tests the fsSelection to be correct."""

        for font in self.fonts:
            bold, italic = self.parse_metadata(font)
            expected_fs_type = ((bold << 5) | italic) or (1 << 6)
            if italic and self.mark_italic_as_oblique:
                expected_fs_type |= (1 << 9)
            self.assertEqual(font['OS/2'].fsSelection, expected_fs_type)

    def test_fs_type(self):
        """Tests the fsType of the fonts."""

        for font in self.fonts:
            self.assertEqual(font['OS/2'].fsType, self.expected_os2_fsType)

    def test_vendor_id(self):
        """Tests the vendor ID of the fonts."""
        for font in self.fonts:
            self.assertEqual(font['OS/2'].achVendID,
                             self.expected_os2_achVendID)

    def test_us_weight(self):
        "Tests the usWeight of the fonts to be correct."""
        for font in self.fonts:
            weight = noto_fonts.parse_weight(font_data.font_name(font))
            expected_numeric_weight = noto_fonts.WEIGHTS[weight]
            self.assertEqual(
                font['OS/2'].usWeightClass,
                expected_numeric_weight)

    def test_version_numbers(self):
        "Tests the two version numbers of the font to be correct."""
        for font in self.fonts:
            version = font_data.font_version(font)
            usable_part_of_version = version.split(';')[0]
            self.assertEqual(usable_part_of_version,
                             'Version ' + self.expected_version)

            revision = font_data.printable_font_revision(font, accuracy=5)
            self.assertEqual(revision, self.expected_version)


class TestNames(FontTest):
    """Tests various strings in the name table."""

    mark_heavier_as_bold = False

    def setUp(self):
        font_files, self.fonts = self.loaded_fonts
        self.font_files = [path.basename(f) for f in font_files]
        self.condensed_family_name = self.family_name + ' Condensed'
        self.names = []
        for font in self.fonts:
            self.names.append(font_data.get_name_records(font))

    def test_copyright(self):
        """Tests the copyright message."""
        for records in self.names:
            self.assertEqual(records[0], self.expected_copyright)

    def parse_filename(self, filename):
        """Parse expected name attributes from filename."""

        name_nosp = self.family_name.replace(' ', '')
        condensed_name_nosp = self.condensed_family_name.replace(' ', '')
        family_names = '%s|%s' % (condensed_name_nosp, name_nosp)

        filename_match = noto_fonts.match_filename(filename, family_names)
        family, _, _, _, _, _, _, _, weight, slope, _ = filename_match.groups()

        if family == condensed_name_nosp:
            family = self.condensed_family_name
        else:  # family == name_nosp
            family = self.family_name
        if not weight:
            weight = 'Regular'
        return family, weight, slope

    def build_style(self, weight, slope):
        """Build style (typographic subfamily) out of weight and slope."""

        style = weight
        if slope:
            if style == 'Regular':
                style = 'Italic'
            else:
                style += ' ' + slope
        return style

    def test_family_name(self):
        """Tests the family name."""

        for font_file, records in zip(self.font_files, self.names):

            family, weight, _ = self.parse_filename(font_file)

            # check that family name includes weight, if not regular or bold
            if weight not in ['Regular', 'Bold']:
                self.assertEqual(records[1], '%s %s' % (family, weight))

                # check typographic name, if present
                self.assertIn(16, records)
                self.assertEqual(records[16], family)

            # check that family name does not include weight, if regular or bold
            else:
                self.assertEqual(records[1], family)

    def test_subfamily_name(self):
        """Tests the subfamily name."""

        for font_file, records in zip(self.font_files, self.names):
            _, weight, slope = self.parse_filename(font_file)
            subfam = records[2]

            # check that subfamily is just a combination of bold and italic
            self.assertIn(subfam, ['Regular', 'Bold', 'Italic', 'Bold Italic'])

            # check that subfamily weight/slope are consistent with filename
            bold = (weight == 'Bold') or (
                self.mark_heavier_as_bold and
                noto_fonts.WEIGHTS[weight] > noto_fonts.WEIGHTS['Bold'])
            self.assertEqual(bold, subfam.startswith('Bold'))
            self.assertEqual(slope == 'Italic', subfam.endswith('Italic'))

            # check typographic name, if present
            if weight not in ['Regular', 'Bold']:
                self.assertIn(17, records)
                self.assertEqual(records[17], self.build_style(weight, slope))

    def test_unique_identifier_and_full_name(self):
        """Tests the unique identifier and full name."""
        for font_file, records in zip(self.font_files, self.names):
            family, weight, slope = self.parse_filename(font_file)
            style = self.build_style(weight, slope)
            expected_name = family
            if style != 'Regular':
                expected_name += ' ' + style
            self.assertEqual(records[3], self.expected_unique_id(family, style))
            self.assertEqual(records[4], expected_name)
            self.assertFalse(records.has_key(18))

    def test_postscript_name(self):
        """Tests the postscript name."""
        for font_file, records in zip(self.font_files, self.names):
            family, weight, slope = self.parse_filename(font_file)
            style = self.build_style(weight, slope)
            expected_name = (family + '-' + style).replace(' ', '')
            self.assertEqual(records[6], expected_name)

    def test_postscript_name_for_spaces(self):
        """Tests that there are no spaces in PostScript names."""
        for records in self.names:
            self.assertFalse(' ' in records[6])


class TestDigitWidths(FontTest):
    """Tests the width of digits."""

    def setUp(self):
        self.font_files, self.fonts = self.loaded_fonts
        self.digits = [
            'zero', 'one', 'two', 'three', 'four',
            'five', 'six', 'seven', 'eight', 'nine']

    def test_digit_widths(self):
        """Tests all decimal digits to make sure they have the same width."""
        for font in self.fonts:
            hmtx_table = font['hmtx']
            widths = [hmtx_table[digit][0] for digit in self.digits]
            self.assertEqual(len(set(widths)), 1)

    def test_superscript_digits(self):
        """Tests that 'numr' features maps digits to Unicode superscripts."""
        ascii_digits = '0123456789'
        superscript_digits = u'⁰¹²³⁴⁵⁶⁷⁸⁹'
        for font_file in self.font_files:
            numr_glyphs = layout.get_advances(
                ascii_digits, font_file, '--features=numr')
            superscript_glyphs = layout.get_advances(
                superscript_digits, font_file)
            self.assertEqual(superscript_glyphs, numr_glyphs)


class TestCharacterCoverage(FontTest):
    """Tests character coverage."""

    def setUp(self):
        _, self.fonts = self.loaded_fonts

    def test_inclusion(self):
        """Tests for characters which should be included."""

        for font in self.fonts:
            charset = coverage.character_set(font)
            for char in self.include:
                self.assertIn(char, charset)

    def test_exclusion(self):
        """Tests that characters which should be excluded are absent."""

        for font in self.fonts:
            charset = coverage.character_set(font)
            for char in self.exclude:
                self.assertNotIn(char, charset)


class TestLigatures(FontTest):
    """Tests formation or lack of formation of ligatures."""

    def setUp(self):
        self.fontfiles, _ = self.loaded_fonts

    def test_lack_of_ff_ligature(self):
        """Tests that the ff ligature is not formed by default."""
        for fontfile in self.fontfiles:
            advances = layout.get_advances('ff', fontfile)
            self.assertEqual(len(advances), 2)

    def test_st_ligatures(self):
        """Tests that st ligatures are formed by dlig."""
        for fontfile in self.fontfiles:
            for combination in [u'st', u'ſt']:
                normal = layout.get_glyphs(combination, fontfile)
                ligated = layout.get_glyphs(
                    combination, fontfile, '--features=dlig')
                self.assertTrue(len(normal) == 2 and len(ligated) == 1)


class TestFeatures(FontTest):
    """Tests typographic features."""

    def setUp(self):
        self.fontfiles, _ = self.loaded_fonts

    def test_smcp_coverage(self):
        """Tests that smcp is supported for our required set."""
        with open('res/smcp_requirements.txt') as smcp_reqs_file:
            smcp_reqs_list = []
            for line in smcp_reqs_file.readlines():
                line = line[:line.index(' #')]
                smcp_reqs_list.append(unichr(int(line, 16)))

        for fontfile in self.fontfiles:
            chars_with_no_smcp = []
            for char in smcp_reqs_list:
                normal = layout.get_glyphs(char, fontfile)
                smcp = layout.get_glyphs(char, fontfile, '--features=smcp')
                if normal == smcp:
                    chars_with_no_smcp.append(char)
            self.assertEqual(
                chars_with_no_smcp, [],
                ("smcp feature is not applied to '%s'" %
                    u''.join(chars_with_no_smcp).encode('UTF-8')))


class TestVerticalMetrics(FontTest):
    """Test the vertical metrics of fonts."""

    def setUp(self):
        self.font_files, self.fonts = self.loaded_fonts

    def test_ymin_ymax(self):
        """Tests yMin and yMax to be equal to expected values."""

        for font in self.fonts:
            head_table = font['head']
            self.assertEqual(head_table.yMin, self.expected_head_yMin)
            self.assertEqual(head_table.yMax, self.expected_head_yMax)

    def test_glyphs_ymin_ymax(self):
        """Tests yMin and yMax of all glyphs to not go outside the range."""

        for font_file, font in zip(self.font_files, self.fonts):
            glyf_table = font['glyf']
            for glyph_name in glyf_table.glyphOrder:
                try:
                    y_min = glyf_table[glyph_name].yMin
                    y_max = glyf_table[glyph_name].yMax
                except AttributeError:
                    continue

                self.assertTrue(
                    self.expected_head_yMin <= y_min and
                    y_max <= self.expected_head_yMax,
                    ('The vertical metrics for glyph %s in %s exceed the '
                     'acceptable range: yMin=%d, yMax=%d' % (
                         glyph_name, font_file, y_min, y_max)))

    def test_hhea_table_metrics(self):
        """Tests ascent, descent, and lineGap to be equal to expected values."""

        for font in self.fonts:
            hhea_table = font['hhea']
            self.assertEqual(hhea_table.descent, self.expected_hhea_descent)
            self.assertEqual(hhea_table.ascent, self.expected_hhea_ascent)
            self.assertEqual(hhea_table.lineGap, self.expected_hhea_lineGap)

    def test_os2_metrics(self):
        """Tests OS/2 vertical metrics to be equal to expected values."""

        for font in self.fonts:
            os2_table = font['OS/2']
            self.assertEqual(os2_table.sTypoDescender,
                             self.expected_os2_sTypoDescender)
            self.assertEqual(os2_table.sTypoAscender,
                             self.expected_os2_sTypoAscender)
            self.assertEqual(os2_table.sTypoLineGap,
                             self.expected_os2_sTypoLineGap)
            self.assertEqual(os2_table.usWinDescent,
                             self.expected_os2_usWinDescent)
            self.assertEqual(os2_table.usWinAscent,
                             self.expected_os2_usWinAscent)


class TestHints(FontTest):
    """Tests hints."""

    def setUp(self):
        self.fontfiles, self.fonts = self.loaded_fonts

    def test_existance_of_hints(self):
        """Tests all glyphs and makes sure non-composite ones have hints."""
        missing_hints = []
        for font in self.fonts:
            glyf_table = font['glyf']
            for glyph_name in font.getGlyphOrder():
                glyph = glyf_table[glyph_name]
                if glyph.numberOfContours <= 0:  # composite or empty glyph
                    continue
                if len(glyph.program.bytecode) <= 0:
                    missing_hints.append(
                        (glyph_name, font_data.font_name(font)))

        self.assertTrue(missing_hints == [])

    def test_height_of_lowercase_o(self):
        """Tests the height of the lowercase o in low resolutions."""
        for fontfile in self.fontfiles:
            for size in range(8, 30):  # Kind of arbitrary
                o_height = get_rendered_char_height(
                    fontfile, size, 'o')
                n_height = get_rendered_char_height(
                    fontfile, size, 'n')
                self.assertEqual(o_height, n_height)


class TestGlyphAreas(unittest.TestCase):
    """Tests that glyph areas between weights have the right ratios.

    Must have the following attributes:
        master/instance_glyph_sets: Tuples each containing a list of font
            filenames and a list of glyph sets corresponding to those fonts.
        master/instance_glyphs_to_test: Lists of glyph names.
        master/instance_weights_to_test: Lists of weights as strings, should
            have exactly two master weights and >1 instance weight.
        exclude: List containing strings which if found in a font filename will
            exclude that font from testing, e.g. "Condensed", "Italic".
        whitelist: List containing names of glyphs to not test.

    Glyph sets are used instead of font objects so that either TTFs or UFOs can
    be tested. `exclude` should be used carefully so that only one
    master/instance per weight is included from the given glyph sets.
    """

    def setUp(self):
        """Determine which glyphs are intentionally unchanged."""

        self.unchanged = set()
        master_a, master_b = self.getGlyphSets(
            self.master_glyph_sets, self.master_weights_to_test)

        pen_a = GlyphAreaPen(master_a)
        pen_b = GlyphAreaPen(master_b)
        for name in self.master_glyphs_to_test:
            if name in self.whitelist:
                continue
            master_a[name].draw(pen_a)
            area_a = pen_a.unload()
            master_b[name].draw(pen_b)
            area_b = pen_b.unload()
            if area_a == area_b:
                if area_a:
                    self.unchanged.add(name)
            else:
                assert area_a and area_b

    def getGlyphSets(self, glyph_sets, weights):
        """Filter glyph sets to only those with certain weights."""

        glyph_set_map = {
            noto_fonts.parse_weight(font_file): glyph_set
            for font_file, glyph_set in zip(*glyph_sets)
            if all(style not in font_file for style in self.exclude)}
        return [glyph_set_map[w] for w in weights]

    def test_output(self):
        """Test that empty or intentionally unchanged glyphs are unchanged, and
        everything else is changed.
        """

        glyph_sets = self.getGlyphSets(
            self.instance_glyph_sets, self.instance_weights_to_test)

        standard = glyph_sets[0]
        pen = GlyphAreaPen(standard)
        areas = {}
        for name in self.instance_glyphs_to_test:
            standard[name].draw(pen)
            areas[name] = pen.unload()

        for other in glyph_sets[1:]:
            other_pen = GlyphAreaPen(other)
            for name, area in areas.iteritems():
                if name in self.whitelist:
                    continue
                other[name].draw(other_pen)
                other_area = other_pen.unload()
                if name in self.unchanged or not area:
                    self.assertEqual(
                        area, other_area,
                        name + " has changed, but should not have: %s vs. %s." %
                        (area, other_area))
                else:
                    self.assertNotEqual(
                        area, other_area,
                        name + " has not changed, but should have: %s vs. %s." %
                        (area, other_area))


class TestSpacingMarks(FontTest):
    """Tests that spacing marks are indeed spacing."""

    def setUp(self):
        self.font_files, _ = self.loaded_fonts
        charset = coverage.character_set(self.font_files[0])
        self.marks_to_test = [char for char in charset
                              if unicode_data.category(char) in ['Lm', 'Sk']]
        self.advance_cache = {}

    def test_individual_spacing_marks(self):
        """Tests that spacing marks are spacing by themselves."""
        for font in self.font_files:
            print 'Testing %s for stand-alone spacing marks...' % font
            for mark in self.marks_to_test:
                mark = unichr(mark)
                advances = layout.get_advances(mark, font)
                assert len(advances) == 1
                self.assertNotEqual(advances[0], 0)

    def test_spacing_marks_in_combination(self):
        """Tests that spacing marks do not combine with base letters."""
        for font in self.font_files:
            print 'Testing %s for spacing marks in combination...' % font
            for base_letter in (u'A\u00C6BCDEFGHIJKLMNO\u00D8\u01A0PRST'
                                u'U\u01AFVWXYZ'
                                u'a\u00E6bcdefghi\u0131j\u0237klmn'
                                u'o\u00F8\u01A1prs\u017Ftu\u01B0vwxyz'
                                u'\u03D2'):
                print 'Testing %s combinations' % base_letter
                for mark in self.marks_to_test:
                    if mark == 0x02DE:
                        # Skip rhotic hook, as it's perhaps OK for it to form
                        # ligatures
                        continue
                    mark = unichr(mark)
                    advances = layout.get_advances(base_letter + mark, font)
                    self.assertEqual(len(advances), 2,
                        'The sequence <%04X, %04X> combines, '
                        'but it should not' % (ord(base_letter), ord(mark)))


class TestSoftDottedChars(FontTest):
    """Tests that soft-dotted characters lose their dots."""

    def setUp(self):
        self.font_files, _ = self.loaded_fonts
        charset = coverage.character_set(self.font_files[0])
        self.marks_to_test = [char for char in charset
                              if unicode_data.combining(char) == 230]
        self.advance_cache = {}

    def test_combinations(self):
        """Tests that soft-dotted characters lose their dots when combined."""

        for font in self.font_files:
            print 'Testing %s for soft-dotted combinations...' % font

            # TODO: replace the following list with actual derivation based on
            # Unicode's soft-dotted property
            for base_letter in (u'ij\u012F\u0249\u0268\u029D\u02B2\u03F3\u0456'
                                u'\u0458\u1D62\u1D96\u1DA4\u1DA8\u1E2D\u1ECB'
                                u'\u2071\u2C7C'):
                print 'Testing %s combinations' % base_letter.encode('UTF-8')
                for mark in self.marks_to_test:
                    mark = unichr(mark)
                    letter_only = layout.get_glyphs(base_letter, font)
                    combination = layout.get_glyphs(base_letter + mark, font)
                    self.assertNotEqual(combination[0], letter_only[0],
                        "The sequence <%04X, %04X> doesn't lose its dot, "
                        "but it should" % (ord(base_letter), ord(mark)))
