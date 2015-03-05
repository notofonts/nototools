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

"""Read config file for noto tools"""

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
