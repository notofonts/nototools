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

"""Tests for coverage.py."""

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'

import os
from os import path
import unittest

import coverage


class CharacterSetTest(unittest.TestCase):
    """Test class for coverage.character_set."""
    def test_sanity(self):
        """Test basic sanity of the method."""
        font_file_name = path.join(
            path.dirname(__file__), os.pardir,
            'fonts', 'individual', 'unhinted', 'NotoSansAvestan-Regular.ttf')
        charset = coverage.character_set(font_file_name)

        self.assertTrue(ord(' ') in charset)
        self.assertTrue(0x10B00 in charset)
        self.assertFalse(ord('A') in charset)


if __name__ == '__main__':
    unittest.main()
