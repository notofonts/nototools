#!/usr/bin/env python
# -*- coding: utf-8 -*-#
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

"""Bleeding-edge version of Unicode Character Database.

Provides an interface similar to Python's own unicodedata package, but with
the bleeding-edge data. The implementation is not efficient at all, it's
just done this way for the ease of use. The data is coming from bleeding
edge version of the Unicode Standard not yet published, so it is expected to
be unstable and sometimes inconsistent.
"""

__author__ = (
    "roozbeh@google.com (Roozbeh Pournader) and "
    "cibu@google.com (Cibu Johny)")

import codecs
import collections
import os
from os import path
import re
import sys

from fontTools.misc.py23 import unichr
try:
  import unicodedata2 as unicodedata  # Unicode 8 compliant native lib
except ImportError:
  import unicodedata  # Python's internal library

from nototools import tool_utils # parse_int_ranges

_data_is_loaded = False
_property_value_aliases_data = {}
_character_names_data = {}
_general_category_data = {}
_combining_class_data = {}
_decomposition_data = {}
_bidi_mirroring_characters = set()
_script_data = {}
_script_extensions_data = {}
_block_data = {}
_block_range = {}
_block_names = []
_age_data = {}
_bidi_mirroring_glyph_data = {}
_core_properties_data = {}
_indic_positional_data = {}
_indic_syllabic_data = {}
_defined_characters = set()
_script_code_to_long_name = {}
_folded_script_name_to_code = {}
_lower_to_upper_case = {}

# emoji data
_presentation_default_emoji = None
_presentation_default_text = None
_emoji_modifier_base = None
_emoji = None
_emoji_variants = None
_emoji_variants_proposed = None

# non-emoji variant data
_variant_data = None
_variant_data_cps = None

# proposed emoji
_proposed_emoji_data = None
_proposed_emoji_data_cps = None

# emoji sequences
_emoji_sequence_data = None
_emoji_non_vs_to_canonical = None
_emoji_group_data = None

# nameslist/namealiases
_nameslist_see_also = None
_namealiases_alt_names = None

def load_data():
  """Loads the data files needed for the module.

  Could be used by processes that care about controlling when the data is
  loaded. Otherwise, data will be loaded the first time it's needed.
  """
  global _data_is_loaded

  if not _data_is_loaded:
    _load_property_value_aliases_txt()
    _load_unicode_data_txt()
    _load_scripts_txt()
    _load_script_extensions_txt()
    _load_blocks_txt()
    _load_derived_age_txt()
    _load_derived_core_properties_txt()
    _load_bidi_mirroring_txt()
    _load_indic_data()
    _load_emoji_data()
    _load_emoji_sequence_data()
    _load_unicode_emoji_variants()
    _load_variant_data()
    _load_proposed_emoji_data()
    _load_nameslist_data()
    _load_namealiases_data()

    _data_is_loaded = True


def name(char, *args):
  """Returns the name of a character.

  Raises a ValueError exception if the character is undefined, unless an
  extra argument is given, in which case it will return that argument.
  """
  if type(char) is int:
    char = unichr(char)
  # First try and get the name from unidata, which is faster and supports
  # CJK and Hangul automatic names
  try:
      return unicodedata.name(char)
  except ValueError as val_error:
    cp = ord(char)
    load_data()
    if cp in _character_names_data:
      return _character_names_data[cp]
    elif (cp,) in _emoji_sequence_data:
      return _emoji_sequence_data[(cp,)][0]
    elif args:
      return args[0]
    else:
      raise Exception('no name for "%0x"' % ord(char))


def _char_to_int(char):
  """Converts a potential character to its scalar value."""
  if type(char) in [str, unicode]:
    return ord(char)
  else:
    return char

def derived_props():
  load_data()
  return frozenset(_core_properties_data.keys())

def chars_with_property(propname):
  load_data()
  return frozenset(_core_properties_data[propname])

def category(char):
  """Returns the general category of a character."""
  load_data()
  char = _char_to_int(char)
  try:
    return _general_category_data[char]
  except KeyError:
    return "Cn"  # Unassigned


def combining(char):
  """Returns the canonical combining class of a character."""
  load_data()
  char = _char_to_int(char)
  try:
    return _combining_class_data[char]
  except KeyError:
    return 0


def to_upper(char):
  """Returns the upper case for a lower case character.
  This is not full upper casing, but simply reflects the 1-1
  mapping in UnicodeData.txt."""
  load_data()
  cp = _char_to_int(char)
  try:
    if _general_category_data[cp] == 'Ll':
      return unichr(_lower_to_upper_case[cp])
  except KeyError:
    pass
  return char


def canonical_decomposition(char):
  """Returns the canonical decomposition of a character as a Unicode string.
  """
  load_data()
  char = _char_to_int(char)
  try:
    return _decomposition_data[char]
  except KeyError:
    return u""


def script(char):
  """Returns the script property of a character as a four-letter code."""
  load_data()
  char = _char_to_int(char)
  try:
    return _script_data[char]
  except KeyError:
    return "Zzzz"  # Unknown


def script_extensions(char):
  """Returns the script extensions property of a character.

  The return value is a frozenset of four-letter script codes.
  """
  load_data()
  char = _char_to_int(char)
  try:
    return _script_extensions_data[char]
  except KeyError:
    return frozenset([script(char)])


def block(char):
  """Returns the block property of a character."""
  load_data()
  char = _char_to_int(char)
  try:
    return _block_data[char]
  except KeyError:
    return "No_Block"


def block_range(block):
  """Returns a range (first, last) of the named block."""
  load_data()
  return _block_range[block]


def block_chars(block):
  """Returns a frozenset of the cps in the named block."""
  load_data()
  first, last = _block_range[block]
  return frozenset(xrange(first, last + 1))


def block_names():
  """Returns the names of the blocks in block order."""
  load_data()
  return _block_names[:]


