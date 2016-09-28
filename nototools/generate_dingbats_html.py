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
           margin-top: 0; border-spacing: 10px 0; text-align: left }
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
    elif filename.endswith('.ttf'):
      return CodeList.fromfontcmap(filename)
    else:
      raise Exception(
          'unrecognized file type %s for CodeList.fromfile' % filename)

  @staticmethod
  def fromtext(text, codelist_type):
    if codelist_type == 'cmap':
      return CodeList.fromrangetext(text)
    elif codelist_type == 'codes':
      return CodeList.frompairtext(text)
    elif codelist_type == 'list':
      return CodeList.fromlisttext(text)
    else:
      raise Exception('unknown codelist type "%s"' % codelist_type)

  @staticmethod
  def fromfontcmap(fontname):
    font = ttLib.TTFont(fontname)
    return CodeList.fromset(font_data.get_cmap(font))

  @staticmethod
  def fromset(cpset):
    return UnicodeCodeList(cpset)

  @staticmethod
  def fromrangetext(cpranges):
    return CodeList.fromset(tool_utils.parse_int_ranges(cpranges))

  @staticmethod
  def fromrangefile(cprange_file):
    with open(cprange_file, 'r') as f:
      return CodeList.fromrangetext(f.read())

  @staticmethod
  def fromlist(cplist):
    return OrderedCodeList(cplist)

  @staticmethod
  def fromlisttext(cplist):
    return CodeList.fromlist([int(item, 16) for item in cplist.split()])

  @staticmethod
  def fromlistfile(cplist_file):
    return CodeList.fromlisttext(_cleanlines(cplist_file))

  @staticmethod
  def frompairs(cppairs):
    return MappedCodeList(cppairs)

  @staticmethod
  def frompairtext(cppairs_text):
    # if no pairs, will treat as listtext.  cppairs must have only one item
    # or pair per line, however.
    pair_list = None
    single_list = []
    for line in cppairs_text.splitlines():
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

  @staticmethod
  def frompairfile(cppairs_file):
    return CodeList.frompairtext('\n'.join(_cleanlines(cppairs_file)))

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


def _load_codelist(codelist_spec, data_dir, codelistfile_map):
  for codelist_type in ['file', 'cmap', 'codes', 'list', None]:
    if codelist_type and codelist_spec.startswith(codelist_type + ':'):
      codelist_spec = codelist_spec[len(codelist_type) + 1:].strip()
      break
  if not codelist_type:
    if codelist_spec.endswith('.txt'):
      codelist_type = 'file'
    else:
      raise Exception(
          'cannot determine type of codelist spec "%s"' % codelist_spec)
  if codelist_type != 'file':
    codelist = CodeList.fromtext(codelist_spec, codelist_type)
  else:
    fullpath = path.join(data_dir, codelist_spec)
    if not path.isfile(fullpath):
      raise Exception('codelist file "%s" not found' % codelist_spec)
    codelist = codelistfile_map.get(fullpath)
    if codelist == None:
      codelist = CodeList.fromfile(fullpath)
      codelistfile_map[codelist_spec] = codelist
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


def _select_used_fonts(codelist, fonts, prefer_fonts, omit_fonts):
  """Return the fonts we want to use to display the codelist, in order.
  If not None, prefer_fonts is a key or list of keys for fonts to order
  at the end.  If not None, omit_fonts is key or list of keys to omit
  even if they would otherwise be used by default, however prefer_fonts
  takes precedence over omit_fonts if the same key is in both."""

  if prefer_fonts is not None:
    if isinstance(prefer_fonts, basestring):
      prefer_fonts = [prefer_fonts]
    preferred = [None] * len(prefer_fonts)
  else:
    prefer_fonts = []
    preferred = []

  if omit_fonts is not None:
    if isinstance(omit_fonts, basestring):
      omit_fonts = [omit_fonts]
    if prefer_fonts:
      omit_fonts = [k for k in omit_fonts if k not in prefer_fonts]
  else:
    omit_fonts = []

  regular = []
  codes = codelist.codes()
  for f in fonts:
    key, keyinfo = f
    if key in omit_fonts:
      continue
    for name, _, cl in keyinfo:
      if any(cl.contains(cp) for cp in codes):
        is_preferred = False
        for i, k in enumerate(prefer_fonts):
          if key == k:
            preferred[i] = f
            is_preferred = True
            break
        if not is_preferred:
          regular.append(f)
        break
  return tuple(regular + filter(None, preferred))


