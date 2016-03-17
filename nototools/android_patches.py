#!/usr/bin/python
# -*- coding: UTF-8 -*-
# Copyright 2016 Google Inc. All rights reserved.
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

"""Patches for Android versions of Noto fonts."""

import glob
from os import path

from nototools import subset
from nototools import coverage
from nototools import fix_khmer_and_lao_coverage as merger
from nototools import font_data
from nototools import tool_utils
from nototools import unicode_data

from fontTools import ttLib
from fontTools.ttLib.tables import otTables

SRC_DIR = tool_utils.resolve_path('[tools]/packages/android')
DST_DIR = tool_utils.resolve_path('[tools]/packages/android-patched')

def _patch_serif_lgc():
  """Delete smiley and playing card suits from Noto Serif LGC.

  Previously, the existance of the five characters in the Noto Serif
  LGC fonts was causing them to override the versions in the Noto Color
  Emoji font when a serif style was specified for text, leading to
  inconsistent use of emoji in sans versus serif text.

  Bug: 24740612"""

  CHARS_TO_DELETE = {
      0x263A, # WHITE SMILING FACE
      0x2660, # BLACK SPADE SUIT
      0x2663, # BLACK CLUB SUIT
      0x2665, # BLACK HEART SUIT
      0x2666, # BLACK DIAMOND SUIT
  }
  for font_file in glob.glob(path.join(SRC_DIR, 'NotoSerif-*.ttf')):
    print 'delete smiley/playing card', font_file
    out_file = path.join(DST_DIR, path.basename(font_file))
    subset.subset_font(font_file, out_file, exclude=CHARS_TO_DELETE)


def _patch_hyphen_armenian_ethiopic():
  """Add hyphen-minus glyphs to Armenian and Ethiopic fonts.

  This is to enable Armenian and Amharic langauges to be hyphenated
  properly, since Minikin's itemizer currently shows tofus if a an
  automatically hyphenated word is displated in a font that has neither
  HYPHEN nor HYPHEN-MINUS.

  In practice only U+002D HYPHEN-MINUS is added, since Noto LGC fonts
  don't have U+2010 HYPHEN.)

  Bug: 21570828"""

  FONTS = [
      'NotoSansArmenian-Regular.ttf',
      'NotoSansArmenian-Bold.ttf',
      'NotoSerifArmenian-Regular.ttf',
      'NotoSerifArmenian-Bold.ttf',
      'NotoSansEthiopic-Regular.ttf',
      'NotoSansEthiopic-Bold.ttf',
  ]

  HYPHENS = {0x002D, 0x2010}

  for font_name in FONTS:
    lgc_font_name = (
        font_name.replace('Armenian', '')
        .replace('Ethiopic', ''))

    font_file = path.join(SRC_DIR, font_name)
    lgc_font_file = path.join(SRC_DIR, lgc_font_name)

    chars_to_add = (
        (HYPHENS - coverage.character_set(font_file))
        & coverage.character_set(lgc_font_file))

    if chars_to_add:
      print 'patch hyphens', font_name
      merger.merge_chars_from_bank(
          path.join(SRC_DIR, font_name),
          path.join(SRC_DIR, lgc_font_name),
          path.join(DST_DIR, font_name),
          chars_to_add)


# Characters we have decided we are doing as emoji-style in Android,
# despite UTR#51's recommendation
ANDROID_EMOJI = [
    0x2600, # ☀ BLACK SUN WITH RAYS
    0x2601, # ☁ CLOUD
    0X260E, # ☎ BLACK TELEPHONE
    0x261D, # ☝ WHITE UP POINTING INDEX
    0x263A, # ☺ WHITE SMILING FACE
    0x2660, # ♠ BLACK SPADE SUIT
    0x2663, # ♣ BLACK CLUB SUIT
    0x2665, # ♥ BLACK HEART SUIT
    0x2666, # ♦ BLACK DIAMOND SUIT
    0x270C, # ✌ VICTORY HAND
    0x2744, # ❄ SNOWFLAKE
    0x2764, # ❤ HEAVY BLACK HEART
]