def age(char):
  """Returns the age property of a character as a string.

  Returns None if the character is unassigned."""
  load_data()
  char = _char_to_int(char)
  try:
    return _age_data[char]
  except KeyError:
    return None


# Uniscribe treats these ignorables (Hangul fillers) as spacing.
UNISCRIBE_USED_IGNORABLES = frozenset([0x115f, 0x1160, 0x3164, 0xffa0])

def is_default_ignorable(char):
  """Returns true if the character has the Default_Ignorable property."""
  load_data()
  if type(char) in [str, unicode]:
    char = ord(char)
  return char in _core_properties_data["Default_Ignorable_Code_Point"]

def default_ignorables():
  load_data()
  return frozenset(_core_properties_data["Default_Ignorable_Code_Point"])


def is_defined(char):
  """Returns true if the character is defined in the Unicode Standard."""
  load_data()
  if type(char) in [str, unicode]:
    char = ord(char)
  return char in _defined_characters


def is_private_use(char):
  """Returns true if the characters is a private use character."""
  return category(char) == "Co"


def mirrored(char):
  """Returns 1 if the characters is bidi mirroring, 0 otherwise."""
  load_data()
  if type(char) in [str, unicode]:
    char = ord(char)
  return int(char in _bidi_mirroring_characters)


def bidi_mirroring_glyph(char):
  """Returns the bidi mirroring glyph property of a character."""
  load_data()
  if type(char) in [str, unicode]:
    char = ord(char)
  try:
    return _bidi_mirroring_glyph_data[char]
  except KeyError:
    return None


def mirrored_chars():
  return frozenset(_bidi_mirroring_glyph_data.keys())


def indic_positional_category(char):
  """Returns the Indic positional category of a character."""
  load_data()
  if type(char) in [str, unicode]:
    char = ord(char)
  try:
    return _indic_positional_data[char]
  except KeyError:
    return "NA"


def indic_syllabic_category(char):
  """Returns the Indic syllabic category of a character."""
  load_data()
  if type(char) in [str, unicode]:
    char = ord(char)
  try:
    return _bidi_syllabic_data[char]
  except KeyError:
    return "Other"


def create_script_to_chars():
  """Returns a mapping from script to defined characters, based on script and
  extensions, for all scripts."""
  load_data()
  result = collections.defaultdict(set)
  for cp in _defined_characters:
    if cp in _script_data:
      result[_script_data[cp]].add(cp)
    if cp in _script_extensions_data:
      for script in _script_extensions_data[cp]:
        result[script].add(cp)
  return result


_DEFINED_CHARACTERS_CACHE = {}

def defined_characters(version=None, scr=None):
  """Returns the set of all defined characters in the Unicode Standard."""
  load_data()
  # handle common error where version is passed as string, the age test
  # will always pass
  if version is not None:
    version = float(version)
  try:
    return _DEFINED_CHARACTERS_CACHE[(version, scr)]
  except KeyError:
    pass
  characters = _defined_characters
  if version is not None:
    characters = {char for char in characters
                  if age(char) is not None and float(age(char)) <= version}
  if scr is not None:
    characters = {char for char in characters
                  if script(char) == scr or scr in script_extensions(char)}
  characters = frozenset(characters)
  _DEFINED_CHARACTERS_CACHE[(version, scr)] = characters
  return characters


_strip_re = re.compile(r"[-'_ ]+")
def _folded_script_name(script_name):
  """Folds a script name to its bare bones for comparison."""
  # string.translate is changed by codecs, the method no longer takes two
  # parameters and so script_name.translate(None, "'-_ ") fails to compile
  return _strip_re.sub('', script_name).lower()


def script_code(script_name):
  """Returns the four-letter ISO 15924 code of a script from its long name.
  """
  load_data()
  folded_script_name = _folded_script_name(script_name)
  try:
    return _HARD_CODED_FOLDED_SCRIPT_NAME_TO_CODE[folded_script_name]
  except:
    return _folded_script_name_to_code.get(folded_script_name, 'Zzzz')


_HARD_CODED_HUMAN_READABLE_SCRIPT_NAMES = {
    'Aran': 'Nastaliq', # not assigned
    'Nkoo': 'N\'Ko',
    'Phag': 'Phags-Pa',
    'Piqd': 'Klingon', # not assigned
    'Zmth': 'Math', # not assigned
    'Zsye': 'Emoji', # not assigned
    'Zsym': 'Symbols', # not assigned
}

_HARD_CODED_FOLDED_SCRIPT_NAME_TO_CODE = {
    _folded_script_name(name): code for code, name in
    _HARD_CODED_HUMAN_READABLE_SCRIPT_NAMES.iteritems()
}

def human_readable_script_name(code):
  """Returns a human-readable name for the script code."""
  try:
    return _HARD_CODED_HUMAN_READABLE_SCRIPT_NAMES[code]
  except KeyError:
    load_data()
    return _script_code_to_long_name[code]


def all_scripts():
  """Return a frozenset of all four-letter script codes."""
  load_data()
  return frozenset(_script_code_to_long_name.keys())


_DATA_DIR_PATH = path.join(path.abspath(path.dirname(__file__)),
                           os.pardir, "third_party", "ucd")


def open_unicode_data_file(data_file_name):
  """Opens a Unicode data file.

  Args:
    data_file_name: A string containing the filename of the data file.

  Returns:
    A file handle to the data file.
  """
  return codecs.open(path.join(_DATA_DIR_PATH, data_file_name), "r", 'utf-8')


