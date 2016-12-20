#!/usr/bin/env python
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

"""Generate name data for emoji resources. Currently in json format."""

import argparse
import collections
import glob
import json
import os
from os import path
import sys

from nototools import emoji_ordering
from nototools import tool_utils
from nototools import unicode_data

def _is_ascii_digit(cp):
  return ord('0') <= cp <= ord('9')

def _is_ascii_uppercase(cp):
  return ord('A') <= cp <= ord('Z')

_NAME_FIXES = {
    'Oclock': "O'Clock",
    'Mans': "Man's",
    'Womans': "Woman's",
    'Mens': "Men's",
    'Womens': "Women's"
}

def _unicode_name(cp, alt=None):
  name = unicode_data.name(cp, alt).title()
  for k, v in _NAME_FIXES.iteritems():
    name = name.replace(k, v)
  return name


_REGIONAL_INDICATOR_START = 0x1f1e6
_REGIONAL_INDICATOR_END = 0x1f1ff

def _is_regional_indicator(cp):
  return _REGIONAL_INDICATOR_START <= cp <= _REGIONAL_INDICATOR_END

def _regional_indicator_letter(cp):
  return unichr(cp - _REGIONAL_INDICATOR_START + ord('A'))

def _is_flag_sequence(cps):
  return len(cps) == 2 and all(_is_regional_indicator(cp) for cp in cps)


def _flag_sequence_name(cps):
  return ''.join(_regional_indicator_letter(cp) for cp in cps)


_FITZ_START = 0x1F3FB
_FITZ_END = 0x1F3FF

def _is_fitzpatrick(cp):
  return _FITZ_START <= cp <= _FITZ_END


def _is_fitz_sequence(cps):
  return len(cps) == 2 and _is_fitzpatrick(cps[1])


_FITZ_NAMES = {
    _FITZ_START: '1-2',
    _FITZ_START+1: '3',
    _FITZ_START+2: '4',
    _FITZ_START+3: '5',
    _FITZ_START+4: '6'
}

def _fitz_sequence_name(cps):
  # return '%s Type %s' % (_unicode_name(cps[0]), _FITZ_NAMES[cps[1]])
  return _unicode_name(cps[0])


def _is_keycap_sequence(cps):
  return len(cps) == 2 and cps[1] == 0x20e3


_KEYCAP_NAMES = {cp: unicode_data.name(cp)[6:] for cp in range(0x30, 0x30+10)}

def _keycap_sequence_name(cps):
  name = _KEYCAP_NAMES.get(cps[0], unicode_data.name(cps[0]))
  return 'Keycap ' + name.title()


def _create_extra_sequence_names():
  BOY = 0x1f466
  GIRL = 0x1f467
  MAN = 0x1f468
  WOMAN = 0x1f469
  HEART = 0x2764  # Heavy Black Heart
  KISS_MARK = 0x1f48b
  EYE = 0x1f441
  SPEECH = 0x1f5e8
  WHITE_FLAG = 0x1f3f3
  RAINBOW = 0x1f308
  return {
      (MAN, HEART, KISS_MARK, MAN): 'Kiss',
      (WOMAN, HEART, KISS_MARK, WOMAN): 'Kiss',
      (WOMAN, HEART, KISS_MARK, MAN): 'Kiss',
      (WOMAN, HEART, MAN): 'Couple',
      (MAN, HEART, MAN): 'Couple',
      (WOMAN, HEART, WOMAN): 'Couple',
      (MAN, GIRL): 'Family',
      (MAN, GIRL, GIRL): 'Family',
      (MAN, GIRL, BOY): 'Family',
      (MAN, BOY): 'Family',
      (MAN, BOY, BOY): 'Family',
      (MAN, WOMAN, GIRL): 'Family',
      (MAN, WOMAN, GIRL, GIRL): 'Family',
      (MAN, WOMAN, GIRL, BOY): 'Family',
      (MAN, WOMAN, BOY): 'Family',
      (MAN, WOMAN, BOY, BOY): 'Family',
      (MAN, MAN, GIRL): 'Family',
      (MAN, MAN, GIRL, GIRL): 'Family',
      (MAN, MAN, GIRL, BOY): 'Family',
      (MAN, MAN, BOY): 'Family',
      (MAN, MAN, BOY, BOY): 'Family',
      (WOMAN, GIRL): 'Family',
      (WOMAN, GIRL, GIRL): 'Family',
      (WOMAN, GIRL, BOY): 'Family',
      (WOMAN, BOY): 'Family',
      (WOMAN, BOY, BOY): 'Family',
      (WOMAN, WOMAN, GIRL): 'Family',
      (WOMAN, WOMAN, GIRL, GIRL): 'Family',
      (WOMAN, WOMAN, GIRL, BOY): 'Family',
      (WOMAN, WOMAN, BOY): 'Family',
      (WOMAN, WOMAN, BOY, BOY): 'Family',
      (EYE, SPEECH): 'I Witness',
      (WHITE_FLAG, RAINBOW): 'Rainbow Flag',
  }

