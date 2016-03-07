#!/usr/bin/python
#
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

"""Extract what lint expects for cmap from our data."""

import argparse
import collections
import sys

from nototools import cldr_data
from nototools import cmap_data
from nototools import compare_cmap_data
from nototools import collect_cldr_punct
from nototools import noto_data
from nototools import opentype_data
from nototools import tool_utils
from nototools import unicode_data

_MERGED_SCRIPTS_BY_TARGET = {
    'CJK': 'Bopo Hang Hani Hans Hant Hira Jpan Kana Kore'.split(),
    'LGC': 'Latn Grek Cyrl'.split(),
}

# If a block has characters with script 'common' or 'inherited', the
# script should be present and assign a default script (font) for it.
# If there are no such characters, no script is defined.
#
# Additional (non-unicode) script values are:
# CJK: for all CJK scripts
# EXCL: for excluded blocks (PUA, surrogates)
# MONO: for blocks going into a monospace font
# MUSIC: for blocks going into a music font
# SYM2: for blocks going into a 'symbols 2' font with fewer masters
# Zmth: for blocks going into a 'math' font
# ZSym: for blocks going into the main symbols font (6 masters)
# ZSye: for blocks going into the color emoji font

_block_to_script = {
    'Basic Latin' : 'Latn',
    'Latin-1 Supplement': 'Latn',
    'Latin Extended-A': 'Latn',
    'Latin Extended-B': 'Latn',
    'IPA Extensions': 'Latn',
    'Spacing Modifier Letters': 'Latn',
    'Combining Diacritical Marks': 'Latn',
    'Greek and Coptic': 'Grek',
    'Cyrillic': 'Cyrl',
    'Cyrillic Supplement': 'Cyrl',
    'Armenian': 'Armn',
    'Hebrew': None,
    'Arabic': 'Arab',
    'Syriac': None,
    'Arabic Supplement': None,
    'Thaana': None,
    'NKo': None,
    'Samaritan': None,
    'Mandaic': None,
    'Arabic Extended-A': 'Arab',
    'Devanagari': 'Deva',
    'Bengali': None,
    'Gurmukhi': None,
    'Gujarati': None,
    'Oriya': None,
    'Tamil': None,
    'Telugu': None,
    'Kannada': None,
    'Malayalam': None,
    'Sinhala': None,
    'Thai': 'Thai',
    'Lao': None,
    'Tibetan': 'Tibt',
    'Myanmar': None,
    'Georgian': 'Geor',
    'Hangul Jamo': None,
    'Ethiopic': None,
    'Ethiopic Supplement': None,
    'Cherokee': None,
    'Unified Canadian Aboriginal Syllabics': None,
    'Ogham': None,
    'Runic': 'Runr',
    'Tagalog': None,
    'Hanunoo': 'Hano',
    'Buhid': None,
    'Tagbanwa': None,
    'Khmer': None,
    'Mongolian': 'Mong',
    'Unified Canadian Aboriginal Syllabics Extended': None,
    'Limbu': None,
    'Tai Le': None,
    'New Tai Lue': None,
    'Khmer Symbols': None,
    'Buginese': None,
    'Tai Tham': None,
    'Combining Diacritical Marks Extended': 'Latn',
    'Balinese': None,
    'Sundanese': None,
    'Batak': None,
    'Lepcha': None,
    'Ol Chiki': None,
    'Cyrillic Extended-C': None,
    'Sundanese Supplement': None,
    'Vedic Extensions': 'Deva',
    'Phonetic Extensions': None,
    'Phonetic Extensions Supplement': None,
    'Combining Diacritical Marks Supplement': 'Latn',
    'Latin Extended Additional': None,
    'Greek Extended': None,
    'General Punctuation': 'Latn',
    'Superscripts and Subscripts': 'Latn',  # numeric super/subs
    'Currency Symbols': 'Zsym',
    'Combining Diacritical Marks for Symbols': 'Zsym',  # also SYM2?
    'Letterlike Symbols': 'Zsym',
    'Number Forms': 'Zsym',  # fractions, turned digits
    'Arrows': 'Zsym',
    'Mathematical Operators': 'Zmth',
    'Miscellaneous Technical': 'Zsym',
    'Control Pictures': 'SYM2',
    'Optical Character Recognition': 'SYM2',
    'Enclosed Alphanumerics': 'Zsym',
    'Box Drawing': 'MONO',
    'Block Elements': 'MONO',
    'Geometric Shapes': 'Zsym',
    'Miscellaneous Symbols': 'Zsym',
    'Dingbats': 'Zsym',
    'Miscellaneous Mathematical Symbols-A': 'Zmth',
    'Supplemental Arrows-A': 'Zsym',
    'Braille Patterns': 'SYM2',
    'Supplemental Arrows-B': 'Zsym',
    'Miscellaneous Mathematical Symbols-B': 'Zmth',
    'Supplemental Mathematical Operators': 'Zmth',
    'Miscellaneous Symbols and Arrows': 'Zsym',
    'Glagolitic': None,
    'Latin Extended-C': None,
    'Coptic': None,
    'Georgian Supplement': None,
    'Tifinagh': None,
    'Ethiopic Extended': None,
    'Cyrillic Extended-A': None,
    'Supplemental Punctuation': 'Zsym',  # might break out further
    'CJK Radicals Supplement': None,
    'Kangxi Radicals': None,
    'Ideographic Description Characters': 'CJK',
    'CJK Symbols and Punctuation': 'CJK',
    'Hiragana': None,
    'Katakana': None,
    'Bopomofo': None,
    'Hangul Compatibility Jamo': None,
    'Kanbun': 'CJK',
    'Bopomofo Extended': None,
    'CJK Strokes': 'CJK',
    'Katakana Phonetic Extensions': None,
    'Enclosed CJK Letters and Months': 'CJK',
    'CJK Compatibility': 'CJK',
    'CJK Unified Ideographs Extension A': None,
    'Yijing Hexagram Symbols': 'SYM2',
    'CJK Unified Ideographs': None,
    'Yi Syllables': None,
    'Yi Radicals': None,
    'Lisu': None,
    'Vai': None,
    'Cyrillic Extended-B': None,
    'Bamum': None,
    'Modifier Tone Letters': 'Zsym',
    'Latin Extended-D': 'Latn',
    'Syloti Nagri': None,
    'Common Indic Number Forms': 'Deva',
    'Phags-pa': None,
    'Saurashtra': None,
    'Devanagari Extended': None,
    'Kayah Li': 'Kali',
    'Rejang': None,
    'Hangul Jamo Extended-A': None,
    'Javanese': 'Java',  # TODO: check
    'Myanmar Extended-B': None,
    'Cham': None,
    'Myanmar Extended-A': None,
    'Tai Viet': None,
    'Meetei Mayek Extensions': None,
    'Ethiopic Extended-A': None,
    'Latin Extended-E': 'Latn',
    'Cherokee Supplement': None,
    'Meetei Mayek': None,
    'Hangul Syllables': None,
    'Hangul Jamo Extended-B': None,
    'High Surrogates': 'EXCL',
    'High Private Use Surrogates': 'EXCL',
    'Low Surrogates': 'EXCL',
    'Private Use Area': 'EXCL',
    'CJK Compatibility Ideographs': None,
    'Alphabetic Presentation Forms': None,
    'Arabic Presentation Forms-A': 'Arab',
    'Variation Selectors': 'EXCL',
    'Vertical Forms': 'CJK',
    'Combining Half Marks': 'Latn',
    'CJK Compatibility Forms': 'CJK',
    'Small Form Variants': 'CJK',
    'Arabic Presentation Forms-B': None,  # This includes BOM at feff, ignore
    'Halfwidth and Fullwidth Forms': 'CJK',
    'Specials': 'Latn',  # interlinear annotations, replacement...
    'Linear B Syllabary': None,
    'Linear B Ideograms': None,
    'Aegean Numbers': 'Linb',
    'Ancient Greek Numbers': 'SYM2',  # no defaults in this block
    'Ancient Symbols': 'SYM2',
    'Phaistos Disc': 'SYM2',
    'Lycian': None,
    'Carian': None,
    'Coptic Epact Numbers': 'SYM2',
    'Old Italic': None,
    'Gothic': None,
    'Old Permic': None,
    'Ugaritic': None,
    'Old Persian': None,
    'Deseret': None,
    'Shavian': None,
    'Osmanya': None,
    'Osage': None,
    'Elbasan': None,
    'Caucasian Albanian': None,
    'Linear A': None,
    'Cypriot Syllabary': None,
    'Imperial Aramaic': None,
    'Palmyrene': None,
    'Nabataean': None,
    'Hatran': None,
    'Phoenician': None,
    'Lydian': None,
    'Meroitic Hieroglyphs': None,
    'Meroitic Cursive': None,
    'Kharoshthi': None,
    'Old South Arabian': None,
    'Old North Arabian': None,
    'Manichaean': None,
    'Avestan': None,
    'Inscriptional Parthian': None,
    'Inscriptional Pahlavi': None,
    'Psalter Pahlavi': None,
    'Old Turkic': None,
    'Old Hungarian': None,
    'Rumi Numeral Symbols': None,
    'Brahmi': None,
    'Kaithi': None,
    'Sora Sompeng': None,
    'Chakma': None,
    'Mahajani': None,
    'Sharada': None,
    'Sinhala Archaic Numbers': None,
    'Khojki': None,
    'Multani': None,
    'Khudawadi': None,
    'Grantha': None,
    'Tirhuta': None,
    'Siddham': None,
    'Modi': None,
    'Mongolian Supplement': None,
    'Takri': None,
    'Ahom': None,
    'Warang Citi': None,
    'Pau Cin Hau': None,
    'Bhaiksuki': None,
    'Marchen': None,
    'Cuneiform': None,
    'Cuneiform Numbers and Punctuation': None,
    'Early Dynastic Cuneiform': None,
    'Egyptian Hieroglyphs': None,
    'Anatolian Hieroglyphs': None,
    'Bamum Supplement': None,
    'Mro': None,
    'Bassa Vah': None,
    'Pahawh Hmong': None,
    'Miao': None,
    'Ideographic Symbols and Punctuation': None,
    'Tangut': None,
    'Tangut Components': None,
    'Kana Supplement': None,
    'Duployan': None,
    'Shorthand Format Controls': 'Dupl',
    'Byzantine Musical Symbols': 'MUSIC',
    'Musical Symbols': 'MUSIC',
    'Ancient Greek Musical Notation': 'MUSIC',
    'Tai Xuan Jing Symbols': 'SYM2',
    'Counting Rod Numerals': 'SYM2',
    'Mathematical Alphanumeric Symbols': 'Zmth',
    'Sutton SignWriting': None,
    'Glagolitic Supplement': None,
    'Mende Kikakui': None,
    'Arabic Mathematical Alphabetic Symbols': 'Zmth',  # need to reassign
    'Mahjong Tiles': 'SYM2',
    'Domino Tiles': 'SYM2',
    'Playing Cards': 'SYM2',
    'Enclosed Alphanumeric Supplement': 'Zsym',
    'Enclosed Ideographic Supplement': 'CJK',
    'Miscellaneous Symbols and Pictographs': 'SYM2',
    'Emoticons': 'Zsye',  # emoji
    'Ornamental Dingbats': 'Zsym',
    'Transport and Map Symbols': 'Zsye',
    'Alchemical Symbols': 'Zsym',
    'Geometric Shapes Extended': 'Zsym',
    'Supplemental Arrows-C': 'Zsym',
    'Supplemental Symbols and Pictographs': 'Zsye',
    'CJK Unified Ideographs Extension B': None,
    'CJK Unified Ideographs Extension C': None,
    'CJK Unified Ideographs Extension D': None,
    'CJK Unified Ideographs Extension E': None,
    'CJK Compatibility Ideographs Supplement': None,
    'Tags': 'SYM2',
    'Variation Selectors Supplement': 'EXCL',
    'Supplementary Private Use Area-A': 'EXCL',
    'Supplementary Private Use Area-B': 'EXCL',
}

