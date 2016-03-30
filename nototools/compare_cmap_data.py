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

"""Compare two cmap data files produced by lint_cmap_reqs or
   noto_font_cmaps."""

import argparse
import collections

from nototools import cmap_data
from nototools import lint_config
from nototools import tool_utils
from nototools import unicode_data


def title_from_metadata(metadata):
  items = [metadata.date, metadata.program]
  if metadata.args:
    items.extend(['%s=%s' % t for t in metadata.args])
  return ' '.join(items)


def compare_cmaps(
    base_cps, target_cps, only_cps, except_cps, no_additions, no_removals):
  """Returns a tuple of added, removed."""
  if only_cps:
    base_cps &= only_cps
    target_cps &= only_cps
  if except_cps:
    base_cps -= except_cps
    target_cps -= except_cps
  if base_cps != target_cps:
    added = None if no_additions else target_cps - base_cps
    removed = None if no_removals else base_cps - target_cps
  else:
    added, removed = None, None
  return added, removed


def compare_cmap_data(base_cmap_data, target_cmap_data, scripts, cps,
                      except_scripts, except_cps, no_additions, no_removals):
  result = {}
  base_map = cmap_data.create_map_from_table(base_cmap_data.table)
  target_map = cmap_data.create_map_from_table(target_cmap_data.table)

  for script in sorted(base_map):
    if except_scripts and script in except_scripts:
      continue
    if scripts and script not in scripts:
      continue
    if script in target_map:
      name = base_map[script].name
      base_cps = lint_config.parse_int_ranges(base_map[script].ranges)
      target_cps = lint_config.parse_int_ranges(target_map[script].ranges)
      added, removed = compare_cmaps(
          base_cps, target_cps, cps, except_cps, no_additions, no_removals)
      base_xcps, target_xcps = (set(), set())
      if int(getattr(base_map[script], 'xcount', -1)) != -1:
        base_xcps = lint_config.parse_int_ranges(base_map[script].xranges)
      if int(getattr(target_map[script], 'xcount', -1)) != -1:
        target_xcps = lint_config.parse_int_ranges(target_map[script].xranges)
      xadded, xremoved = compare_cmaps(
          base_xcps, target_xcps, cps, except_cps, no_additions, no_removals)
      result[script] = added, removed, xadded, xremoved
  return result


def compare_cmap_data_files(base_file, target_file, scripts, ranges,
                            except_scripts, except_ranges,
                            no_additions, no_removals):
  base_cmap_data = cmap_data.read_cmap_data_file(base_file)
  target_cmap_data = cmap_data.read_cmap_data_file(target_file)
  compare = compare_cmap_data(
      base_cmap_data, target_cmap_data, scripts, ranges,
      except_scripts, except_ranges, no_additions, no_removals)
  return compare, base_cmap_data, target_cmap_data


def _print_detailed(cps, inverted_target=None):
  last_block = None
  undefined_start = -1
  undefined_end = -1
  def show_undefined(start, end):
    if start >= 0:
      if end > start:
        print '      %04x-%04x Zzzz <%d undefined>' % (
            start, end, end - start - 1)
      else:
        print '      %04x Zzzz <1 undefined>' % start

  for cp in sorted(cps):
    block = unicode_data.block(cp)
    if block != last_block or (undefined_end > -1 and cp > undefined_end + 1):
      show_undefined(undefined_start, undefined_end)
      undefined_start, undefined_end = -1, -1
      if block != last_block:
        print '    %s' % block
        last_block = block
    script = unicode_data.script(cp)
    if script == 'Zzzz':
      if undefined_start >= 0:
        undefined_end = cp
      else:
        undefined_start, undefined_end = cp, cp
      continue

    show_undefined(undefined_start, undefined_end)
    undefined_start, undefined_end = -1, -1
    extensions = unicode_data.script_extensions(cp) - set([script])
    if extensions:
      extensions = ' (%s)' % ','.join(sorted(extensions))
    else:
      extensions = ''
    if not inverted_target:
      extra = ''
    elif cp not in inverted_target:
      extra = ' !missing'
    else:
      scripts = sorted(inverted_target[cp])
      if len(scripts) > 3:
        script_text = ', '.join(scripts[:3]) + '... ' + scripts[-1]
      else:
        script_text = ', '.join(scripts)
      extra = ' (in %s)' % script_text
    print '    %6s %4s %2s %3s %s%s%s' % (
        '%04x' % cp,
        script,
        unicode_data.category(cp),
        unicode_data.age(cp),
        unicode_data.name(cp, ''),
        extensions,
        extra)
  show_undefined(undefined_start, undefined_end)


