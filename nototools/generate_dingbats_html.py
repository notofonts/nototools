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

import argparse
import codecs
import collections
import re
import string
import sys

from fontTools import ttLib

from os import path

from nototools import cmap_data
from nototools import font_data
from nototools import tool_utils
from nototools import unicode_data

"""Generate html comparison of codepoints in various fonts.

Currently hardwired for select target and comparison fonts."""

_HTML_HEADER_TEMPLATE = """<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset="utf-8">
  <title>$title</title>
  <style>
  $styles
  </style>
  <style>
    table { background-color: #eee; font-size: 20pt; text-align: center }
    tr.head { font-weight: bold; font-size: 12pt;
              border-style: solid; border-width: 1px; border-color: black;
              border-collapse: separate }
    .code, .age, .name { font-size: 12pt; text-align: left }
    .key { background-color: white; font-size: 12pt; border-collapse: separate;
           margin-top: 0; border-spacing: 10px 0 }
  </style>
</head>
<body>
  <h3>$title</h3>
"""


_HTML_FOOTER = """
</body>
</html>
"""

def _cleanlines(textfile):
  """Strip comments and blank lines from textfile, return list of lines."""
  result = []
  with open(textfile, 'r') as f:
    for line in f:
      ix = line.find('#')
      if ix >= 0:
        line = line[:ix]
      line = line.strip()
      if line:
        result.append(line)
  return result


class CodeList(object):
  """An ordered list of code points (ints).  These might map to other (PUA) code
  points that the font knows how to display."""

  @staticmethod
  def fromfile(filename):
    if filename.endswith('_codes.txt'):
      return CodeList.frompairfile(filename)
    elif filename.endswith('_cmap.txt'):
      return CodeList.fromrangefile(filename)
    else:
      raise Exception(
          'unrecognized file type %s for CodeList.fromfile' % filename)

  @staticmethod
  def fromset(cpset):
    return UnicodeCodeList(cpset)

  @staticmethod
  def fromrangefile(cprange_file):
    with open(cprange_file, 'r') as f:
      return CodeList.fromset(tool_utils.parse_int_ranges(f.read()))

  @staticmethod
  def fromlist(cplist):
    return OrderedCodeList(cplist)

  @staticmethod
  def fromlistfile(cplist_file):
    return CodeList.fromlist(
        [int(line, 16) for line in _cleanlines(cplist_file)])

  @staticmethod
  def frompairs(cppairs):
    return MappedCodeList(cppairs)

  @staticmethod
  def frompairfile(cppairs_file):
    # if no pairs, will treat as listfile
    pair_list = None
    single_list = []
    for line in _cleanlines(cppairs_file):
      parts = [int(s, 16) for s in line.split(';')]
      if pair_list:
        if len(parts) < 2:
          parts.append(parts[0])
        pair_list.append(tuple(parts)[:2])
      elif len(parts) > 1:
        pair_list = [(cp, cp) for cp in single_list]
        pair_list.append(tuple(parts[:2]))
      else:
        single_list.append(parts[0])

    if pair_list:
      return CodeList.frompairs(pair_list)
    return CodeList.fromlist(single_list)

  def contains(self, cp):
    """Returns True if cp is in the code list."""
    raise NotImplementedError

  def codes(self):
    """Returns the codes in preferred order."""
    raise NotImplementedError

  def codeset(self):
    """Returns the frozenset of codes."""
    raise NotImplementedError

  def mapped_code(self, cp):
    """Returns the mapped code for this code point."""
    raise NotImplementedError


class UnicodeCodeList(CodeList):
  """A codelist based on unicode code point order with no mapping."""
  def __init__(self, codeset):
    super(CodeList, self).__init__()
    self._codeset = frozenset(codeset)

  def contains(self, cp):
    return cp in self._codeset

  def codes(self):
    return sorted(self._codeset)

  def codeset(self):
    return self._codeset

  def mapped_code(self, cp):
    return cp if cp in self._codeset else None


class MappedCodeList(CodeList):
  def __init__ (self, codepairs):
    super(MappedCodeList, self).__init__()
    # hack, TODO: change the column order in the input files
    self._codemap = {v : k for k, v in codepairs}
    self._codes = tuple(p[1] for p in codepairs)

  def contains(self, cp):
    return cp in self._codemap

  def codes(self):
    return self._codes

  def codeset(self):
    return frozenset(self._codes)

  def mapped_code(self, cp):
    return self._codemap.get(cp)