def _invert_script_to_chars(script_to_chars):
  """Convert script_to_chars to char_to_scripts and return."""
  char_to_scripts = collections.defaultdict(set)
  for script, cps in script_to_chars.iteritems():
    for cp in cps:
      char_to_scripts[cp].add(script)
  return char_to_scripts


class CmapOps(object):
  def __init__(self, script_to_chars={}, log_events=False, log_details=False):
    self._script_to_chars = {
        script: set(script_to_chars[script])
        for script in script_to_chars
    }
    self._log_events = log_events
    self._log_details = log_details
    self._suppressed_blocks = {
        'Hangul Jamo',
        'Kangxi Radicals',
        'Kanbun',
        'CJK Symbols and Punctuation',
        'Hangul Compatibility Jamo',
        'CJK Strokes',
        'Enclosed CJK Letters and Months',
        'CJK Compatibility',
        'CJK Compatibility Ideographs',
        'CJK Compatibility Ideographs Supplement',
        'CJK Unified Ideographs Extension A',
        'CJK Unified Ideographs Extension B',
        'CJK Unified Ideographs Extension C',
        'CJK Unified Ideographs Extension D',
        'CJK Unified Ideographs Extension E',
        'CJK Unified Ideographs',
        'CJK Radicals Supplement',
        'Hangul Jamo Extended-A',
        'Hangul Jamo Extended-B',
        'Hangul Syllables',
    }
    self._suppress_cp_report = False
    self._block = None

  def _report(self, text):
    if self._log_events:
      print text

  def _finish_block(self):
    if self._block and self._log_events and not self._log_details:
      for text in sorted(self._block_count):
        print '%s: %s' % (
            text, tool_utils.write_int_ranges(
                self._block_count[text]))

  def _report_cp(self, cp, text):
    if not self._log_events:
      return
    cp_block = unicode_data.block(cp)
    if cp_block != self._block:
      self._finish_block()
      self._block = cp_block
      print '# block: ' + self._block
      self._block_count = collections.defaultdict(set)
      self._suppress_cp_report = self._block in self._suppressed_blocks
    if self._log_details:
      if not self._suppress_cp_report:
        print self._cp_info(cp), text
    else:
      self._block_count[text].add(cp)

  def _error(self, text):
    print >> sys.stderr, text
    raise ValueError('failed')

  def _verify_script_exists(self, script):
    if script not in self._script_to_chars:
      self._error('script %s does not exist' % script)

  def _verify_script_does_not_exist(self, script):
    if script in self._script_to_chars:
      self._error('script %s already exists' % script)

  def _verify_scripts_exist(self, scripts):
    for script in scripts:
      self._verify_script_exists(script)
    return sorted(scripts)

  def _verify_script_empty(self, script):
    if len(self._script_to_chars[script]):
      self._error('script %s is not empty, cannot delete' % script)

  def _op(self, op_name):
    return self._phase + '/' + op_name

  def _cp_info(self, cp):
    return '%04X (%s)' % (cp, unicode_data.name(cp, '<unnamed>'))

  def _script_ok_add(self, cp, script):
    if unicode_data.is_defined(cp):
      self._script_cp_ok_add(cp, script)

  def _script_cp_ok_add(self, cp, script):
    if cp not in self._script_to_chars[script]:
      self._script_to_chars[script].add(cp)
      self._report_cp(cp, 'added to ' + script)

  def _script_ok_remove(self, cp, script):
    if unicode_data.is_defined(cp):
      self._script_cp_ok_remove(cp, script)

  def _script_cp_ok_remove(self, cp, script):
    if cp in self._script_to_chars[script]:
      self._report_cp(cp, 'removed from ' + script)
      self._script_to_chars[script].remove(cp)

  def _finish_phase(self):
    self._finish_block()
    self._block = None

  def phase(self, phase_name):
    self._finish_phase()
    self._report('\n# phase: ' + phase_name)

  def log(self, log_msg):
    self._report('\n# log: ' + log_msg)

  def ensure_script(self, script):
    if script in self._script_to_chars:
      return
    self.create_script(script)

  def create_script(self, script):
    self._verify_script_does_not_exist(script)
    self._script_to_chars[script] = set()
    self._report('# create script: ' + script)

  def delete_script(self, script):
    self._verify_script_exists(script)
    self._verify_script_empty(script)
    del self._script_to_chars[script]
    self._report('# delete script: ' + script)

  def add(self, cp, script):
    self._verify_script_exists(script)
    self._script_ok_add(cp, script)

  def add_all(self, cps, script):
    self._verify_script_exists(script)
    for cp in sorted(cps):
      self._script_ok_add(cp, script)

  def add_all_to_all(self, cps, scripts):
    scripts = self._verify_scripts_exist(scripts)
    for cp in sorted(cps):
      if unicode_data.is_defined(cp):
        for script in scripts:
          self._script_cp_ok_add(cp, script)

  def remove(self, cp, script):
    self._verify_script_exists(script)
    self._script_ok_remove(cp, script)

  def remove_all(self, cps, script):
    self._verify_script_exists(script)
    for cp in sorted(cps):
      self._script_ok_remove(cp, script)

  def remove_all_from_all(self, cps, scripts):
    scripts = self._verify_scripts_exist(scripts)
    for cp in sorted(cps):
      if unicode_data.is_defined(cp):
        for script in scripts:
          self._script_cp_ok_remove(cp, script)

  def all_scripts(self):
    return self._script_to_chars.keys()

  def create_char_to_scripts(self):
    return _invert_script_to_chars(self._script_to_chars)

  def script_chars(self, script):
    self._verify_script_exists(script)
    return sorted(self._script_to_chars[script])

  def create_script_to_chars(self):
    return {
        script: set(self._script_to_chars[script])
        for script in self._script_to_chars
    }

  def finish(self):
    self._finish_phase()


def _build_block_to_primary_script():
  """Create a map from block to the primary script in a block.
  If there are no characters defined in the block, it gets the script 'EXCL',
  for 'exclude.'  We don't define characters in this block.
  If the most common script accounts for less than 80% of the defined characters
  in the block, we use the primary from assigned_primaries, which might be None.
  It's an error if there's no default primary and it's not listed in
  assigned_primaries."""

  assigned_primaries = {
      'Basic Latin': 'Latn',
      'Latin-1 Supplement': 'Latn',
      'Vedic Extensions': 'Deva',
      'Superscripts and Subscripts': 'Latn',
      'Number Forms': 'Zyyy',
      'CJK Symbols and Punctuation': 'CJK',
      'Enclosed CJK Letters and Months': 'CJK',
      'CJK Compatibility': 'CJK',
      'Alphabetic Presentation Forms': None,
      'Halfwidth and Fullwidth Forms': 'CJK',
      'Kana Supplement': 'CJK',
  }

  inherited_primaries = {
      'Combining Diacritical Marks': 'Latn',
      'Combining Diacritical Marks Extended': 'Latn',
      'Combining Diacritical Marks Supplement': 'Latn',
      'Combining Diacritical Marks for Symbols': 'Zyyy',
      'Variation Selectors': 'EXCL',
      'Combining Half Marks': 'Latn',
      'Variation Selectors Supplement': 'EXCL',
  }

  block_to_script = {}
  for block in unicode_data.block_names():
    start, finish = unicode_data.block_range(block)
    script_counts = collections.defaultdict(int)
    num = 0
    for cp in range(start, finish + 1):
      script = unicode_data.script(cp)
      if script != 'Zzzz':
        script_counts[script] += 1
        num += 1
    max_script = None
    max_script_count = 0
    for script, count in script_counts.iteritems():
      if count > max_script_count:
        max_script = script
        max_script_count = count
    if num == 0:
      max_script = 'EXCL'  # exclude
    elif float(max_script_count) / num < 0.8:
      info = sorted(script_counts.iteritems(), key = lambda t: (-t[1], t[0]))
      block_info = '%s %s' % (block, ', '.join('%s/%d' % t for t in info))
      if block in assigned_primaries:
        max_script = assigned_primaries[block]
        # print 'assigning primary', block_info, '->', max_script
      else:
        print >> sys.stderr, 'ERROR: no primary', block, block_info
        max_script = None
    elif max_script == 'Zinh':
      if block in inherited_primaries:
        max_script = inherited_primaries[block]
      else:
        print >> sys.stderr, 'ERROR: no inherited primary', block, block_info
        max_script = None
    block_to_script[block] = max_script
  return block_to_script


_block_to_primary_script = None
def _primary_script_for_block(block):
  """Return the primary script for the block, or None if no primary script."""
  global _block_to_primary_script
  if not _block_to_primary_script:
    _block_to_primary_script = _build_block_to_primary_script()
  return _block_to_primary_script[block]


def _unassign_inherited_and_common_with_extensions(cmap_ops):
  """Inherited and common characters with an extension that is neither of
  these get removed from inherited/common scripts."""

  def remove_cps_with_extensions(script):
    for cp in cmap_ops.script_chars(script):
      for s in unicode_data.script_extensions(cp):
        if s != 'Zinh' and s != 'Zyyy':
          cmap_ops.remove(cp, script)
          break

  cmap_ops.phase('unassign inherited with extensions')
  remove_cps_with_extensions('Zinh')
  cmap_ops.phase('unassign common with extensions')
  remove_cps_with_extensions('Zyyy')


def _reassign_inherited(cmap_ops):
  """Assign all 'Zinh' chars to the primary script in their block.
  Fail if there's no primary script.  'Zinh' is removed from script_to_chars."""
  cmap_ops.phase('reassign inherited')
  for cp in cmap_ops.script_chars('Zinh'):
    primary_script = _primary_script_for_block(unicode_data.block(cp))
    if not primary_script:
      print >> sys.stderr, 'Error: no primary script for %04X' % cp
    elif primary_script == 'Zinh':
      print >> sys.stderr, 'Error: primary script for %04X is Zinh' % cp
    else:
      cmap_ops.ensure_script(primary_script)
      cmap_ops.add(cp, primary_script)
      cmap_ops.remove(cp, 'Zinh')
  cmap_ops.delete_script('Zinh')


def _reassign_common(cmap_ops):
  """Move 'Zyyy' chars in blocks where 'Zyyy' is not primary to the primary
  script."""
  cmap_ops.phase('reassign common')
  for cp in cmap_ops.script_chars('Zyyy'):
    primary_script = _primary_script_for_block(unicode_data.block(cp))
    if primary_script != None and primary_script != 'Zyyy':
      cmap_ops.ensure_script(primary_script)
      cmap_ops.add(cp, primary_script)
      cmap_ops.remove(cp, 'Zyyy')


