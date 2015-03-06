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

"""Update internal svn repo with .ttf files from unpacked font drops.

This checks the font files direct from the vendor to our internal repo.
Other files are not checked in at the moment.

This uses compare_summary to generate a comment for the submit, since
we can't view the file contents, just so we have some idea of what is
going in."""

__author__ = 'dougfelt@google.com (Doug Felt)'

import argparse
import filecmp
import os
import os.path
import re
import shutil
import subprocess
import sys

import notoconfig
import compare_summary

class RedirectStdout(object):
  """Redirect stdout to file."""
  def __init__(self, filename):
    self._filename = filename

  def __enter__(self):
    self._stdout = sys.stdout
    sys.stdout = open(self._filename, 'w')

  def __exit__(self, etype, evalue, etraceback):
    file = sys.stdout
    sys.stdout = self._stdout
    try:
      file.close()
    except e:
      if not etype:
        raise e
    # else raise the original exception

def push_to_noto_alpha(alphadir, srcdir):
  # strip possible trailing slash for later relpath manipulations
  alphadir = os.path.normpath(alphadir)
  srcdir = os.path.normpath(srcdir)

  # could try to use pysvn, but that would be a separate dependency
  # poke svn first in case there's some issue with username/pw, etc.
  os.chdir(alphadir)
  print 'Updating svn.'
  subprocess.check_call(['svn', 'up'], stderr=subprocess.STDOUT)

  # TODO(dougfelt): make sure there's nothing already staged in the
  # repo, and that there's no files in the alpha tree that aren't
  # actually part of the repo.

  # collect file info, we do this so we can generate msg header
  font_paths = []
  added = 0
  updated = 0
  for root, dirs, files in os.walk(srcdir):
    for file in files:
      if file.endswith('.ttf'):
        src_path = os.path.join(root, file)
        rel_path = src_path[len(srcdir)+1:]
        dst_path = os.path.join(alphadir, rel_path)
        # skip files that are the same as targets
        if not os.path.exists(dst_path):
          added += 1
          font_paths.append(src_path)
        elif True or not filecmp.cmp(src_path, dst_path):
          updated += 1
          font_paths.append(src_path)

  if not font_paths:
    print 'All .ttf files compare identical.  Exiting.'
    return

  # summarize fonts in this commit
  name_rx = re.compile(r'.*/Noto(?:Sans|Serif)?(.+?)(?:UI)?-.*')
  name_info = {}
  for f in font_paths:
    hinted = f.find('unhinted') == -1
    result = name_rx.match(f)
    if not result:
      raise ValueError('Could not match root font name in %s' % f)
    root_name = result.group(1)
    new_label = 'h' if hinted else 'u'
    cur_label = name_info.get(root_name, None)
    if cur_label:
      if cur_label.find(new_label) != -1:
        new_label = None
      else:
        # Using 'uh' would cause find to fail, if we processed unhinted first.
        # Which we don't, but relying on that is kind of obscure.
        new_label = 'h/u'
    if new_label:
      name_info[root_name] = new_label
    names = ', '.join(sorted(['%s(%s)' % (k, v) for k, v in name_info.iteritems()]))

  # get date of the drop from srcdir
  result = re.search(r'\d{4}_\d{2}_\d{2}', srcdir)
  if not result:
    raise ValuError('no date in ' + srcdir)
  date_str = result.group().replace('_', '/')

  if added:
    if updated:
      operation = 'Add/Update'
    else:
      operation = 'Add'
  else:
    operation = 'Update'
  one_line_msg = '%s %s from delivery on %s.' % (operation, names, date_str)
  print 'msg: ' + one_line_msg

  # generate compare file to use as checkin log
  with RedirectStdout('/tmp/svn_checkin.txt'):
    print one_line_msg
    print
    compare_summary.compare_summary(
      alphadir, srcdir, compare_summary.tuple_compare, False, False, True, False)


  # make the changes
  for src_path in font_paths:
    rel_path = src_path[len(srcdir)+1:]
    dst_path = os.path.join(alphadir, rel_path)
    need_add = not os.path.exists(dst_path)
    # assume if it exists, its under version control
    print ('adding ' if need_add else 'editing ') + rel_path
    shutil.copy2(src_path, dst_path)
    if need_add:
      subprocess.check_call(['svn', 'add', rel_path], stderr=subprocess.STDOUT)

  # commit the change
  # leave this out for now, it's useful to check before the commit to make sure
  # nothing screwed up.
  # subprocess.check_call(['svn', 'commit', '-F', log_msg_file],
  #                       stderr=subprocess.STDOUT)

def main():
  values = notoconfig.values

  parser = argparse.ArgumentParser()
  parser.add_argument('srcdir', help='source to push to noto-alpha')
  parser.add_argument('--alpha', help='local noto-alpha svn repo',
                      default=values.get('alpha', None))
  args = parser.parse_args()

  if not os.path.isdir(args.srcdir):
    print '%s does not exist or is not a directory' % args.srcdir
    return

  if not os.path.exists(args.alpha):
    print '%s does not exist or is not a directory' % args.alpha

  push_to_noto_alpha(args.alpha, args.srcdir)

if __name__ == '__main__':
    main()
