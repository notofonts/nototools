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
    r = r.strip();
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
      v = v.strip()
      if v.endswith('*'):
        v = v[:-1]
      if not v or v == u'\u001a':
        continue
      try:
        data[i].add(int(v, 16))
      except:
        raise ValueError('could not parse col %d of row %d: "%s" %x' % (
            i, n, v, ord(v[0])))
  return { script: cmap for script, cmap in zip(header, data) }


def cmap_data_from_csv(csvdata, infile=None):
  args = [('infile', infile)] if infile else None
  metadata = cmap_data.create_metadata('mti_cmap_data', args)
  tabledata = cmap_data.create_table_from_map(
      get_script_to_cmap(csvdata))
  return cmap_data.CmapData(metadata, tabledata)


def cmap_data_from_csv_file(csvfile):
  with open(csvfile, 'r') as f:
    csvdata = f.read()
  return cmap_data_from_csv(csvdata, csvfile)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--infile', help='input file name', metavar='fname')
  parser.add_argument(
      '--outfile', help='write to output file, otherwise to stdout, '
      'provide file name or will default to one based on infile',
      metavar='fname', nargs='?', const='-default-')
  args = parser.parse_args()

  cmapdata = cmap_data_from_csv_file(args.infile)
  if args.outfile:
    if args.outfile == '-default-':
      args.outfile = path.splitext(path.basename(args.infile))[0] + '.xml'
    print >> sys.stderr, 'writing %s' % args.outfile
    cmap_data.write_cmap_data_file(cmapdata, args.outfile, pretty=True)
  else:
    print cmap_data.write_cmap_data(cmapdata, pretty=True)


if __name__ == "__main__":
  main()