def _parse_code_ranges(input_data):
  """Reads Unicode code ranges with properties from an input string.

  Reads a Unicode data file already imported into a string. The format is
  the typical Unicode data file format with either one character or a
  range of characters separated by a semicolon with a property value (and
  potentially comments after a number sign, that will be ignored).

  Example source data file:
    http://www.unicode.org/Public/UNIDATA/Scripts.txt

  Example data:
    0000..001F    ; Common # Cc  [32] <control-0000>..<control-001F>
    0020          ; Common # Zs       SPACE

  Args:
    input_data: An input string, containing the data.

  Returns:
    A list of tuples corresponding to the input data, with each tuple
    containing the beginning of the range, the end of the range, and the
    property value for the range. For example:
    [(0, 31, 'Common'), (32, 32, 'Common')]
  """
  ranges = []
  line_regex = re.compile(
      r"^"
      r"([0-9A-F]{4,6})"  # first character code
      r"(?:\.\.([0-9A-F]{4,6}))?"  # optional second character code
      r"\s*;\s*"
      r"([^#]+)")  # the data, up until the potential comment
  for line in input_data.split("\n"):
    match = line_regex.match(line)
    if not match:
      continue

    first, last, data = match.groups()
    if last is None:
      last = first

    first = int(first, 16)
    last = int(last, 16)
    data = data.rstrip()

    ranges.append((first, last, data))

  return ranges


def _parse_semicolon_separated_data(input_data):
  """Reads semicolon-separated Unicode data from an input string.

  Reads a Unicode data file already imported into a string. The format is
  the Unicode data file format with a list of values separated by
  semicolons. The number of the values on different lines may be different
  from another.

  Example source data file:
    http://www.unicode.org/Public/UNIDATA/PropertyValueAliases.txt

  Example data:
    sc;  Cher  ; Cherokee
    sc;  Copt  ; Coptic   ; Qaac

  Args:
    input_data: An input string, containing the data.

  Returns:
    A list of lists corresponding to the input data, with each individual
    list containing the values as strings. For example:
    [['sc', 'Cher', 'Cherokee'], ['sc', 'Copt', 'Coptic', 'Qaac']]
  """
  all_data = []
  for line in input_data.split('\n'):
    line = line.split('#', 1)[0].strip()  # remove the comment
    if not line:
      continue

    fields = line.split(';')
    fields = [field.strip() for field in fields]
    all_data.append(fields)

  return all_data


def _load_unicode_data_txt():
  """Load character data from UnicodeData.txt."""
  global _defined_characters
  global _bidi_mirroring_characters
  if _defined_characters:
    return

  with open_unicode_data_file("UnicodeData.txt") as unicode_data_txt:
    unicode_data = _parse_semicolon_separated_data(unicode_data_txt.read())

  for line in unicode_data:
    code = int(line[0], 16)
    char_name = line[1]
    general_category = line[2]
    combining_class = int(line[3])

    decomposition = line[5]
    if decomposition.startswith('<'):
        # We only care about canonical decompositions
        decomposition = ''
    decomposition = decomposition.split()
    decomposition = [unichr(int(char, 16)) for char in decomposition]
    decomposition = ''.join(decomposition)

    bidi_mirroring = (line[9] == 'Y')
    if general_category == 'Ll':
      upcode = line[12]
      if upcode:
        upper_case = int(upcode, 16)
        _lower_to_upper_case[code] = upper_case

    if char_name.endswith("First>"):
      last_range_opener = code
    elif char_name.endswith("Last>"):
      # Ignore surrogates
      if "Surrogate" not in char_name:
        for char in xrange(last_range_opener, code+1):
          _general_category_data[char] = general_category
          _combining_class_data[char] = combining_class
          if bidi_mirroring:
            _bidi_mirroring_characters.add(char)
          _defined_characters.add(char)
    else:
      _character_names_data[code] = char_name
      _general_category_data[code] = general_category
      _combining_class_data[code] = combining_class
      if bidi_mirroring:
        _bidi_mirroring_characters.add(code)
      _decomposition_data[code] = decomposition
      _defined_characters.add(code)

  _defined_characters = frozenset(_defined_characters)
  _bidi_mirroring_characters = frozenset(_bidi_mirroring_characters)


def _load_scripts_txt():
  """Load script property from Scripts.txt."""
  with open_unicode_data_file("Scripts.txt") as scripts_txt:
    script_ranges = _parse_code_ranges(scripts_txt.read())

  for first, last, script_name in script_ranges:
    folded_script_name = _folded_script_name(script_name)
    script = _folded_script_name_to_code[folded_script_name]
    for char_code in xrange(first, last+1):
      _script_data[char_code] = script


def _load_script_extensions_txt():
  """Load script property from ScriptExtensions.txt."""
  with open_unicode_data_file("ScriptExtensions.txt") as se_txt:
    script_extensions_ranges = _parse_code_ranges(se_txt.read())

  for first, last, script_names in script_extensions_ranges:
    script_set = frozenset(script_names.split(' '))
    for character_code in xrange(first, last+1):
      _script_extensions_data[character_code] = script_set


def _load_blocks_txt():
  """Load block name from Blocks.txt."""
  with open_unicode_data_file("Blocks.txt") as blocks_txt:
    block_ranges = _parse_code_ranges(blocks_txt.read())

  for first, last, block_name in block_ranges:
    _block_names.append(block_name)
    _block_range[block_name] = (first, last)
    for character_code in xrange(first, last + 1):
      _block_data[character_code] = block_name


def _load_derived_age_txt():
  """Load age property from DerivedAge.txt."""
  with open_unicode_data_file("DerivedAge.txt") as derived_age_txt:
    age_ranges = _parse_code_ranges(derived_age_txt.read())

  for first, last, char_age in age_ranges:
    for char_code in xrange(first, last+1):
      _age_data[char_code] = char_age


def _load_derived_core_properties_txt():
  """Load derived core properties from Blocks.txt."""
  with open_unicode_data_file("DerivedCoreProperties.txt") as dcp_txt:
    dcp_ranges = _parse_code_ranges(dcp_txt.read())

  for first, last, property_name in dcp_ranges:
    for character_code in xrange(first, last+1):
      try:
        _core_properties_data[property_name].add(character_code)
      except KeyError:
        _core_properties_data[property_name] = {character_code}


