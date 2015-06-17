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

import collections
import os
from os import path
import unicode_data
import xml.etree.cElementTree as ElementTree

from nototools import extra_locale_data

TOOLS_DIR = path.abspath(path.join(path.dirname(__file__), os.pardir))
CLDR_DIR = path.join(TOOLS_DIR, 'third_party', 'cldr')

# Maps from a less-specific tag to tuple of lang, script, region
# Keys either have a lang or 'und'.  If lang, then script or region.  If und,
# then either script or region or both.
_LIKELY_SUBTAGS = {}

def _parse_likely_subtags():
  if _LIKELY_SUBTAGS:
    return

  data_file = path.join(CLDR_DIR, 'common', 'supplemental', 'likelySubtags.xml')
  tree = ElementTree.parse(data_file)

  for tag in tree.findall('likelySubtags/likelySubtag'):
    from_tag = tag.get('from').replace('_', '-')
    to_tag = tag.get('to').split('_')
    _LIKELY_SUBTAGS[from_tag] = to_tag

  _LIKELY_SUBTAGS.update(extra_locale_data.LIKELY_SUBTAGS)


# from language elements
# lang has no script tag
_LANG_TO_REGIONS = collections.defaultdict(set)

# from language elements
# lang has no script tag
_LANG_TO_SCRIPTS = collections.defaultdict(set)

# from territory elements
# values are lang-script, script is based on likely subtag data if not present
# in the territory element data.
# if lang has script tag, the script is also in lang_to_scripts.
_REGION_TO_LANG_SCRIPTS = collections.defaultdict(set)

_LOCALE_TO_PARENT = {}

def _parse_supplemental_data():
  if _LOCALE_TO_PARENT:
    return

  # _LIKELY_SUBTAGS data used directly below
  _parse_likely_subtags()

  data_file = path.join(
      CLDR_DIR, 'common', 'supplemental', 'supplementalData.xml')
  root = ElementTree.parse(data_file).getroot()

  for language_tag in root.iter('language'):
    attribs = language_tag.attrib

    if 'alt' in attribs:
      assert attribs['alt'] == 'secondary'

    lang = attribs['type']

    if 'territories' in attribs:
      territories = set(attribs['territories'].split(' '))
      _LANG_TO_REGIONS[lang].update(territories)

    if 'scripts' in attribs:
      scripts = set(attribs['scripts'].split(' '))
      _LANG_TO_SCRIPTS[lang].update(scripts)

  for tag in root.iter('territory'):
    territory = tag.get('type')
    for child in tag:
      assert child.tag == 'languagePopulation'
#     if 'officialStatus' not in child.attrib:
#       continue  # Skip non-official languages
      lang = child.get('type')
      ix = lang.find('_')
      if ix == -1:
        key = lang + '-' + territory
        try:
          likely_tuple = _LIKELY_SUBTAGS[key]
        except:
          likely_tuple = _LIKELY_SUBTAGS[lang]
        script = likely_tuple[1]
      else:
        script = lang[ix + 1:]
        lang = lang[:ix]
      lang_script = lang + '-' + script
      _REGION_TO_LANG_SCRIPTS[territory].add(lang_script)

  # Use likely subtag data mapping script to lang to extend lang_to_scripts.
  known_scripts = set()
  for scripts in _LANG_TO_SCRIPTS.values():
    known_scripts |= scripts

  for script in known_scripts:
    und_scr = 'und-' + script
    if und_scr in _LIKELY_SUBTAGS:
      lang = _LIKELY_SUBTAGS[und_scr][0]
      if lang != 'und' and script not in _LANG_TO_SCRIPTS[lang]:
        print 'lang to scripts missing script %s for %s' % (script, lang)
        _LANG_TO_SCRIPTS[lang].add(script)

  # Use extra locale data's likely subtag info to change the supplemental
  # data we got from the language and territory elements.
  # 1) Add the script to the scripts for the language
  # 2) Add the lang_script to the lang_scripts for the region
  for tags in extra_locale_data.LIKELY_SUBTAGS.values():
    lang = tags[0]
    script = tags[1]
    region = tags[2]
    lang_scripts = _LANG_TO_SCRIPTS[lang]
    if script not in lang_scripts:
      print 'likely subtags lang %s has script %s but supplemental only has [%s]' % (
          lang, script, ', '.join(sorted(lang_scripts)))
      if len(lang_scripts) == 1:
        replacement = set([script])
        print 'replacing %s with %s' % (lang_scripts, replacement)
        _LANG_TO_SCRIPTS[lang] = replacement
      else:
        _LANG_TO_SCRIPTS[lang].add(script)
    lang_script = lang + '-' + script
    # skip ZZ region
    if region != 'ZZ' and lang_script not in _REGION_TO_LANG_SCRIPTS[region]:
      print '%s not in lang_scripts for %s, adding' % (
          lang_script, region)
      _REGION_TO_LANG_SCRIPTS[region].add(lang_script)

  for tag in root.iter('parentLocale'):
    parent = tag.get('parent')
    parent = parent.replace('_', '-')
    for locl in tag.get('locales').split(' '):
      locl = locl.replace('_', '-')
      _LOCALE_TO_PARENT[locl] = parent

  _LOCALE_TO_PARENT.update(extra_locale_data.PARENT_LOCALES)


