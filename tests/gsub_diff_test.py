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


"""Tests for gsub_diff module. Test examples for each LookupType taken from
the Adobe fea spec:
http://www.adobe.com/devnet/opentype/afdko/topic_feature_file_syntax.html#5.b
"""

import tempfile
import unittest
from nototools.gsub_diff import GsubDiffFinder
from hb_input_test import make_font


class GposDiffFinderText(unittest.TestCase):
    def _expect_gsub_diffs(self, source_a, source_b, pairs):
        font_a = make_font('feature ccmp {\n%s\n} ccmp;' % source_a)
        font_b = make_font('feature ccmp {\n%s\n} ccmp;' % source_b)
        file_a = tempfile.NamedTemporaryFile()
        file_b = tempfile.NamedTemporaryFile()
        font_a.save(file_a.name)
        font_b.save(file_b.name)
        finder = GsubDiffFinder(file_a.name, file_b.name)

        diffs = finder.find_gsub_diffs()
        self.assertIn('%d differences in GSUB rules' % len(pairs), diffs)
        for pair_diff in pairs:
            self.assertIn(pair_diff, diffs)

    def test_type1_gsub_1(self):
        """Test LookupType 1 Single substitutions"""
        self._expect_gsub_diffs('''
                sub A by A.sc;
                sub B by B.sc;
            ''', '''
                sub A by A.sc;
            ''',
            [('- ccmp B by B.sc')])

    def test_type1_gsub_2(self):
        """Test LookupType 1 Single substitutions on groups"""
        self._expect_gsub_diffs('''
                sub [A B] by [A.sc B.sc];
            ''', '''
                sub [A] by [A.sc];
            ''',
            [('- ccmp B by B.sc')])

    def test_type2_gsub(self):
        """Test LookupType 2 Multiple substitutions"""
        self._expect_gsub_diffs('''
                sub f_l by f l;
            ''', '''
                sub f_l by f l;
                sub c_h by c h;
            ''',
            [('+ ccmp c_h by c h')])

    def test_type3_gsub(self):
        """Test LookupType 3 Alternate substitutions"""
        self._expect_gsub_diffs('''
                sub A from [A.swash A.sc];
            ''', '''
                sub A from [A.swash A.sc];
                sub B from [B.swash B.sc];
            ''',
            [('+ ccmp B from B.swash'),
             ('+ ccmp B from B.sc')])

    def test_type4_gsub_1(self):
        """Test LookupType 4 Ligature substitutions"""
        self._expect_gsub_diffs('''
            sub f l by f_l;
            sub c h by c_h;
            ''', '''
            sub f l by f_l;
            ''',
            [('- ccmp c h by c_h')])

    def test_type4_gsub_2(self):
        """Test LookupType 4 Ligature substitutions on groups"""
        self._expect_gsub_diffs('''
            sub [f F.swash] [l L.swash] by f_l;
            ''', '''
            sub [f] [l] by f_l;
            ''',
            [('- ccmp F.swash L.swash by f_l'),
             ('- ccmp F.swash l by f_l'),
             ('- ccmp f L.swash by f_l'),
            ])

    def test_type5_and_6_gsub_1(self):
        """LookupType 5 and 6 not implemented, make sure it returns nothing.

        This lookupType can use other lookups so include them in the test"""
        self._expect_gsub_diffs('''
            lookup CNTXT_LIGS {
                 sub c t by c_t;
             } CNTXT_LIGS;
             
            lookup CNTXT_SUB {
                 sub s by s.end;
             } CNTXT_SUB;
            
            # LookupType 6 implementation
            lookup test {
                 sub [ a e i o u] c' lookup CNTXT_LIGS t' s' lookup CNTXT_SUB;
             } test;
            ''','''
            lookup CNTXT_LIGS {
                 sub c t by c_t;
             } CNTXT_LIGS;
             
            lookup CNTXT_SUB {
                 sub s by s.end;
             } CNTXT_SUB;
            ''',
            [])

    def test_type5_and_6_gsub_2(self):
        """LookupType 5 and 6 not implemented, make sure it returns nothing.
        """
        self._expect_gsub_diffs('''
            substitute [a e n] d' by d.alt;
            ''','''
            ''',
            [])

    def test_type5_and_6_gsub_3(self):
        """LookupType 5 and 6 not implemented, make sure it returns nothing.
        """
        self._expect_gsub_diffs('''
            substitute [e e.begin]' t' c by ampersand;
            ''','''
            ''',
            [])

    def test_type7_gsub(self):
        """Test LookupType 7 Extension substitution"""
        self._expect_gsub_diffs('''
            lookup fracbar useExtension {
                 sub slash by fraction;
             } fracbar;
            ''','''
            lookup fracbar useExtension {
                # missing rules
             } fracbar;
            ''',
            [('- ccmp slash by fraction')])

    def test_type8_gsub(self):
        """LookupType 8 not implemented, make sure it returns nothing"""
        self._expect_gsub_diffs('''
            reversesub [a e n] d' by d.alt;
            ''','''

            ''',
            [])


if __name__ == '__main__':
    unittest.main()