def _unassign_latin(cmap_ops):
  """Remove some characters that extensions assigns to Latin but which we don't
  need there."""
  unwanted_latn = tool_utils.parse_int_ranges("""
    0951 0952  # devanagari marks
    10FB  # Georgian paragraph separator
    """)
  cmap_ops.phase('unassign latin')
  cmap_ops.remove_all(unwanted_latn, 'Latn')


def _assign_cldr_punct(cmap_ops):
  """Assigns cldr punctuation to scripts."""
  for script, punct in collect_cldr_punct.script_to_punct().iteritems():
    if script != 'CURRENCY':
      cmap_ops.phase('assign cldr punct for ' + script)
      cmap_ops.ensure_script(script)
      for cp in punct:
        cmap_ops.add(ord(cp), script)


def _reassign_scripts(cmap_ops, scripts, new_script):
  """Reassign all chars in scripts to new_script."""
  assert new_script not in scripts

  cmap_ops.phase('reassign scripts')
  cmap_ops.ensure_script(new_script)
  for script in sorted(scripts):
    cmap_ops.phase('reassign %s to %s' % (script, new_script))
    for cp in cmap_ops.script_chars(script):
      cmap_ops.remove(cp, script)
      cmap_ops.add(cp, new_script)
    cmap_ops.delete_script(script)


def _reassign_merged_scripts(cmap_ops):
  """Reassign merged scripts."""
  for target, scripts in sorted(_MERGED_SCRIPTS_BY_TARGET.iteritems()):
    cmap_ops.phase('reassign to ' + target)
    _reassign_scripts(cmap_ops, scripts, target)


def _reassign_common_by_block(cmap_ops):
  """Reassign common chars to new scripts based on block."""
  block_assignments = {
    'Spacing Modifier Letters': 'LGC',
    'General Punctuation': 'LGC',
    'Currency Symbols': 'LGC',
    'Combining Diacritical Marks for Symbols': 'Zsym',
    'Letterlike Symbols': 'Zsym',
    'Number Forms': 'Zsym',
    'Arrows': 'Zsym',
    'Mathematical Operators': 'Zmth',
    'Miscellaneous Technical': 'Zsym',
    'Control Pictures': 'SYM2',
    'Optical Character Recognition': 'SYM2',
    'Enclosed Alphanumerics': 'Zsym',
    'Box Drawing': 'MONO',
    'Block Elements': 'MONO',
    'Geometric Shapes': 'Zsym',
    'Miscellaneous Symbols': 'Zsym',
    'Dingbats': 'SYM2',
    'Miscellaneous Mathematical Symbols-A': 'Zmth',
    'Supplemental Arrows-A': 'Zsym',
    'Supplemental Arrows-B': 'Zsym',
    'Miscellaneous Mathematical Symbols-B': 'Zmth',
    'Supplemental Mathematical Operators': 'Zmth',
    'Miscellaneous Symbols and Arrows': 'SYM2',
    'Supplemental Punctuation': 'Zsym',
    'Ideographic Description Characters': 'CJK',
    'Yijing Hexagram Symbols': 'SYM2',
    'Modifier Tone Letters': 'Zsym',
    'Vertical Forms': 'CJK',
    'CJK Compatibility Forms': 'CJK',
    'Small Form Variants': 'CJK',
    'Specials': 'SYM2',
    'Ancient Symbols': 'SYM2',
    'Phaistos Disc': 'SYM2',
    'Byzantine Musical Symbols': 'MUSIC',
    'Musical Symbols': 'MUSIC',
    'Tai Xuan Jing Symbols': 'SYM2',
    'Mathematical Alphanumeric Symbols': 'Zmth',
    'Mahjong Tiles': 'SYM2',
    'Domino Tiles': 'SYM2',
    'Playing Cards': 'SYM2',
    'Enclosed Alphanumeric Supplement': 'Zsym',
    'Enclosed Ideographic Supplement': 'CJK',
    'Miscellaneous Symbols and Pictographs': 'SYM2',
    'Emoticons': 'SYM2',
    'Ornamental Dingbats': 'SYM2',
    'Transport and Map Symbols': 'SYM2',
    'Alchemical Symbols': 'Zsym',
    'Geometric Shapes Extended': 'SYM2',
    'Supplemental Arrows-C': 'SYM2',
    'Supplemental Symbols and Pictographs': 'SYM2',
    'Tags': 'SYM2',
  }

  cmap_ops.phase('reassign common by block')
  used_assignments = set()
  last_block = None
  for cp in cmap_ops.script_chars('Zyyy'):
    block = unicode_data.block(cp)
    if block != last_block:
      last_block = block
      if block not in block_assignments:
        print >> sys.stderr, 'ERROR: no assignment for block %s' % block
        new_script = None
      else:
        new_script = block_assignments[block]
        cmap_ops.ensure_script(new_script)
        used_assignments.add(block)
    if new_script:
      cmap_ops.remove(cp, 'Zyyy')
      cmap_ops.add(cp, new_script)
    else:
      print >> sys.stderr, '  could not assign %04x %s' % (
          cp, unicode_data.name(cp))

  if len(used_assignments) != len(block_assignments):
    print >> sys.stderr, 'ERROR: some block assignments unused'
    unused = set([block for block in block_assignments
        if block not in used_assignments])
    for block in unicode_data.block_names():
      if block in unused:
        print >> sys.stderr, '  %s' % block
        unused.remove(block)
    if unused:
      print >> sys.stderr, 'ERROR: unknown block names'
      for block in sorted(unused):
        print >> sys.stderr, '  %s' % block

  cmap_ops.delete_script('Zyyy')


def _reassign_by_block(cmap_ops):
  """Reassign all chars in select blocks to designated scripts."""
  # block, from, to.  from is '*' for all scripts.
  block_assignments = [
      ('Number Forms', 'LGC', 'Zsym'),
      ('Halfwidth and Fullwidth Forms', 'LGC', 'CJK'),
      ('Aegean Numbers', '*', 'Linb'),
      ('Ancient Greek Numbers', '*', 'SYM2'),
      ('Ancient Symbols', 'LGC', 'SYM2'),
      ('Braille Patterns', 'Brai', 'SYM2'),
      ('Coptic Epact Numbers', '*', 'SYM2'),
      ('Rumi Numeral Symbols', '*', 'SYM2'),
      ('Ancient Greek Musical Notation', '*', 'MUSIC'),
      ('Counting Rod Numerals', 'CJK', 'SYM2'),
      ('Arabic Mathematical Alphabetic Symbols', '*', 'Zmth'),
  ]
  block_assignments = sorted(
      block_assignments, key=lambda k: unicode_data.block_range(k[0])[0])

  cmap_ops.phase('reassign by block')
  char_to_scripts = cmap_ops.create_char_to_scripts()
  for block, from_scripts, to_script in block_assignments:
    start, finish = unicode_data.block_range(block)
    if from_scripts == '*':
      all_scripts = True
    else:
      all_scripts = False
      from_scripts = from_scripts.split()
    for cp in range(start, finish + 1):
      if not unicode_data.is_defined(cp):
        continue
      if cp not in char_to_scripts:
        print >> sys.stderr, 'reassign missing %04X %s' % (
            cp, unicode_data.name(cp, '<unnamed>'))
        continue
      if all_scripts:
        from_list = char_to_scripts[cp]
      else:
        from_list = from_scripts
      for from_script in char_to_scripts[cp]:
        if from_script == to_script:
          continue
        if not all_scripts and (from_script not in from_scripts):
          continue
        cmap_ops.remove(cp, from_script)
      cmap_ops.add(cp, to_script)

def _remove_empty(cmap_ops):
  """Remove any empty scripts (Braille should be one)."""
  cmap_ops.phase('remove empty')
  script_to_chars = cmap_ops.create_script_to_chars()
  for script, chars in script_to_chars.iteritems():
    if not chars:
      cmap_ops.delete_script(script)


def _reassign_emoji(cmap_ops):
  """Reassign all emoji to emoji-color. Then assign all emoji with default text
  presentation, plus select others, to SYM2."""

  cmap_ops.phase('reassign emoji')
  char_to_scripts = cmap_ops.create_char_to_scripts()

  color_only_emoji = set(unicode_data.get_presentation_default_emoji())
  color_only_emoji.remove(0x1f004)  # mahjong tile red dragon
  color_only_emoji.remove(0x1f0cf)  # playing card black joker

  all_emoji = unicode_data.get_emoji()
  cmap_ops.create_script('Zsye')
  cmap_ops.add_all(all_emoji, 'Zsye')

  cmap_ops.remove_all_from_all(color_only_emoji, ['Zsym', 'SYM2'])


def _assign_nastaliq(cmap_ops):
  """Create Aran script based on requirements doc."""

  # Range spec matches "Noto Nastaliq requirements" doc, Tier 1.
  urdu_chars = tool_utils.parse_int_ranges("""
    0600-0604 060b-0614 061b 061c 061e-061f 0620 0621-063a
    0640-0659 065e-066d 0670-0673 0679 067a-067b 067c 067d
    067e 067f-0680 0681 0683-0684 0685-0686 0687 0688-0689
    068a 068b 068c-068d 068e 068f 0691 0693 0696 0698 0699
    069a 069e 06a6 06a9 06ab 06af-06b0 06b1 06b3 06b7 06ba
    06bb 06bc 06be 06c0-06c4 06cc-06cd 06d0 06d2-06d5
    06dd-06de 06e9 06ee-06ef 06f0-06f9 06ff 0759 075c 0763
    0767-0769 076b-077d 08ff fbb2-fbc1 fd3e-fd3f fdf2
    fdfa-fdfd""")
  cmap_ops.phase('assign nastaliq')
  cmap_ops.create_script('Aran')
  cmap_ops.add_all(urdu_chars, 'Aran')

  # These additional arabic were in phase 2 scripts.
  additional_arabic = tool_utils.parse_int_ranges("""
      0609  # ARABIC-INDIC PER MILLE SIGN
      060a  # ARABIC-INDIC PER TEN THOUSAND SIGN
      063b  # ARABIC LETTER KEHEH WITH TWO DOTS ABOVE
      063c  # ARABIC LETTER KEHEH WITH THREE DOTS BELOW
      063d  # ARABIC LETTER FARSI YEH WITH INVERTED V
      063e  # ARABIC LETTER FARSI YEH WITH TWO DOTS ABOVE
      063f  # ARABIC LETTER FARSI YEH WITH THREE DOTS ABOVE
      065d  # ARABIC REVERSED DAMMA
      066e  # ARABIC LETTER DOTLESS BEH
      066f  # ARABIC LETTER DOTLESS QAF
      06a1  # ARABIC LETTER DOTLESS FEH
      06a4  # ARABIC LETTER VEH
      06e0  # ARABIC SMALL HIGH UPRIGHT RECTANGULAR ZERO
      06e1  # ARABIC SMALL HIGH DOTLESS HEAD OF KHAH
      076a  # ARABIC LETTER LAM WITH BAR
  """)
  cmap_ops.add_all(additional_arabic, 'Aran')