_EXTRA_SEQUENCE_NAMES = _create_extra_sequence_names()

def _extra_sequence_name(cps):
  trim_cps = tuple([cp for cp in cps if cp not in [0x200d, 0xfe0f]])
  return _EXTRA_SEQUENCE_NAMES.get(trim_cps, '')


_MAN = 0x2642
_WOMAN = 0x2640
_gendered_singles = {
  0x26f9: _MAN,
  0x1f3c3: _MAN,
  0x1f3c4: _MAN,
  0x1f3ca: _MAN,
  0x1f3cb: _MAN,
  0x1f3cc: _MAN,
  0x1f46e: _MAN,
  0x1f46f: _WOMAN,
  0x1f471: _MAN,
  0x1f473: _MAN,
  0x1f477: _MAN,
  0x1f481: _WOMAN,
  0x1f482: _MAN,
  0x1f486: _WOMAN,
  0x1f487: _WOMAN,
  0x1f575: _MAN,
  0x1f645: _WOMAN,
  0x1f646: _WOMAN,
  0x1f647: _MAN,
  0x1f64b: _WOMAN,
  0x1f64d: _WOMAN,
  0x1f64e: _WOMAN,
  0x1f6a3: _MAN,
  0x1f6b4: _MAN,
  0x1f6b5: _MAN,
  0x1f6b6: _MAN,
  0x1f926: _WOMAN,
  0x1f937: _WOMAN,
  0x1f938: _MAN,
  0x1f939: _MAN,
  0x1f93c: _MAN,
  0x1f93d: _MAN,
  0x1f93e: _MAN,
}

def _gendered_single(cp):
  """Return gender of gendered single, or None if not gendered"""
  return _gendered_singles.get(cp, None)


def _is_gendered_single_sequence(cps):
  """Return True if the sequence is a gendered single (with or without
  fitzpatrik modifier).  Otherwise return False, including if there is
  an explicit gender in the sequence."""
  if 0x200d in cps:
    return False
  return any(_gendered_single(cp) is not None for cp in cps)


def _char_name(cp):
  if _is_regional_indicator(cp):
    return 'RIS ' + _regional_indicator_letter(cp)
  if _is_fitzpatrick(cp):
    return None
  if cp in [0x200d, 0xfe0f]:
    return None
  return unicode_data.name(cp, '<?>')


def _fallback_name(cps):
  return '+'.join(filter(None, (_char_name(cp) for cp in cps)))


def _sequence_name_orig(cps):
  if len(cps) == 1:
    name = _unicode_name(cps[0])
  elif _is_flag_sequence(cps):
    name = _flag_sequence_name(cps)
  elif _is_fitz_sequence(cps):
    name = _fitz_sequence_name(cps)
  elif _is_keycap_sequence(cps):
    name = _keycap_sequence_name(cps)
  else:
    name = _extra_sequence_name(cps)
    if not name:
      name = _fallback_name(cps)
  return name


def _create_gender_map():
  """The gender map maps ZWJ, emoji var sel, and fitz modifiers to None,
  and MAN, WOMAN, MALE, and FEMALE to 0xe000."""

  _strip_cps = [0x200d, 0xfe0f] + range(_FITZ_START, _FITZ_END + 1)
  _gender_cps = [0x1f468, 0x1f469, 0x2642, 0x2640]
  gender_map = {}
  for cp in _strip_cps:
    gender_map[cp] = None
  for cp in _gender_cps:
    gender_map[cp] = 0xe000
  return gender_map

_gender_map = _create_gender_map()