def _load_property_value_aliases_txt():
  """Load property value aliases from PropertyValueAliases.txt."""
  with open_unicode_data_file("PropertyValueAliases.txt") as pva_txt:
    aliases = _parse_semicolon_separated_data(pva_txt.read())

  for data_item in aliases:
    if data_item[0] == 'sc': # Script
      code = data_item[1]
      long_name = data_item[2]
      _script_code_to_long_name[code] = long_name.replace('_', ' ')
      folded_name = _folded_script_name(long_name)
      _folded_script_name_to_code[folded_name] = code


def _load_bidi_mirroring_txt():
  """Load bidi mirroring glyphs from BidiMirroring.txt."""

  with open_unicode_data_file("BidiMirroring.txt") as bidi_mirroring_txt:
    bmg_pairs = _parse_semicolon_separated_data(bidi_mirroring_txt.read())

  for char, bmg in bmg_pairs:
    char = int(char, 16)
    bmg = int(bmg, 16)
    _bidi_mirroring_glyph_data[char] = bmg


def _load_indic_data():
  """Load Indic properties from Indic(Positional|Syllabic)Category.txt."""
  with open_unicode_data_file("IndicPositionalCategory.txt") as inpc_txt:
    positional_ranges = _parse_code_ranges(inpc_txt.read())
  for first, last, char_position in positional_ranges:
    for char_code in xrange(first, last+1):
      _indic_positional_data[char_code] = char_position

  with open_unicode_data_file("IndicSyllabicCategory.txt") as insc_txt:
    syllabic_ranges = _parse_code_ranges(insc_txt.read())
  for first, last, char_syllabic_category in syllabic_ranges:
    for char_code in xrange(first, last+1):
      _indic_syllabic_data[char_code] = char_syllabic_category


def _load_emoji_data():
  """Parse the new draft format of emoji-data.txt"""
  global _presentation_default_emoji, _presentation_default_text
  global _emoji, _emoji_modifier_base

  if _presentation_default_emoji:
    return

  emoji_sets = {
      'Emoji': set(),
      'Emoji_Presentation': set(),
      'Emoji_Modifier': set(),
      'Emoji_Modifier_Base': set(),
      'Emoji_Regional_Indicator': set(),
      'Emoji_Component': set(),
  }

  set_names = '|'.join(sorted(emoji_sets.keys()))
  line_re = re.compile(
      r'([0-9A-F]{4,6})(?:\.\.([0-9A-F]{4,6}))?\s*;\s*'
      r'(%s)\s*#.*$' % set_names)

  with open_unicode_data_file('emoji-data.txt') as f:
    for line in f:
      line = line.strip()
      if not line or line[0] == '#':
          continue
      m = line_re.match(line)
      if not m:
          raise ValueError('Did not match "%s"' % line)
      start = int(m.group(1), 16)
      end = start if not m.group(2) else int(m.group(2), 16)
      emoji_set = emoji_sets.get(m.group(3))
      emoji_set.update(range(start, end + 1))

  _presentation_default_emoji = frozenset(
      emoji_sets['Emoji_Presentation'])
  _presentation_default_text = frozenset(
      emoji_sets['Emoji'] - emoji_sets['Emoji_Presentation'])
  _emoji_modifier_base = frozenset(
      emoji_sets['Emoji_Modifier_Base'])
  _emoji = frozenset(
      emoji_sets['Emoji'])

  # we have no real use for the 'Emoji_Regional_Indicator' and
  # 'Emoji_Component' sets, and they're not documented, so ignore them.
  # The regional indicator set is just the 26 regional indicator
  # symbols, and the component set is number sign, asterisk, ASCII digits,
  # the regional indicators, and the skin tone modifiers.


ZWJ = 0x200d
EMOJI_VS = 0xfe0f
EMOJI_SEQUENCE_TYPES = frozenset([
    'Emoji_Combining_Sequence',
    'Emoji_Flag_Sequence',
    'Emoji_Tag_Sequence',
    'Emoji_Modifier_Sequence',
    'Emoji_ZWJ_Sequence',
    'Emoji_Single_Sequence'])

def _read_emoji_data_file(filename):
  """Parse an emoji data file and return a map from sequence to tuples of
  name, age, type."""
  line_re = re.compile(
      r'([0-9A-F ]+);\s*(%s)\s*;\s*([^#]*)\s*#\s*(\d+\.\d+)\s.*' %
      '|'.join(EMOJI_SEQUENCE_TYPES))
  result = {}
  with open_unicode_data_file(filename) as f:
    for line in f:
      line = line.strip()
      if not line or line[0] == '#':
        continue
      m = line_re.match(line)
      if not m:
        raise ValueError('Did not match "%s" in %s' % (line, filename))
      # discourage lots of redundant copies of seq_type
      seq_type = intern(m.group(2).strip().encode('ascii'))
      seq = tuple(int(s, 16) for s in m.group(1).split())
      name = m.group(3).strip()
      age = float(m.group(4))
      result[seq] = (name, age, seq_type)
  return result


_EMOJI_QUAL_TYPES = ['fully-qualified', 'non-fully-qualified']

