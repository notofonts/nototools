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

"""Compare summaries of ttf files in two noto file trees"""

__author__ = "dougfelt@google.com (Doug Felt)"

import argparse
import filecmp
import os
import os.path

import summary
import noto_lint

def summary_to_map(summary_list):
  result = {}
  for tuple in summary_list:
    key = tuple[0]
    result[key] = tuple
  return result

def get_key_lists(base_map, target_map):
  missing_in_base = []
  missing_in_target = []
  shared = []
  for k in base_map:
    if not target_map.get(k):
      missing_in_target.append(k)
    else:
      shared.append(k)
  for k in target_map:
    if not base_map.get(k):
      missing_in_base.append(k)
  return sorted(missing_in_base), sorted(missing_in_target), sorted(shared)

def print_keys(key_list):
  for k in key_list:
    print '\t' + k

def print_difference(base_tuple, target_tuple):
  b_path, b_version, b_name, b_size, b_numglyphs, b_numchars, b_cmap = base_tuple
  t_path, t_version, t_name, t_size, t_numglyphs, t_numchars, t_cmap = target_tuple
  print "%s differs:" % b_path
  versions_differ = b_version != t_version
  diff_list = []
  if versions_differ:
    if float(b_version) > float(t_version):
      msg = '(base is newer!)'
    else:
      msg = ''
    print '  version: %s vs %s %s' % (b_version, t_version, msg)
  if b_name != t_name:
    diff_list.append('name')
    print "  name: '%s' vs '%s'" % (b_name, t_name)
  if b_size != t_size:
    diff_list.append('size')
    delta = int(t_size) - int(b_size)
    if delta < 0:
      msg = '%d byte%s smaller' % (-delta, '' if delta == -1 else 's')
    else:
      msg = '%d byte%s bigger' % (delta, '' if delta == 1 else 's')
    print '  size: %s vs %s (%s)' % (b_size, t_size, msg)
  if b_numglyphs != t_numglyphs:
    diff_list.append('glyph count')
    delta = int(t_numglyphs) - int(b_numglyphs)
    if delta < 0:
      msg = '%d fewer glyph%s' % (-delta, '' if delta == -1 else 's')
    else:
      msg = '%d more glyph%s' % (delta, '' if delta == 1 else 's')
    print '  glyphs: %s vs %s (%s)' % (b_numglyphs, t_numglyphs, msg)
  if b_numchars != t_numchars:
    diff_list.append('char count')
    delta = int(t_numchars) - int(b_numchars)
    if delta < 0:
      msg = '%d fewer char%s' % (-delta, '' if delta == -1 else 's')
    else:
      msg = '%d more char%s' % (delta, '' if delta == 1 else 's')
    print '  chars: %s vs %s (%s)' % (b_numchars, t_numchars, msg)
  if b_cmap != t_cmap:
    removed_from_base = b_cmap - t_cmap
    if removed_from_base:
      print '  cmap removed: ' + noto_lint.printable_unicode_range(
        removed_from_base)
    added_in_target = t_cmap - b_cmap
    if added_in_target:
      print '  cmap added: ' + noto_lint.printable_unicode_range(
          added_in_target)
  if diff_list and not versions_differ:
    print '  %s differ but same revision number' % ', '.join(diff_list)

def print_identical(path, identical, show_identical):
  if not identical:
    print '%s differs:' % path
    print '  other difference'
  elif show_identical:
    print '%s identical' % path

def print_shared(key_list, base_map, target_map, comparefn,
                 base_root, target_root, show_identical):
  for k in key_list:
    base_tuple = base_map.get(k)
    target_tuple = target_map.get(k)
    if not comparefn(base_tuple, target_tuple):
      print_difference(base_tuple, target_tuple)
    else:
      # The key is also the path
      identical = filecmp.cmp(os.path.join(base_root, k),
                              os.path.join(target_root, k))
      print_identical(k, identical, show_identical)

def compare_summary(base_root, target_root, comparefn, show_missing, show_paths,
                    show_identical):
  base_map = summary_to_map(summary.summarize(base_root))
  target_map = summary_to_map(summary.summarize(target_root))
  missing_in_base, missing_in_target, shared = get_key_lists(base_map, target_map)

  if show_paths:
    print 'base root: ' + base_root
    print 'target root: ' + target_root
  if show_missing:
    if missing_in_base:
      print 'missing in base'
      print_keys(missing_in_base)
      print
    if missing_in_target:
      print 'missing in target'
      print_keys(missing_in_target)
      print
  if shared:
    if show_missing:
      print 'shared'
    print_shared(shared, base_map, target_map, comparefn, base_root, target_root,
                 show_identical)

def tuple_compare(base_t, target_t):
  return base_t == target_t

def tuple_compare_no_size(base_t, target_t):
  for i in range(len(base_t)):
    if i == 3:
      continue
    if base_t[i] != target_t[i]:
      return False
  return True

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('base_root', help='root of directory tree, base for comparison')
  parser.add_argument('target_root', help='root of directory tree, target for comparison')
  parser.add_argument('--size', help='include size in comparisons',
                      action='store_true')
  parser.add_argument('--missing',  help='include mismatched files', action='store_true')
  parser.add_argument('--nopaths', help='do not print root paths', action='store_false',
                      default=True, dest='show_paths')
  parser.add_argument('--show_identical', help='report when files are identical',
                      action='store_true')
  args = parser.parse_args()

  if not os.path.isdir(args.base_root):
    print 'base_root %s does not exist or is not a directory' % args.base_root
    return

  if not os.path.isdir(args.target_root):
    print 'target_root %s does not exist or is not a directory' % args.target_root
    return

  base_root = os.path.abspath(args.base_root)
  target_root = os.path.abspath(args.target_root)

  comparefn = tuple_compare if args.size else tuple_compare_no_size

  compare_summary(base_root, target_root, comparefn, args.missing, args.show_paths,
                  args.show_identical)

if __name__ == '__main__':
  main()