def report_cmap_compare(
    label, added, removed, xadded, xremoved, inverted_target=None,
    detailed=True, report_same=False):
  def report_cps(label, cps, inverted=None):
    if not cps:
      return
    print '  %s (%d): %s' % (
        label, len(cps), lint_config.write_int_ranges(cps))
    if detailed:
      _print_detailed(cps, inverted)

  if report_same:
    print label
  if added or removed or xadded or xremoved:
    if not report_same:
      print label
    removed_to_fallback = removed & xadded
    if removed_to_fallback:
      removed -= removed_to_fallback
      xadded -= removed_to_fallback
    added_from_fallback = added & xremoved
    if added_from_fallback:
      added -= added_from_fallback
      xremoved -= added_from_fallback
    report_cps('added', added)
    report_cps('added, no longer fallback', added_from_fallback)
    report_cps('removed', removed, inverted_target)
    report_cps('removed, now in fallback', removed_to_fallback, inverted_target)
    report_cps('added to fallback', xadded, inverted_target)
    report_cps('removed from fallback', xremoved)


def report_compare(compare_result, detailed=True):
  compare, base_cmap_data, target_cmap_data = compare_result
  base_map = cmap_data.create_map_from_table(base_cmap_data.table)
  target_map = cmap_data.create_map_from_table(target_cmap_data.table)

  inverted_target = collections.defaultdict(set)
  for script, row in target_map.iteritems():
    cps = tool_utils.parse_int_ranges(row.ranges)
    for cp in cps:
      inverted_target[cp].add(script)

  base_title = title_from_metadata(base_cmap_data.meta)
  target_title = title_from_metadata(target_cmap_data.meta)

  print 'base: %s' % base_title
  print 'target: %s' % target_title
  for script in sorted(compare):
    added, removed, xadded, xremoved = compare[script]
    label = '%s # %s' % (script, base_map[script].name)
    report_cmap_compare(
        label, added, removed, xadded, xremoved, inverted_target, detailed)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-b', '--base', help='base cmap data file',
      metavar='file', required=True)
  parser.add_argument(
      '-t', '--target', help='target cmap data file',
      metavar='file', required=True)
  parser.add_argument(
      '-s', '--scripts', help='only these scripts (except ignored)',
      metavar='code', nargs='+')
  parser.add_argument(
      '-r', '--ranges', help='only these ranges (except ignored)',
      metavar='ranges', nargs='+')
  parser.add_argument(
      '-xs', '--except_scripts', help='ignore these scripts',
      metavar='code', nargs='+')
  parser.add_argument(
      '-xr', '--except_ranges', help='ignore these codepoints',
      metavar='ranges', nargs='+')
  parser.add_argument(
      '-na', '--no_additions', help='do not report additions (in target '
      'but not base)', action='store_true')
  parser.add_argument(
      '-nr', '--no_removals', help='do not report removals (in base '
      'but not target)', action='store_true')

  args = parser.parse_args()
  if args.scripts:
    scripts = set(args.scripts)
  else:
    scripts = None

  if args.ranges:
    cps = lint_config.parse_int_ranges(' '.join(args.ranges))
  else:
    cps = None

  if args.except_ranges:
    except_cps = lint_config.parse_int_ranges(' '.join(args.except_ranges))
  else:
    except_cps = None

  if args.except_scripts:
    except_scripts = set(args.except_scripts)
  else:
    except_scripts = None

  result = compare_cmap_data_files(
      args.base, args.target, scripts, cps, except_scripts, except_cps,
      args.no_additions, args.no_removals)
  report_compare(result)


if __name__ == "__main__":
  main()
