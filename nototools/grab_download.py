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

"""Copy downloaded font zip files from Monotype into noto directory
structure.

This leverages some properties of the font drops.  The drops come in
zip files with an underscore and 8-digit date suffix before the extension.
This reflects the date of the drop. For each zip of this type we build
a root named for the date in the target directory.

Most drops contain a two-level tree with the font name and a suffix of
either '_hinted or '_unhinted' on the top level, and the relevant data
underneath.  Our structure just uses 'hinted' or 'unhinted', so we
convert, putting these under the root for the zip.

Some drops have a single level tree, we examine the fonts to determine if
they have hints (probably all do not) and assign it to one of our trees based
on that.

Other files with names matching the font name (in particular, .csv files
corresponding to our linter output) are put into the folder matching the
font.  Files that are not in a two-level hierarchy and do not correspond to
a font are put at the top level.

Other tools (for updating the internal staging repo) work off the structure
built by this tool.
"""

__author__ = "dougfelt@google.com (Doug Felt)"

import argparse
import cStringIO
import os
import os.path
import re
import shutil
import sys
import zipfile

from fontTools import ttLib

import notoconfig

def write_data_to_file(data, root, subdir, filename):
  dstdir = os.path.join(root, subdir)
  if not os.path.exists(dstdir):
    os.mkdir(dstdir)
  with open(os.path.join(dstdir, filename), 'wb') as f:
    f.write(data)
  print 'extracted \'%s\' into %s' % (filename, subdir)


def unzip_to_directory_tree(drop_dir, filepath):
  hint_rx = re.compile(r'_((?:un)?hinted)/(.+)')
  plain_rx = re.compile(r'[^/]+')
  zf = zipfile.ZipFile(filepath, 'r')
  print 'extracting files from %s to %s' % (filepath, drop_dir)
  count = 0
  mapped_names = []
  unmapped = []
  for name in zf.namelist():
    # skip names representing portions of the path
    if name.endswith('/'):
      continue
    # get the blob
    try:
      data = zf.read(name)
    except KeyError:
      print 'did not find %s in zipfile' % name
      continue

    result = hint_rx.search(name)
    if result:
      # we know where it goes
      subdir = result.group(1)
      filename = result.group(2)
      write_data_to_file(data, drop_dir, subdir, filename)
      count += 1
      continue

    result = plain_rx.match(name)
    if not result:
      print "subdir structure without hint/unhint: '%s'" % name
      continue

    # we have to figure out where it goes.
    # if it's a .ttf file, we look for 'fpgm'
    # and 'prep' and if they are present, we put
    # it into hinted, else unhinted.
    # if it's not a .ttf file, but it starts with
    # the name of a .ttf file (sans suffix), we put
    # it in the same subdir the .ttf file went into.
    # else we put it at drop_dir (no subdir).
    if name.endswith('.ttf'):
      blobfile = cStringIO.StringIO(data)
      font = ttLib.TTFont(blobfile)
      subdir = 'hinted' if font.get('fpgm') or font.get('prep') else 'unhinted'
      write_data_to_file(data, drop_dir, subdir, name)
      count += 1

      basename = os.path.splitext(name)[0]
      mapped_names.append((basename, subdir))
      continue

    # get to these later
    unmapped.append((name, data))

  # write the remainder
  if unmapped:
    for name, data in unmapped:
      subdir = ''
      for mapped_name, mapped_subdir in mapped_names:
        if name.startswith(mapped_name):
          subdir = mapped_subdir
          break
      write_data_to_file(data, drop_dir, subdir, name)
      count += 1

  print 'extracted %d files' % count


def grab_files(dst, files):
  """Get date from each filename in files, create a folder for it, under
  dst/drops, then extract the files to it."""

  # The zip indicates that the corresponding drop is good and built from it. But
  # we might have messed up along the way, so:
  # - if we have a drop and a zip, assume it's already handled
  # - if we have a drop but no zip, assume the drop needs to be rebuilt from the zip
  # - if we have a zip and no drop
  #   - if we have new zip, complain
  #   - else rebuild the drop from the old zip
  # - else build the drop, and if successful, save the zip

  name_date_rx = re.compile(r'(.*)_(\d{4})(\d{2})(\d{2})\.zip')
  for f in files:
    filename = os.path.basename(f)
    result = name_date_rx.match(filename)
    if not result:
      print 'could not parse %s, skipping' % f
      continue
    name = result.group(1)
    date = '_'.join([d for d in result.group(2,3,4)])
    drop_dir = os.path.join(dst, 'drops', date)

    zip_dir = os.path.join(dst, 'zips')
    zip_filename = os.path.join(zip_dir, filename)
    if os.path.exists(drop_dir):
      if os.path.exists(zip_filename):
        print 'already have a Monotype drop and zip for %s' % filename
        continue
      else:
        # clean up, assume needs rebuild
        shutil.rmtree(drop_dir)
    else:
      if os.path.exists(zip_filename):
        if os.path.realpath(f) != os.path.realpath(zip_filename):
          print 'already have a zip file named %s for %s' % (zip_filename, f)
          continue

    os.mkdir(drop_dir)
    unzip_to_directory_tree(drop_dir, f)

    if not os.path.exists(zip_filename):
      print 'writing %s to %s' % (f, zip_filename)
      shutil.copy2(f, zip_filename)


def find_and_grab_files(dst, src, namere):
  """Iterate over files in src with names matching namere, and pass
  this list to grab_files."""
  filelist = []
  for f in os.listdir(src):
    path = os.path.join(src, f)
    if not os.path.isfile(path):
      continue
    if not re.search(namere, f):
      continue
    filelist.append(path)
  if not filelist:
    print "no files in %s matched '%s'" % (src, namere)
    return
  grab_files(dst, filelist)


def main():
  # The dest directory must exist and should have 'zips' and 'drops' subdirs.

  default_srcdir = os.path.expanduser('~/Downloads')
  default_dstdir = notoconfig.values.get('monotype_data')
  default_regex = r'Noto.*_\d{8}.zip'

  parser = argparse.ArgumentParser()
  parser.add_argument('-dd', '--dstdir', help='destination directory (default %s)' %
                      default_dstdir, default=default_dstdir)
  parser.add_argument('-sd', '--srcdir', help='source directory (default %s)' %
                      default_srcdir, default=default_srcdir)
  parser.add_argument('--name', help='file name regex to match ( default \'%s\'' %
                      default_regex, default=default_regex)
  parser.add_argument('--srcs', help='source files (if defined, use instead of srcdir+name)',
                      nargs="*")
  args = parser.parse_args()

  if not os.path.exists(args.dstdir):
    print '%s does not exists or is not a directory' % args.dstdir
    return

  if args.srcs:
    grab_files(args.dstdir, args.srcs)
  else:
    if not os.path.isdir(args.srcdir):
      print '%s does not exist or is not a directory' % args.srcdir
      return

    find_and_grab_files(args.dstdir, args.srcdir, args.name)

if __name__ == "__main__":
    main()
