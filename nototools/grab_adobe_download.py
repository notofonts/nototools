#!/usr/bin/python
#
# Copyright 2015 Google Inc. All rights reserved.
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

"""Copy downloaded font zip files from Adobe into noto directory structure.

This leverages some properties of the font drops. The drops come in
zip files that look like this, if you select the Noto Sans CJK subfolder from
the Adobe Sans Version x.xxx folder on google drive and ask to download it:
  Noto_Sans_CJK-yyyy-mm-dd.zip

This reflects the date of the download. For each zip of this type we build
a root named for the date in the drops subdir of the adobe_data tree.

The drops contain a multi-level tree:
  OTF-Fallback (these are for Android and don't go in to Noto)
  OTC (the ttc fonts, weight specific and ginormous)
  OTF-Subset (language-specific subsets, 7 weights each)
    JP (e.g. NotoSansJP-Thin.otf)
    KR
    SC
    TC
  OTF (language defaults, 7 weights plus 2 mono weights each)
    JP (e.g. NotoSansCJKjp-Thin.otf, NotoSansMonoCJKjp-Regular.otf)
    KR
    SC
    TC

The data built under the drops subdir is flat, and does not include the
fallback files.

The Noto zips from Adobe don't have any other files in them (Adobe puts their
metadata in the Source Han Sans directory). This assumes the zip is only the
Noto directory.
"""

__author__ = "dougfelt@google.com (Doug Felt)"

import argparse
import os
import os.path
import re
import shutil
import sys
import zipfile

import notoconfig


def unzip_to_directory_tree(drop_dir, filepath):
  skip_re = re.compile('.*/OTF-Fallback/.*')
  zf = zipfile.ZipFile(filepath, 'r')
  print 'extracting files from %s to %s' % (filepath, drop_dir)
  count = 0
  for name in zf.namelist():
    # skip names representing portions of the path
    if name.endswith('/'):
      continue
    # skip names for data we don't use
    if skip_re.match(name):
      continue
    # get the blob
    try:
      data = zf.read(name)
    except KeyError:
      print 'did not find %s in zipfile' % name
      continue
    dst_file = os.path.join(drop_dir, os.path.basename(name))
    with open(dst_file, 'wb') as f:
      f.write(data)
    count += 1
    print 'extracted \'%s\'' % name
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

  name_date_rx = re.compile(r'(.*)-(\d{4})-(\d{2})-(\d{2})\.zip')
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
        print 'already have an Adobe drop and zip for %s' % filename
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
  # The dest directory must exists and should have 'zips' and 'drops' subdirs.

  default_srcdir = os.path.expanduser('~/Downloads')
  default_dstdir = notoconfig.values.get('adobe_data')
  default_regex = r'Noto_Sans_CJK-\d{4}-\d{2}-\d{2}\.zip'
  parser = argparse.ArgumentParser()
  parser.add_argument('-dd', '--dstdir', help='destination directory (default %s)' %
                      default_dstdir, default=default_dstdir)
  parser.add_argument('-sd', '--srcdir', help='source directory (default %s)' %
                      default_srcdir, default=default_srcdir)
  parser.add_argument('--name', help='file name regex to match (default \'%s\')' %
                      default_regex, default=default_regex)
  parser.add_argument('--srcs', help='source files (if defined, use instead of srcdir+name)',
                      nargs='*')
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