_gendered_names = {
    (0x2695,): 'Health Worker',
  (0x1f393,): 'Student',
  (0x1f3eb,): 'Teacher',
  (0x2696,): 'Judge',
  (0x1f33e,): 'Farmer',
  (0x1f373,): 'Cook',
  (0x1f527,): 'Mechanic',
  (0x1f3ed,): 'Factory Worker',
  (0x1f4bc,): 'Office Worker',
  (0x1f52c,): 'Scientist',
  (0x1f4bb,): 'Technologist',
  (0x1f3a4,): 'Singer',
  (0x1f3a8,): 'Artist',
  (0x2708,): 'Pilot',
  (0x1f680,): 'Astronaut',
  (0x1f692,): 'Fire Fighter',
  (0x1f46e,): 'Police Officer',
  (0x1f575,): 'Detective',
  (0x1f482,): 'Guard',
  (0x1f477,): 'Construction Worker',
  (0x1f473,): 'Person wearing Turban',
  (0x1f471,): 'Person with Blond Hair',
  (0x1f64d,): 'Frowning',
  (0x1f64e,): 'Pouting',
  (0x1f645,): 'No Good',
  (0x1f646,): 'OK',
  (0x1f481,): 'Tipping Hand',
  (0x1f64b,): 'Raising Hand',
  (0x1f647,): 'Bowing Deeply',
  (0x1f926,): 'Face Palm',
  (0x1f937,): 'Shrug',
  (0x1f486,): 'Face Massage',
  (0x1f487,): 'Haircut',
  (0x1f6b6,): 'Walking',
  (0x1f3c3,): 'Running',
  (0x1f46f,): 'Partying',
  (0x1f3cc,): 'Golfing',
  (0x1f3c4,): 'Surfing',
  (0x1f6a3,): 'Rowing',
  (0x1f3ca,): 'Swimming',
  (0x26f9,): 'Playing Ball',
  (0x1f3cb,): 'Weight Lifting',
  (0x1f6b4,): 'Bicycling',
  (0x1f6b5,): 'Mountain Biking',
  (0x1f938,): 'Doing a Cartwheel',
  (0x1f93c,): 'Wrestling',
  (0x1f93d,): 'Water Polo',
  (0x1f93e,): 'Handball',
  (0x1f939,): 'Juggling',
}

def _sequence_name(cps):
  if 0x200d not in cps:
    return _sequence_name_orig(cps)
  name = _extra_sequence_name(cps)
  if name:
    return name

  trim_cps = filter(None, [_gender_map.get(cp, cp) for cp in cps])
  name = None
  if 0xe000 in trim_cps:
    gender_tup = tuple(cp for cp in trim_cps if cp != 0xe000)
    name = _gendered_names.get(gender_tup)
    if not name:
      raise Exception('!! gender tup %s failed' % repr(gender_tup))
  if not name:
    name = _fallback_name(cps)
    raise Exception('fallback', '_'.join('%04x' % cp for cp in cps), name)
  return name


def _keep_sequence(cps):
  if _is_gendered_single_sequence(cps):
    return False
  if len(cps) > 1:
    return True
  cp = cps[0]
  if (unicode_data.is_private_use(cp) or
      unicode_data.category(cp)[0] not in ['L', 'P', 'S'] or
      _is_regional_indicator(cp) or
      _is_ascii_digit(cp) or
      cp == ord('#') or
      cp == ord('*')):
    return False
  return True


# NotoColorEmoji currently adds the following regions aliased to other flags.
_FLAG_ALIASES = {
    'BV': 'NO',
    'CP': 'FR',
    'HM': 'AU',
    'SJ': 'NO',
    'UM': 'US',
}

def _flag_name_to_estr(flag_name):
  return ''.join(unichr(
      _REGIONAL_INDICATOR_START + ord(cp) - ord('A')) for cp in flag_name)


def _add_flag_aliases(estr_to_file, added, skipped, missing):
  for src_name, dst_name in _FLAG_ALIASES.items():
    src_estr = _flag_name_to_estr(src_name)
    src_cps = [ord(cp) for cp in src_estr]
    dst_estr = _flag_name_to_estr(dst_name)
    if src_estr in estr_to_file:
      skipped.append(src_cps)
      continue
    fname = estr_to_file.get(dst_estr)
    if not fname:
      missing.append(src_cps)
      continue
    added.append(src_cps)
    estr_to_file[src_estr] = fname


def _report_info(title, cps_list):
  if not cps_list:
    return
  print '%s %d:' % (title, len(cps_list))
  for cps in sorted(cps_list):
    print '  %s (%s)' % (
        '_'.join('%04x' % cp for cp in cps),
        ','.join(unicode_data.name(cp, '') for cp in cps))