class OrderedCodeList(CodeList):
  def __init__(self, codes):
    super(OrderedCodeList, self).__init__()
    self._codes = tuple(codes)
    self._codeset = frozenset(codes)

  def contains(self, cp):
    return cp in self._codeset

  def codes(self):
    return self._codes

  def codeset(self):
    return self._codeset

  def mapped_code(self, cp):
    return cp if cp in self._codeset else None


def _load_codelist(codelistfile, data_dir,  codelist_map):
  fullpath = path.join(data_dir, codelistfile)
  if not path.isfile(fullpath):
    raise Exception('font "%s" codelist file "%s" not found' % (
      key, codelistfile))
  codelist = codelist_map.get(fullpath)
  if codelist == None:
    codelist = CodeList.fromfile(fullpath)
    codelist_map[codelistfile] = codelist
  return codelist


def _load_fonts(data_list, data_dir, codelist_map):
  """data_list is a list of tuples of two to four items.  The first item is
  the key, the second is the name of the font file in data_dir.  The
  second can be None, otherwise it must exist.  The third item, if
  present, is the name to use for the font, otherwise it will be read
  from the font, it must be present where there is no font.  The
  fourth item, if present, is the name of a codelist file, it must be present
  where there is no font.  If present and None, the the unicode cmap from the
  font is used.  otherwise the font file name is stripped of its extension and
  try to find a file from which to create a codelist.
  Multiple tuples can share the same key, these form one column and the order
  of the files composing the tuple defines the order in which they are searched
  for a glyph.
  Returns a list of tuples of key, keyinfo, where keyinfo is
  a list of tuples of filepath, name, codelist."""

  def _load_font(data, codelist_map):
    if len(data) < 4:
      data = data + tuple([None] * (4 - len(data)))
    key, fname, name, codelistfile = data

    if not fname:
      if not name:
        raise Exception('must have name if no font provided')
      if not codelistfile:
        raise Exception('must have codelist file if no font provided')
      fontpath = None
    else:
      fontpath = path.join(data_dir, fname)
      if not path.isfile(fontpath):
        raise Exception('font "%s" not found' % fontpath)

    if codelistfile:
      codelist = _load_codelist(codelistfile, data_dir, codelist_map)

    if fname and (not codelistfile or not name):
      font = ttLib.TTFont(fontpath)
      if not name:
        names = font_data.get_name_records(font)
        name = names[16] if 16 in names else names[1] if 1 in names else None
        if not name:
          raise Exception('cannot read name from font "%s"' % fontpath)
      if not codelistfile:
        codelist = CodeList.fromset(font_data.get_cmap(font))

    return key, fontpath, name, codelist

  # group by key
  keyorder = []
  keyinfo = collections.defaultdict(list)
  for data in data_list:
    key, fontpath, name, codelist = _load_font(data, codelist_map)
    if key not in keyinfo:
      keyorder.append(key)
    keyinfo[key].append((fontpath, name, codelist))

  return [(key, keyinfo[key]) for key in keyorder]


def _select_used_fonts(codelist, fonts):
  result = []
  codes = codelist.codes()
  for f in fonts:
    for name, _, cl in f[1]:
      if any(cl.contains(cp) for cp in codes):
        result.append(f)
        break
  return tuple(result)


def _load_targets(target_data, fonts, data_dir, codelist_map):
  """Target data is a list of tuples of target names and codelist files.  All
  files should be in data_dir.  codelist_map is a cache in case the codelist
  file has already been read.  Returns a list of tuples of target names and
  codelists."""
  result = []
  for name, codelist_file in target_data:
    codelist = _load_codelist(codelist_file, data_dir, codelist_map)
    used_fonts = _select_used_fonts(codelist, fonts)
    if not used_fonts:
      raise Exception('no fonts used by target %s' % name)
    result.append((name, codelist, used_fonts))
  return tuple(result)


def _load_fonts_and_targets(font_data, target_data, data_dir):
  # we cache the codelists to avoid building them twice if they're referenced by
  # both fonts and targets, not a big deal but...
  codelist_map = {}
  fonts = _load_fonts(font_data, data_dir, codelist_map)
  targets = _load_targets(target_data, fonts, data_dir, codelist_map)
  return fonts, targets