def _remove_cjk_emoji():
  """(two fixes)
  ---
  Remove default emoji characters from CJK fonts.

  Twenty-six characters that Unicode Technical Report #51 "Unicode
  Emoji" defines as defaulting to emoji styles used to be displayed as
  black and white ("text" style) before this. This patch removes those
  characters from Noto CJK fonts, so they get displayed as color.

  As a side effect of the subsetting process, some ideographic
  variation sequences are also removed from some of the fonts, but this
  doesn't cause a difference, as they are not presently supported in
  Minikin.

  The Korean font doesn't change in coverage, but seems to get some
  size reduction being passed through fontTools, so it's included in
  the patch.

  (1c4749e20391a4)
  ----
  ### NOTE: Roozbeh says (2016/03/10) this is no longer needed.

  Make 12 characters default to color emoji style.

  The Noto Sans Symbols font and the script that subsets it have been
  updated to excluce the 12 characters we decided to make default to
  color in Android.

  The Noto Sans Simplified Chinese font was also subsetted.

  (5855164ed87)"""

  def _remove_from_cmap(infile, outfile, exclude=[]):
    font = ttLib.TTFont(infile)
    font_data.delete_from_cmap(font, exclude)
    font.save(outfile)

  EMOJI = (
      [0x26BD, 0x26BE, 0x1F18E]
      + range(0x1F191, 0x1F19A+1)
      + [0x1F201, 0x1F21A, 0x1F22F]
      + range(0x1F232, 0x1F236+1)
      + [0x1F238, 0x1F239, 0x1F23A, 0x1F250, 0x1F251]
  )

  names = ['cjk/NotoSans%sCJK%s-Regular.otf' % (m, v)
           for m in ['', 'Mono']
           for v in ['jp', 'kr', 'sc', 'tc']]
  for font_name in names:
    print 'remove cjk emoji', font_name
    _remove_from_cmap(
        font_name,
        path.join(outdir, font_name),
        exclude=EMOJI)


def _fix_arabic_ligatures():
  """Fix U+FDF2 and Allah-related ligatures in Naskh fonts.

  U+FDF2 ARABIC LIGATURE ALLAH ISOLATED FORM missed the initial alef in
  its glyph, while the Allah ligatures were incorrectly formed.

  (8ae3a28c050ef9)"""

  # noto-fonts/issues/384 was fixed, so this patch is not needed.
  pass


# below are used by _subset_symbols

# Unicode blocks that we want to include in the font
BLOCKS_TO_INCLUDE = """
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
2A00..2AFF; Supplemental Mathematical Operators
"""

# One-off characters to be included, needed for backward compatibility and
# supporting various character sets, including ARIB sets and black and white
# emoji
ONE_OFF_ADDITIONS = {
    0x27D0, # ⟐ WHITE DIAMOND WITH CENTRED DOT
    0x2934, # ⤴ ARROW POINTING RIGHTWARDS THEN CURVING UPWARDS
    0x2935, # ⤵ ARROW POINTING RIGHTWARDS THEN CURVING DOWNWARDS
    0x2985, # ⦅ LEFT WHITE PARENTHESIS
    0x2986, # ⦆ RIGHT WHITE PARENTHESIS
    0x2B05, # ⬅ LEFTWARDS BLACK ARROW
    0x2B06, # ⬆ UPWARDS BLACK ARROW
    0x2B07, # ⬇ DOWNWARDS BLACK ARROW
    0x2B24, # ⬤ BLACK LARGE CIRCLE
    0x2B2E, # ⬮ BLACK VERTICAL ELLIPSE
    0x2B2F, # ⬯ WHITE VERTICAL ELLIPSE
    0x2B56, # ⭖ HEAVY OVAL WITH OVAL INSIDE
    0x2B57, # ⭗ HEAVY CIRCLE WITH CIRCLE INSIDE
    0x2B58, # ⭘ HEAVY CIRCLE
    0x2B59, # ⭙ HEAVY CIRCLED SALTIRE
}

# letter-based characters, provided by Roboto
LETTERLIKE_CHARS_IN_ROBOTO = {
    0x2100, # ℀ ACCOUNT OF
    0x2101, # ℁ ADDRESSED TO THE SUBJECT
    0x2103, # ℃ DEGREE CELSIUS
    0x2105, # ℅ CARE OF
    0x2106, # ℆ CADA UNA
    0x2109, # ℉ DEGREE FAHRENHEIT
    0x2113, # ℓ SCRIPT SMALL L
    0x2116, # № NUMERO SIGN
    0x2117, # ℗ SOUND RECORDING COPYRIGHT
    0x211E, # ℞ PRESCRIPTION TAKE
    0x211F, # ℟ RESPONSE
    0x2120, # ℠ SERVICE MARK
    0x2121, # ℡ TELEPHONE SIGN
    0x2122, # ™ TRADE MARK SIGN
    0x2123, # ℣ VERSICLE
    0x2125, # ℥ OUNCE SIGN
    0x2126, # Ω OHM SIGN
    0x212A, # K KELVIN SIGN
    0x212B, # Å ANGSTROM SIGN
    0x212E, # ℮ ESTIMATED SYMBOL
    0x2132, # Ⅎ TURNED CAPITAL F
    0x213B, # ℻ FACSIMILE SIGN
    0x214D, # ⅍ AKTIESELSKAB
    0x214F, # ⅏ SYMBOL FOR SAMARITAN SOURCE
}