def _load_targets(target_data, fonts, data_dir, codelist_map):
  """Target data is a list of tuples of target names, codelist files, an
  optional preferred font key or list of keys, and an optional omitted font
  key or list of keys. All files should be in data_dir.  Codelist_map is a
  cache in case the codelist file has already been read.  Returns a list of
  tuples of target name, codelist, and fontlist."""
  result = []
  for target in target_data:
    if len(target) < 4:
      target = target + ((None,) * (4 - len(target)))
    name, codelist_spec, prefer_fonts, omit_fonts = target
    codelist = _load_codelist(codelist_spec, data_dir, codelist_map)
    used_fonts = _select_used_fonts(codelist, fonts, prefer_fonts, omit_fonts)
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


def strip_comments_from_file(filename):
  with open(filename, 'r') as f:
    for line in f:
      ix = line.find('#')
      if ix >= 0:
        line = line[:ix]
      line = line.strip()
      if not line:
        continue
      yield line


def _read_font_data_from_file(filename):
  font_data = []
  for line in strip_comments_from_file(filename):
    info = line.split(';')
    while len(info) < 4:
      info.append(None)
    font_data.append(tuple(info))
  return font_data


def _read_target_data_from_file(filename):
  """Target data uses # to indicate a comment to end of line.
  Comments are stripped, then an empty or blank line is ignored.

  Each line defines a tuple of four values: target name,
  codelist, preferred font ids, and omitted font ids.
  A line can also start with either of two directives,
  !define and !default.

  If a line starts with '!define ' we expect a key followed
  by '=' and then one or more names separated by space. The
  names are turned into a list, and entered into a dictionary
  for the key.  Once defined a key cannot be redefined.

  If a line starts with '!default ' we expect a key of either
  'prefer' or 'omit' optionally followed by '=' and a list of
  names to prefer or omit; these will become the default
  values until the next '!default ' directive.  If there is
  no '=' the value is reset.  An omitted or empty prefer or
  omit field will get the fallback, to explicitly request None
  and override the fallback the field should contain 'None'.

  Normally, a line consists of 2-4 fields separated by ';'.
  The first two are a target name and a codelist spec.  The
  third is the preferred font ids separated by space,
  previously !defined keys can be used here instead of this
  list and the list defined for that key will be used.
  The fourth is the omitted font ids separated by space, they
  are treated similarly.  If the preferred or omit field is
  missing or empty and a default value for it has been set,
  that value is used."""

  def add_index_list_or_defined(info, index, fallback, defines):
    """Extend or update info[index], possibly using defines"""
    if len(info) <= index:
      info.append(fallback)
    elif info[index] != None:
      item = info[index]
      if item in defines:
        items = defines[item]
      elif item == 'None':
        items = None
      elif item:
        items = item.split()
      else:
        items = fallback
      info[index] = items

  prefer_fallback = None
  omit_fallback = None
  defines = {}
  target_data = []
  kDefineDirective = '!define '
  kDefaultDirective = '!default '
  for line in strip_comments_from_file(filename):
    if line.startswith(kDefineDirective):
      # !define key=val val...
      name, rest = line[len(kDefineDirective):].split('=')
      name = name.strip()
      if name in defines:
        raise Exception('name %s already defined in %s' % (name, filename))
      rest = rest.strip().split()
      defines[name] = tuple(rest)
      continue
    if line.startswith(kDefaultDirective):
      # !default prefer|omit=val val...
      values = line[len(kDefaultDirective):].split('=')
      name = values[0].strip()
      rest = values[1].strip().split() if len(values) > 1 else None
      if not rest:
        rest = None
      if name == 'prefer':
        prefer_fallback = rest
      elif name == 'omit':
        omit_fallback = rest
      else:
        raise Exception('default only understands \'prefer\' or \'omit\'')
      continue
    info = line.split(';')
    # name;character spec or filename;prefer_id... or empty;omit_id... or empty
    add_index_list_or_defined(info, 2, prefer_fallback, defines)  # preferred
    add_index_list_or_defined(info, 3, omit_fallback, defines)  # omitted
    target_data.append(tuple(info))

  return target_data


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


