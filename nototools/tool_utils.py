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

"""Some common utilities for tools to use."""

import contextlib
import datetime
import os
import subprocess
import time
import zipfile

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


def check_dir_exists(dirpath):
  if not os.path.isdir(dirpath):
    raise ValueError('%s does not exist or is not a directory' % dirpath)


def check_file_exists(filepath):
  if not os.path.isfile(filepath):
    raise ValueError('%s does not exist or is not a file' % filepath)


def ensure_dir_exists(path):
  path = os.path.realpath(path)
  if not os.path.isdir(path):
    if os.path.exists(path):
      raise ValueError('%s exists and is not a directory' % path)
    print "making '%s'" % path
    os.makedirs(path)
  return path


def generate_zip_with_7za(root_dir, file_paths, archive_path):
  """file_paths is a list of files relative to root_dir, these will be the names
  in the archive at archive_path."""

  arg_list = ['7za', 'a', archive_path, '-tzip', '-mx=7', '-bd', '--']
  arg_list.extend(file_paths)
  with temp_chdir(root_dir):
    # capture but discard output
    subprocess.check_output(arg_list)


def zip_extract_with_timestamp(zippath, dstdir):
  zip = zipfile.ZipFile(zippath)
  with temp_chdir(dstdir):
    for info in zip.infolist():
      zip.extract(info.filename)
      # of course, time zones mess this up, so don't expect precision
      date_time = time.mktime(info.date_time + (0, 0, -1))
      os.utime(info.filename, (date_time, date_time))


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


def git_add_all(repo_subdir):
  """Add all changed, deleted, and new files in subdir to the staging area."""
  # git can now add everything, even removed files
  with temp_chdir(repo_subdir):
    subprocess.check_call(['git', 'add', '--', '.'])


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
