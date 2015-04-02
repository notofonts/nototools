#!/usr/bin/python
# -*- coding: UTF-8 -*-
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

"""Update cldr data under third_party from local svn snapshot."""

import argparse
import contextlib
import os
import shutil
import string
import subprocess

import notoconfig

CLDR_SUBDIRS = [
  'common/main',
  'common/properties',
  'exemplars/main',
  'seed/main']

CLDR_FILES = [
  'common/supplemental/likelySubtags.xml',
  'common/supplemental/supplementalData.xml']

README_TEMPLATE = """URL: http://unicode.org/cldr/trac/export/$version/trunk
Version: r$version
License: Unicode
License File: LICENSE

Description:
CLDR data files for language and country information.

Local Modifications:
No Modifications.
"""

@contextlib.contextmanager
def temp_chdir(path):
  """Usage: with temp_chdir(path):
    do_something
  """
  saved_dir = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(saved_dir)


def _check_dir_exists(dirpath):
  if not os.path.isdir(dirpath):
    raise ValueError('%s does not exist or is not a directory' % dirpath)


def git_get_branch(repo):
  with temp_chdir(repo):
    return subprocess.check_output(['git', 'symbolic-ref', '--short', 'HEAD']).strip()


def git_is_clean(repo):
  """Ensure there are no unstaged or uncommitted changes in the repo."""

  result = True
  with temp_chdir(repo):
    subprocess.check_call(['git', 'update-index', '-q', '--ignore-submodules', '--refresh'])
    if subprocess.call(['git', 'diff-files', '--quiet', '--ignore-submodules', '--']):
      print 'There are unstaged changes in the noto branch:'
      subprocess.call(['git', 'diff-files', '--name-status', '-r', '--ignore-submodules', '--'])
      result = False
    if subprocess.call(
        ['git', 'diff-index', '--cached', '--quiet', 'HEAD', '--ignore-submodules', '--']):
      print 'There are uncommitted changes in the noto branch:'
      subprocess.call(
        ['git', 'diff-index', '--cached', '--name-status', '-r', 'HEAD', '--ignore-submodules', '--'])
      result = False
  return result


def svn_get_version(repo):
  with temp_chdir(repo):
    version_string = subprocess.check_output(['svnversion', '-c']).strip()
    colon_index = version_string.find(':')
    if colon_index >= 0:
      version_string = version_string[colon_index + 1:]
  return version_string


def svn_update(repo):
  with temp_chdir(repo):
    subprocess.check_call(['svn', 'up'], stderr=subprocess.STDOUT)


def update_cldr(noto_repo, cldr_repo, update=False):
  """Copy needed directories/files from cldr_repo to noto_repo/third_party/cldr."""

  noto_repo = os.path.abspath(noto_repo)
  cldr_repo = os.path.abspath(cldr_repo)

  noto_cldr = os.path.join(noto_repo, 'third_party/cldr')
  _check_dir_exists(noto_cldr)
  _check_dir_exists(cldr_repo)

  if not git_is_clean(noto_repo):
    print 'Please fix'
    return

  if update:
    svn_update(cldr_repo)

  # get version of cldr
  cldr_version = svn_get_version(cldr_repo)

  # prepare and create README.third_party
  readme_text = string.Template(README_TEMPLATE).substitute(version=cldr_version)
  with open(os.path.join(noto_cldr, 'README.third_party'), 'w') as f:
    f.write(readme_text)

  # remove/replace directories
  for subdir in CLDR_SUBDIRS:
    src = os.path.join(cldr_repo, subdir)
    dst = os.path.join(noto_cldr, subdir)
    print 'replacing directory %s...' % subdir
    shutil.rmtree(dst)
    shutil.copytree(src, dst)

  # replace files
  for f in CLDR_FILES:
    print 'replacing file %s...' % f
    src = os.path.join(cldr_repo, f)
    dst = os.path.join(noto_cldr, f)
    shutil.copy(src, dst)

  # git can now add everything, even removed files
  with temp_chdir(noto_cldr):
    subprocess.check_call(['git', 'add', '--', '.'])

  # print commit message
  print 'Update CLDR data to SVN r%s.' % cldr_version


def main():
  values = notoconfig.values
  parser = argparse.ArgumentParser()
  parser.add_argument('--cldr', help='directory of local cldr svn repo',
                      default=values.get('cldr', None))
  parser.add_argument('--noto', help='directory of local noto git repo',
                      default=values.get('noto', None))
  parser.add_argument('--branch', help='confirm current branch of noto git repo')
  args = parser.parse_args()

  if not args.cldr or not args.noto:
    print "need both cldr and not repository information"
    return

  if args.branch:
    cur_branch = git_get_branch(args.noto)
    if cur_branch != args.branch:
      print "Expected branch '%s' but %s is in branch '%s'." % (args.branch, args.noto, cur_branch)
      return

  update_cldr(args.noto, args.cldr)

if __name__ == '__main__':
    main()