def known_langs():
  _parse_supplemental_data()
  # Assume this is a superset of the keys in _LANG_TO_REGIONS
  return _LANG_TO_SCRIPTS.keys()


def known_regions():
  _parse_supplemental_data()
  return _REGION_TO_LANG_SCRIPTS.keys()


def lang_to_regions(lang):
  _parse_supplemental_data()
  try:
    return _LANG_TO_REGIONS[lang]
  except:
    return None

def lang_to_scripts(lang):
  _parse_supplemental_data()
  try:
    return _LANG_TO_SCRIPTS[lang]
  except:
    return None


def region_to_lang_scripts(region_tag):
  _parse_supplemental_data()
  try:
    return _REGION_TO_LANG_SCRIPTS[region_tag]
  except:
    return None


def get_likely_script(language):
  _parse_likely_subtags()
  try:
    return _LIKELY_SUBTAGS[language][1]
  except KeyError:
    print 'No likely script for %s' % language
    return 'Zzzz'


def get_likely_subtags(lang_tag):
  if not lang_tag:
    raise ValueError('empty lang tag')
  _parse_likely_subtags()
  try:
    return _LIKELY_SUBTAGS[lang_tag]
  except KeyError:
    print 'no likely subtag for %s' % lang_tag
    return ('und', 'Zzzz', 'ZZ')


_SCRIPT_METADATA = {}

def _parse_script_metadata():
  global _SCRIPT_METADATA
  data = open(path.join(
      CLDR_DIR, 'common', 'properties', 'scriptMetadata.txt')).read()
  parsed_data = unicode_data._parse_semicolon_separated_data(data)
  _SCRIPT_METADATA = {line[0]:tuple(line[1:]) for line in parsed_data}


def is_script_rtl(script):
  if not _SCRIPT_METADATA:
    _parse_script_metadata()
  try:
    return _SCRIPT_METADATA[script][5] == 'YES'
  except KeyError:
    print 'No script metadata for %s' % script
    return False


def is_rtl(lang_tag):
  tags = lang_tag.split('-')
  if len(tags) > 1:
    script = tags[1]
  else:
    script = get_likely_script(tags[0])
  return is_script_rtl(script)


_LANGUAGE_NAME_FROM_FILE_CACHE = {}

def _get_language_name_from_file(language, cldr_file_path):
  cache_key = (language, cldr_file_path)
  try:
    return _LANGUAGE_NAME_FROM_FILE_CACHE[cache_key]
  except KeyError:
    pass

  data_file = path.join(CLDR_DIR, cldr_file_path)
  try:
    root = ElementTree.parse(data_file).getroot()
  except IOError:
    _LANGUAGE_NAME_FROM_FILE_CACHE[cache_key] = None
    return None

  parent = root.find('.//languages')
  if parent is None:
    return None
  for tag in parent:
    assert tag.tag == 'language'
    if tag.get('type').replace('_', '-') == language:
      _LANGUAGE_NAME_FROM_FILE_CACHE[cache_key] = tag.text
      return _LANGUAGE_NAME_FROM_FILE_CACHE[cache_key]
  return None


def parent_locale(locale):
  if not _LOCALE_TO_PARENT:
    _parse_supplemental_data()

  if locale in _LOCALE_TO_PARENT:
    return _LOCALE_TO_PARENT[locale]
  if '-' in locale:
    return locale[:locale.rindex('-')]
  if locale == 'root':
    return None
  return 'root'


def get_native_language_name(lang_scr):
    """Get the name of a language/script in its own locale."""
    try:
      return extra_locale_data.NATIVE_NAMES[lang_scr]
    except KeyError:
      pass

    if '-' in lang_scr:
      langs = [lang_scr, lang_scr.split('-')[0]]
    else:
      langs = [lang_scr]

    locale = lang_scr
    while locale != 'root':
      filename = locale.replace('-', '_') + '.xml'
      for subdir in ['common', 'seed']:
        cldr_file_path = path.join(subdir, 'main', filename)
        for lang in langs:
          native_name = _get_language_name_from_file(lang, cldr_file_path)
          if native_name:
            return native_name
      locale = parent_locale(locale)
    return None


