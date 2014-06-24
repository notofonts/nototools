#!/usr/bin/python
#
# Copyright 2014 Google Inc. All rights reserved.
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

"""Tests for unicode_data.py."""

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'

import unittest

import unicode_data


class UnicodeDataTest(unittest.TestCase):
    """Tests for unicode_data module."""
    def test_name(self):
        """Tests the name() method."""
        self.assertEqual('WARANG CITI OM', unicode_data.name(0x118FF))

    def test_category(self):
        """Tests the category() method."""
        self.assertEqual('Co', unicode_data.category(0xF0001))
        self.assertEqual('Cn', unicode_data.category(0xE01F0))

    def test_script(self):
        """Tests the script() method."""
        self.assertEqual('Latn', unicode_data.script(0xA794))
        self.assertEqual('Zzzz', unicode_data.script(0xE006))

    def test_block(self):
        """Tests the block() method."""
        self.assertEqual('Emoticons', unicode_data.block(0x1F600))

    def test_default_ignorable(self):
        """Tests the is_default_ignorable() method."""
        self.assertTrue(unicode_data.is_default_ignorable(0x061C))
        self.assertFalse(unicode_data.is_default_ignorable(0x0020))

    def test_defined(self):
        """Tests the is_defined() method."""
        self.assertTrue(unicode_data.is_defined(0x20BD))
        self.assertFalse(unicode_data.is_defined(0xFDD0))
        # CJK ranges
        self.assertTrue(unicode_data.is_defined(0x3400))
        self.assertTrue(unicode_data.is_defined(0x4DB5))
        self.assertFalse(unicode_data.is_defined(0x4DB6))

    def test_parse_code_ranges(self):
        """Tests the _parse_code_ranges method."""
        source = (
            '0000..001F    ; Common # Cc  [32] <control-0000>..<control-001F>\n'
            '0020          ; Common # Zs       SPACE\n')
        self.assertEqual(
            [(0, 31, 'Common'), (32, 32, 'Common')],
            unicode_data._parse_code_ranges(source))

if __name__ == '__main__':
    unittest.main()
