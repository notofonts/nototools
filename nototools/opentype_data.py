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

"""OpenType-related data."""

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'


from nototools import unicode_data

OMPL = {}
def _set_ompl():
    """Set up OMPL.

    OMPL is defined to be the list of mirrored pairs in Unicode 5.1:
    http://www.microsoft.com/typography/otspec/ttochap1.htm#ltrrtl
    """

    global OMPL
    unicode_data.load_data()
    bmg_data = unicode_data._bidi_mirroring_glyph_data
    OMPL = {char:bmg for (char, bmg) in bmg_data.items()
            if float(unicode_data.age(char)) <= 5.1}


ZWSP = [0x200B]
JOINERS = [0x200C, 0x200D]
BIDI_MARKS = [0x200E, 0x200F]
DOTTED_CIRCLE = [0x25CC]

# From the various script-specific specs at
# http://www.microsoft.com/typography/SpecificationsOverview.mspx
SPECIAL_CHARACTERS_NEEDED = {
    'Arab': JOINERS + BIDI_MARKS + DOTTED_CIRCLE,
    'Beng': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Bugi': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Deva': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Gujr': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Guru': ZWSP + JOINERS + DOTTED_CIRCLE,
    # Hangul may not need the special characters:
    # https://code.google.com/p/noto/issues/detail?id=147#c2
    # 'Hang': ZWSP + JOINERS,
    'Hebr': BIDI_MARKS + DOTTED_CIRCLE,
    'Java': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Khmr': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Knda': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Laoo': ZWSP + DOTTED_CIRCLE,
    'Mlym': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Mymr': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Orya': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Sinh': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Syrc': JOINERS + BIDI_MARKS + DOTTED_CIRCLE,
    'Taml': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Telu': ZWSP + JOINERS + DOTTED_CIRCLE,
    'Thaa': BIDI_MARKS + DOTTED_CIRCLE,
    'Thai': ZWSP + DOTTED_CIRCLE,
    'Tibt': ZWSP + JOINERS + DOTTED_CIRCLE,
}

if not OMPL:
    _set_ompl()