def _read_emoji_test_data(data_string):
  """Parse the emoji-test.txt data.  This has names of proposed emoji that are
  not yet in the full Unicode data file.  Returns a list of tuples of
  sequence, group, subgroup, name.

  The data is a string."""
  line_re = re.compile(
      r'([0-9a-fA-F ]+)\s*;\s*(%s)\s*#\s*(?:[^\s]+)\s+(.*)\s*' %
      '|'.join(_EMOJI_QUAL_TYPES)
  )
  result = []
  GROUP_PREFIX = '# group: '
  SUBGROUP_PREFIX = '# subgroup: '
  group = None
  subgroup = None
  for line in data_string.splitlines():
    line = line.strip()
    if not line:
      continue

    if line[0] == '#':
      if line.startswith(GROUP_PREFIX):
        group = line[len(GROUP_PREFIX):].strip().encode('ascii')
        subgroup = None
      elif line.startswith(SUBGROUP_PREFIX):
        subgroup = line[len(SUBGROUP_PREFIX):].strip().encode('ascii')
      continue

    m = line_re.match(line)
    if not m:
      raise ValueError('Did not match "%s" in emoji-test.txt' % line)
    if m.group(2) == _EMOJI_QUAL_TYPES[1]:
      # we only want fully-qualified sequences, as those are 'canonical'.
      # Information for the non-fully-qualified sequences should be
      # redundant.  At the moment we don't verify this so if the file
      # changes we won't catch that.
      continue
    seq = tuple(int(s, 16) for s in m.group(1).split())
    name = m.group(3).strip()
    if not (group and subgroup):
      raise Exception(
          'sequence %s missing group or subgroup' % seq_to_string(seq))
    result.append((seq, group, subgroup, name))

  return result

_SUPPLEMENTAL_EMOJI_GROUP_DATA = """
# group: Misc

# subgroup: used with keycaps
0023 fe0f ; fully-qualified # ? number sign
002a fe0f ; fully-qualified # ? asterisk
0030 fe0f ; fully-qualified # ? digit zero
0031 fe0f ; fully-qualified # ? digit one
0032 fe0f ; fully-qualified # ? digit two
0033 fe0f ; fully-qualified # ? digit three
0034 fe0f ; fully-qualified # ? digit four
0035 fe0f ; fully-qualified # ? digit five
0036 fe0f ; fully-qualified # ? digit six
0037 fe0f ; fully-qualified # ? digit seven
0038 fe0f ; fully-qualified # ? digit eight
0039 fe0f ; fully-qualified # ? digit nine
20e3 ; fully-qualified # ? combining enclosing keycap

# subgroup: skin-tone modifiers
1f3fb ; fully-qualified # ? emoji modifier fitzpatrick type-1-2
1f3fc ; fully-qualified # ? emoji modifier fitzpatrick type-3
1f3fd ; fully-qualified # ? emoji modifier fitzpatrick type-4
1f3fe ; fully-qualified # ? emoji modifier fitzpatrick type-5
1f3ff ; fully-qualified # ? emoji modifier fitzpatrick type-6

# subgroup: regional indicator symbols
1f1e6 ; fully-qualified # ? regional indicator symbol letter A
1f1e7 ; fully-qualified # ? regional indicator symbol letter B
1f1e8 ; fully-qualified # ? regional indicator symbol letter C
1f1e9 ; fully-qualified # ? regional indicator symbol letter D
1f1ea ; fully-qualified # ? regional indicator symbol letter E
1f1eb ; fully-qualified # ? regional indicator symbol letter F
1f1ec ; fully-qualified # ? regional indicator symbol letter G
1f1ed ; fully-qualified # ? regional indicator symbol letter H
1f1ee ; fully-qualified # ? regional indicator symbol letter I
1f1ef ; fully-qualified # ? regional indicator symbol letter J
1f1f0 ; fully-qualified # ? regional indicator symbol letter K
1f1f1 ; fully-qualified # ? regional indicator symbol letter L
1f1f2 ; fully-qualified # ? regional indicator symbol letter M
1f1f3 ; fully-qualified # ? regional indicator symbol letter N
1f1f4 ; fully-qualified # ? regional indicator symbol letter O
1f1f5 ; fully-qualified # ? regional indicator symbol letter P
1f1f6 ; fully-qualified # ? regional indicator symbol letter Q
1f1f7 ; fully-qualified # ? regional indicator symbol letter R
1f1f8 ; fully-qualified # ? regional indicator symbol letter S
1f1f9 ; fully-qualified # ? regional indicator symbol letter T
1f1fa ; fully-qualified # ? regional indicator symbol letter U
1f1fb ; fully-qualified # ? regional indicator symbol letter V
1f1fc ; fully-qualified # ? regional indicator symbol letter W
1f1fd ; fully-qualified # ? regional indicator symbol letter X
1f1fe ; fully-qualified # ? regional indicator symbol letter Y
1f1ff ; fully-qualified # ? regional indicator symbol letter Z

#subgroup: unknown flag
fe82b ; fully-qualified # ? unknown flag PUA codepoint
"""


def _load_emoji_group_data():
  global _emoji_group_data
  if _emoji_group_data:
    return

  _emoji_group_data = {}

  with open_unicode_data_file('emoji-test.txt') as f:
    text = f.read()
  group_list = _read_emoji_test_data(text)
  group_list.extend(_read_emoji_test_data(_SUPPLEMENTAL_EMOJI_GROUP_DATA))
  for i, (seq, group, subgroup, name) in enumerate(group_list):
    _emoji_group_data[seq] = (i, group, subgroup, name)

  assert len(group_list) == len(_emoji_group_data)


def get_emoji_group_data(seq):
  """Return group data for the canonical sequence seq, or None.
  Group data is a tuple of index, group, subgroup, and name.  The
  index is a unique global sort index for the sequence among all
  sequences in the group data."""
  _load_emoji_group_data()
  return _emoji_group_data.get(seq, None)


def get_emoji_groups():
  """Return the main emoji groups, in order."""
  _load_emoji_group_data()
  groups = []
  group = None
  for _, g, _, _ in sorted(_emoji_group_data.values()):
    if g != group:
      group = g
      groups.append(group)
  return groups


def get_emoji_subgroups(group):
  """Return the subgroups of this group, in order, or None
  if the group is not recognized."""
  _load_emoji_group_data()
  subgroups = []
  subgroup = None
  for _, g, sg, _ in sorted(_emoji_group_data.values()):
    if g == group:
      if sg != subgroup:
        subgroup = sg
        subgroups.append(subgroup)
  return subgroups if subgroups else None