def _generate_styles(fonts, relpath):
  face_pat = """@font-face {
      font-family: "%s"; src:url("%s")
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
        if relpath is None:
          font = 'file://' + font
        else:
          font = path.join(relpath, path.basename(font))
        facelines.append(face_pat % (kname, font))
        classlines.append(
            '.%s { font-family: "%s", "noto_0" }' % (kname, kname))

  lines = []
  lines.extend(facelines)
  lines.append('')
  lines.extend(classlines)
  return '\n    '.join(lines)


def _generate_header(used_fonts):
  header_parts = ['<tr class="head"><th>CP']
  for key, _ in used_fonts:
    header_parts.append('<th>' + key)
  header_parts.append('<th>Age<th>Name')
  return ''.join(header_parts)


def _generate_table(index, target, context, emoji_only):
  name, codelist, used_fonts = target

  def context_string(codelist, cp):
    cps = unichr(codelist.mapped_code(cp))
    return (context % cps) if context else cps

  lines = ['<h3 id="target_%d">%s</h3>' % (index, name)]
  lines.append('<table>')
  header = _generate_header(used_fonts)
  linecount = 0
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
            cell_text = context_string(rcodelist, cp0)
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


def generate_html(outfile, title, fonts, targets, context, data_dir, relpath):
  """If not None, relpath is the relative path from the outfile to
  the datadir, for use when generating font paths."""
  template = string.Template(_HTML_HEADER_TEMPLATE)
  styles = _generate_styles(fonts, relpath)
  print >> outfile, template.substitute(title=title, styles=styles)

  print >> outfile, _generate_fontkey(fonts, targets, data_dir)

  emoji_only = (
      unicode_data.get_emoji() - unicode_data.get_unicode_emoji_variants())
  for index, target in enumerate(targets):
    print >> outfile, _generate_table(index, target, context, emoji_only)

  print >> outfile, _HTML_FOOTER


def generate(outfile, fmt, data_dir, title=None, context=None, relpath=None):
  if not path.isdir(data_dir):
    raise Exception('data dir "%s" does not exist' % data_dir)

  font_data = _read_font_data_from_file(path.join(data_dir, 'font_data.txt'))
  target_data = _read_target_data_from_file(
      path.join(data_dir, 'target_data.txt'))
  fonts, targets = _load_fonts_and_targets(font_data, target_data, data_dir)

  if fmt == 'txt':
    generate_text(outfile, title, fonts, targets, data_dir)
  elif fmt == 'html':
    generate_html(outfile, title, fonts, targets, context, data_dir, relpath)
  else:
    raise Exception('unrecognized format "%s"' % fmt)


def _call_generate(outfile, fmt, data_dir, title=None, context=None):
  data_dir = path.realpath(path.abspath(data_dir))
  if outfile:
    outfile = path.realpath(path.abspath(outfile))
    base, ext = path.splitext(outfile)
    if ext:
      ext = ext[1:]
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
    outfile = base + '.' + ext
    outdir = path.dirname(outfile)
    if data_dir == outdir:
      relpath = ''
    elif data_dir.startswith(outdir):
      relpath = data_dir[len(outdir) + 1:]
    else:
      relpath = None
    print 'relpath: "%s"' % relpath
    print 'writing %s ' % outfile
    with codecs.open(outfile, 'w', 'utf-8') as f:
      generate(f, fmt, data_dir, title, context, relpath)
  else:
    if not fmt:
      fmt = 'txt'
    generate(sys.stdout, fmt, data_dir, title, context)


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
  parser.add_argument(
      '--title', help='Title on html page', metavar='title',
      default='Character and Font Comparison')
  parser.add_argument(
      '--context', help='Context pattern for glyphs (e.g. \'O%%sg\')',
      metavar='ctx', nargs='?', const='O%sg')
  args = parser.parse_args()

  _call_generate(
      args.outfile, args.output_type, args.data_dir, args.title, args.context)

if __name__ == '__main__':
  main()
