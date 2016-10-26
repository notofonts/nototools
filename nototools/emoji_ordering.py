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

Functions are provided to parse three kinds of source data files.

.csv file:
This has three columns: Category name, emoji-strings separated by space, and
subcategory name.  The first row, headers, starts with a # and is ignored.

emojiOrdering.txt file:
This data is a bit raw, so gets validated during processing.
For an example see the unicodetools svn repo, i.e.
http://www.unicode.org/utility/trac/browser/trunk/unicodetools
at data/emoji/3.0/source/emojiOrdering.txt

.html file
This data comes from unicode, e.g.
http://unicode.org/emoji/charts-beta/emoji-ordering.html
Note, this html file closes the table tags and the parser relies on this.
"""

import argparse
import codecs
import collections
from HTMLParser import HTMLParser
from itertools import chain
import os
from os import path
import re
import sys

from nototools import unicode_data

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


def _strip_varsels(odict):
  """Remove fe0f from sequences in odict."""
  for cat, d in odict.items():
    for subcat, elist in d.items():
      d[subcat] = [s.replace(u'\ufe0f', '') for s in elist]


def from_file(fname, ext=None, sep=None, strip_varsel=False):
  """Return an EmojiOrdering from the .csv or emojiOrdering file."""
  _, fext = path.splitext(fname)
  if not ext:
    ext = fext[1:]
  with codecs.open(fname, 'r', 'utf-8') as f:
    text = f.read()
  if ext == 'csv':
    odict = _category_odict_from_csv(text, sep or ',')
  elif ext == 'html':
    odict = _category_odict_from_html(text)
  else:
    odict = _category_odict_from_eo(text)
  if strip_varsel:
    _strip_varsels(odict)
  return EmojiOrdering(odict)


def _category_odict_from_csv(text, sep=','):
  print 'processing csv file'
  text_lines = text.splitlines()
  result = collections.OrderedDict()
  category_name = None
  category_data = None
  for line in text_lines:
    line = line.strip()
    if not line or line[0] == '#':
      continue
    category, subcategory, count, estrs = line.split(sep)
    category = category.strip()
    subcategory = subcategory.strip()
    if category != category_name:
      if category_name:
        result[category_name] = category_data
      category_name = category
      category_data = collections.OrderedDict()
    data = tuple(estrs.split())
    if len(data) != int(count):
      print '### expected %d emoji in %s/%s but got %d' % (
          int(count), category, subcategory, len(data))
    category_data[subcategory] = data

  result[category_name] = category_data
  return result


# set to true to log parsing of file
DEBUG_LOAD_EMOJI = False
def _category_odict_from_eo(text):
  print 'processing eo file'

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


_keep_varsel_estrs = frozenset([
    u'\U0001f468\u200d\u2764\ufe0f\u200d\U0001f48b\u200d\U0001f468',
    u'\U0001f469\u200d\u2764\ufe0f\u200d\U0001f48b\u200d\U0001f469',
    u'\U0001f468\u200d\u2764\ufe0f\u200d\U0001f468',
    u'\U0001f469\u200d\u2764\ufe0f\u200d\U0001f469'])


def _fix_estrs(estrs):
  """Add fitzpatrick colors, and remove emoji variation selectors.

  1) The emoji ordering html page omits the skin color variants, because
  reasons. Since we want to display them, we have to add them.  However,
  we don't add them for sequences with multiple people.

  2) Currently we don't include emoji variation selectors in our sequences
  except after heavy black heart (and we probably don't need them there
  either).  The font will work fine without them, but some systems doing
  fallback might break the sequences apart if the variation selectors are
  not present in text.  So they should be there in the text, and not there
  in the font.  Anyway, while we clean this up, we currently strip them
  except for the four cases where we retain them for legacy reasons.
  """

  new_estrs = []
  for estr in estrs:
    if estr in _keep_varsel_estrs:
      nestr = estr
    else:
      if u'\u2764' in estr:
        print '# oops', u''.join('\\u%04x' % ord(cp) for cp in estr)
      nestr = u''.join(cp for cp in estr if cp != u'\ufe0f')
    new_estrs.append(nestr)
    num_bases = sum(unicode_data.is_emoji_modifier_base(ord(cp)) for cp in estr)
    if num_bases != 1:
      continue

    split_before = len(nestr)
    for i, cp in enumerate(nestr):
      if unicode_data.is_emoji_modifier_base(ord(cp)):
        split_before = i + 1
        break
    prefix = nestr[:split_before]
    suffix = nestr[split_before:]
    for cp in range(0x1f3fb, 0x1f3ff + 1):
      new_estrs.append(u''.join([prefix, unichr(cp), suffix]))
  return new_estrs


def _category_odict_from_html(text):
  """Build by scraping the emoji ordering html page.  This leverages the
  fact that all tr, td, th tags have closing tags (currently, at least)."""

  class odict_builder(HTMLParser):
    def __init__(self):
      HTMLParser.__init__(self)
      self.in_table = False
      self.in_category = False
      self.is_subcat = False
      self.text = []
      self.estrs = []
      self.d = collections.OrderedDict()
      self.cat = None
      self.subcat = None

    def handle_starttag(self, tag, attrs):
      if not self.in_table:
        if tag == 'table':
          self.in_table = True
      elif tag == 'th':
        self.in_category = True
        self.is_subcat = True
        if attrs:
          for k, v in attrs:
            if k == 'class' and v == u'bighead':
              self.is_subcat = False
              break
      elif tag == 'img':
        if attrs:
          for k, v in attrs:
            if k == 'alt':
              self.estrs.append(v)
      elif tag == 'tr':
        # currently, all th, tr have closing tags
        assert not self.estrs

    def handle_endtag(self, tag):
      if not self.in_table:
        return
      if self.estrs and tag == 'tr':
        self.d[self.cat][self.subcat] = _fix_estrs(self.estrs)
        self.estrs = []
      elif tag == 'th':
        text = ' '.join(self.text)
        text = text.encode('utf-8')
        self.text = []
        if self.is_subcat:
          self.subcat = text
        else:
          self.cat = text
          self.d[self.cat] = collections.OrderedDict()
        self.in_category = False
      elif tag == 'table':
        self.in_table = False
        return

    def handle_data(self, data):
      if self.in_category:
        data = data.strip()
        if data:
          self.text.append(data)

  b = odict_builder()
  b.feed(text)
  return b.d


def _name_to_str(emoji_name):
  return u''.join(unichr(int(n, 16)) for n in emoji_name.split('_'))


def _str_to_name(emoji_str):
  return '_'.join('%04x' % ord(cp) for cp in emoji_str)


def _compare_with_dir(eo, dirname):
  # problem here is we omit fe0f in our emoji image names, but the category data
  # doesn't.

  def name_to_tuple(name):
    return tuple(int(n, 16) for n in name.split('_'))

  names = set()
  missing_names = set()
  prefix = 'emoji_u'
  prefix_len = len(prefix)
  emoji_names = set()
  for f in sorted(os.listdir(dirname)):
    basename, ext = path.splitext(f)
    if ext != '.png':
      continue
    if not basename.startswith(prefix):
      print 'skipping %s' % f
      continue
    emoji_name = basename[prefix_len:]
    emoji_names.add(emoji_name)

    if not eo.emoji_to_category(_name_to_str(emoji_name)):
      missing_names.add(emoji_name)

  if missing_names:
    print 'missing %d names' % len(missing_names)
    for name in sorted(missing_names, key=name_to_tuple):
      print '  %s' % name
    print

  category_count = 0
  for category_name in eo.category_names():
    for subcategory_name in eo.subcategory_names(category_name):
      category_set = set(
          _str_to_name(s) for s in
          eo.emoji_in_category(category_name, subcategory_name))
      category_count += len(category_set)
      category_set -= emoji_names
      if category_set:
        print '%s/%s is missing %d items:' % (
            category_name, subcategory_name, len(category_set))
        for n in sorted(category_set, key=lambda n: name_to_tuple(n)):
          print '  %s' % n

  print '%4d emoji in category set' % category_count
  print '%4d emoji in directory %s' % (len(emoji_names), dirname)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-f', '--file', help='emoji ordering data file',
      metavar='fname', required=True)
  parser.add_argument(
      '--ext', help='treat file as having extension ext',
      metavar='ext')
  parser.add_argument(
      '--sep', help='separator for csv file', default=',',
      metavar='sep')
  parser.add_argument(
      '--cmpdir', help='directory of images to compare against',
      metavar='dir')
  parser.add_argument(
      '--dump', help='dump category lists even if we\'re comparing',
      action='store_true')

  args = parser.parse_args()
  eo = from_file(
      args.file, ext=args.ext, sep=args.sep,
      strip_varsel=args.cmpdir is not None)

  if not args.cmpdir or args.dump:
    print 'dumping category info'
    for category in eo.category_names():
      print category
      for subcategory in eo.subcategory_names(category):
        print ' ', subcategory
        for estr in eo.emoji_in_category(category, subcategory):
          print '   ', '_'.join('%04x' % ord(cp) for cp in estr)

  if args.cmpdir:
    _compare_with_dir(eo, args.cmpdir)


if __name__ == '__main__':
  main()
