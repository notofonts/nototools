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

"""Represents an ordering of emoji strings, broken into categories and
subcategories.  Emoji strings are sequences of emoji and related characters
defined by Unicode, for example flags from pairs of regional indicator symbols,
varieties of families and couples, emoji with skin tone variants, and
standalone emoji.  API is provided to return the categories and subcategories,
the emoji strings in them, and the category, subcategory tuple for an emoji
string.

Functions are provided to parse two kinds of source data files.

.csv file:
This has three columns: Category name, emoji-strings separated by space, and
subcategory name.  The first row, headers, starts with a # and is ignored.

emojiOrdering.txt file:
This data is a bit raw, so gets validated during processing.
For an example see the unicodetools svn repo, i.e.
http://www.unicode.org/utility/trac/browser/trunk/unicodetools/data/emoji/3.0/source/emojiOrdering.txt"""

import argparse
import codecs
import collections
from itertools import chain
from os import path
import re
import sys

def _generate_emoji_to_cat_tuple(category_odict):
    """category_odict is an ordered dict of categories to ordered dict of
    subcategories to lists of emoji sequences.  Returns a mapping from
    emoji sequence to a tuple of category, subcategory."""
    result = {}
    for cat, subcat_odict in category_odict.items():
      for subcat, emoji_sequences in subcat_odict.items():
        for emoji_sequence in emoji_sequences:
          result[emoji_sequence] = (cat, subcat)
    return result


class EmojiOrdering(object):
  def __init__(self, category_odict):
    """category_odict is an ordered dict of categories to ordered dict of
    subcategories to lists of emoji sequences. Since they're ordered we have
    a total ordering of all the emoji sequences."""
    self._category_odict = category_odict
    self._emoji_to_cat_tuple = None

  def category_names(self):
    """Returns the names of the categories."""
    return self._category_odict.keys()

  def subcategory_names(self, category_name):
    """Returns None if category_name is not recognized."""
    subcat_odict = self._category_odict.get(category_name)
    return subcat_odict.keys() if subcat_odict else None

  def emoji_in_category(self, category_name, subcategory_name=None):
    cat_odict = self._category_odict.get(category_name)
    if not cat_odict:
      return None
    if subcategory_name:
      return cat_odict.get(subcategory_name)
    return [i for i in chain.from_iterable(cat_odict.values())]

  def emoji_to_category(self, emoji_string):
    """Emoji_string is an emoji sequence, returns a tuple of
    category, subcategory if present, else None."""
    return self._get_emoji_to_cat_tuple().get(emoji_string, None)

  def emoji_strings(self):
    return self._get_emoji_to_cat_tuple().keys()

  def _get_emoji_to_cat_tuple(self):
    if not self._emoji_to_cat_tuple:
      self._emoji_to_cat_tuple = _generate_emoji_to_cat_tuple(
        self._category_odict)
    return self._emoji_to_cat_tuple


def from_file(fname):
  """Return an EmojiOrdering from the .csv or emojiOrdering file."""
  _, ext = path.splitext(fname)
  with codecs.open(fname, 'r', 'utf-8') as f:
    text = f.read()
  if ext == '.csv':
    odict = _category_odict_from_csv(text)
  else:
    odict = _category_odict_from_eo(text)
  return EmojiOrdering(odict)


def _category_odict_from_csv(text):
  text_lines = text.splitlines()
  result = collections.OrderedDict()
  category_name = None
  category_data = None
  for line in text_lines:
    line = line.strip()
    if not line or line[0] == '#':
      continue
    category, estrs, subcategory = line.split(',')
    if category != category_name:
      if category_name:
        result[category_name] = category_data
      category_name = category
      category_data = collections.OrderedDict()
    category_data[subcategory] = tuple(estrs.split())
  result[category_name] = category_data
  return result