def get_emoji_in_group(group, subgroup=None):
  """Return the sorted list of the emoji sequences in the group (limiting to
  subgroup if subgroup is not None).  Returns None if group does not
  exist, and an empty list if subgroup does not exist in group."""
  _load_emoji_group_data()
  result = None
  for seq, (index, g, sg, _) in _emoji_group_data.iteritems():
    if g == group:
      if result == None:
        result = []
      if subgroup and sg != subgroup:
        continue
      result.append(seq)
  result.sort(key=lambda s: _emoji_group_data[s][0])
  return result


def get_sorted_emoji_sequences(seqs):
  """Seqs is a collection of canonical emoji sequences.  Returns a list of
  these sequences in the canonical emoji group order.  Sequences that are not
  canonical are placed at the end, in unicode code point order.
  """
  _load_emoji_group_data()
  return sorted(seqs, key=lambda s: (_emoji_group_data.get(s, 100000), s))


def _load_emoji_sequence_data():
  """Ensure the emoji sequence data is initialized."""
  global _emoji_sequence_data, _emoji_non_vs_to_canonical

  if _emoji_sequence_data is not None:
    return

  _emoji_sequence_data = {}
  _emoji_non_vs_to_canonical = {}

  for datafile in ['emoji-zwj-sequences.txt', 'emoji-sequences.txt']:
    data = _read_emoji_data_file(datafile)
    for k, t in data.iteritems():
      if k in _emoji_sequence_data:
        print 'already have data for sequence:', seq_to_string(k), t
      _emoji_sequence_data[k] = t
      if EMOJI_VS in k:
        _emoji_non_vs_to_canonical[strip_emoji_vs(k)] = k

  _load_unicode_data_txt()  # ensure character_names_data is populated
  _load_emoji_data()  # ensure presentation_default_text is populated
  _load_emoji_group_data()  # ensure group data is populated

  # Get names for single emoji from the test data. We will prefer these over
  # those in UnicodeData (e.g. prefer "one o'clock" to "clock face one oclock"),
  # and if they're not in UnicodeData these are proposed new emoji.
  for seq, (_, _, _, emoji_name) in _emoji_group_data.iteritems():
    non_vs_seq = strip_emoji_vs(seq)
    if len(non_vs_seq) > 1:
      continue

    cp = non_vs_seq[0]

    # If it's not in character names data, it's a proposed emoji.
    if cp not in _character_names_data:
      # use 'ignore' to strip curly quotes etc if they exist, unicode
      # character names are ASCII, and it's probably best to keep it that way.
      cp_name = emoji_name.encode('ascii', 'ignore').upper()
      _character_names_data[cp] = cp_name

    is_default_text_presentation = cp in _presentation_default_text
    if is_default_text_presentation:
      seq = (cp, EMOJI_VS)

    current_data = _emoji_sequence_data.get(seq) or (
        emoji_name, 10.0, 'Emoji_Single_Sequence')

    current_version = current_data[1] or 10.0
    if is_default_text_presentation:
      emoji_name = '(emoji) ' + emoji_name

    _emoji_sequence_data[seq] = (emoji_name, current_version, current_data[2])

  # Fill in sequences of single emoji, handling non-canonical to canonical also.
  for k in _emoji:
    non_vs_seq = (k,)

    is_default_text_presentation = k in _presentation_default_text
    if is_default_text_presentation:
      canonical_seq = (k, EMOJI_VS)
      _emoji_non_vs_to_canonical[non_vs_seq] = canonical_seq
    else:
      canonical_seq = non_vs_seq

    if canonical_seq in _emoji_sequence_data:
      # Prefer names we have where they exist
      emoji_name, emoji_age, seq_type = _emoji_sequence_data[canonical_seq]
    else:
      emoji_name = name(k, 'unnamed').lower()
      if name == 'unnamed':
        continue
      emoji_age = age(k)
      seq_type = 'Emoji_Single_Sequence'

    if is_default_text_presentation and not emoji_name.startswith('(emoji) '):
      emoji_name = '(emoji) ' + emoji_name
    _emoji_sequence_data[canonical_seq] = (emoji_name, emoji_age, seq_type)


def get_emoji_sequences(age=None, types=None):
  """Return the set of canonical emoji sequences, filtering to those <= age
  if age is not None, and those with type in types (if not a string) or
  type == types (if type is a string) if types is not None.  By default
  all sequences are returned, including those for single emoji."""
  _load_emoji_sequence_data()

  result = _emoji_sequence_data.keys()
  if types is not None:
    if isinstance(types, basestring):
      types = frozenset([types])
    result = [k for k in result if _emoji_sequence_data[k][1] in types]
  if age is not None:
    age = float(age)
    result = [k for k in result if _emoji_sequence_data[k][0] <= age]
  return result


def get_emoji_sequence_data(seq):
  """Return a tuple of the name, age, and type for the (possibly non-canonical)
  sequence, or None if not recognized as a sequence."""
  _load_emoji_sequence_data()

  seq = get_canonical_emoji_sequence(seq)
  if not seq or seq not in _emoji_sequence_data:
    return None
  return _emoji_sequence_data[seq]


def get_emoji_sequence_name(seq):
  """Return the name of the (possibly non-canonical)  sequence, or None if
  not recognized as a sequence."""
  data = get_emoji_sequence_data(seq)
  return None if not data else data[0]


def get_emoji_sequence_age(seq):
  """Return the age of the (possibly non-canonical)  sequence, or None if
  not recognized as a sequence.  Proposed sequences have 1000.0 as the age."""
  # floats are a pain since the actual values are decimal.  maybe use
  # strings to represent age.
  data = get_emoji_sequence_data(seq)
  return None if not data else data[1]


