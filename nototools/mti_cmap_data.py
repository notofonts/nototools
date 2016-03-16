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

"""Extract cmap data from mti phase 3 spreadsheet."""

import argparse
from os import path
import sys

from nototools import cmap_data
from nototools import tool_utils
from nototools import unicode_data

def get_script_for_name(script_name):
  if script_name in ['LGC']:
    return script_name

  code = unicode_data.script_code(script_name)
  if code == 'Zzzz':
    raise ValueError('cannot identify script for "%s"' % script_name)
  return code


def get_script_to_cmap(csvdata):
  # Roll our own parse, the data is simple... well, mostly.
  # Google sheets inconsistently puts ^Z in first empty cell in a column.
  # Also, MTI puts asterisks into the data to mark some values, which is just
  # noise for our purposes.
  header = None
  data = None
  for n, r in enumerate(csvdata.splitlines()):
    r = r.strip()
    if not r:
      continue
    rowdata = r.split(',')
    if not header:
      header = [get_script_for_name(name) for name in rowdata]
      ncols = len(header)
      data = [set() for _ in range(ncols)]
      continue

    if len(rowdata) != ncols:
      raise ValueError('row %d had %d cols but expected %d:\n"%s"' % (
          n, len(rowdata), ncols, r))
    for i, v in enumerate(rowdata):
      v = v.strip(' \n\t*')
      if not v or v == u'\u001a':
        continue
      try:
        data[i].add(int(v, 16))
      except:
        raise ValueError('could not parse col %d of row %d: "%s" %x' % (
            i, n, v, ord(v[0])))
  return { script: cmap for script, cmap in zip(header, data) }


def cmap_data_from_csv(
    csvdata, scripts=None, exclude_scripts=None, infile=None):
  args = [('infile', infile)] if infile else None
  metadata = cmap_data.create_metadata('mti_cmap_data', args)
  script_to_cmap = get_script_to_cmap(csvdata)
  if scripts or exclude_scripts:
    script_list = script_to_cmap.keys()
    for script in script_list:
      if scripts and script not in scripts:
        del script_to_cmap[script]
      elif exclude_scripts and script in exclude_scripts:
        del script_to_cmap[script]
  tabledata = cmap_data.create_table_from_map(script_to_cmap)
  return cmap_data.CmapData(metadata, tabledata)


def cmap_data_from_csv_file(
    csvfile, scripts=None, exclude_scripts=None):
  with open(csvfile, 'r') as f:
    csvdata = f.read()
  return cmap_data_from_csv(csvdata, scripts, exclude_scripts, csvfile)


def csv_to_xml(csv_file, xml_file, scripts, exclude_scripts):
  cmapdata = cmap_data_from_csv_file(csv_file, scripts, exclude_scripts)
  if xml_file:
    print >> sys.stderr, 'writing %s' % xml_file
    cmap_data.write_cmap_data_file(cmapdata, xml_file, pretty=True)
  else:
    print cmap_data.write_cmap_data(cmapdata, pretty=True)


def _script_to_name(script):
  try:
    return unicode_data.human_readable_script_name(script)
  except KeyError:
    return script


def csv_from_cmap_data(data, scripts, exclude_scripts):
  script_to_rowdata = cmap_data.create_map_from_table(data.table)
  cols = []
  max_lines = 0
  num_cells = 0
  for script in sorted(
      script_to_rowdata, key=lambda s: _script_to_name(s).lower()):
    if scripts and script not in scripts:
      continue
    if script in exclude_scripts:
      continue

    col = [
        '"%s"' % _script_to_name(script)
    ]
    rd = script_to_rowdata[script]
    cps = tool_utils.parse_int_ranges(rd.ranges)
    num_cells += len(cps)
    col.extend('U+%04X' % cp for cp in sorted(
        tool_utils.parse_int_ranges(rd.ranges)))
    cols.append(col)
    max_lines = max(max_lines, len(col))

  num_cols = len(cols)
  num_cells += num_cols  # headers are not empty
  all_cells = num_cols * max_lines
  fmt = 'Columns: %d\nRows: %d\nNon-empty cells: %d\nCells: %d'
  print >> sys.stderr, fmt % (num_cols, max_lines, num_cells, all_cells)
  cmap_lines = []
  cmap_lines.append(','.join(col[0] for col in cols))
  for i in range(1, max_lines):
    cmap_lines.append(','.join(col[i] if i < len(col) else '' for col in cols))
  return '\n'.join(cmap_lines)


def xml_to_csv(xml_file, csv_file, scripts, exclude_scripts):
  data = cmap_data.read_cmap_data_file(xml_file)
  csv_data = csv_from_cmap_data(data, scripts, exclude_scripts)
  if csv_file:
    with open(csv_file, 'w') as f:
      f.write(csv_data)
  else:
    print csv_data


def _check_scripts(scripts):
  """Return True if all scripts are known (pseudo) codes."""
  have_unknown = False
  if scripts:
    all_scripts = unicode_data.all_scripts()
    all_scripts = all_scripts | set(
        ['CJK', 'EXCL', 'LGC', 'MONO', 'MUSIC', 'SYM2'])
    for s in scripts:
      if s not in all_scripts:
        print >> sys.stderr, 'unknown script:', s
        have_unknown = True
  return not have_unknown


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-i', '--infile', help='input file name', metavar='fname')
  parser.add_argument(
      '-o', '--outfile', help='write to output file, otherwise to stdout, '
      'provide file name or will default to one based on infile',
      metavar='fname', nargs='?', const='-default-')
  parser.add_argument(
      '-op', '--operation', help='read csv, or write csv', metavar='op',
      choices=['read', 'write'], default='read')
  parser.add_argument(
      '-s', '--scripts', help='limit to these scripts',
      metavar='script', nargs='*')
  parser.add_argument(
      '-xs', '--exclude_scripts', help='omit these scripts',
      metavar='script', nargs='*')

  args = parser.parse_args()

  if not _check_scripts(args.scripts):
    print >> sys.stderr, 'some scripts failed'
    return
  if not _check_scripts(args.exclude_scripts):
    print >> sys.stderr, 'some exclude scripts failed'
    return

  if args.outfile == '-default-':
    args.outfile = path.splitext(path.basename(args.infile))[0]
    args.outfile += '.xml' if args.operation == 'read' else '.csv'
  if args.operation == 'read':
    csv_to_xml(args.infile, args.outfile, args.scripts, args.exclude_scripts)
  else:
    xml_to_csv(args.infile, args.outfile, args.scripts, args.exclude_scripts)


if __name__ == "__main__":
  main()