def _assign_complex_script_extra(cmap_ops):
  """Assigns Harfbuzz and USE characters to the corresponding scripts."""
  # Based on harfbuzz hb-ot-shape-complex-private
  # Removes Hang, Jungshik reports Behdad says it's not needed for Hang.
  hb_complex_scripts = """
    Arab Aran Bali Batk Beng Brah Bugi Buhd Cakm Cham Deva Dupl Egyp Gran
    Gujr Guru Hano Hebr Hmng Java Kali Khar Khmr Khoj Knda Kthi Lana
    Laoo Lepc Limb Mahj Mand Mani Mlym Modi Mong Mtei Mymr Nkoo Orya Phag
    Phlp Rjng Saur Shrd Sidd Sind Sinh Sund Sylo Syrc Tagb Takr Tale Talu
    Taml Tavt Telu Tfng Tglg Thai Tibt Tirh
    """.split()
  hb_extra = tool_utils.parse_int_ranges("""
      200c  # ZWNJ
      200d  # ZWJ
      25cc  # dotted circle""")

  # these scripts are based on github noto-fonts#576
  use_complex_scripts = """
    Bali Batk Brah Bugi Buhd Hano Kthi Khar Lepc Limb Mtei Rjng Saur Sund
    Sylo Tglg Tagb Tale Tavt
    """.split()
  # these characters are based on
  # https://www.microsoft.com/typography/OpenTypeDev/USE/intro.htm
  use_extra = tool_utils.parse_int_ranges("""
      200b  # ZWS
      200c  # ZWNJ
      200d  # ZWJ
      25cc  # dotted circle
      00a0  # NBS
      00d7  # multiplication sign
      2012  # figure dash
      2013  # en dash
      2014  # em dash
      2015  # horizontal bar
      2022  # bullet
      25fb  # white medium square
      25fc  # black medium square
      25fd  # white medium small square
      25fe  # black medium small square""")

  cmap_ops.phase('assign hb complex')
  cmap_ops.add_all_to_all(hb_extra, hb_complex_scripts)

  cmap_ops.phase('assign use complex')
  cmap_ops.add_all_to_all(use_extra, use_complex_scripts)


def _assign_hyphens_for_autohyphenation(cmap_ops):
  """Assign hyphens per Roozbeh's request."""
  hyphens = [
      0x002d,  # hyphen-minus
      0x2010   # hyphen
  ]
  # see github noto-fonts#524
  # Cyrl, Grek, Latn rolled into LGC
  # CJK not listed, these don't hyphenate, data is in CLDR for other reasons
  hyphen_scripts = """
      Arab Armn Beng Copt Deva Ethi Geor Gujr Guru Hebr
      Khmr Knda LGC  Mlym Orya Taml Telu Thai Tibt
  """.split()
  cmap_ops.phase('assign hyphens')
  cmap_ops.add_all_to_all(hyphens, hyphen_scripts)



def _assign_extra_indic(cmap_ops):
  """Assign extra characters added to Indic fonts by MTI/Jelle."""
  extra_indic = tool_utils.parse_int_ranges("""
    0021-0023 0025 0027-002C 002D-002F 0030-0039 003A-003E
    005b-005f 007B-007e 00AD 00AF 00D7 00F7 02BC 2013-2014
    20B9 2212
    """)
  indic_scripts = 'Beng Deva Gujr Guru Knda Mlym Orya Sinh Taml Telu'.split()
  cmap_ops.phase('add extra indic')
  cmap_ops.add_all_to_all(extra_indic, indic_scripts)


def _generate_script_extra(script_to_chars):
  """Generate script extra table."""
  for script in sorted(noto_data.P3_EXTRA_CHARACTERS_NEEDED):
    block = None
    cps = noto_data.P3_EXTRA_CHARACTERS_NEEDED[script]
    chars = script_to_chars[script]
    if script == 'Zsym':
      chars.update(script_to_chars['Zmth'])
      chars.update(script_to_chars['SYM2'])
      chars.update(script_to_chars['MUSIC'])
      chars.update(script_to_chars['MONO'])
    for cp in sorted(cps):
      if not unicode_data.is_defined(cp):
        continue
      name = unicode_data.name(cp, '<unnamed">')
      if cp not in chars:
        if block == None:
          print "'%s': tool_utils.parse_int_ranges(\"\"\"" % script
        cp_block = unicode_data.block(cp)
        if cp_block != block:
          block = cp_block
          print '  # %s' % block
        print '  %04X # %s' % (cp, name)
        chars.add(cp)
    if block != None:
      print '  """),'