def get_emoji_sequence_type(seq):
  """Return the type of the (possibly non-canonical)  sequence, or None if
  not recognized as a sequence.  Types are in EMOJI_SEQUENCE_TYPES."""
  data = get_emoji_sequence_data(seq)
  return None if not data else data[2]


def is_canonical_emoji_sequence(seq):
  """Return true if this is a canonical emoji sequence (has 'vs' where Unicode
  says it should), and is known."""
  _load_emoji_sequence_data()
  return seq in _emoji_sequence_data


def get_canonical_emoji_sequence(seq):
  """Return the canonical version of this emoji sequence if the sequence is
  known, or None."""
  if is_canonical_emoji_sequence(seq):
    return seq
  seq = strip_emoji_vs(seq)
  return _emoji_non_vs_to_canonical.get(seq, None)


def strip_emoji_vs(seq):
  """Return a version of this emoji sequence with emoji variation selectors
  stripped. This is the 'non-canonical' version used by the color emoji font,
  which doesn't care how the sequence is represented in text."""
  if EMOJI_VS in seq:
    return tuple([cp for cp in seq if cp != EMOJI_VS])
  return seq


def seq_to_string(seq):
  """Return a string representation of the codepoint sequence."""
  return '_'.join('%04x' % cp for cp in seq)


def string_to_seq(seq_str):
  """Return a codepoint sequence (tuple) given its string representation."""
  return tuple([int(s, 16) for s in seq_str.split('_')])


def is_regional_indicator(cp):
  return 0x1f1e6 <= cp <= 0x1f1ff


def regional_indicator_to_ascii(cp):
  assert is_regional_indicator(cp)
  return chr(cp - 0x1f1e6 + ord('A'))


def is_tag(cp):
  return 0xe0020 < cp < 0xe0080 or cp == 0xe0001


def tag_character_to_ascii(cp):
  assert is_tag(cp)
  if cp == 0xe0001:
    return '[begin]'
  if cp == 0xe007f:
    return '[end]'
  return chr(cp - 0xe0000)


def is_skintone_modifier(cp):
  return 0x1f3fb <= cp <= 0x1f3ff


def get_presentation_default_emoji():
  _load_emoji_data()
  return _presentation_default_emoji


def get_presentation_default_text():
  _load_emoji_data()
  return _presentation_default_text


def get_emoji():
  _load_emoji_data()
  return _emoji


def is_emoji(cp):
  _load_emoji_data()
  return cp in _emoji


def is_emoji_modifier_base(cp):
  _load_emoji_data()
  return cp in _emoji_modifier_base


def _load_unicode_emoji_variants():
  """Parse StandardizedVariants.txt and initialize a set of characters
  that have a defined emoji variant presentation.  All such characters
  also have a text variant presentation so a single set works for both."""

  global _emoji_variants, _emoji_variants_proposed
  if _emoji_variants:
    return

  emoji_variants = set()
  line_re = re.compile(r'([0-9A-F]{4,6})\s+FE0F\s*;\s*emoji style\s*;')
  with open_unicode_data_file('StandardizedVariants.txt') as f:
    for line in f:
      m = line_re.match(line)
      if m:
        emoji_variants.add(int(m.group(1), 16))

  # temporarily hard-code in some post-9.0 proposed exceptions used
  # in gendered emoji sequences
  emoji_variants.union(set([0x2640, 0x2642, 0x2695]))

  _emoji_variants = frozenset(emoji_variants)

  with open_unicode_data_file('proposed-variants.txt') as f:
    for line in f:
      m = line_re.match(line)
      if m:
        emoji_variants.add(int(m.group(1), 16))
  _emoji_variants_proposed = frozenset(emoji_variants)


def get_unicode_emoji_variants(include_proposed='proposed'):
  """Returns the emoji characters that have both emoji and text presentations.
  If include_proposed is 'proposed', include the ones proposed in 2016/08.  If
  include_proposed is 'proposed_extra', also include the emoji Noto proposes
  for text presentation treatment to align related characters.  Else
  include_proposed should resolve to boolean False."""
  _load_unicode_emoji_variants()
  if not include_proposed:
    return _emoji_variants
  elif include_proposed == 'proposed':
    return _emoji_variants_proposed
  elif include_proposed == 'proposed_extra':
    extra = tool_utils.parse_int_ranges(
        '1f4b9 1f4c8-1f4ca 1f507 1f509-1f50a 1f44c')
    return _emoji_variants_proposed | extra
  else:
    raise Exception(
        "include_proposed is %s which is not in ['proposed', 'proposed_extra']"
        % include_proposed)


def _load_variant_data():
  """Parse StandardizedVariants.txt and initialize all non-emoji variant
  data.  The data is a mapping from codepoint to a list of tuples of:
  - variant selector
  - compatibility character (-1 if there is none)
  - shaping context (bitmask, 1 2 4 8 for isolate initial medial final)
  The compatibility character is for cjk mappings that map to 'the same'
  glyph as another CJK character."""

  global _variant_data, _variant_data_cps
  if _variant_data:
    return

  compatibility_re = re.compile(
      r'\s*CJK COMPATIBILITY IDEOGRAPH-([0-9A-Fa-f]+)')
  variants = collections.defaultdict(list)
  with open_unicode_data_file('StandardizedVariants.txt') as f:
    for line in f:
      x = line.find('#')
      if x >= 0:
        line = line[:x]
      line = line.strip()
      if not line:
        continue

      tokens = line.split(';');
      cp, var = tokens[0].split(' ')
      cp = int(cp, 16)
      varval = int(var, 16)
      if varval in [0xfe0e, 0xfe0f]:
        continue  # ignore emoji variants
      m = compatibility_re.match(tokens[1].strip())
      compat = int(m.group(1), 16) if m else -1
      context = 0
      if tokens[2]:
        ctx = tokens[2]
        if ctx.find('isolate') != -1:
          context += 1
        if ctx.find('initial') != -1:
          context += 2
        if ctx.find('medial') != -1:
          context += 4
        if ctx.find('final') != -1:
          context += 8
      variants[cp].append((varval, compat, context))

  _variant_data_cps = frozenset(variants.keys())
  _variant_data = variants


