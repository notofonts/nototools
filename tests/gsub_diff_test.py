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
        print(len(diffs))
        self.assertIn('%d differences in GSUB rules' % len(pairs), diffs)
        for pair_diff in pairs:
            self.assertIn(pair_diff, diffs)

    def test_type1_gsub(self):
        self._expect_gsub_diffs('''
                sub A by A.sc;
                sub B by B.sc;
            ''', '''
                sub A by A.sc;
            ''',
            [('- ccmp B B.sc')])


if __name__ == '__main__':
    unittest.main()
