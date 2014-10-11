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

"""Noto-specific data about division of ranges between fonts.
"""

__author__ = "roozbeh@google.com (Roozbeh Pournader)"


CJK_RANGES_TXT = """
# Core
3400..4DBF; CJK Unified Ideographs Extension A
4E00..9FFF; CJK Unified Ideographs
F900..FAFF; CJK Compatibility Ideographs
20000..2A6DF; CJK Unified Ideographs Extension B
2A700..2B73F; CJK Unified Ideographs Extension C
2B740..2B81F; CJK Unified Ideographs Extension D
2F800..2FA1F; CJK Compatibility Ideographs Supplement
AC00..D7AF; Hangul Syllables
1100..11FF; Hangul Jamo
A960..A97F; Hangul Jamo Extended-A
D7B0..D7FF; Hangul Jamo Extended-B
3130..318F; Hangul Compatibility Jamo

3040..309F; Hiragana
1B000..1B0FF; Kana Supplement
30A0..30FF; Katakana
31F0..31FF; Katakana Phonetic Extensions

3100..312F; Bopomofo
31A0..31BF; Bopomofo Extended

# Others
3000..303F; CJK Symbols and Punctuation
3190..319F; Kanbun
31C0..31EF; CJK Strokes
3200..32FF; Enclosed CJK Letters and Months
FE10..FE1F; Vertical Forms
FE30..FE4F; CJK Compatibility Forms
FE50..FE6F; Small Form Variants
FF00..FFEF; Halfwidth and Fullwidth Forms

3300..33FF; CJK Compatibility
2FF0..2FFF; Ideographic Description Characters
2E80..2EFF; CJK Radicals Supplement
2F00..2FDF; Kangxi Radicals
"""

SYMBOL_RANGES_TXT = """
20A0..20CF; Currency Symbols
20D0..20FF; Combining Diacritical Marks for Symbols
2100..214F; Letterlike Symbols
2190..21FF; Arrows
2200..22FF; Mathematical Operators
2300..23FF; Miscellaneous Technical
2400..243F; Control Pictures
2440..245F; Optical Character Recognition
2460..24FF; Enclosed Alphanumerics
2500..257F; Box Drawing
2580..259F; Block Elements
25A0..25FF; Geometric Shapes
2600..26FF; Miscellaneous Symbols
2700..27BF; Dingbats
27C0..27EF; Miscellaneous Mathematical Symbols-A
27F0..27FF; Supplemental Arrows-A
2800..28FF; Braille Patterns
2900..297F; Supplemental Arrows-B
2980..29FF; Miscellaneous Mathematical Symbols-B
2A00..2AFF; Supplemental Mathematical Operators
2B00..2BFF; Miscellaneous Symbols and Arrows
2E00..2E7F; Supplemental Punctuation
4DC0..4DFF; Yijing Hexagram Symbols
A700..A71F; Modifier Tone Letters
FFF0..FFFF; Specials
10100..1013F; Aegean Numbers
10140..1018F; Ancient Greek Numbers
10190..101CF; Ancient Symbols
101D0..101FF; Phaistos Disc
1D000..1D0FF; Byzantine Musical Symbols
1D100..1D1FF; Musical Symbols
1D200..1D24F; Ancient Greek Musical Notation
1D300..1D35F; Tai Xuan Jing Symbols
1D360..1D37F; Counting Rod Numerals
1D400..1D7FF; Mathematical Alphanumeric Symbols
1F000..1F02F; Mahjong Tiles
1F030..1F09F; Domino Tiles
1F0A0..1F0FF; Playing Cards
1F100..1F1FF; Enclosed Alphanumeric Supplement
1F200..1F2FF; Enclosed Ideographic Supplement
1F700..1F77F; Alchemical Symbols
"""

UNDER_DEVELOPMENT_RANGES_TXT = """
0780..07BF; Thaana
0B00..0B7F; Oriya
0F00..0FFF; Tibetan
"""

DEEMED_UI_SCRIPTS_SET = frozenset({
  'Armn', # Armenian
  'Cher', # Cherokee
  'Ethi', # Ethiopic
  'Geor', # Georgian
  'Hebr', # Hebrew
  'Sinh', # Sinhala
  'Thaa', # Thaana
  'Qaae', # Emoji
})


EXTRA_CHARACTERS_NEEDED = {
    'Arab': [
        0x2010, 0x2011,   # Hyphen and non-breaking hyphen need different shapes
        0x204F, 0x2E41],  # For Sindhi

    # From http://www.unicode.org/L2/L2014/14064r-n4537r-cherokee.pdf section 8
    'Cher': [
        0x0300, 0x0301, 0x0302, 0x0304, 0x030B,
        0x030C, 0x0323, 0x0324, 0x0330, 0x0331],

    # From Core Specification
    'Copt': [
        0x0300, 0x0304, 0x0305, 0x0307, 0x033F,
        0x0374, 0x0375, 0xFE24, 0xFE25, 0xFE26],

    'Lisu': [0x02BC, 0x02CD],  # From Core Specification

    'Sylo': [0x2055],  # From Core Specification

    # From Core Specification & http://www.unicode.org/L2/L2001/01369-n2372.pdf
    'Tale': [0x0300, 0x0301, 0x0307, 0x0308, 0x030C],

    # From Core Specificaion and
    # http://www.unicode.org/L2/L2010/10407-ext-tamil-follow2.pdf
    'Taml': [0x00B2, 0x00B3, 0x2074, 0x2082, 0x2083, 0x2084],

    # From Core Specification and
    # http://www.unicode.org/L2/L2010/10451-patani-proposal.pdf
    'Thai': [0x02BC, 0x02D7, 0x0303, 0x0331],

    # Azerbaijani manat, Russian ruble, and Georgian Lari
    'Zsym': [0x20BC, 0x20BD, 0x20BE],
}


def char_range(start, end):
    return range(start, end+1)

CHARACTERS_NOT_NEEDED = {
    'Arab': char_range(0x10E60, 0x10E7E),
    'Latn': (  # Actually LGC
        char_range(0x0370, 0x0373) +
        [0x0376, 0x0377, 0x03CF, 0x0951, 0x0952, 0x1E9C, 0x1E9D, 0x1E9F] +
        char_range(0x1EFA, 0x1EFF) +
        [0x2071] +
        char_range(0x2095, 0x209C) +
        char_range(0x2160, 0x2183) +
        char_range(0x2185, 0x2188) +
        char_range(0x2C6E, 0x2C70) +
        char_range(0x2C78, 0x2C7F) +
        char_range(0x2DE0, 0x2DFF) +
        char_range(0xA640, 0xA673) +
        char_range(0xA67C, 0xA697) +
        char_range(0xA722, 0xA787) +
        [0xA78D, 0xA78E, 0xA790, 0xA791] +
        char_range(0xA7A0, 0xA7A9) +
        char_range(0xA7FA, 0xA7FF) +
        [0xA92E, 0xFB00, 0xFB05, 0xFB06]),
}

ACCEPTABLE_AS_COMBINING = {
    0x02DE,  # MODIFIER LETTER RHOTIC HOOK
}