def _estr_to_file(srcdir, eo, verbose=False):
  """Return a mapping from emoji string to filename, for emoji strings
  that we don't skip.  Verifies that we have group information for each
  file that we don't skip."""

  # flag aliases we added
  added = []
  # sequences in srcdir that we don't show, and unused flag aliases
  skipped = []
  # sequences in srcdir not in the eo categories, and missing flag alias targets
  missing = []

  result = {}

  emoji_strings = eo.emoji_strings()
  for f in sorted(glob.glob(path.join(srcdir, 'emoji_u*.png'))):
    fname = path.basename(f)
    parts = fname[7:-4].split('_')
    # Omit emoji presentation variation selector, it should not be necessary.
    cps = [int(part, 16) for part in parts]
    if not _keep_sequence(cps):
      skipped.append(cps)
      continue
    estr = u''.join(unichr(cp) for cp in cps)
    if estr not in emoji_strings:
      missing.append(cps)
      continue
    result[estr] = f

  _add_flag_aliases(result, added, skipped, missing)

  if verbose:
    _report_info('added', added)
    _report_info('skipped', skipped)
    _report_info('missing', missing)
  assert not missing

  return result


def _name_data(estr, estr_to_file):
  cps = tuple([ord(cp) for cp in estr])
  name = _sequence_name(cps)
  sequence = ''.join('&#x%x;' % cp for cp in cps)
  try:
    fname = path.basename(estr_to_file[estr])
  except KeyError as e:
    print 'error', e
    print 'estr', estr, '_'.join('%04x' % ord(cp) for cp in estr)
    print '\n'.join('%s %s' % (estr, '_'.join('%04x' % ord(cp) for cp in estr))
                    for estr in estr_to_file.keys())
    raise e
  return fname, sequence, name


def generate_names(
    srcdir, outfile, ordering_file, eext=None, esep=None, force=False,
    pretty_print=False, verbose=False):
  if not path.isdir(srcdir):
    print >> sys.stderr, '%s is not a directory' % srcdir
    return

  parent = tool_utils.ensure_dir_exists(path.dirname(outfile))
  if path.exists(outfile):
    if not force:
      print >> sys.stderr, '%s already exists' % outfile
      return
    if not path.isfile(outfile):
      print >> sys.stderr, '%s is not a file' % outfile
      return

  eo = emoji_ordering.from_file(ordering_file, ext=eext, sep=esep)

  estr_to_file = _estr_to_file(srcdir, eo, verbose)

  skipped = collections.defaultdict(list)
  data = []
  for category in eo.category_names():
    name_data = []
    for estr in eo.emoji_in_category(category):
      if not estr in estr_to_file:
        skipped[category].append(estr)
      else:
        name_data.append(_name_data(estr, estr_to_file))
    data.append({'category': category, 'emojis': name_data})

  if verbose and skipped:
    # report sequences in the categories for which we have no images
    total = 0
    print '\nskipped items (no images):'
    for category in eo.category_names():
      estrs = skipped.get(category)
      if not estrs:
        continue
      count = len(estrs)
      total += count
      cps_list = [[ord(cp) for cp in estr]
                for estr in estrs]
      _report_info(category, cps_list)
    print 'skipped %d items total' % total

  with open(outfile, 'w') as f:
    indent = 2 if pretty_print else None
    separators = None if pretty_print else (',', ':')
    json.dump(data, f, indent=indent, separators=separators)
  print 'wrote %s' % outfile


def main():
  DEFAULT_OUTFILE = 'emoji/data.json'
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '-s', '--srcdir', help='directory containing images',
      metavar='dir', required = True)
  parser.add_argument(
      '-o', '--outfile', help='name of output file (default %s)' %
      DEFAULT_OUTFILE, metavar='fname', default=DEFAULT_OUTFILE)
  parser.add_argument(
      '-eo', '--emoji_ordering',
      help='name of file containing emoji ordering data',
      metavar='fname', required=True)
  parser.add_argument(
      '-ee', '--emoji_ordering_ext',
      help='treat emoji ordering file as having extension ext',
      metavar='ext')
  parser.add_argument(
      '-es', '--emoji_ordering_sep',
      help='separator for emoji ordering csv file',
      metavar='sep', default=',')
  parser.add_argument(
      '-f', '--force', help='overwrite output file if it exists',
      action='store_true')
  parser.add_argument(
      '-p', '--pretty_print', help='pretty-print json file',
      action='store_true')
  parser.add_argument(
      '-v', '--verbose', help='print progress information to stdout',
      action='store_true')
  args = parser.parse_args()
  generate_names(
      args.srcdir, args.outfile, args.emoji_ordering,
      eext=args.emoji_ordering_ext, esep=args.emoji_ordering_sep,
      force=args.force, pretty_print=args.pretty_print, verbose=args.verbose)


if __name__ == "__main__":
    main()
