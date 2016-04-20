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

import codecs
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

def _patch_hyphen():
  """Add hyphen-minus glyphs to fonts that need it.

  This is to enable languages to be hyphenated properly,
  since Minikin's itemizer currently shows tofus if an
  automatically hyphenated word is displated in a font
  that has neither HYPHEN nor HYPHEN-MINUS.

  The list of font names comes from LANG_TO_SCRIPT in
  tools/font/fontchain_lint.py.

  (In practice only U+002D HYPHEN-MINUS is added, since Noto LGC fonts
  don't have U+2010 HYPHEN.)

  Bug: 21570828"""

  # Names of fonts for which Android requires a hyphen.
  # This list omits Japanese and Korean.
  script_names = [
      'Armenian', 'Ethiopic', 'Bengali', 'Gujarati', 'Devanagari',
      'Kannada', 'Malayalam', 'Oriya', 'Gurmukhi', 'Tamil', 'Telugu']

  HYPHENS = {0x002D, 0x2010}

  for sn in script_names:
    globexp = path.join(SRC_DIR, 'Noto*%s-*.ttf' % sn)
    fonts = glob.glob(globexp)
    if not fonts:
      raise ValueError('could not match ' + globexp)
    fonts = [path.basename(f) for f in fonts]
    for font_name in fonts:
      lgc_font_name = font_name.replace(sn, '')

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
      else:
        print 'already have hyphens', font_name


def _remove_cjk_emoji():
  """
  Remove default emoji characters from CJK fonts.

  Twenty-six characters that Unicode Technical Report #51 "Unicode
  Emoji" defines as defaulting to emoji styles used to be displayed as
  black and white ("text" style) before this. This patch removes those
  characters from Noto CJK fonts, so they get displayed as color.

  (1c4749e20391a4)
  """

  # Since subsetting changes tables in a way that would prevent a compact
  # .ttc file, this simply removes entries from the cmap table.  This
  # does not affect other tables in the font.  There are no emoji presentation
  # variation sequences in the fonts.

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
# TODO see if we need to change this subset based on Noto Serif coverage
# (so the serif fallback chain would support them)
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

BELONG_IN_SUBSETTED2 = {
    0x2600,  # ☀ BLACK SUN WITH RAYS
    0x2601,  # ☁ CLOUD
    0x260E,  # ☎ BLACK TELEPHONE
    0x261D,  # ☝ WHITE UP POINTING INDEX
    0x263A,  # ☺ WHITE SMILING FACE
    0x2660,  # ♠ BLACK SPADE SUIT
    0x2663,  # ♣ BLACK CLUB SUIT
    0x2665,  # ♥ BLACK HEART SUIT
    0x2666,  # ♦ BLACK DIAMOND SUIT
    0x270C,  # ✌ VICTORY HAND
    0x2744,  # ❄ SNOWFLAKE
    0x2764,  # ❤ HEAVY BLACK HEART
}

def _format_set(char_set, name, filename):
  lines = ['%s = {' % name]
  for cp in sorted(char_set):
    name = unicode_data.name(cp)
    lines.append('    0x%04X,  # %s %s' % (cp, unichr(cp), name))
  lines.append('}\n')
  with codecs.open(filename, 'w', 'UTF-8') as f:
    f.write('\n'.join(lines))
  print 'wrote', filename


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

  # TODO see if we need to change this subset based on Noto Serif coverage
  # (so the serif fallback chain would support them)

  target_coverage = set()
  # Add all characters in BLOCKS_TO_INCLUDE
  for first, last, _ in unicode_data._parse_code_ranges(BLOCKS_TO_INCLUDE):
    target_coverage.update(range(first, last+1))

  # Add one-off characters
  target_coverage |= ONE_OFF_ADDITIONS
  # Remove characters preferably coming from Roboto
  target_coverage -= LETTERLIKE_CHARS_IN_ROBOTO
  # Remove characters that are supposed to default to emoji

  target_coverage -= unicode_data.get_presentation_default_emoji()

  # Remove dentistry symbols, as their main use appears to be for CJK:
  # http://www.unicode.org/L2/L2000/00098-n2195.pdf
  target_coverage -= set(range(0x23BE, 0x23CC+1))

  # Remove COMBINING ENCLOSING KEYCAP. It's needed for Android's color emoji
  # mechanism to work properly
  target_coverage.remove(0x20E3)

  # Remove symbol characters for Android that belong in subsetted2 but not
  # subsetted.
  target_coverage -= BELONG_IN_SUBSETTED2

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
  target_coverage |= BELONG_IN_SUBSETTED2

  for font_file in glob.glob(path.join(SRC_DIR, 'NotoSansSymbols-*.ttf')):
    print 'secondary subset', font_file
    out_file = path.join(
        DST_DIR, path.basename(font_file)[:-4] + '-Subsetted2.ttf')
    subset.subset_font(font_file, out_file, include=target_coverage)


def main():
  tool_utils.ensure_dir_exists(DST_DIR, clean=True)
  _patch_hyphen()
  # TODO: first unpack from ttc, then rebuild
  # _remove_cjk_emoji()
  _subset_symbols()


if __name__ == '__main__':
  main()