def _xml_to_dict(element):
  result = {}
  for child in list(element):
    if 'alt' in child.attrib:
      continue
    key = child.get('type')
    key = key.replace('_', '-')
    result[key] = child.text
  return result


_ENGLISH_LANGUAGE_NAMES = {}
_ENGLISH_SCRIPT_NAMES = {}
_ENGLISH_TERRITORY_NAMES = {}

def _parse_english_labels():
  global _ENGLISH_LANGUAGE_NAMES, _ENGLISH_SCRIPT_NAMES, _ENGLISH_TERRITORY_NAMES

  if _ENGLISH_LANGUAGE_NAMES:
    return

  data_file = path.join(CLDR_DIR, 'common', 'main', 'en.xml')
  root = ElementTree.parse(data_file).getroot()
  ldn = root.find('localeDisplayNames')

  _ENGLISH_LANGUAGE_NAMES = _xml_to_dict(ldn.find('languages'))
  _ENGLISH_SCRIPT_NAMES = _xml_to_dict(ldn.find('scripts'))
  # Shorten name of Cans for display purposes-- match the name of the font used for Cans.
  _ENGLISH_SCRIPT_NAMES['Cans'] = 'Canadian Aboriginal'
  _ENGLISH_TERRITORY_NAMES = _xml_to_dict(ldn.find('territories'))

  # Add languages used that miss names
  _ENGLISH_LANGUAGE_NAMES.update(extra_locale_data.ENGLISH_LANGUAGE_NAMES)


def get_english_script_name(script):
  """Get the name of a script in the en-US locale."""
  _parse_english_labels()
  try:
    return _ENGLISH_SCRIPT_NAMES[script]
  except KeyError:
    return script


def get_english_language_name(lang_scr):
  """Get the name of a language/script in the en-US locale."""
  _parse_english_labels()
  try:
    return _ENGLISH_LANGUAGE_NAMES[lang_scr]
  except KeyError:
    if '-' in lang_scr:
      lang, script = lang_scr.split('-')
      try:
        langName = _ENGLISH_LANGUAGE_NAMES[lang]
        name = '%s (%s script)' % (langName, _ENGLISH_SCRIPT_NAMES[script])
        print "Constructing name '%s' for %s." % (name, lang_scr)
        return name
      except KeyError:
        pass
  print 'No English name for lang \'%s\'' % lang_scr
  return None


def get_english_region_name(region):
  _parse_english_labels()
  try:
    return _ENGLISH_TERRITORY_NAMES[region]
  except KeyError:
    print 'No English name for region %s' % region
    return ''


def _read_character_at(source, pointer):
  """Reads a code point or a backslash-u-escaped code point."""
  assert source[pointer] not in ' -{}'
  if source[pointer] == '\\':
    if source[pointer + 1] == 'u':
      end_of_hex = pointer + 2
      while (end_of_hex < len(source)
         and source[end_of_hex].upper() in '0123456789ABCDEF'):
        end_of_hex += 1
      assert end_of_hex-(pointer + 2) in {4, 5, 6}
      hex_code = source[pointer + 2:end_of_hex]
      return end_of_hex, unichr(int(hex_code, 16))
    else:
      return pointer + 2, source[pointer + 1]
  else:
    return pointer + 1, source[pointer]


def unicode_set_string_to_list(us_str):
  if us_str[0] == '[':
    assert us_str[-1] == ']'
    us_str = us_str[1:-1]

  return_list = []
  pointer = 0
  while pointer < len(us_str):
    if us_str[pointer] in ' ':
      pointer += 1
    elif us_str[pointer] == '{':
      multi_char = ''
      mc_ptr = pointer+1
      while us_str[mc_ptr] != '}':
        mc_ptr, char = _read_character_at(us_str, mc_ptr)
        multi_char += char
      return_list.append(multi_char)
      pointer = mc_ptr + 1
    elif us_str[pointer] == '-':
      previous = return_list[-1]
      assert len(previous) == 1  # can't have ranges with strings
      previous = ord(previous)

      pointer, last = _read_character_at(us_str, pointer + 1)
      assert last not in [' ', '\\', '{', '}', '-']
      last = ord(last)
      return_list += [unichr(code) for code in range(previous + 1, last + 1)]
    else:
      pointer, char = read_character_at(us_str, pointer)
      return_list.append(char)

  return return_list