# set to true to log parsing of file
DEBUG_LOAD_EMOJI = False
def _category_odict_from_eo(text):
  text_lines = text.splitlines()
  line_re = re.compile(r'^([a-z-]+)\s+(.+)$')
  category = None
  subcategory = None
  result = collections.OrderedDict()
  category_data = None  # an odict from category to a tuple of emoji_strings
  subcategory_data = None  # a list of emoji_strings

  def finish_subcategory():
    if not subcategory:
      return
    if DEBUG_LOAD_EMOJI:
      print 'finish subcategory %s' % subcategory
    if subcategory_data:
      category_data[subcategory] = tuple(subcategory_data)
    else:
      print >> sys.stderr, 'ERROR no subcategory data'

  def finish_category():
    if not category:
      return
    finish_subcategory()
    if DEBUG_LOAD_EMOJI:
      print 'finish category %s' % category
    if category_data:
      result[category] = category_data
    else:
      print >> sys.stderr, 'ERROR no category data'

  COMBINING_KEYCAPS = 0x20E3
  EMOJI_VARSEL = 0xFE0F
  ZWJ = 0x200D
  REG_INDICATOR_START = 0x1F1E6
  REG_INDICATOR_END = 0x1F1FF
  FITZ_START = 0x1F3FB
  FITZ_END = 0x1F3FF

  def emoji_strs(line):
    strs = []

    def add(str, start, limit):
      s = str[start:limit]
      if DEBUG_LOAD_EMOJI:
        print 'adding', '_'.join('%04x' % ord(cp) for cp in s)
      strs.append(s)

    for s in line.split():
      limit = len(s)
      if limit == 1:
        strs.append(s)
        continue
      if DEBUG_LOAD_EMOJI:
        print 'splitting %s' % ('_'.join('%04x' % ord(cp) for cp in s))
      start = 0
      break_on_non_special = False
      have_reg_indicator = False
      for i in range(limit):
        cp = ord(s[i])
        if cp == COMBINING_KEYCAPS:
          if i == start:
            print >> sys.stderr, 'error, combining keycaps with no base'
          add(s, start, i+1)
          start = i + 1
          continue
        if cp == EMOJI_VARSEL:
          if i == start:
            print >> sys.stderr, 'error, varsel with no base'
            add(s, start, i + 1)
            start = i + 1
          continue
        if cp == ZWJ:
          if i == start:
            print >> sys.stderr, 'error, ZWJ with no lhs'
            start = i + 1
          else:
            break_on_non_special = False
          continue
        if FITZ_START <= cp <= FITZ_END:
          if i == start:
            print >> sys.stderr, 'error, fitzpatrick modifier with no base'
            add(s, start, i + 1)
            start = i + 1
          else:
            continue
        if REG_INDICATOR_START <= cp <= REG_INDICATOR_END:
          if have_reg_indicator:
            add(s, start, i + 1)
            start = i + 1
            have_reg_indicator = False
          else:
            have_reg_indicator = True
          continue
        if break_on_non_special:
          add(s, start, i)
          start = i
        else:
          break_on_non_special = True
      if start < limit:
        add(s, start, limit)
    return strs

  for line in text_lines:
    line = line.strip()
    if not line or line[0] == '#':
      continue
    if line[0] == '@':
      finish_category()
      subcategory_data = []
      category_data = collections.OrderedDict()
      subcategory = None
      category = line[1:].replace('_', ' ')
      if DEBUG_LOAD_EMOJI:
        print 'start category %s' % category
      continue
    m = line_re.match(line)
    if m:
      finish_subcategory()
      subcategory = m.group(1)
      subcategory_data = emoji_strs(m.group(2))
      if DEBUG_LOAD_EMOJI:
        print 'start subcategory %s (%d)' % (subcategory, len(subcategory_data))
    else:
      subcategory_data.extend(emoji_strs(line))
      if DEBUG_LOAD_EMOJI:
        print '...', len(subcategory_data)

  finish_category()
  return result


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-f', '--file', help='emoji ordering data file',
      metavar='fname', required=True)
  args = parser.parse_args()
  eo = from_file(args.file)
  for category in eo.category_names():
    print category
    for subcategory in eo.subcategory_names(category):
      print ' ', subcategory
      for estr in eo.emoji_in_category(category, subcategory):
        print '   ', '_'.join('%04x' % ord(cp) for cp in estr)


if __name__ == '__main__':
  main()
