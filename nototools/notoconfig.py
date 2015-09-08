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
environment and shell prefs clean."""

import os

values = {}

def _setup():
  """The config consists of lines of the form <name> = <value>.
  values will hold a mapping from the <name> to value.
  Blank lines and lines starting with '#' are ignored."""

  configfile = os.path.expanduser("~/.notoconfig")
  if os.path.exists(configfile):
    with open(configfile, "r") as f:
      for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
          continue
        k, v = line.split('=', 1)
        values[k.strip()] = v.strip()

_setup()

# convenience for common stuff, should be in local .notoconfig file.

def noto_tools(default=''):
  """Local path to git nototools git repo"""
  return values.get('noto_tools', default)

def noto_fonts(default=''):
  """Local path to git noto-font git repo"""
  return values.get('noto_fonts', default)

def noto_cjk(default=''):
  """Local path to git noto-cjk git repo"""
  return values.get('noto_cjk', default)

def noto_emoji(default=''):
  """Local path to git noto-emoji git repo"""
  return values.get('noto_emoji', default)