def _get_driver(data_dir):
  """Hard code the driver data.  Should parse from a file."""
  title = 'Dingbats Comparison Tables'
  font_data = [
      ('color', 'NotoColorEmoji.ttf'),
      ('b/w', 'NotoEmoji-Regular.ttf'),
      ('osym', 'NotoSansSymbols-Regular.ttf', 'Old Symbols'),
      ('noto', 'NotoSans-Regular.ttf', 'Noto LGC'),
      ('noto', None, 'Noto Sans Math', 'notosansmath_cmap.txt'),
      ('nsym', 'NotoSansSymbolsNew-Regular.ttf', 'New Symbols'),
      ('sym2', 'NotoSansSymbols2-Regular.ttf', 'Noto Sans Symbols2',
       'notosanssymbols2_cmap.txt'),
      ('webd', 'webdings.ttf', 'Webdings', 'webdings_codes.txt'),
      ('wng1', 'wingding.ttf', 'Wingdings 1', 'wingding_codes.txt'),
      ('wng2', 'WINGDNG2.TTF', 'Wingdings 2', 'wingdng2_codes.txt'),
      ('wng3', 'WINGDNG3.TTF', 'Wingdings 3', 'wingdng3_codes.txt'),
      ('zdng', 'ZapfDingbats_x.ttf', 'Zapf Dingbats', 'zapfdingbats_codes.txt')
  ]
  target_data = [
      ('Webdings', 'webdings_codes.txt'),
      ('Wingdings 1', 'wingding_codes.txt'),
      ('Wingdings 2', 'wingdng2_codes.txt'),
      ('Wingdings 3', 'wingdng3_codes.txt'),
      ('Zapf Dingbats', 'zapfdingbats_codes.txt')
  ]
  fonts, targets = _load_fonts_and_targets(font_data, target_data, data_dir)

  return title, fonts, targets


def generate_text(outfile, title, fonts, targets, data_dir):
  emoji_only = (
      unicode_data.get_emoji() - unicode_data.get_unicode_emoji_variants())

  print >> outfile, title
  print >> outfile
  print >> outfile, 'Fonts:'
  for key, keyinfos in fonts:
    for font, name, _ in keyinfos:
      rel_font = path.relpath(font, data_dir) if font else '(no font)'
      print >> outfile, '  %s: %s (%s)' % (key, name, rel_font)
  print >> outfile

  for name, codelist, used_fonts in targets:
    print >> outfile
    print >> outfile, name
    header = ['idx  code']
    header.extend(f[0] for f in used_fonts)
    header.append('age name')
    print >> outfile, ' '.join(header)
    index = 1
    for cp in codelist.codes():
      print >> outfile, '%3d' % index,
      index += 1
      print >> outfile, '%5s' % ('%04x' % cp),
      for rkey, keyinfos in used_fonts:
        match = any(codelist.contains(cp) for _, _, codelist in keyinfos)
        print >> outfile, rkey if match else ('-' * len(rkey)),
      print >> outfile, unicode_data.age(cp),
      name = unicode_data.name(cp)
      if cp in emoji_only:
        name = '(add) ' + name
      print >> outfile, name


def _generate_fontkey(fonts, targets, data_dir):
  lines = ['<p style="margin-bottom:5px"><b>Targets</b>']
  lines.append('<div style="margin-left:20px"><table class="key">')
  tid = 0
  for name, _, _ in targets:
    lines.append(
        '<tr><th><a href="#target_%s">%s</a>' % (
            tid, name))
    tid += 1
  lines.append('</table></div>')

  lines.append('<p style="margin-bottom:5px"><b>Fonts</b>')
  lines.append('<div style="margin-left:20px"><table class="key">')
  for key, keyinfos in fonts:
    for font, name, _ in keyinfos:
      rel_font = path.relpath(font, data_dir) if font else '(no font)'
      lines.append('<tr><th>%s<td>%s<td>%s' % (key, name, rel_font))
  lines.append('</table></div>')

  return '\n'.join(lines)


_nonalpha_re = re.compile(r'\W')
def replace_nonalpha(key):
  return _nonalpha_re.sub('_', key)


def _generate_styles(fonts):
  face_pat = """@font-face {
    font-family: "%s"; src:url("file://%s")
  }"""

  facelines = []
  classlines = []
  for key, keyinfos in fonts:
    index = 0
    for font, _, _ in keyinfos:
      if len(keyinfos) > 1:
        kname = '%s_%d' % (replace_nonalpha(key), index)
      else:
        kname = replace_nonalpha(key)
      index += 1
      if not font:
        classlines.append('.%s { font-size: 12pt }' % kname)
      else:
        facelines.append(face_pat % (kname, font))
        classlines.append(
            '.%s { font-family: "%s", "noto_0" }' % (kname, kname))

  lines = []
  lines.extend(facelines)
  lines.append('')
  lines.extend(classlines)
  return '\n  '.join(lines)


