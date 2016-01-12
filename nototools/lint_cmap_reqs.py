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

"""Extract what lint expects for cmap from our data."""

import argparse
import sys

from nototools import lint_config
from nototools import noto_data
from nototools import noto_lint
from nototools import opentype_data
from nototools import unicode_data
from nototools import cmap_data

_PHASE_TWO_SCRIPTS = """
  Arab, Aran, Armi, Armn, Avst, Bali, Bamu, Batk, Beng, Brah, Bugi, Buhd, Cans,
  Cari, Cham, Cher, Copt, Cprt, Deva, Dsrt, Egyp, Ethi, Geor, Glag, Goth, Gujr,
  Guru, Hano, Hans, Hant, Hebr, Ital, Java, Jpan, Kali, Khar, Khmr, Knda, Kore,
  Kthi, LGC, Lana, Laoo, Lepc, Limb, Linb, Lisu, Lyci, Lydi, Mand, Mlym, Mong,
  Mtei, Mymr, Nkoo, Ogam, Olck, Orkh, Orya, Osma, Phag, Phli, Phnx, Prti, Qaae,
  Rjng, Runr, Samr, Sarb, Saur, Shaw, Sinh, Sund, Sylo, Syrc, Tagb, Tale, Talu,
  Taml, Tavt, Telu, Tfng, Tglg, Thaa, Thai, Tibt, Ugar, Vaii, Xpeo, Xsux, Yiii,
  Zsym
"""

def code_range_to_set(code_range):
  """Converts a code range output by _parse_code_ranges to a set."""
  characters = set()
  for first, last, _ in code_range:
      characters.update(range(first, last+1))
  return frozenset(characters)


_SYMBOL_SET = None

def _symbol_set():
  """Returns set of characters that should be supported in Noto Symbols.
  """
  global _SYMBOL_SET

  if not _SYMBOL_SET:
    ranges = unicode_data._parse_code_ranges(noto_data.SYMBOL_RANGES_TXT)
    _SYMBOL_SET = code_range_to_set(ranges) & unicode_data.defined_characters()
  return _SYMBOL_SET


def _cjk_set():
  """Returns set of characters that will be provided in CJK fonts.
  """
  ranges = unicode_data._parse_code_ranges(noto_data.CJK_RANGES_TXT)
  return code_range_to_set(ranges) & unicode_data.defined_characters()


def _emoji_pua_set():
  """Returns the legacy PUA characters required for Android emoji."""
  return lint_config.parse_int_ranges('FE4E5-FE4EE FE82C FE82E-FE837')


def _get_script_required(script, unicode_version, unicode_only, verbose=False):
  needed_chars = set()
  if script == "Qaae":
    # TODO: Check emoji coverage
    if not unicode_only:
      needed_chars = _emoji_pua_set()  # legacy PUA for android emoji
  elif script == "Zsym":
    if not unicode_only:
      needed_chars = _symbol_set()
  elif script == "LGC":
    needed_chars = (
        unicode_data.defined_characters(scr="Latn")
        | unicode_data.defined_characters(scr="Grek")
        | unicode_data.defined_characters(scr="Cyrl"))
    if not unicode_only:
      needed_chars -= _symbol_set()
      needed_chars -= _cjk_set()
  elif script == "Aran":
    if unicode_only:
      needed_chars = unicode_data.defined_characters(scr='Arab')
    else:
      needed_chars = noto_data.urdu_set()
  elif script in ['Hans', 'Hant', 'Jpan', 'Kore']:
      needed_chars = _cjk_set()
  else:
    needed_chars = unicode_data.defined_characters(scr=script)
    if not unicode_only:
      needed_chars -= _symbol_set()

  needed_chars &= unicode_data.defined_characters(version=unicode_version)

  if not unicode_only and script != 'Aran':
    try:
      needed_chars |= set(noto_data.EXTRA_CHARACTERS_NEEDED[script])
    except KeyError:
      pass

    try:
      needed_chars |= set(opentype_data.SPECIAL_CHARACTERS_NEEDED[script])
    except KeyError:
      pass

    try:
      needed_chars -= set(noto_data.CHARACTERS_NOT_NEEDED[script])
    except KeyError:
      pass

  if not unicode_only:
    needed_chars |= set([0, 0xd, 0x20])

  if verbose:
    print >> sys.stderr, script,

  return needed_chars


def _check_scripts(scripts):
  # TODO(dougfelt): something realer
  bad_scripts = []
  for script in scripts:
    if script[0] < 'A' or script[0] > 'Z':
      bad_scripts.append(script)
  if bad_scripts:
    print 'bad scripts: %s' % ', '.join(bad_scripts)
    raise ValueError('bad scripts')

  return set(scripts)


def get_cmap_data(scripts, unicode_version, unicode_only, verbose):
  metadata = cmap_data.create_metadata('lint_cmap_reqs', [
      ('unicode_version', unicode_version),
      ('unicode_only', unicode_only)])
  tabledata = cmap_data.create_table_from_map({
      script : _get_script_required(
          script, unicode_version, unicode_only, verbose)
      for script in sorted(scripts)
    })
  return cmap_data.CmapData(metadata, tabledata)


def main():
  DEFAULT_UNICODE_VERSION = 9.0

  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--scripts', help='list of pseudo-script codes, empty for all '
      'phase 2 scripts', metavar='code', nargs='*')
  parser.add_argument(
      '--unicode_version', help='version of unicode to use (default %s)' %
      DEFAULT_UNICODE_VERSION, metavar='version', type=float,
      default=DEFAULT_UNICODE_VERSION)
  parser.add_argument(
      '--unicode_only', help='only use unicode data, not noto-specific data',
      action='store_true')
  parser.add_argument(
      '--outfile', help='write to output file, otherwise to stdout',
      metavar='fname', nargs='?', const='-default-')
  parser.add_argument(
      '--verbose', help='log to stderr as each script is complete',
      action='store_true')
  args = parser.parse_args()

  if not args.scripts:
    scripts = set(s.strip() for s in _PHASE_TWO_SCRIPTS.split(','))
  else:
    scripts = _check_scripts(args.scripts)

  cmapdata = get_cmap_data(
      scripts, args.unicode_version, args.unicode_only, args.verbose)
  if args.outfile:
    if args.outfile == '-default-':
      args.outfile = 'lint_cmap_%s.xml' % args.unicode_version
    print >> sys.stderr, 'writing %s' % args.outfile
    cmap_data.write_cmap_data_file(cmapdata, args.outfile, pretty=True)
  else:
    print cmap_data.write_cmap_data(cmapdata, pretty=True)

if __name__ == "__main__":
  main()
