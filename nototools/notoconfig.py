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

"""Read config file for noto tools.  One could also just define some
environment variables, but using Python for this lets you keep your
environment and shell prefs clean.

This expects a file named '.notoconfig' in the users home directory.
It should contain lines consisting of a name, '=' and a path.  The
expected names are 'noto_tools', 'noto_fonts', 'noto_cjk',
'noto_emoji', and 'noto_source'.  The values are absolute paths
to the base directories of these noto repositories.

Formerly these were a single repository so the paths could all be reached
from a single root, but that is no longer the case.
"""

import os
from os import path

# 'NOTOTOOLS_DIR' and 'DEFAULT_NOTOTOOLS' apparently don't work
DEFAULT_ROOT = path.dirname(path.dirname(__file__))

values = {}

def _setup():
  """The config consists of lines of the form <name> = <value>.
  values will hold a mapping from the <name> to value.
  Blank lines and lines starting with '#' are ignored."""

  configfile = path.expanduser("~/.notoconfig")
  if path.exists(configfile):
    with open(configfile, "r") as f:
      for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
          continue
        k, v = line.split('=', 1)
        values[k.strip()] = v.strip()
  else:
    print ('# Homedir has no .notoconfig file, see ' +
           'nototools/nototools/notoconfig.py')

_setup()

# convenience for common stuff, should be in local .notoconfig file.

def noto_tools(default=''):
  """Local path to nototools git repo, defaults to root of nototools."""
  if not default:
    default = DEFAULT_ROOT
  return values.get('noto_tools', default)

def noto_fonts(default=''):
  """Local path to noto-font git repo"""
  return values.get('noto_fonts', default)

def noto_cjk(default=''):
  """Local path to noto-cjk git repo"""
  return values.get('noto_cjk', default)

def noto_emoji(default=''):
  """Local path to noto-emoji git repo"""
  return values.get('noto_emoji', default)

def noto_source(default=''):
  """Local path to noto-source git repo"""
  return values.get('noto_source', default)

def get(key):
  """Throws exception if key not present, except for noto_tools which
  defaults to the parent of the parent of this file."""
  if key not in values:
    if key == 'noto_tools':
      return DEFAULT_ROOT
    raise Exception('.notoconfig has no entry for "%s"' % key)
  return values[key]