def _generate_header(used_fonts):
  header_parts = ['<tr class="head"><th>CP']
  for key, _ in used_fonts:
    header_parts.append('<th>' + key)
  header_parts.append('<th>Age<th>Name')
  return ''.join(header_parts)


def _generate_table(index, target, emoji_only):
  name, codelist, used_fonts = target

  lines = ['<h3 id="target_%d">%s</h3>' % (index, name)]
  lines.append('<table>')
  header = _generate_header(used_fonts)
  linecount = 0
  # cp0 is the valid unicode, cp1 is the PUA if the font uses PUA encodings
  for cp0 in codelist.codes():
    if linecount % 20 == 0:
      lines.append(header)
    linecount += 1

    line = ['<tr>']
    line.append('<td class="code">U+%04x' % cp0)
    for rkey, keyinfos in used_fonts:
      cell_class = None
      cell_text = None
      index = 0
      for font, _, rcodelist in keyinfos:
        if rcodelist.contains(cp0):
          if len(keyinfos) > 1:
            cell_class = '%s_%d' % (rkey, index)
          else:
            cell_class = rkey
          cell_class = replace_nonalpha(cell_class)
          if font:
            cell_text = 'O' + unichr(rcodelist.mapped_code(cp0)) + 'g'
          else:
            cell_text = ' * '
            cell_class += ' star'
          break
        index += 1
      if cell_class:
        line.append('<td class="%s">%s' % (cell_class, cell_text))
      else:
        line.append('<td>&nbsp;')
    line.append('<td class="age">%s' % unicode_data.age(cp0))
    name = unicode_data.name(cp0)
    if cp0 in emoji_only:
      name = '(add) ' + name
    line.append('<td class="name">%s' % name)
    lines.append(''.join(line))
  lines.append('</table>')
  return '\n'.join(lines)


def generate_html(outfile, title, fonts, targets, data_dir):
  template = string.Template(_HTML_HEADER_TEMPLATE)
  styles = _generate_styles(fonts)
  print >> outfile, template.substitute(title=title, styles=styles)

  print >> outfile, _generate_fontkey(fonts, targets, data_dir)

  emoji_only = (
      unicode_data.get_emoji() - unicode_data.get_unicode_emoji_variants())
  for index, target in enumerate(targets):
    print >> outfile, _generate_table(index, target, emoji_only)

  print >> outfile, _HTML_FOOTER


def generate(outfile, fmt, data_dir):
  if not path.isdir(data_dir):
    raise Exception('data dir "%s" does not exist' % data_dir)

  title, fonts, targets = _get_driver(data_dir)

  if fmt == 'txt':
    generate_text(outfile, title, fonts, targets, data_dir)
  elif fmt == 'html':
    generate_html(outfile, title, fonts, targets, data_dir)
  else:
    raise Exception('unrecognized format "%s"' % fmt)


def _call_generate(outfile, fmt, data_dir):
  if outfile:
    base, ext = path.splitext(outfile)
    if not ext:
      if not fmt:
        fmt = 'txt'
        ext = 'txt'
      else:
        ext = fmt
    elif not fmt:
      if ext not in ['html', 'txt']:
        raise Exception('don\'t understand "%s" format' % ext)
      fmt = ext
    elif ext != fmt:
      raise Exception('mismatching format "%s" and output extension "%s"' % (
          fmt, ext))
    outfile += '.' + ext
    print 'writing %s' % outfile
    with codecs.open(outfile, 'w', 'utf-8') as f:
      generate(f, fmt, data_dir)
  else:
    if not fmt:
      fmt = 'txt'
    generate(sys.stdout, fmt, data_dir)


def main():
  DEFAULT_OUT = 'dingbats_compare'

  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-o', '--outfile', help='Path to output file (will use %s)' % DEFAULT_OUT,
      const=DEFAULT_OUT, metavar='file', nargs='?')
  parser.add_argument(
      '-t', '--output_type', help='output format (defaults based on outfile '
      'extension, else "txt")', choices=['txt', 'html'])
  parser.add_argument(
      '-d', '--data_dir', help='Path to directory containing fonts '
      'and data', metavar='dir', required=True)
  args = parser.parse_args()

  _call_generate(args.outfile, args.output_type, args.data_dir)

if __name__ == '__main__':
  main()