# default emoji characters in the BMP, based on
# http://www.unicode.org/draft/Public/emoji/1.0/emoji-data.txt
# We exclude these, so we don't block color emoji.
BMP_DEFAULT_EMOJI = {
    0x231A, # ⌚ WATCH
    0x231B, # ⌛ HOURGLASS
    0x23E9, # ⏩ BLACK RIGHT-POINTING DOUBLE TRIANGLE
    0x23EA, # ⏪ BLACK LEFT-POINTING DOUBLE TRIANGLE
    0x23EB, # ⏫ BLACK UP-POINTING DOUBLE TRIANGLE
    0x23EC, # ⏬ BLACK DOWN-POINTING DOUBLE TRIANGLE
    0x23F0, # ⏰ ALARM CLOCK
    0x23F3, # ⏳ HOURGLASS WITH FLOWING SAND
    0x25FD, # ◽ WHITE MEDIUM SMALL SQUARE
    0x25FE, # ◾ BLACK MEDIUM SMALL SQUARE
    0x2614, # ☔ UMBRELLA WITH RAIN DROPS
    0x2615, # ☕ HOT BEVERAGE
    0x2648, # ♈ ARIES
    0x2649, # ♉ TAURUS
    0x264A, # ♊ GEMINI
    0x264B, # ♋ CANCER
    0x264C, # ♌ LEO
    0x264D, # ♍ VIRGO
    0x264E, # ♎ LIBRA
    0x264F, # ♏ SCORPIUS
    0x2650, # ♐ SAGITTARIUS
    0x2651, # ♑ CAPRICORN
    0x2652, # ♒ AQUARIUS
    0x2653, # ♓ PISCES
    0x267F, # ♿ WHEELCHAIR SYMBOL
    0x2693, # ⚓ ANCHOR
    0x26A1, # ⚡ HIGH VOLTAGE SIGN
    0x26AA, # ⚪ MEDIUM WHITE CIRCLE
    0x26AB, # ⚫ MEDIUM BLACK CIRCLE
    0x26BD, # ⚽ SOCCER BALL
    0x26BE, # ⚾ BASEBALL
    0x26C4, # ⛄ SNOWMAN WITHOUT SNOW
    0x26C5, # ⛅ SUN BEHIND CLOUD
    0x26CE, # ⛎ OPHIUCHUS
    0x26D4, # ⛔ NO ENTRY
    0x26EA, # ⛪ CHURCH
    0x26F2, # ⛲ FOUNTAIN
    0x26F3, # ⛳ FLAG IN HOLE
    0x26F5, # ⛵ SAILBOAT
    0x26FA, # ⛺ TENT
    0x26FD, # ⛽ FUEL PUMP
    0x2705, # ✅ WHITE HEAVY CHECK MARK
    0x270A, # ✊ RAISED FIST
    0x270B, # ✋ RAISED HAND
    0x2728, # ✨ SPARKLES
    0x274C, # ❌ CROSS MARK
    0x274E, # ❎ NEGATIVE SQUARED CROSS MARK
    0x2753, # ❓ BLACK QUESTION MARK ORNAMENT
    0x2754, # ❔ WHITE QUESTION MARK ORNAMENT
    0x2755, # ❕ WHITE EXCLAMATION MARK ORNAMENT
    0x2757, # ❗ HEAVY EXCLAMATION MARK SYMBOL
    0x2795, # ➕ HEAVY PLUS SIGN
    0x2796, # ➖ HEAVY MINUS SIGN
    0x2797, # ➗ HEAVY DIVISION SIGN
    0x27B0, # ➰ CURLY LOOP
    0x27BF, # ➿ DOUBLE CURLY LOOP
    0x2B1B, # ⬛ BLACK LARGE SQUARE
    0x2B1C, # ⬜ WHITE LARGE SQUARE
    0x2B50, # ⭐ WHITE MEDIUM STAR
    0x2B55, # ⭕ HEAVY LARGE CIRCLE
}


