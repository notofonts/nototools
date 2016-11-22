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


from __future__ import print_function, unicode_literals

import unittest

from fontTools.agl import AGL2UV
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.feaLib.builder_test import makeTTFont
from fontTools.misc import UnicodeIO
from fontTools import mtiLib
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4

from nototools.hb_input import HbInputGenerator

CYCLIC_RULES = '''
feature onum {
    sub zero by zero.oldstyle;
} onum;

feature lnum {
    sub zero.oldstyle by zero;
} lnum;
'''

CONTEXTUAL_FORMAT1 = '''
FontDame GSUB table

feature table begin
0\ttest\ttest-lookup-ctx
feature table end

lookup\ttest-lookup-ctx\tcontext
glyph\tb,a\t1,test-lookup-sub
lookup end

lookup\ttest-lookup-sub\tsingle
a\tA.sc
lookup end
'''

CHAINED_FORMAT1 = '''
FontDame GSUB table

feature table begin
0\ttest\ttest-lookup-ctx
feature table end

lookup\ttest-lookup-ctx\tchained
glyph\tb\ta\tc\t1,test-lookup-sub
lookup end

lookup\ttest-lookup-sub\tsingle
a\tA.sc
lookup end
'''

SPEC_5fi1 = '''
lookup CNTXT_LIGS {
    substitute f i by f_i;
    substitute c t by c_t;
} CNTXT_LIGS;

lookup CNTXT_SUB {
    substitute n by n.end;
    substitute s by s.end;
} CNTXT_SUB;

feature test {
    substitute [a e i o u] f' lookup CNTXT_LIGS i' n' lookup CNTXT_SUB;
    substitute [a e i o u] c' lookup CNTXT_LIGS t' s' lookup CNTXT_SUB;
} test;
'''

SPEC_5fi2 = '''
feature test {
    substitute [a e n] d' by d.alt;
} test;
'''

SPEC_5fi3 = '''
feature test {
    substitute [A-Z] [A.sc-Z.sc]' by [a-z];
} test;
'''

SPEC_5fi4 = '''
feature test {
    substitute [e e.begin]' t' c by ampersand;
} test;
'''

CHAINING_REVERSE_BACKTRACK = '''
feature test {
    substitute [b e] [c f] a' [d g] by A.sc;
} test;
'''


class HbInputGeneratorTest(unittest.TestCase):
    def _make_generator(self, feature_source, fea_type='fea'):
        """Return input generator for font with GSUB compiled from given source.

        Adds a bunch of filler tables so the font can be saved if needed, for
        debugging purposes.
        """

        font = makeTTFont()
        glyph_order = font.getGlyphOrder()

        font['cmap'] = cmap = newTable('cmap')
        table = cmap_format_4(4)
        table.platformID = 3
        table.platEncID = 1
        table.language = 0
        table.cmap = {AGL2UV[n]: n for n in glyph_order if n in AGL2UV}
        cmap.tableVersion = 0
        cmap.tables = [table]

        font['glyf'] = glyf = newTable('glyf')
        glyf.glyphs = {}
        glyf.glyphOrder = glyph_order
        for name in glyph_order:
            pen = TTGlyphPen(None)
            glyf[name] = pen.glyph()

        font['head'] = head = newTable('head')
        head.tableVersion = 1.0
        head.fontRevision = 1.0
        head.flags = head.checkSumAdjustment = head.magicNumber =\
            head.created = head.modified = head.macStyle = head.lowestRecPPEM =\
            head.fontDirectionHint = head.indexToLocFormat =\
            head.glyphDataFormat =\
            head.xMin = head.xMax = head.yMin = head.yMax = 0
        head.unitsPerEm = 1000

        font['hhea'] = hhea = newTable('hhea')
        hhea.tableVersion = 0x00010000
        hhea.ascent = hhea.descent = hhea.lineGap =\
            hhea.caretSlopeRise = hhea.caretSlopeRun = hhea.caretOffset =\
            hhea.reserved0 = hhea.reserved1 = hhea.reserved2 = hhea.reserved3 =\
            hhea.metricDataFormat = hhea.advanceWidthMax = hhea.xMaxExtent =\
            hhea.minLeftSideBearing = hhea.minRightSideBearing =\
            hhea.numberOfHMetrics = 0

        font['hmtx'] = hmtx = newTable('hmtx')
        hmtx.metrics = {}
        for name in glyph_order:
            hmtx[name] = (600, 50)

        font['loca'] = newTable('loca')

        font['maxp'] = maxp = newTable('maxp')
        maxp.tableVersion = 0x00005000
        maxp.numGlyphs = 0

        font['post'] = post = newTable('post')
        post.formatType = 2.0
        post.extraNames = []
        post.mapping = {}
        post.glyphOrder = glyph_order
        post.italicAngle = post.underlinePosition = post.underlineThickness =\
            post.isFixedPitch = post.minMemType42 = post.maxMemType42 =\
            post.minMemType1 = post.maxMemType1 = 0

        if fea_type == 'fea':
            addOpenTypeFeaturesFromString(font, feature_source)
        elif fea_type == 'mti':
            font['GSUB'] = mtiLib.build(UnicodeIO(feature_source), font)
        return HbInputGenerator(font)

    def test_no_gsub(self):
        g = self._make_generator('')
        self.assertEqual(g.input_from_name('a'), ((), 'a'))
        self.assertEqual(g.input_from_name('acute', pad=True), ((), ' \u00b4'))

    def test_input_not_found(self):
        g = self._make_generator('')
        self.assertEqual(g.input_from_name('A.sc'), None)

    def test_cyclic_rules_not_followed(self):
        g = self._make_generator(CYCLIC_RULES)
        self.assertEqual(g.input_from_name('zero.oldstyle'), (('onum',), '0'))

    def test_contextual_substitution_type1(self):
        g = self._make_generator(CONTEXTUAL_FORMAT1, fea_type='mti')
        self.assertEqual(g.input_from_name('A.sc'), (('test',), 'ba'))

    def test_chaining_substitution_type1(self):
        g = self._make_generator(CHAINED_FORMAT1, fea_type='mti')
        self.assertEqual(g.input_from_name('A.sc'), (('test',), 'bac'))

    def test_chaining_substitution_type3(self):
        g = self._make_generator(SPEC_5fi1)
        self.assertEqual(g.input_from_name('f_i'), (('test',), 'afin'))
        self.assertEqual(g.input_from_name('c_t'), (('test',), 'acts'))
        self.assertEqual(g.input_from_name('n.end'), (('test',), 'afin'))
        self.assertEqual(g.input_from_name('s.end'), (('test',), 'acts'))

        g = self._make_generator(SPEC_5fi2)
        self.assertEqual(g.input_from_name('d.alt'), (('test',), 'ad'))

    def test_no_feature_rule_takes_precedence(self):
        g = self._make_generator(SPEC_5fi3)
        self.assertEqual(g.input_from_name('a'), ((), 'a'))

        g = self._make_generator(SPEC_5fi4)
        self.assertEqual(g.input_from_name('ampersand'), ((), '&'))

    def test_chaining_substitution_backtrack_reversed(self):
        g = self._make_generator(CHAINING_REVERSE_BACKTRACK)
        self.assertEqual(g.input_from_name('A.sc'), (('test',), 'bcad'))

if __name__ == '__main__':
    unittest.main()