def has_variant_data(cp):
  _load_variant_data()
  return cp in _variant_data


def get_variant_data(cp):
  _load_variant_data()
  return _variant_data[cp][:] if cp in _variant_data else None


def variant_data_cps():
  _load_variant_data()
  return _variant_data_cps

# proposed emoji

def _load_proposed_emoji_data():
  """Parse proposed-emoji-10.txt to get cps/names of proposed emoji that are not
  yet approved for Unicode 10."""

  global _proposed_emoji_data, _proposed_emoji_data_cps
  if _proposed_emoji_data:
    return

  _proposed_emoji_data = {}
  line_re = re.compile(
      r'^U\+([a-zA-z0-9]{4,5})\s.*\s\d{4}Q\d\s+(.*)$')
  with open_unicode_data_file('proposed-emoji-10.txt') as f:
    for line in f:
      line = line.strip()
      if not line or line[0] == '#' or line.startswith(u'\u2022'):
        continue

      m = line_re.match(line)
      if not m:
        raise ValueError('did not match "%s"' % line)
      cp = int(m.group(1), 16)
      name = m.group(2)
      if cp in _proposed_emoji_data:
        raise ValueError('duplicate emoji %x, old name: %s, new name: %s' % (
            cp, _proposed_emoji_data[cp], name))

      _proposed_emoji_data[cp] = name
  _proposed_emoji_data_cps = frozenset(_proposed_emoji_data.keys())


def proposed_emoji_name(cp):
  _load_proposed_emoji_data()
  return _proposed_emoji_data.get(cp, '')


def proposed_emoji_cps():
  _load_proposed_emoji_data()
  return _proposed_emoji_data_cps


def is_proposed_emoji(cp):
  _load_proposed_emoji_data()
  return cp in _proposed_emoji_data_cps


def read_codeset(text):
  line_re = re.compile(r'^0x([0-9a-fA-F]{2,6})\s+0x([0-9a-fA-F]{4,6})\s+.*')
  codeset = set()
  for line in text.splitlines():
    m = line_re.match(line)
    if m:
      cp = int(m.group(2), 16)
      codeset.add(cp)
  return codeset


def codeset(cpname):
  """Return a set of the unicode codepoints in the code page named cpname, or
  None."""
  filename = ('%s.txt' % cpname).upper()
  filepath = path.join(
      path.dirname(__file__), os.pardir, 'third_party', 'unicode',
      filename)
  if not path.isfile(filepath):
    return None
  with open(filepath, 'r') as f:
    return read_codeset(f.read())


def _dump_emoji_presentation():
  """Dump presentation info, for testing."""

  text_p = 0
  emoji_p = 0
  for cp in sorted(get_emoji()):
    cp_name = name(cp, '<error>')
    if cp in get_presentation_default_emoji():
      presentation = 'emoji'
      emoji_p += 1
    elif cp in get_presentation_default_text():
      presentation = 'text'
      text_p += 1
    else:
      presentation = '<error>'
    print '%s%04x %5s %s' % (
        ' ' if cp < 0x10000 else '', cp, presentation, cp_name)
  print '%d total emoji, %d text presentation, %d emoji presentation' % (
      len(get_emoji()), text_p, emoji_p)


def _load_nameslist_data():
  global _nameslist_see_also
  if _nameslist_see_also is not None:
    return

  _nameslist_see_also = collections.defaultdict(set)
  cp = None
  line_re = re.compile(r'^(?:(?:([0-9A-F]{4,6})\t.*)|(?:^\s+([x=])\s+(.*)))$')
  see_also_re = re.compile(
      r'\s*(?:\(.*\s-\s+([0-9A-F]{4,6})\))|([0-9A-F]{4,6})')
  with open_unicode_data_file('NamesList.txt') as f:
    for line in f:
      m = line_re.match(line)
      if not m:
        continue
      if m.group(1):
        cp = int(m.group(1), 16)
      else:
        rel = m.group(2).strip()
        val = m.group(3).strip()
        if rel != 'x':
          continue
        m = see_also_re.match(val)
        if not m:
          raise Exception(
              'could not match see also val "%s" in line "%s"' % (val, line))
        ref_cp = int(m.group(1) or m.group(2), 16)
        _nameslist_see_also[cp].add(ref_cp)


def see_also(cp):
  _load_nameslist_data()
  return frozenset(_nameslist_see_also.get(cp))


def _load_namealiases_data():
  global _namealiases_alt_names
  if _namealiases_alt_names is not None:
    return

  _namealiases_alt_names = collections.defaultdict(list)
  line_re = re.compile(r'([0-9A-F]{4,6});([^;]+);(.*)$')
  with open_unicode_data_file('NameAliases.txt') as f:
    for line in f:
      m = line_re.match(line)
      if not m:
        continue
      cp = int(m.group(1), 16)
      name = m.group(2).strip()
      name_type = m.group(3).strip()
      if not name_type in [
          'correction', 'control', 'alternate', 'figment', 'abbreviation']:
        raise Exception('unknown name type in "%s"' % line)
      if name_type == 'figment':
        continue
      _namealiases_alt_names[cp].append((name, name_type))


def alt_names(cp):
  """Return list of name, nametype tuples for cp, or None."""
  _load_namealiases_data()
  return tuple(_namealiases_alt_names.get(cp))


if __name__ == '__main__':
  for k in sorted(get_emoji_sequences()):
    if not get_emoji_group_data(k):
      print 'no data:', seq_to_string(k)

  for group in get_emoji_groups():
    print 'group:', group
    for subgroup in get_emoji_subgroups(group):
      print '  subgroup:', subgroup
      print '    %d items' % len(get_emoji_in_group(group, subgroup))