# maintained using 'regen_script_required' fn
_SCRIPT_REQUIRED = [
  # Adlm - Adlm (Adlam)

  # Aghb - Caucasian Albanian
  ('Aghb',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Combining Diacritical Marks
   0304  # COMBINING MACRON
   0331  # COMBINING MACRON BELOW
   # Combining Half Marks
   FE20  # COMBINING LIGATURE LEFT HALF
   FE21  # COMBINING LIGATURE RIGHT HALF
   FE22  # COMBINING DOUBLE TILDE LEFT HALF
   FE23  # COMBINING DOUBLE TILDE RIGHT HALF
   FE24  # COMBINING MACRON LEFT HALF
   FE25  # COMBINING MACRON RIGHT HALF
   FE26  # COMBINING CONJOINING MACRON
   FE27  # COMBINING LIGATURE LEFT HALF BELOW
   FE28  # COMBINING LIGATURE RIGHT HALF BELOW
   FE29  # COMBINING TILDE LEFT HALF BELOW
   FE2A  # COMBINING TILDE RIGHT HALF BELOW
   FE2B  # COMBINING MACRON LEFT HALF BELOW
   FE2C  # COMBINING MACRON RIGHT HALF BELOW
   FE2D  # COMBINING CONJOINING MACRON BELOW
   FE2E  # COMBINING CYRILLIC TITLO LEFT HALF
   FE2F  # COMBINING CYRILLIC TITLO RIGHT HALF
   """),

  # Ahom - Ahom

  # Arab - Arabic
  ('Arab',
   # Comment
   """
   According to Roozbeh (and existing fonts) the following punctuation and
   digits are used with and interact with Arabic characters.  Hyphen and
   comma are to align with Aran.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002E  # FULL STOP
   0030  # DIGIT ZERO
   0031  # DIGIT ONE
   0032  # DIGIT TWO
   0033  # DIGIT THREE
   0034  # DIGIT FOUR
   0035  # DIGIT FIVE
   0036  # DIGIT SIX
   0037  # DIGIT SEVEN
   0038  # DIGIT EIGHT
   0039  # DIGIT NINE
   003A  # COLON
   # Latin-1 Supplement
   00A0  # NO-BREAK SPACE
   # General Punctuation
   200E  # LEFT-TO-RIGHT MARK
   200F  # RIGHT-TO-LEFT MARK
   2010  # HYPHEN
   2011  # NON-BREAKING HYPHEN
   204F  # REVERSED SEMICOLON
   # Supplemental Punctuation
   2E41  # REVERSED COMMA
   """),

  # Aran - Aran (Nastaliq)
  ('Aran',
   # Comment
   """
   Hyphens are required for Urdu from the Arabic
   Guillimets used for Persian according to Behdad
   Other punctuation was in phase2 fonts, so presumably from Kamal.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   002C  # COMMA
   002E  # FULL STOP
   003A  # COLON
   # Latin-1 Supplement
   00AB  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
   00BB  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
   # Arabic
   061C  # ARABIC LETTER MARK
   # General Punctuation
   2010  # HYPHEN
   2011  # NON-BREAKING HYPHEN
   # Arabic Presentation Forms-A
   FDF4  # ARABIC LIGATURE MOHAMMAD ISOLATED FORM
   """),

  # Armi - Imperial Aramaic

  # Armn - Armenian
  ('Armn',
   # Comment
   """
   Characters referenced in Armenian encoding cross ref page
   see http://www.unicode.org/L2/L2010/10354-n3924-armeternity.pdf
   also see http://man7.org/linux/man-pages/man7/armscii-8.7.html
   also see core specification.
   """,
   # Data
   """
   # Basic Latin
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002D  # HYPHEN-MINUS
   002E  # FULL STOP
   # Latin-1 Supplement
   00A0  # NO-BREAK SPACE
   00A7  # SECTION SIGN
   # Spacing Modifier Letters
   02BB  # MODIFIER LETTER TURNED COMMA
   # General Punctuation
   2010  # HYPHEN
   2014  # EM DASH
   2019  # RIGHT SINGLE QUOTATION MARK
   2024  # ONE DOT LEADER
   # Alphabetic Presentation Forms
   FB13  # ARMENIAN SMALL LIGATURE MEN NOW
   FB14  # ARMENIAN SMALL LIGATURE MEN ECH
   FB15  # ARMENIAN SMALL LIGATURE MEN INI
   FB16  # ARMENIAN SMALL LIGATURE VEW NOW
   FB17  # ARMENIAN SMALL LIGATURE MEN XEH
   """),

  # Avst - Avestan
  ('Avst',
   # Comment
   """
   From Core Specification and NamesList.txt
   www.unicode.org/L2/L2007/07006r-n3197r-avestan.pdf
   """,
   # Data
   """
   # Basic Latin
   002E  # FULL STOP
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # General Punctuation
   200C  # ZERO WIDTH NON-JOINER
   # Supplemental Punctuation
   2E30  # RING POINT
   2E31  # WORD SEPARATOR MIDDLE DOT
   """),

  # Bali - Balinese

  # Bamu - Bamum

  # Bass - Bassa Vah
  ('Bass',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   0022  # QUOTATION MARK
   002C  # COMMA
   002E  # FULL STOP
   # General Punctuation
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Batk - Batak

  # Beng - Bengali

  # Bhks - Bhks (Bhaiksuki)

  # Brah - Brahmi

  # Brai - Braille

  # Bugi - Buginese

  # Buhd - Buhid

  # CJK - (Bopo,Hang,Hani,Hans,Hant,Hira,Jpan,Kana,Kore)

  # Cakm - Chakma

  # Cans - Canadian Aboriginal
  ('Cans',
   # Comment
   """
   From core specification and web sites.
   """,
   # Data
   """
   # Basic Latin
   0022  # QUOTATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002D  # HYPHEN-MINUS
   002E  # FULL STOP
   # General Punctuation
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Cari - Carian
  ('Cari',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # General Punctuation
   205A  # TWO DOT PUNCTUATION
   205D  # TRICOLON
   # Supplemental Punctuation
   2E31  # WORD SEPARATOR MIDDLE DOT
   """),

  # Cham - Cham
  ('Cham',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002D  # HYPHEN-MINUS
   003A  # COLON
   003F  # QUESTION MARK
   # General Punctuation
   2010  # HYPHEN
   """),

  # Cher - Cherokee
  ('Cher',
   # Comment
   """
   From core specification and
   http://www.unicode.org/L2/L2014/14064r-n4537r-cherokee.pdf section 8.
   Core spec says 'uses latin punctuation', these are a subset of the latin-1
   punct because the intent of listing them is to ensure that use in running
   text works with the script.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0022  # QUOTATION MARK
   0027  # APOSTROPHE
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002D  # HYPHEN-MINUS
   002E  # FULL STOP
   002F  # SOLIDUS
   003A  # COLON
   003B  # SEMICOLON
   003F  # QUESTION MARK
   005B  # LEFT SQUARE BRACKET
   005D  # RIGHT SQUARE BRACKET
   007E  # TILDE
   # Combining Diacritical Marks
   0300  # COMBINING GRAVE ACCENT
   0301  # COMBINING ACUTE ACCENT
   0302  # COMBINING CIRCUMFLEX ACCENT
   0304  # COMBINING MACRON
   030B  # COMBINING DOUBLE ACUTE ACCENT
   030C  # COMBINING CARON
   0323  # COMBINING DOT BELOW
   0324  # COMBINING DIAERESIS BELOW
   0330  # COMBINING TILDE BELOW
   0331  # COMBINING MACRON BELOW
   # General Punctuation
   2010  # HYPHEN
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Copt - Coptic
  ('Copt',
   # Comment
   """
   From Core specification and
   http://std.dkuug.dk/JTC1/SC2/WG2/docs/n2636.pdf
   """,
   # Data
   """
   # Basic Latin
   002E  # FULL STOP
   003A  # COLON
   003B  # SEMICOLON
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Combining Diacritical Marks
   0300  # COMBINING GRAVE ACCENT
   0301  # COMBINING ACUTE ACCENT
   0302  # COMBINING CIRCUMFLEX ACCENT
   0304  # COMBINING MACRON
   0305  # COMBINING OVERLINE
   0307  # COMBINING DOT ABOVE
   0308  # COMBINING DIAERESIS
   033F  # COMBINING DOUBLE OVERLINE
   # Greek and Coptic
   0374  # GREEK NUMERAL SIGN
   0375  # GREEK LOWER NUMERAL SIGN
   # General Punctuation
   2019  # RIGHT SINGLE QUOTATION MARK
   # Supplemental Punctuation
   2E17  # DOUBLE OBLIQUE HYPHEN
   # Combining Half Marks
   FE24  # COMBINING MACRON LEFT HALF
   FE25  # COMBINING MACRON RIGHT HALF
   FE26  # COMBINING CONJOINING MACRON
   """),

  # Cprt - Cypriot

  # Deva - Devanagari

  # Dsrt - Deseret

  # Dupl - Duployan shorthand (Duployan)

  # Egyp - Egyptian hieroglyphs

  # Elba - Elbasan
  ('Elba',
   # Comment
   """
   see http://www.unicode.org/L2/L2011/11050-n3985-elbasan.pdf
   adds combining overbar and greek numerals for ones and tens, and
   both stigma/digamma for 6.
   """,
   # Data
   """
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Combining Diacritical Marks
   0305  # COMBINING OVERLINE
   # Greek and Coptic
   0391  # GREEK CAPITAL LETTER ALPHA
   0392  # GREEK CAPITAL LETTER BETA
   0393  # GREEK CAPITAL LETTER GAMMA
   0394  # GREEK CAPITAL LETTER DELTA
   0395  # GREEK CAPITAL LETTER EPSILON
   0396  # GREEK CAPITAL LETTER ZETA
   0397  # GREEK CAPITAL LETTER ETA
   0398  # GREEK CAPITAL LETTER THETA
   0399  # GREEK CAPITAL LETTER IOTA
   039A  # GREEK CAPITAL LETTER KAPPA
   039B  # GREEK CAPITAL LETTER LAMDA
   039C  # GREEK CAPITAL LETTER MU
   039D  # GREEK CAPITAL LETTER NU
   039E  # GREEK CAPITAL LETTER XI
   039F  # GREEK CAPITAL LETTER OMICRON
   03A0  # GREEK CAPITAL LETTER PI
   03DA  # GREEK LETTER STIGMA
   03DD  # GREEK SMALL LETTER DIGAMMA
   03DE  # GREEK LETTER KOPPA
   """),

  # Ethi - Ethiopic
  ('Ethi',
   # Comment
   """
   From core specification, also see
   http://abyssiniagateway.net/fidel/l10n/
   Recommends combining diaeresis 'for scholarly use', should look Ethiopian.
   Also claims hyphen is not used, but a wikipedia page in Amharic does use
   it, see
   https://am.wikipedia.org/wiki/1_%E1%8A%A5%E1%88%BD%E1%88%98-%E1%8B%B3%E1%8C%8B%E1%8A%95
   Western numerals and punctuation should look heavier to match the Ethiopic.
   A keyboard standard is here:
   See http://www.mcit.gov.et/documents/1268465/1282796/Keyboard+Layout+Standard/a8aa75ca-e125-4e25-872e-380e2a9b2313
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002B  # PLUS SIGN
   002E  # FULL STOP
   002F  # SOLIDUS
   003D  # EQUALS SIGN
   # Combining Diacritical Marks
   0308  # COMBINING DIAERESIS
   030E  # COMBINING DOUBLE VERTICAL LINE ABOVE
   # Mathematical Operators
   22EE  # VERTICAL ELLIPSIS
   """),

  # Geor - Georgian
  ('Geor',
   # Comment
   """
   From core specification (references unspecified additionl latin punct), also see
   example news article: http://www.civil.ge/geo/article.php?id=29970
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0025  # PERCENT SIGN
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002E  # FULL STOP
   003A  # COLON
   003B  # SEMICOLON
   # Latin-1 Supplement
   00A0  # NO-BREAK SPACE
   00B7  # MIDDLE DOT
   # General Punctuation
   2014  # EM DASH
   2056  # THREE DOT PUNCTUATION
   2057  # QUADRUPLE PRIME
   2058  # FOUR DOT PUNCTUATION
   2059  # FIVE DOT PUNCTUATION
   205A  # TWO DOT PUNCTUATION
   205B  # FOUR DOT MARK
   205C  # DOTTED CROSS
   205D  # TRICOLON
   205E  # VERTICAL FOUR DOTS
   # Supplemental Punctuation
   2E2A  # TWO DOTS OVER ONE DOT PUNCTUATION
   2E2B  # ONE DOT OVER TWO DOTS PUNCTUATION
   2E2C  # SQUARED FOUR DOT PUNCTUATION
   2E2D  # FIVE DOT MARK
   2E31  # WORD SEPARATOR MIDDLE DOT
   """),

  # Glag - Glagolitic
  ('Glag',
   # Comment
   """
   See core specification.  It refers to 'numerous diacritical marks', these
   are not listed.
   """,
   # Data
   """
   # Basic Latin
   0022  # QUOTATION MARK
   002C  # COMMA
   002E  # FULL STOP
   003B  # SEMICOLON
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Combining Diacritical Marks
   0303  # COMBINING TILDE
   0305  # COMBINING OVERLINE
   # General Punctuation
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   2056  # THREE DOT PUNCTUATION
   2058  # FOUR DOT PUNCTUATION
   2059  # FIVE DOT PUNCTUATION
   """),

  # Goth - Gothic
  ('Goth',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   003A  # COLON
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Combining Diacritical Marks
   0304  # COMBINING MACRON
   0305  # COMBINING OVERLINE
   0308  # COMBINING DIAERESIS
   0331  # COMBINING MACRON BELOW
   """),

  # Gran - Grantha
  ('Gran',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Devanagari
   0951  # DEVANAGARI STRESS SIGN UDATTA
   0952  # DEVANAGARI STRESS SIGN ANUDATTA
   # Vedic Extensions
   1CD0  # VEDIC TONE KARSHANA
   1CD2  # VEDIC TONE PRENKHA
   1CD3  # VEDIC SIGN NIHSHVASA
   1CF2  # VEDIC SIGN ARDHAVISARGA
   1CF3  # VEDIC SIGN ROTATED ARDHAVISARGA
   1CF4  # VEDIC TONE CANDRA ABOVE
   1CF8  # VEDIC TONE RING ABOVE
   1CF9  # VEDIC TONE DOUBLE RING ABOVE
   # Combining Diacritical Marks for Symbols
   20F0  # COMBINING ASTERISK ABOVE
   """),

  # Gujr - Gujarati

  # Guru - Gurmukhi
  ('Guru',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Miscellaneous Symbols
   262C  # ADI SHAKTI
   """),

  # Hano - Hanunoo

  # Hatr - Hatr (Hatran)
  ('Hatr',
   # Comment
   """
   See http://www.unicode.org/L2/L2012/12312-n4324-hatran.pdf (most info, but
   not latest assignment, which doesn't have all digits shown here)
   single and double vertical line, also ZWNJ in case ligatures need breaking
   might want to ligate hatran digit 1 forms 11 (2), 111 (3), 1111 (4) to
   look as the suggested (dropped) digits were represented in the doc.
   """,
   # Data
   """
   # Basic Latin
   007C  # VERTICAL LINE
   # General Punctuation
   200C  # ZERO WIDTH NON-JOINER
   2016  # DOUBLE VERTICAL LINE
   """),

  # Hebr - Hebrew
  ('Hebr',
   # Comment
   """
   From core specification, adds currency.
   """,
   # Data
   """
   # Basic Latin
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   # Combining Diacritical Marks
   0307  # COMBINING DOT ABOVE
   0308  # COMBINING DIAERESIS
   034F  # COMBINING GRAPHEME JOINER
   # General Punctuation
   200C  # ZERO WIDTH NON-JOINER
   200D  # ZERO WIDTH JOINER
   200E  # LEFT-TO-RIGHT MARK
   200F  # RIGHT-TO-LEFT MARK
   # Currency Symbols
   20AA  # NEW SHEQEL SIGN
   # Letterlike Symbols
   2135  # ALEF SYMBOL
   2136  # BET SYMBOL
   2137  # GIMEL SYMBOL
   2138  # DALET SYMBOL
   """),

  # Hluw - Anatolian Hieroglyphs
  ('Hluw',
   # Comment
   """
   see http://www.unicode.org/L2/L2012/12213-n4282-anatolian.pdf
   """,
   # Data
   """
   # General Punctuation
   200B  # ZERO WIDTH SPACE
   """),

  # Hmng - Pahawh Hmong

  # Hrkt - Japanese syllabaries (Katakana Or Hiragana)

  # Hung - Old Hungarian
  ('Hung',
   # Comment
   """
   see  http://www.unicode.org/L2/L2012/12168r-n4268r-oldhungarian.pdf
   letters with LTR override mirror reverse (!) "which has to be handled by
   the rendering engine"
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   002C  # COMMA
   002D  # HYPHEN-MINUS
   002E  # FULL STOP
   003A  # COLON
   # General Punctuation
   200D  # ZERO WIDTH JOINER
   2010  # HYPHEN
   201F  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
   204F  # REVERSED SEMICOLON
   205A  # TWO DOT PUNCTUATION
   205D  # TRICOLON
   205E  # VERTICAL FOUR DOTS
   # Supplemental Punctuation
   2E2E  # REVERSED QUESTION MARK
   2E31  # WORD SEPARATOR MIDDLE DOT
   2E41  # REVERSED COMMA
   2E42  # DOUBLE LOW-REVERSED-9 QUOTATION MARK
   """),

  # Ital - Old Italic

  # Java - Javanese

  # Kali - Kayah Li
  ('Kali',
   # Comment
   """
   From core specification, also see
   http://www.unicode.org/L2/L2006/06073-n3038r-kayahli.pdf
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0022  # QUOTATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002D  # HYPHEN-MINUS
   003F  # QUESTION MARK
   # General Punctuation
   2010  # HYPHEN
   """),

  # Khar - Kharoshthi
  ('Khar',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002D  # HYPHEN-MINUS
   # General Punctuation
   2010  # HYPHEN
   """),

  # Khmr - Khmer
  ('Khmr',
   # Comment
   """
   Latin punct see web sites
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   """),

  # Khoj - Khojki
  ('Khoj',
   # Comment
   """
   From core specification, also see
   http://www.unicode.org/L2/L2011/11021-khojki.pdf
   """,
   # Data
   """
   # Basic Latin
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002E  # FULL STOP
   003B  # SEMICOLON
   # General Punctuation
   2013  # EN DASH
   2026  # HORIZONTAL ELLIPSIS
   """),

  # Knda - Kannada

  # Kthi - Kaithi
  ('Kthi',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002B  # PLUS SIGN
   002D  # HYPHEN-MINUS
   # General Punctuation
   2010  # HYPHEN
   # Supplemental Punctuation
   2E31  # WORD SEPARATOR MIDDLE DOT
   """),

  # LGC - (Latn,Grek,Cyrl)
  ('LGC',
   # Comment
   """
   """,
   # Data
   """
   # Spacing Modifier Letters
   02EA  # MODIFIER LETTER YIN DEPARTING TONE MARK
   02EB  # MODIFIER LETTER YANG DEPARTING TONE MARK
   # Letterlike Symbols
   2105  # CARE OF
   2113  # SCRIPT SMALL L
   2116  # NUMERO SIGN
   2117  # SOUND RECORDING COPYRIGHT
   2120  # SERVICE MARK
   2121  # TELEPHONE SIGN
   2122  # TRADE MARK SIGN
   213B  # FACSIMILE SIGN
   # Arrows
   2190  # LEFTWARDS ARROW
   2191  # UPWARDS ARROW
   2192  # RIGHTWARDS ARROW
   2193  # DOWNWARDS ARROW
   2194  # LEFT RIGHT ARROW
   2195  # UP DOWN ARROW
   # Geometric Shapes
   25A0  # BLACK SQUARE
   25A1  # WHITE SQUARE
   25CA  # LOZENGE
   25CB  # WHITE CIRCLE
   25CC  # DOTTED CIRCLE
   25CF  # BLACK CIRCLE
   25D8  # INVERSE BULLET
   25D9  # INVERSE WHITE CIRCLE
   25E6  # WHITE BULLET
   # Modifier Tone Letters
   A717  # MODIFIER LETTER DOT VERTICAL BAR
   A718  # MODIFIER LETTER DOT SLASH
   A719  # MODIFIER LETTER DOT HORIZONTAL BAR
   A71A  # MODIFIER LETTER LOWER RIGHT CORNER ANGLE
   A71B  # MODIFIER LETTER RAISED UP ARROW
   A71C  # MODIFIER LETTER RAISED DOWN ARROW
   A71D  # MODIFIER LETTER RAISED EXCLAMATION MARK
   A71E  # MODIFIER LETTER RAISED INVERTED EXCLAMATION MARK
   A71F  # MODIFIER LETTER LOW INVERTED EXCLAMATION MARK
   # Specials
   FFFC  # OBJECT REPLACEMENT CHARACTER
   FFFD  # REPLACEMENT CHARACTER
   """),

  # Lana - Lanna (Tai Tham)

  # Laoo - Lao
  ('Laoo',
   # Comment
   """
   For latin punct use see web sites, e.g. nuol.edu.la
   """,
   # Data
   """
   # Basic Latin
   0022  # QUOTATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002E  # FULL STOP
   003A  # COLON
   # General Punctuation
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Lepc - Lepcha
  ('Lepc',
   # Comment
   """
   From core specification, only the specificially mentioned punct.
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002E  # FULL STOP
   003F  # QUESTION MARK
   """),

  # Limb - Limbu
  ('Limb',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Devanagari
   0965  # DEVANAGARI DOUBLE DANDA
   """),

  # Lina - Linear A

  # Linb - Linear B

  # Lisu - Fraser (Lisu)
  ('Lisu',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0022  # QUOTATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002D  # HYPHEN-MINUS
   003A  # COLON
   003B  # SEMICOLON
   003F  # QUESTION MARK
   # Spacing Modifier Letters
   02BC  # MODIFIER LETTER APOSTROPHE
   02CD  # MODIFIER LETTER LOW MACRON
   # General Punctuation
   2010  # HYPHEN
   2026  # HORIZONTAL ELLIPSIS
   # CJK Symbols and Punctuation
   300A  # LEFT DOUBLE ANGLE BRACKET
   300B  # RIGHT DOUBLE ANGLE BRACKET
   """),

  # Lyci - Lycian
  ('Lyci',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # General Punctuation
   205A  # TWO DOT PUNCTUATION
   """),

  # Lydi - Lydian
  ('Lydi',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   003A  # COLON
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Supplemental Punctuation
   2E31  # WORD SEPARATOR MIDDLE DOT
   """),

  # Mahj - Mahajani
  ('Mahj',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002D  # HYPHEN-MINUS
   003A  # COLON
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Devanagari
   0964  # DEVANAGARI DANDA
   0965  # DEVANAGARI DOUBLE DANDA
   # General Punctuation
   2013  # EN DASH
   """),

  # Mand - Mandaean (Mandaic)
  ('Mand',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Arabic
   0640  # ARABIC TATWEEL
   """),

  # Mani - Manichaean

  # Marc - Marc (Marchen)

  # Mend - Mende (Mende Kikakui)

  # Merc - Meroitic Cursive
  ('Merc',
   # Comment
   """
   From core specification.
   also see http://www.unicode.org/L2/L2009/09188r-n3646-meroitic.pdf
   """,
   # Data
   """
   # Basic Latin
   003A  # COLON
   # General Punctuation
   2026  # HORIZONTAL ELLIPSIS
   205D  # TRICOLON
   """),

  # Mero - Meroitic (Meroitic Hieroglyphs)

  # Mlym - Malayalam

  # Modi - Modi
  ('Modi',
   # Comment
   """
   From core specification, also see
   http://www.unicode.org/L2/L2011/11212r2-n4034-modi.pdf
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002E  # FULL STOP
   003B  # SEMICOLON
   """),

  # Mong - Mongolian
  ('Mong',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0022  # QUOTATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   003F  # QUESTION MARK
   # General Punctuation
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   2048  # QUESTION EXCLAMATION MARK
   2049  # EXCLAMATION QUESTION MARK
   """),

  # Mroo - Mro

  # Mtei - Meitei Mayek (Meetei Mayek)

  # Mult - Mult (Multani)

  # Mymr - Myanmar
  ('Mymr',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # General Punctuation
   200B  # ZERO WIDTH SPACE
   """),

  # Narb - Old North Arabian

  # Nbat - Nabataean

  # Newa - Newa

  # Nkoo - N'Ko
  ('Nkoo',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Arabic
   060C  # ARABIC COMMA
   061B  # ARABIC SEMICOLON
   061F  # ARABIC QUESTION MARK
   # Supplemental Punctuation
   2E1C  # LEFT LOW PARAPHRASE BRACKET
   2E1D  # RIGHT LOW PARAPHRASE BRACKET
   # Arabic Presentation Forms-A
   FD3E  # ORNATE LEFT PARENTHESIS
   FD3F  # ORNATE RIGHT PARENTHESIS
   """),

  # Ogam - Ogham

  # Olck - Ol Chiki
  ('Olck',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   002C  # COMMA
   003F  # QUESTION MARK
   # General Punctuation
   2014  # EM DASH
   2018  # LEFT SINGLE QUOTATION MARK
   2019  # RIGHT SINGLE QUOTATION MARK
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Orkh - Orkhon (Old Turkic)
  ('Orkh',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # General Punctuation
   205A  # TWO DOT PUNCTUATION
   # Supplemental Punctuation
   2E30  # RING POINT
   """),

  # Orya - Oriya

  # Osge - Osge (Osage)

  # Osma - Osmanya

  # Palm - Palmyrene

  # Pauc - Pau Cin Hau
  ('Pauc',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002E  # FULL STOP
   """),

  # Perm - Old Permic
  ('Perm',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   0027  # APOSTROPHE
   003A  # COLON
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   # Combining Diacritical Marks
   0300  # COMBINING GRAVE ACCENT
   0306  # COMBINING BREVE
   0307  # COMBINING DOT ABOVE
   0308  # COMBINING DIAERESIS
   0313  # COMBINING COMMA ABOVE
   # Cyrillic
   0483  # COMBINING CYRILLIC TITLO
   # Combining Diacritical Marks for Symbols
   20DB  # COMBINING THREE DOTS ABOVE
   """),

  # Phag - Phags-pa

  # Phli - Inscriptional Pahlavi

  # Phlp - Psalter Pahlavi
  ('Phlp',
   # Comment
   """
   from core specification.
   """,
   # Data
   """
   # Arabic
   0640  # ARABIC TATWEEL
   """),

  # Phnx - Phoenician

  # Plrd - Pollard Phonetic (Miao)

  # Prti - Inscriptional Parthian

  # Rjng - Rejang
  ('Rjng',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002E  # FULL STOP
   003A  # COLON
   """),

  # Runr - Runic

  # Samr - Samaritan
  ('Samr',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Supplemental Punctuation
   2E31  # WORD SEPARATOR MIDDLE DOT
   """),

  # Sarb - Old South Arabian

  # Saur - Saurashtra
  ('Saur',
   # Comment
   """
   From core specification, only the specificially mentioned punct.
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002E  # FULL STOP
   003F  # QUESTION MARK
   """),

  # Sgnw - SignWriting

  # Shaw - Shavian
  ('Shaw',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Latin-1 Supplement
   00B7  # MIDDLE DOT
   """),

  # Shrd - Sharada

  # Sidd - Siddham

  # Sind - Khudawadi
  ('Sind',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002E  # FULL STOP
   003A  # COLON
   003B  # SEMICOLON
   # Devanagari
   0964  # DEVANAGARI DANDA
   0965  # DEVANAGARI DOUBLE DANDA
   # General Punctuation
   2013  # EN DASH
   2014  # EM DASH
   """),

  # Sinh - Sinhala
  ('Sinh',
   # Comment
   """
   From core specification, plus unspecified latin punctuation seen on web
   sites.
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002E  # FULL STOP
   # Devanagari
   0964  # DEVANAGARI DANDA
   """),

  # Sora - Sora Sompeng
  ('Sora',
   # Comment
   """
   From core specification and
   http://www.unicode.org/L2/L2009/09189r-n3647r-sora-sompeng.pdf
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002D  # HYPHEN-MINUS
   002E  # FULL STOP
   003B  # SEMICOLON
   # General Punctuation
   2010  # HYPHEN
   """),

  # Sund - Sundanese
  ('Sund',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   0022  # QUOTATION MARK
   002D  # HYPHEN-MINUS
   003C  # LESS-THAN SIGN
   003E  # GREATER-THAN SIGN
   003F  # QUESTION MARK
   # General Punctuation
   2010  # HYPHEN
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Sylo - Syloti Nagri
  ('Sylo',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002E  # FULL STOP
   003A  # COLON
   003B  # SEMICOLON
   # Devanagari
   0964  # DEVANAGARI DANDA
   0965  # DEVANAGARI DOUBLE DANDA
   # General Punctuation
   2055  # FLOWER PUNCTUATION MARK
   """),

  # Syrc - Syriac
  ('Syrc',
   # Comment
   """
   From core specification.  In it, the eference to 'arabic harakat' used with
   Garshuni is based on the Harakat section of the wikipedia page on Arabic
   diacritics.
   """,
   # Data
   """
   # Combining Diacritical Marks
   0303  # COMBINING TILDE
   0304  # COMBINING MACRON
   0307  # COMBINING DOT ABOVE
   0308  # COMBINING DIAERESIS
   030A  # COMBINING RING ABOVE
   0320  # COMBINING MINUS SIGN BELOW
   0323  # COMBINING DOT BELOW
   0324  # COMBINING DIAERESIS BELOW
   0325  # COMBINING RING BELOW
   032D  # COMBINING CIRCUMFLEX ACCENT BELOW
   032E  # COMBINING BREVE BELOW
   0330  # COMBINING TILDE BELOW
   # Arabic
   060C  # ARABIC COMMA
   061B  # ARABIC SEMICOLON
   061F  # ARABIC QUESTION MARK
   0640  # ARABIC TATWEEL
   064E  # ARABIC FATHA
   064F  # ARABIC DAMMA
   0650  # ARABIC KASRA
   0651  # ARABIC SHADDA
   0652  # ARABIC SUKUN
   0653  # ARABIC MADDAH ABOVE
   0670  # ARABIC LETTER SUPERSCRIPT ALEF
   0671  # ARABIC LETTER ALEF WASLA
   # General Punctuation
   200C  # ZERO WIDTH NON-JOINER
   """),

  # Tagb - Tagbanwa

  # Takr - Takri
  ('Takr',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Devanagari
   0964  # DEVANAGARI DANDA
   0965  # DEVANAGARI DOUBLE DANDA
   """),

  # Tale - Tai Le
  ('Tale',
   # Comment
   """
   From core specification & http://www.unicode.org/L2/L2001/01369-n2372.pdf
   Myanmar digits have glyphic variants according to the spec.
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002E  # FULL STOP
   003A  # COLON
   003F  # QUESTION MARK
   # Combining Diacritical Marks
   0300  # COMBINING GRAVE ACCENT
   0301  # COMBINING ACUTE ACCENT
   0307  # COMBINING DOT ABOVE
   0308  # COMBINING DIAERESIS
   030C  # COMBINING CARON
   # Myanmar
   1040  # MYANMAR DIGIT ZERO
   1041  # MYANMAR DIGIT ONE
   1042  # MYANMAR DIGIT TWO
   1043  # MYANMAR DIGIT THREE
   1044  # MYANMAR DIGIT FOUR
   1045  # MYANMAR DIGIT FIVE
   1046  # MYANMAR DIGIT SIX
   1047  # MYANMAR DIGIT SEVEN
   1048  # MYANMAR DIGIT EIGHT
   1049  # MYANMAR DIGIT NINE
   # General Punctuation
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   # CJK Symbols and Punctuation
   3002  # IDEOGRAPHIC FULL STOP
   """),

  # Talu - New Tai Lue

  # Taml - Tamil
  ('Taml',
   # Comment
   """
   From core specificaion and
   http://www.unicode.org/L2/L2010/10407-ext-tamil-follow2.pdf
   """,
   # Data
   """
   # Latin-1 Supplement
   00B2  # SUPERSCRIPT TWO
   00B3  # SUPERSCRIPT THREE
   # Superscripts and Subscripts
   2074  # SUPERSCRIPT FOUR
   2082  # SUBSCRIPT TWO
   2083  # SUBSCRIPT THREE
   2084  # SUBSCRIPT FOUR
   """),

  # Tang - Tangut

  # Tavt - Tai Viet
  ('Tavt',
   # Comment
   """
   Used in SIL fonts.
   """,
   # Data
   """
   # Latin Extended-D
   A78B  # LATIN CAPITAL LETTER SALTILLO
   A78C  # LATIN SMALL LETTER SALTILLO
   """),

  # Telu - Telugu

  # Tfng - Tifinagh
  ('Tfng',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Combining Diacritical Marks
   0302  # COMBINING CIRCUMFLEX ACCENT
   0304  # COMBINING MACRON
   0307  # COMBINING DOT ABOVE
   0309  # COMBINING HOOK ABOVE
   # General Punctuation
   200D  # ZERO WIDTH JOINER
   """),

  # Tglg - Tagalog

  # Thaa - Thaana
  ('Thaa',
   # Comment
   """
   From core specification, parens from text sample.  Probably other punct
   as well but spec does not list.
   """,
   # Data
   """
   # Basic Latin
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002E  # FULL STOP
   # Arabic
   060C  # ARABIC COMMA
   061B  # ARABIC SEMICOLON
   061F  # ARABIC QUESTION MARK
   """),

  # Thai - Thai
  ('Thai',
   # Comment
   """
   From core specification and
   http://www.unicode.org/L2/L2010/10451-patani-proposal.pdf
   for latin punct see web sites e.g. pandip.com, sanook.com
   Bhat already here, or should be
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0022  # QUOTATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002E  # FULL STOP
   003A  # COLON
   003F  # QUESTION MARK
   # Spacing Modifier Letters
   02BC  # MODIFIER LETTER APOSTROPHE
   02D7  # MODIFIER LETTER MINUS SIGN
   # Combining Diacritical Marks
   0303  # COMBINING TILDE
   0331  # COMBINING MACRON BELOW
   # General Punctuation
   200B  # ZERO WIDTH SPACE
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   2026  # HORIZONTAL ELLIPSIS
   """),

  # Tibt - Tibetan
  ('Tibt',
   # Comment
   """
   Wheel of Dharma from core specification, not sure of source for vertical
   line.
   """,
   # Data
   """
   # Basic Latin
   007C  # VERTICAL LINE
   # Miscellaneous Symbols
   2638  # WHEEL OF DHARMA
   """),

  # Tirh - Tirhuta
  ('Tirh',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Devanagari
   0964  # DEVANAGARI DANDA
   0965  # DEVANAGARI DOUBLE DANDA
   """),

  # Ugar - Ugaritic

  # Vaii - Vai
  ('Vaii',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # Basic Latin
   002C  # COMMA
   002D  # HYPHEN-MINUS
   """),

  # Wara - Varang Kshiti (Warang Citi)
  ('Wara',
   # Comment
   """
   "Uses latin punctuation," so guess based on sample text from
   proposal doc, see
   http://www.unicode.org/L2/L2012/12118-n4259-warang-citi.pdf
   """,
   # Data
   """
   # Basic Latin
   0021  # EXCLAMATION MARK
   0028  # LEFT PARENTHESIS
   0029  # RIGHT PARENTHESIS
   002C  # COMMA
   002D  # HYPHEN-MINUS
   002E  # FULL STOP
   003A  # COLON
   003B  # SEMICOLON
   003F  # QUESTION MARK
   # General Punctuation
   2013  # EN DASH
   2014  # EM DASH
   201C  # LEFT DOUBLE QUOTATION MARK
   201D  # RIGHT DOUBLE QUOTATION MARK
   """),

  # Xpeo - Old Persian

  # Xsux - Sumero-Akkadian Cuneiform (Cuneiform)

  # Yiii - Yi
  ('Yiii',
   # Comment
   """
   From core specification.
   """,
   # Data
   """
   # CJK Symbols and Punctuation
   3001  # IDEOGRAPHIC COMMA
   3002  # IDEOGRAPHIC FULL STOP
   """),
]

def _regen_script_required():
  """Rerun after editing script required to check/reformat."""
  script_to_comment_and_data = {
      script: (comment, data)
      for script, comment, data in _SCRIPT_REQUIRED
  }
  scripts = set(unicode_data.all_scripts())
  for to_script, from_scripts in _MERGED_SCRIPTS_BY_TARGET.iteritems():
    scripts.add(to_script)
    scripts -= set(from_scripts)
  # keep extra script data, e.g. 'Aran'
  scripts.update(set(script_to_comment_and_data.keys()))
  scripts -= set(['Zinh', 'Zyyy', 'Zzzz'])

  for script in sorted(scripts):
    if script in _MERGED_SCRIPTS_BY_TARGET:
      script_name = '(%s)' % ','.join(_MERGED_SCRIPTS_BY_TARGET[script])
    else:
      script_name = cldr_data.get_english_script_name(script)
      unicode_script_name = unicode_data.human_readable_script_name(script)
      if script_name.lower() != unicode_script_name.lower():
        script_name += ' (%s)' % unicode_script_name
      script_name = script_name.replace(unichr(0x2019), "'")
    print '  # %s - %s' % (script, script_name)
    if script in script_to_comment_and_data:
      print "  ('%s'," % script
      lines = []
      comment, data = script_to_comment_and_data[script]
      lines.append('   # Comment')
      lines.append('"""')
      for line in comment.strip().splitlines():
        lines.append(line.strip())
      lines.append('""",')

      lines.append('# Data')
      lines.append('"""')
      cps = tool_utils.parse_int_ranges(data)
      block = None
      for cp in sorted(cps):
        cp_block = unicode_data.block(cp)
        if cp_block != block:
          block = cp_block
          lines.append('# ' + block)
        cp_name = unicode_data.name(cp, '<unnamed>')
        lines.append('%04X  # %s' % (cp, cp_name))
      lines.append('"""),')
      print '\n   '.join(lines)
    print


def _assign_script_required(cmap_ops):
  """Assign extra characters for various scripts."""

  for script, _, data in _SCRIPT_REQUIRED:
    extra = tool_utils.parse_int_ranges(data)
    cmap_ops.phase('assign script required for ' + script)
    cmap_ops.add_all(extra, script)


def _assign_legacy_phase2(cmap_ops):
  """Assign legacy chars in some scripts, excluding some blocks."""
  legacy_data = cmap_data.read_cmap_data_file('noto_cmap_phase2.xml')
  legacy_map = cmap_data.create_map_from_table(legacy_data.table)
  legacy_script_to_chars = {
      script: tool_utils.parse_int_ranges(row.ranges)
      for script, row in legacy_map.iteritems()}

  # The default is to include all legacy characters, except for the chars
  # listed for these scripts, for some default chars, and for some scripts.

  # Find out why these were included in the phase two fonts.
  # This excludes lots of punctuation and digits from Cham, Khmer, and Lao
  # but leaves some common latin characters like quotes, parens, comma/period,
  # and so on.
  exclude_script_ranges = {
    'Cham': '23-26 2A-2B 30-39 3C-3E 40 5B-60 7B-7E 037E',
    'Copt': '0323 0361 1dcd 25cc',
    'Kthi': '0030-0039',
    'Khmr': '23-26 2A-2B 30-39 3C-3E 40 5B-60 7B-7E 037E',
    'LGC': '03E2',
    'Lana': '2219',
    'Laoo': '23-26 2A-2B 30-39 3C-3E 40 5B-60 7B-7E 037E',
    'Limb': '0964', # I think double-danda was intended
    'Mlym': '0307 0323',
    'Syrc': '250C 2510', # box drawing?
    'Tavt': 'A78C',
  }

  # mono temporarily
  ignore_legacy = frozenset('LGC Zsye Zsym MONO'.split())
  ignore_cps = frozenset([0x0, 0xd, 0x20, 0xa0, 0xfeff])

  cmap_ops.phase('assign legacy phase 2')
  script_to_chars = cmap_ops.create_script_to_chars()
  for script in sorted(legacy_script_to_chars):
    if script not in script_to_chars:
      cmap_ops.log('skipping script %s' % script)
      continue
    if script in ignore_legacy:
      cmap_ops.log('ignoring %s' % script)
      continue

    script_chars = script_to_chars[script]
    legacy_chars = legacy_script_to_chars[script]
    missing_legacy = set(legacy_chars) - set(script_chars) - ignore_cps
    if script in exclude_script_ranges:
      ranges = exclude_script_ranges[script]
      missing_legacy -= set(tool_utils.parse_int_ranges(ranges))
    if missing_legacy:
      cmap_ops.phase('assign legacy %s' % script)
      cmap_ops.add_all(missing_legacy, script)

  """
  # check CJK
  cmap_ops.log('check cjk legacy')
  legacy_cjk_chars = set()
  for script in _MERGED_SCRIPTS_BY_TARGET['CJK']:
    if script in legacy_script_to_chars:
      legacy_cjk_chars |= legacy_script_to_chars[script]

  cjk_chars = script_to_chars['CJK']
  not_in_legacy = cjk_chars - legacy_cjk_chars
  # ignore plane 2 and above
  not_in_legacy -= set(range(0x20000, 0x120000))
  if not_in_legacy:
    print 'not in legacy (%d):' % len(not_in_legacy)
    compare_cmap_data._print_detailed(not_in_legacy)
  not_in_new = legacy_cjk_chars - cjk_chars
  if not_in_new:
    print 'not in new (%d):' % len(not_in_new)
    compare_cmap_data._print_detailed(not_in_new)
  """

def _excludes(cmap_ops):
  """Exclude some characters based on script."""
  exclude_chars = {
      'CJK': """
      332c         # Jungshik says excluded on purpose
      fa70-fad9    # Jungshik says Ken regards DPRK compatibility chars as
                   # outside of scope, like most of plane 2.
      1b000-1b001  # Ken says these are controversial.
      """,
  }
  cmap_ops.phase('excludes')
  for script in sorted(script_to_exclude_range):
    exclude = tool_utils.parse_int_ranges(script_to_exclude_range[script])
    cmap_ops.remove_all(exclude, script)


def _assign_mono(cmap_ops):
  """Monospace should be similar to LGC, with the addition of box drawing
  and block elements."""
  cmap_ops.phase('assign mono')
  lgc_chars = cmap_ops.script_chars('LGC')
  cmap_ops.add_all(lgc_chars, 'MONO')


# note: not currently used, script to punct does not support 'CURRENCY'
def _reassign_currency_to_lgc(script_to_chars):
  """Reassign current CLDR currencies in currency block from Zsym to LGC."""
  start, finish = unicode_data.block_range('Currency Symbols')
  currencies = set(range(start, finish + 1))
  currencies &= collect_cldr_punct.script_to_punct()['CURRENCY']
  symbols = script_to_chars['Zsym']
  lgc = script_to_chars['LGC']
  for cp in currencies:
    if cp not in symbols:
      print >> sys.stderr, 'ERROR currency %04X (%s) not in Zsym' % (
          cp, unicode_data.name(cp))
    else:
      symbols.remove(cp)
    lgc.add(cp)


def _remove_unwanted(cmap_ops):
  excluded_controls = tool_utils.parse_int_ranges("""
      0000-001f  # C0 controls
      007F       # DEL
      0080-009f  # C1 controls
      FEFF       # BOM""")
  cmap_ops.phase('remove unwanted')
  cmap_ops.remove_all_from_all(excluded_controls, cmap_ops.all_scripts())


def _assign_basic(cmap_ops):
  """Add NUL, CR, Space, NBS to all scripts."""
  basic_chars = frozenset([0x0, 0x0D, 0x20, 0xA0])
  cmap_ops.phase('assign basic')
  cmap_ops.add_all_to_all(basic_chars, cmap_ops.all_scripts())


def _propose_block_data():
  """Generate the block data list above."""
  info = []
  for block in unicode_data.block_names():
    start, finish = unicode_data.block_range(block)
    script_counts = collections.defaultdict(int)
    must_assign = False
    for cp in range(start, finish + 1):
      script = unicode_data.script(cp)
      if script != 'Zzzz':
        script_counts[script] += 1
      if script == 'Zyyy' or script == 'Zinh':
        must_assign_cp = True
        for s in unicode_data.script_extensions(cp):
          if s != 'Zyyy' and s != 'Zinh':
            must_assign_cp = False
            break
        if script == 'Zinh':
          if must_assign_cp:
            print 'must assign Zinh %04x %s' % (
                cp, unicode_data.name(cp, 'unnamed'))
          else:
            print 'ok          Zinh %04x %s (%s)' % (
                cp, unicode_data.name(cp, 'unnamed'),
                ', '.join(unicode_data.script_extensions(cp)))
        must_assign |= must_assign_cp

    max_script = None
    max_script_count = 0
    for script, count in script_counts.iteritems():
      if count > max_script_count:
        max_script = script
        max_script_count = count
    try:
      assigned_script = _block_to_script[block]
    except KeyError:
      print 'no info for block \'%s\'' % block
      assigned_script = None
    if must_assign and not assigned_script:
      assigned_script = max_script
    info.append((start, finish, block, max_script, assigned_script))
  print '_BLOCK_DATA = [\n  %s\n]' % '\n  '.join(
      '%-40s  # %s %04X-%04X' % (
          '(\'%s\', %s)' % (t[2], 'None' if not t[4] else "'%s'" % t[4]),
          t[3], t[0], t[1])
      for t in sorted(info, key=lambda t: t[0])
      if t[4])



def _compute_block_fallback(debug=False):
  """Examine all characters only script inherited or common, and assign to new
  scripts based on block range data.  Return a dict from new script to chars."""

  script_chars = collections.defaultdict(set)
  script_blocks = collections.defaultdict(list)
  block_names = unicode_data.block_names()
  inherited_set = _unicode_required('Zinh')
  common_set = _unicode_required('Zyyy')
  all_scripts = unicode_data.all_scripts()
  extra_scripts = set()
  unknown_scripts = set()

  zinh_and_zyyy = frozenset(['Zinh', 'Zyyy'])

  def ignore_multiscript(cps):
    """Return the cps that have only Zinh and/or Zyyy in script
    and script_extension."""
    result_cps = set()
    for cp in cps:
      script = unicode_data.script(cp)
      extensions = unicode_data.script_extensions(cp)
      all_scripts = set([script]) | extensions
      if all_scripts <= zinh_and_zyyy:
        result_cps.add(cp)
    return result_cps

  def _block_info(block_name):
    return '%13s %s' % (
        '%04x-%04x' % unicode_data.block_range(block_name), block_name)

  for block_name in sorted(block_names, key=lambda n: _block_ranges(n)[0]):
    block_cps = unicode_data.block_chars(block_name)
    block_inherited = ignore_multiscript(block_cps & inherited_set)
    block_common = ignore_multiscript(block_cps & common_set)
    block_either = block_inherited | block_common
    block_info = _block_info(block_name)
    if block_name not in _block_to_script:
      print '%s missing' % block_info
    if not block_either:
      continue
    if block_name not in _block_to_script:
      print '%s has no data but %d chars' % (block_info, len(block_either))
    else:
      assigned_script = _block_to_script[block_name]
      if assigned_script not in all_scripts:
        unknown_scripts.add(assigned_script)

      if debug:
        print '%s, %d chars to script "%s"' % (
            block_info, len(block_either), assigned_script)
      script_blocks[assigned_script].append(block_name)
      script_chars[assigned_script].update(block_either)

      # for cp in sorted(block_either):
      #   print '  %6s %s' % ('%04x' % cp, unicode_data.name(cp, '<unknown>'))

  if debug:
    for script in sorted(script_blocks):
      print '%s:' % script
      for block in script_blocks[script]:
        print _block_info(block)
        for cp in sorted(script_chars[script] & unicode_data.block_chars(block)):
          print '%13s   %04X %s %s' % (
              '', cp, sorted(set([unicode_data.script(cp)])
                             | unicode_data.script_extensions(cp)),
              unicode_data.name(cp, '<unknown>'))

  return script_chars


def build_script_to_chars(log_level):
  if log_level == 0:
    log_events = False
    log_details = False
  else:
    log_events = True
    log_details = log_level > 1

  script_to_chars = unicode_data.create_script_to_chars()

  cmap_ops = CmapOps(
      script_to_chars, log_events=log_events, log_details=log_details)

  _unassign_inherited_and_common_with_extensions(cmap_ops)
  _reassign_inherited(cmap_ops)
  _reassign_common(cmap_ops)
  _unassign_latin(cmap_ops)
  _assign_cldr_punct(cmap_ops)
  _reassign_merged_scripts(cmap_ops)
  _reassign_common_by_block(cmap_ops)
  _reassign_by_block(cmap_ops)
  _remove_empty(cmap_ops)
  _reassign_emoji(cmap_ops)
  _assign_nastaliq(cmap_ops)
  _assign_complex_script_extra(cmap_ops)
  _assign_hyphens_for_autohyphenation(cmap_ops)
  _assign_extra_indic(cmap_ops)
  _assign_script_required(cmap_ops)
  _assign_legacy_phase2(cmap_ops)
  _assign_mono(cmap_ops) # after LGC is defined except for basics
  _remove_unwanted(cmap_ops)  # comes before assign_basic
  _assign_basic(cmap_ops)
  cmap_ops.finish()  # so we can clean up log

  return cmap_ops.create_script_to_chars()


def _get_cmap_data(script_to_chars):
  metadata = cmap_data.create_metadata('noto_cmap_reqs', [])
  tabledata = cmap_data.create_table_from_map(script_to_chars)
  return cmap_data.CmapData(metadata, tabledata)


### debug

def _dump_primaries():
  for block in unicode_data.block_names():
    block_range = unicode_data.block_range(block)
    primary_script = _primary_script_for_block(block)
    print '%13s %6s %s' % (
      '%04X-%04X' % block_range,
      '\'%s\'' % primary_script if primary_script else '------',
      block)


def main():
  DEFAULT_OUTFILE = 'noto_cmap_phase3_temp.xml'
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-o', '--outfile', help='name of cmap file to output ("%s" if name '
      'omitted)' % DEFAULT_OUTFILE, metavar='file', nargs='?', default=None,
      const=DEFAULT_OUTFILE)
  parser.add_argument(
      '-l', '--loglevel', help='log detail 0-2',
      metavar='level', nargs='?', type=int, const=1, default=0)
  parser.add_argument(
      '--regen', help='reformat script required data, no cmap generation',
      action='store_true')

  args = parser.parse_args()
  if args.regen:
    _regen_script_required()
    return

  script_to_chars = build_script_to_chars(args.loglevel)
  cmapdata = _get_cmap_data(script_to_chars)
  if args.outfile:
    cmap_data.write_cmap_data_file(cmapdata, args.outfile, pretty=True)
    print 'wrote %s' % args.outfile
  else:
    print cmap_data.write_cmap_data(cmapdata, pretty=True)


if __name__ == "__main__":
  main()