def _subset_symbols():
  """Subset Noto Sans Symbols in a curated way.

  Noto Sans Symbols is now subsetted in a curated way. Changes include:

  * Currency symbols now included in Roboto are removed.

  * All combining marks for symbols (except for combining keycap) are
    added, to combine with other symbols if needed.

  * Characters in symbol blocks that are also covered by Noto CJK fonts
    are added, for better harmony with the rest of the fonts in non-CJK
    settings. The dentistry characters at U+23BE..23CC are not added,
    since they appear to be Japan-only and full-width.

  * Characters that UTR #51 defines as default text are added, although
    they may also exist in the color emoji font, to make sure they get
    a default text style.

  * Characters that UTR #51 defines as default emoji are removed, to
    make sure they don't block the fallback to the color emoji font.

  * A few math symbols that are currently included in Roboto are added,
    to prepare for potentially removing them from Roboto when they are
    lower-quality in Roboto.

  Based on subset_noto_sans_symbols.py from AOSP external/noto-fonts."""

  target_coverage = set()
  # Add all characters in BLOCKS_TO_INCLUDE
  for first, last, _ in unicode_data._parse_code_ranges(BLOCKS_TO_INCLUDE):
    target_coverage.update(range(first, last+1))

  # Add one-off characters
  target_coverage |= ONE_OFF_ADDITIONS
  # Remove characters preferably coming from Roboto
  target_coverage -= LETTERLIKE_CHARS_IN_ROBOTO
  # Remove characters that are supposed to default to emoji

  # According to Roozbeh, CJK is not available on all platforms, so even
  # if we don't remove the ANDROID_EMOJI from CJK we might still want
  # them if there's no fallback for them in DroidSansFallback-- and there
  # isn't.  So leave them in the Symbols-Subsetted font.
  target_coverage -= BMP_DEFAULT_EMOJI # | ANDROID_EMOJI

  # Remove dentistry symbols, as their main use appears to be for CJK:
  # http://www.unicode.org/L2/L2000/00098-n2195.pdf
  target_coverage -= set(range(0x23BE, 0x23CC+1))

  # Remove COMBINING ENCLOSING KEYCAP. It's needed for Android's color emoji
  # mechanism to work properly
  target_coverage.remove(0x20E3)

  for font_file in glob.glob(path.join(SRC_DIR, 'NotoSansSymbols-*.ttf')):
    print 'main subset', font_file
    out_file = path.join(
        DST_DIR, path.basename(font_file)[:-4] + '-Subsetted.ttf')
    subset.subset_font(font_file, out_file, include=target_coverage)

  # Roozbeh wants a second subset with emoji presentation characters that
  # take text-presentation variation sequences.  This will be a fallback
  # after the color emoji.
  target_coverage = set(
      unicode_data.get_presentation_default_emoji() &
      unicode_data.get_unicode_emoji_variants())
  for font_file in glob.glob(path.join(SRC_DIR, 'NotoSansSymbols-*.ttf')):
    print 'secondary subset', font_file
    out_file = path.join(
        DST_DIR, path.basename(font_file)[:-4] + '-Subsetted2.ttf')
    subset.subset_font(font_file, out_file, include=target_coverage)


def _fix_sea_missing_chars():
  """
  Add dotted circle and other characters to Khmer and Lao fonts.

  According to the OpenType layout specifications, Khmer and Lao fonts
  need to support DOTTED CIRCLE and ZWSP, while Khmer addtionally needs
  to support ZWNJ and ZWJ.  Otherwise, vowels without base letters
  would be displyed without a dotted circle, among other potential
  issues (https://code.google.com/p/noto/issues/detail?id=4).

  This adds glyphs from Noto Sans LGC for ZWJ, ZWNJ, and DOTTED CIRCLE
  to the Khmer fonts, and ZWSP and DOTTED CIRCLE to the Lao fonts.
  """
  # There's no difference between our Khmer/Lao and Android's, so
  # I assume we're ok here.  Looks like the Noto bug (noto-fonts#4)
  # was fixed.
  pass


def main():
  tool_utils.ensure_dir_exists(DST_DIR)
  _patch_serif_lgc()
  _patch_hyphen_armenian_ethiopic()
  # _remove_cjk_emoji()
  _fix_arabic_ligatures()
  _fix_sea_missing_chars()
  _subset_symbols()


if __name__ == '__main__':
  main()
