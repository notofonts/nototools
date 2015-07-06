#!/usr/bin/python
#
# Copyright 2014 Google Inc. All rights reserved.
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
"""Finds potential problems in Noto fonts."""

__author__ = (
    "roozbeh@google.com (Roozbeh Pournader), "
    "cibu@google.com (Cibu Johny), "
    "behdad@google.com (Behdad Esfahbod), and "
    "stuartg@google.com (Stuart Gill)")


import argparse
import collections
import itertools
import json
import math
import os
import re
import sys

from fontTools import subset
from fontTools import ttLib
from fontTools.misc import arrayTools
from fontTools.misc import bezierTools
from fontTools.pens import basePen

from nototools import noto_data
from nototools import font_data
from nototools import lint_config
from nototools import notoconfig
from nototools import opentype_data
from nototools import render
from nototools import unicode_data

NOTO_URL = "http://code.google.com/p/noto/"
NOTO_NEW_URL = "http://www.google.com/get/noto/"

# from wikipedia windows 1252 page.  As of windows 98.
WIN_ANSI_CODEPOINTS = (
    '0000-007f 00A0-00ff 20ac 201a 0192 201e 2026 2020 2021 02c6 2030 0160 2039 0152 017d'
    '2018 2019 201c 201d 2022 2013 2014 02dc 2122 0161 203a 0153 017e 0178')

def all_scripts():
    """Extends unicode scripts with pseudo-script 'Urdu'."""
    result = set(unicode_data.all_scripts())
    result.add('Urdu')
    return frozenset(result)


def human_readable_script_name(script):
    """Supports 'Urdu' pseudo-script."""
    if script == 'Urdu':
        return 'Urdu'
    return unicode_data.human_readable_script_name(script)


def script_code(compact_script):
    """Supports 'Urdu' pseudo-script."""
    if compact_script == 'Urdu':
        return 'Urdu'
    return unicode_data.script_code(compact_script)


def printable_unicode_range(input_char_set):
    char_set = set(input_char_set) # copy
    parts_list = []
    while char_set:
        last = first = min(char_set)
        while last in char_set:
            char_set.remove(last)
            last += 1
        if last == first + 1:
            part = "%04X" % first
        else:
            part = "%04X..%04X" % (first, last-1)
        parts_list.append(part)
    return ", ".join(parts_list)


def next_circular_point(current_point, start_of_range, end_of_range):
    if current_point == end_of_range:
        return start_of_range
    else:
        return current_point + 1


def curve_between(
    coordinates, start_at, end_at, start_of_contour, end_of_contour):
    """Returns indices of a part of a contour between start and end of a curve.

    The contour is the cycle between start_of_contour and end_of_contour,
    and start_at and end_at are on-curve points, and the return value
    is the part of the curve between them.
    Args:
      coordinates: An slicable object containing the data.
      start_at: The index of on-curve beginning of the range.
      end_at: The index of on-curve end of the range.
      start_of_contour: The index of beginning point of the contour.
      end_of_contour: The index of ending point of the contour.
    Returns:
      A list of coordinates, including both start_at and end_at. Will go around
      the contour if necessary.
    """
    if end_at > start_at:
        return list(coordinates[start_at:end_at+1])
    elif start_of_contour == end_of_contour:  # single-point contour
        assert start_at == end_at == start_of_contour
        return [coordinates[start_at]]
    else:  # the curve goes around the range
        return (list(coordinates[start_at:end_of_contour+1]) +
                list(coordinates[start_of_contour:end_at+1]))


def curve_has_off_curve_extrema(curve):
    """Checks if a curve has off-curve extrema.

    Args:
      curve: a list of coordinates for the curve, where the first and the last
        coordinates are on-curve points, and the rest are off-curve.
    Returns:
      A boolean value, True if there are off-curve extrema,
      False if there are none.
    """
    if len(curve) <= 2:  # It's a straight line
        return False

    angles = []
    prev_x, prev_y = curve[0]
    for curr_x, curr_y in curve[1:]:
        angle = math.atan2(curr_y - prev_y, curr_x - prev_x)
        angles.append(angle)
        prev_x, prev_y = curr_x, curr_y

    # For the curve to have no local extrema, the angles must all fall in the
    # same quartet of the plane (e.g. all being between pi/2 and pi).
    #
    # There's a painful edge case, where an angle is equal to pi, and is
    # acceptable as both +pi and -pi for the logic that comes after. But since
    # the return value of math.atan2 is always in (-pi, +pi], we'll miss the -pi
    # case, resulting in false positives.
    #
    # For these cases, we check for the curve being proper once with all of
    # these set to +pi and then with all set to -pi. If the curve is proper in
    # at least one case, we assume the curve has no missing extrema.

    ninety_deg = math.pi/2
    score = 0
    for sign in [-1, +1]:
        angles = [sign*math.pi if math.fabs(angle) == math.pi else angle
                  for angle in angles]
        min_quarter = math.floor(min(angles) / ninety_deg)
        max_quarter = math.ceil(max(angles) / ninety_deg)
        if math.fabs(max_quarter - min_quarter) > ninety_deg:
            score += 1

    if score == 2:  # The curve failed the test in both cases
        return out_of_box_size(curve)

    return 0

# Finds out the how far away the off-curve extrema lies from the on-curve
# points. This is done by comparing the bounding box of the endpoints with that
# of the bezier curve. If there are implicit on-curve points, the curve is
# split up into a sequence of simple 3-point curves by inserting those implicit
# points.
def out_of_box_size(curve):
    if len(curve) < 3:
        return 0

    if len(curve) > 3:
        # If curve has more than 3 points, then it has implicit on-curve points.
        # First two off-curve points.
        ax, ay = curve[1]
        bx, by = curve[2]
        # Implicit point is the mid point of first two off-curve points.
        implicit_point = ((ax + bx)/2, (ay + by)/2)
        first_curve = curve[:2] + [implicit_point]
        remaining_curve = [implicit_point] + curve[2:]
    else:
        # Curve with exact 3 points has no implicit on-curve point.
        first_curve = curve
        remaining_curve = []

    # Endpoints of the first curve.
    ax, ay = first_curve[0]
    bx, by = first_curve[-1]
    # Bounding box for just the endpoints.
    ex1, ey1, ex2, ey2 = min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)
    # Bounding box for the bezier curve.
    bx1, by1, bx2, by2 = bezierTools.calcQuadraticBounds(*first_curve)

    # Bounding box of the bezier will contain that of the endpoints.
    # The out-of-box size for the entire curve will be maximum of the deviation
    # for the first curve and that of the remaining curve.
    return max(ex1 - bx1, ey1 - by1, bx2 - ex2, by2 - ey2,
               out_of_box_size(remaining_curve))

def calc_bounds(piece):
    if len(piece) == 2:
        return arrayTools.normRect(piece[0] + piece[1])
    else:
        return bezierTools.calcQuadraticBounds(piece[0], piece[1], piece[2])


def interpolate(start, end, amount):
    return start + amount * (end - start)


def interpolate_segment(segment, amount):
    return (interpolate(segment[0][0], segment[1][0], amount),
            interpolate(segment[0][1], segment[1][1], amount))


def cut_piece_in_half(piece):
    if len(piece) == 2:
        mid_point = interpolate_segment(piece, 0.5)
        return (piece[0], mid_point), (mid_point, piece[1])
    else:
        return bezierTools.splitQuadraticAtT(
            piece[0], piece[1], piece[2],
            0.5)

def cut_ends(piece, cut_amount):
    if len(piece) == 2:
        return (interpolate_segment(piece, cut_amount),
                interpolate_segment(piece, 1 - cut_amount))
    else:
        return bezierTools.splitQuadraticAtT(
            piece[0], piece[1], piece[2],
            cut_amount, 1 - cut_amount)[1]


def probably_intersect(piece1, piece2):
    bounds1 = calc_bounds(piece1)
    bounds2 = calc_bounds(piece2)
    return arrayTools.sectRect(bounds1, bounds2)[0]


_EPSILON = 1.0/(2**14)
_MAX_DEPTH = 30

def curve_pieces_intersect(piece1, piece2, ignore_ends):
    if ignore_ends:
        piece1 = cut_ends(piece1, _EPSILON)
        piece2 = cut_ends(piece2, _EPSILON)

    # If we are not ignoring end points, let's quickly check for end point
    # collision
    if not ignore_ends and {piece1[0], piece1[-1]} & {piece2[0], piece2[-1]}:
        return True

    pairs_to_investigate = collections.deque()
    if probably_intersect(piece1, piece2):
        pairs_to_investigate.append((piece1, piece2, 0))

    while True:
        if not pairs_to_investigate:
            return False
        section1, section2, level = pairs_to_investigate.popleft()
        section11, section12 = cut_piece_in_half(section1)
        section21, section22 = cut_piece_in_half(section2)
        for first_section in [section11, section12]:
            for second_section in [section21, section22]:
                if probably_intersect(first_section, second_section):
                    if level > _MAX_DEPTH:
                        return True
                    else:
                        pairs_to_investigate.append(
                            (first_section, second_section, level+1))

def to_float_tuples(curve):
    coord_list = []
    for coords in curve:
        coord_list.append(
            (float(coords[0]), float(coords[1]))
        )
    return tuple(coord_list)


def curves_intersect(contour_list):
    """Takes a list of contours and tells if any two curves in them intersect.
    Returns a message string with an error, or None if ok.
    """
    all_contours = []
    for contour in contour_list:
        contour_pieces = []
        for curve in contour:
            if len(curve) == 2:
                contour_pieces.append(to_float_tuples(curve))
            elif len(curve) > 2:
                last_point = curve[0]
                for curve_part in basePen.decomposeQuadraticSegment(curve[1:]):
                    contour_pieces.append(
                        to_float_tuples((last_point,) + curve_part))
                    last_point = curve_part[1]
        all_contours.append(contour_pieces)

    for contour_pieces in all_contours:
        for piece in contour_pieces:
            if piece[0] == piece[-1]:
                return 'start and end segments match: %s' % str(piece[0])

    all_pieces = sum(all_contours, [])
    if len(set(all_pieces)) != len(all_pieces):
        print 'some pieces are duplicates' # No piece should be repeated

    adjacent_pairs = set()
    for contour_pieces in all_contours:
        for i in range(len(contour_pieces)-1):
            adjacent_pairs.add(
                frozenset({contour_pieces[i], contour_pieces[i+1]}))
        if len(contour_pieces) > 2:
            adjacent_pairs.add(
                frozenset({contour_pieces[-1], contour_pieces[0]}))

    for piece1, piece2 in itertools.combinations(all_pieces, 2):
        # FIXME(roozbeh): we are ignoring one edge case: where end points
        # of the wrong side of an adjacent pair overlap. For example, if
        # a contour curves from A to B, then immediately back to A, and then
        # on to C, we won't catch it.
        ok_to_intersect_at_ends = frozenset({piece1, piece2}) in adjacent_pairs
        if curve_pieces_intersect(piece1, piece2, ok_to_intersect_at_ends):
            return 'intersection %s and %s' % (piece1, piece2)

    return None


def font_version(font):
    return font_data.get_name_records(font)[5]


def printable_font_revision(font, accuracy=2):
    font_revision = font["head"].fontRevision
    font_revision_int = int(font_revision)
    font_revision_frac = int(
        round((font_revision - font_revision_int) * 10**accuracy))

    font_revision_int = str(font_revision_int)
    font_revision_frac = str(font_revision_frac).zfill(accuracy)
    return font_revision_int+"."+font_revision_frac


def printable_font_versions(font):
    version = font_version(font)
    match = re.match(r"Version (\d{1,5})\.(\d{1,5})", version)
    major_version = match.group(1)
    minor_version = match.group(2)
    accuracy = len(minor_version)

    font_revision = printable_font_revision(font, accuracy)
    if font_revision == major_version+"."+minor_version:
        return version
    else:
        return "%s (font revision in 'head' table: %s)" % (
            version, font_revision)


FONT_STYLES = [
    "Sans",
    "Serif",
    "Kufi",
    "Naskh",
    "Nastaliq",
    "Emoji",
]

CJK_FONT_STYLES = [
    "Sans"
]

FONT_WEIGHTS = [
    "Regular",
    "Bold",
    "Italic",
    "BoldItalic",
]

CJK_FONT_WEIGHTS = [
    "Light",
    "DemiLight",
    "Thin",
    "Regular",
    "Medium",
    "Bold",
    "Black"
]

FONT_VARIANTS = [
    "UI",
    # The next three are for Syriac
    "Eastern",
    "Western",
    "Estrangela",
]

CJK_FONT_VARIANTS = [
    "JP",
    "KR",
    "SC",
    "TC",
    "CJKjp",
    "CJKkr",
    "CJKsc",
    "CJKtc"
]

CJK_VARIANT_NAMES = {
    "JP": "JP",
    "KR": "KR",
    "SC": "SC",
    "TC": "TC",
    "CJKjp": "CJK JP",
    "CJKkr": "CJK KR",
    "CJKsc": "CJK SC",
    "CJKtc": "CJK TC"
}

CJK_VARIANT_TO_SCRIPT = {
    "JP": "Jpan",
    "KR": "Kore",
    "SC": "Hans",
    "TC": "Hant",
    "CJKjp": "Jpan",
    "CJKkr": "Kore",
    "CJKsc": "Hans",
    "CJKtc": "Hant"
}

HARD_CODED_FONT_INFO = {
    "AndroidEmoji.ttf": ("Sans", "Qaae", None, "Regular"),
    "DroidEmoji.ttf": ("Sans", "Qaae", None, "Regular"),
    "NotoEmoji-Regular.ttf": ("", "Qaae", None, "Regular"),
    "NotoNaskh-Regular.ttf": ("Naskh", "Arab", None, "Regular"),
    "NotoNaskh-Bold.ttf": ("Naskh", "Arab", None, "Bold"),
    "NotoNaskhUI-Regular.ttf": ("Naskh", "Arab", "UI", "Regular"),
    "NotoNaskhUI-Bold.ttf": ("Naskh", "Arab", "UI", "Bold"),
    "NotoSansCypriotSyllabary-Regular.ttf": ("Sans", "Cprt", None, "Regular"),
    "NotoSansEmoji-Regular.ttf": ("Sans", "Qaae", None, "Regular"),
    "NotoSansKufiArabic-Regular.ttf": ("Kufi", "Arab", None, "Regular"),
    "NotoSansKufiArabic-Bold.ttf": ("Kufi", "Arab", None, "Bold"),
    "NotoSansSymbols-Regular.ttf": ("Sans", "Zsym", None, "Regular"),
    "NotoNastaliqUrduDraft.ttf": ("Nastaliq", "Urdu", None, "Regular")
}

MAX_UI_HEIGHT = 2163
MIN_UI_HEIGHT = -555
ASCENT = 2189
DESCENT = -600


_last_printed_file_name = None


def make_compact_scripts_regex(scripts=None):
    """Creates a regular expression that accepts all compact scripts names.
    """
    if scripts == None:
        scripts = all_scripts()
    scripts = {human_readable_script_name(script).translate(None, '_ ') for script in scripts}
    return '|'.join(scripts)


FontProps = collections.namedtuple(
'FontProps',
'file_path, family, style, script, variant, weight, vendor, char_version, '
'is_cjk, is_mono, is_hinted, is_ui, is_noto, is_google')


def font_properties_from_name(file_path):
    """Use the font name and parent directory to determine the following properties:
    - file_path
    - family
    - style
    - script (code)
    - variant (e.g. UI)
    - weight (and slant)
    - vendor (used for vendor filter in lint_config)
    - char_version (unicode version e.g. for script to codepoint mapping)
    - is_cjk
    - is_mono
    - is_hinted
    - is_ui
    - is_noto
    These are returned as a map."""

    is_cjk = False
    is_mono = False
    is_google = True

    filename_error = ''
    # by default, don't require characters after this version
    char_version = 6.0

    file_name = file_path.split("/")[-1]
    fontname_regex = (
        "(Noto|Arimo|Tinos|Cousine)"
        + "(?P<style>" + "|".join(FONT_STYLES) + ")?"
        + "(?P<script>" + make_compact_scripts_regex() + ")?"
        + "(?P<variant>" + "|".join(FONT_VARIANTS) + ")?"
        + "-"
        + "(?P<weight>" + "|".join(FONT_WEIGHTS) + ")"
        + ".ttf$")
    match = re.match(fontname_regex, file_name)
    if match:
        family, style, compact_script, variant, weight = match.groups()
        if compact_script:
          script = script_code(compact_script)
          assert script != "Zzzz"
        elif style in ["Sans", "Serif"]:
            script = "Latn"  # LGC really
        elif family != 'Noto':
          script = "Latn" # LGC for Tinos and Arimo
        else:
            style, script, variant, weight = HARD_CODED_FONT_INFO[
                file_name]
            if style != '': # Emoji, OK for it to not have script
              filename_error = 'script'
    else:
        cjkfontname_regex = (
        "Noto"
        + "(?P<style>" + "|".join(CJK_FONT_STYLES) + ")"
        + "(?P<mono>Mono)?"
        + "(?P<variant>" + "|".join(CJK_FONT_VARIANTS) + ")?"
        + "-"
        + "(?P<weight>" + "|".join(CJK_FONT_WEIGHTS) + ")"
        + ".otf$")
        match = re.match(cjkfontname_regex, file_name)
        if match:
            family = 'Noto'
            style, mono, variant, weight = match.groups()
            script = CJK_VARIANT_TO_SCRIPT[variant]
            is_cjk = True
            is_mono = (mono == "Mono")
        else:
            style, script, variant, weight = HARD_CODED_FONT_INFO[
                file_name]
            filename_error = 'name'

    is_hinted = "/hinted" in file_path or "_hinted" in file_name

    is_ui = (variant == "UI")

    is_noto = family == 'Noto'
    if not is_noto:
      # for Arimo and Tinos, require coverage up to Unicode 8
      char_version = 8.0

    vendor = 'Adobe' if is_cjk else 'Monotype'

    return (FontProps(file_path, family, style, script, variant, weight, vendor, char_version,
                      is_cjk, is_mono, is_hinted, is_ui, is_noto, is_google),
            filename_error)


def check_font(font_props, filename_error,
               lint_spec, runlog=False, skiplog=False,
               csv_flag=False, info_flag=False,
               extrema_details=True):

    def warn(category, message, details=True):
        global _last_printed_file_name

        interesting_part_of_file_name = ",".join(font_props.file_path.split("/")[-2:])
        if interesting_part_of_file_name != _last_printed_file_name:
            _last_printed_file_name = interesting_part_of_file_name
            if not csv_flag:
                print "Automatic testing for '%s', %s:" % (
                    interesting_part_of_file_name,
                    printable_font_versions(font))

        # Assumes "info" warning only and always comes at the end of
        # processing a file.
        if category is "info":
            def pluralize_errmsg(count):
                if count == 0:
                    return "no issues"
                elif count == 1:
                    return "1 issue"
                else:
                    return "%d issues" % count

            if not csv_flag:
                ec = err_count[0]
                sc = suppressed_err_count[0]
                if not sc:
                  print "Found %s." % pluralize_errmsg(ec)
                else:
                  print "Found %s (%s hidden)." % (pluralize_errmsg(ec),
                                                   "all" if sc == ec else sc)
            if not info_flag:
                return

        err_count[0] += 1

        if not details:
            suppressed_err_count[0] += 1
            return

        if csv_flag:
            print ('%s,%s,%s,%s,%s,%s,%s,%s,"%s"' % (
                human_readable_script_name(font_props.script),
                font_props.style,
                font_props.variant if font_props.variant else '',
                font_props.weight,
                font_data.get_name_records(font)[8].split()[0],
                category,
                interesting_part_of_file_name,
                printable_font_revision(font),
                message)).encode('UTF-8')
        else:
            if category is "info":
                print "[informational]",
            print message.encode('UTF-8')
        sys.stdout.flush()


    def code_range_to_set(code_range):
        """Converts a code range output by _parse_code_ranges to a set."""
        characters = set()
        for first, last, _ in code_range:
            characters.update(range(first, last+1))
        return frozenset(characters)

    def _symbol_set():
        """Returns set of characters that should be supported in Noto Symbols.
        """
        ranges = unicode_data._parse_code_ranges(noto_data.SYMBOL_RANGES_TXT)
        return code_range_to_set(ranges) & unicode_data.defined_characters()

    def _cjk_set():
        """Returns set of characters that will be provided in CJK fonts.
        """
        ranges = unicode_data._parse_code_ranges(noto_data.CJK_RANGES_TXT)
        return code_range_to_set(ranges) & unicode_data.defined_characters()


    def check_name_table():
        if not tests.check('name'):
          return

        if font_props.is_cjk:
           check_name_table_cjk()
           return

        names = font_data.get_name_records(font)

        # Check family name
        expected_family_name = font_props.family
        if font_props.style:
            # emoji has no style
            # the name comes from the script alone
            expected_family_name += ' ' + font_props.style
        if font_props.script != 'Latn' and font_props.is_google:
            expected_family_name += ' ' + human_readable_script_name(font_props.script)
        if font_props.variant:
            expected_family_name += ' ' + font_props.variant
        if font_props.weight == 'BoldItalic':
            expected_subfamily_name = 'Bold Italic'
        else:
            expected_subfamily_name = font_props.weight

        expected_full_name = expected_family_name
        expected_postscript_name = expected_family_name.replace(' ', '')
        if font_props.weight != 'Regular':
            expected_full_name += ' ' + expected_subfamily_name
            expected_postscript_name += (
                '-' + expected_subfamily_name.replace(' ', ''))

        if tests.check('name/copyright') and font_props.is_google and not re.match(
            r'Copyright 201\d Google Inc. All Rights Reserved.$', names[0]):
            warn("Copyright",
                 "Copyright message doesn't match template: '%s'." % names[0])

        if tests.check('name/family') and names[1] != expected_family_name:
            warn("Family name",
                 "Font family name is '%s', but was expecting '%s'." % (
                     names[1], expected_family_name))

        if tests.check('name/subfamily') and names[2] != expected_subfamily_name:
            warn("Sub-family name",
                 "Font subfamily name is '%s', but was expecting '%s'." % (
                     names[2], expected_subfamily_name))

        if tests.check('name/full') and names[4] != expected_full_name:
            warn("Font name",
                 "Full font name is '%s', but was expecting '%s'." % (
                     names[4], expected_full_name))

        # TODO(roozbeh): Make sure the description field contains information on
        # whether or not the font is hinted

        if tests.check('name/version'):
            match = re.match(r"Version (\d{1,5})\.(\d{1,5})", names[5])
            if match:
                major_version = match.group(1)
                minor_version = match.group(2)
                if ((0 <= int(major_version) <= 65535)
                    and (0 <= int(minor_version) <= 65535)):
                    match_end = names[5][match.end():]
                    if tests.check('name/version/hinted_suffix'):
                        if (font_props.is_google and
                            (font_props.is_hinted and match_end != "") or
                            (not font_props.is_hinted and match_end not in ["", " uh"])):
                            warn(
                                "Version",
                                "Version string '%s' has extra characters at its end." %
                                names[5])
                    accuracy = len(minor_version)
                    font_revision = printable_font_revision(font, accuracy)
                    if (tests.check('name/version/match_head') and
                        font_revision != major_version + "." + minor_version):
                        warn("Font Revision", "fontRevision in 'head' table is %s, "
                             "while font version in 'name' table is %s.%s." % (
                                 font_revision, major_version, minor_version))
                else:
                    if tests.check('name/version/out_of_range'):
                        warn("Version",
                             "Version string has numerical parts out of "
                             "[0, 65535]: '%s'." % names[5])
            else:
                if tests.check('name/version/expected_pattern'):
                    warn("Version", "Version string is irregular: '%s'." % names[5])

        if tests.check('name/postscript') and names[6] != expected_postscript_name:
            warn("Postscript name",
                 "Postscript name is '%s', but was expecting '%s'." % (
                     names[6], expected_postscript_name))

        if tests.check('name/trademark'):
            if 7 not in names:
                warn("Trademark", "Trademark in 'name' table is not set.")
            elif font_props.is_google and names[7] != "%s is a trademark of Google Inc." % family:
                warn("Trademark",
                     "Trademark message doesn't match template: '%s'." % names[7])

        if tests.check('name/manufacturer') and 8 not in names:
            warn("Manufacturer",
                 "Manufacturer name in 'name' table is not set.")

        if tests.check('name/designer') and 9 not in names:
            warn("Designer", "Designer name in 'name' table is not set.")

        if tests.check('name/description') and 10 not in names:
            warn("Description",
                 "The description field in 'name' table is not set.")

        if tests.check('name/vendor_url'):
            if 11 not in names:
                warn("Vendor", "The Vendor URL field in 'name' table is not set.")
            elif names[11] != NOTO_URL:
                warn("Vendor",
                     "Vendor URL field doesn't match template: '%s'." % names[11])

        if tests.check('name/designer_url'):
            if 12 not in names:
                warn("Designer",
                     "The Designer URL field in 'name' table is not set.")
            elif not names[12].startswith('http://'):
                warn("Designer",
                     "The Designer URL field in 'name' table is not an "
                     "http URL: '%s'." % names[12])

        if tests.check('name/license'):
            if 13 not in names:
                warn("License",
                     "The License field in 'name' table is not set.")
            elif names[13] != "Licensed under the Apache License, Version 2.0":
                warn("License",
                     "License message doesn't match template: '%s'." % names[13])

        if tests.check('name/license_url'):
            if 14 not in names:
                warn("License",
                     "The License URL in 'name' table is not set.")
            elif names[14] != "http://www.apache.org/licenses/LICENSE-2.0":
                warn("License",
                     "License URL doesn't match template: '%s'." % names[14])


    def check_name_table_cjk():
        names = font_data.get_name_records(font)

        # Check family name
        expected_family_name = 'Noto ' + font_props.style
        if font_props.is_mono:
            expected_family_name += ' Mono'
        if font_props.variant:
            expected_family_name += ' ' + CJK_VARIANT_NAMES[font_props.variant]
        expected_family_name += ' ' + font_props.weight # weight always included

        expected_subfamily_name = 'Regular' # all regular for now

        expected_full_name = expected_family_name
        expected_postscript_name = 'Noto' + font_props.style
        if font_props.is_mono:
          expected_postscript_name += 'Mono'
        expected_postscript_name += font_props.variant + '-' + font_props.weight

        ADOBE_COPYRIGHT = (u"Copyright \u00a9 2014(?:, 20\d\d)? Adobe Systems Incorporated "
                           u"\(http://www.adobe.com/\).")
        SIL_LICENSE = ("This Font Software is licensed under the SIL Open Font License, "
                       "Version 1.1. This Font Software is distributed on an \"AS IS\" "
                       "BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express "
                       "or implied. See the SIL Open Font License for the specific language, "
                       "permissions and limitations governing your use of this Font Software.")
        SIL_LICENSE_URL = "http://scripts.sil.org/OFL"

        if tests.check('name/copyright') and not re.match(ADOBE_COPYRIGHT, names[0]):
            warn("Copyright",
                 "Copyright message doesn't match template: '%s': \n%s" %
                 (names[0], ADOBE_COPYRIGHT))

        if tests.check('name/family') and names[1] != expected_family_name:
            warn("Family name",
                 "Font family name is '%s', but was expecting '%s'." % (
                     names[1], expected_family_name))

        if tests.check('name/subfamily') and names[2] != expected_subfamily_name:
            warn("Sub-family name",
                 "Font subfamily name is '%s', but was expecting '%s'." % (
                     names[2], expected_subfamily_name))

        if tests.check('name/full') and names[4] != expected_full_name:
            warn("Font name",
                 "Full font name is '%s', but was expecting '%s'." % (
                     names[4], expected_full_name))

        # CFF font hinting isn't a thing we expect to see in a version string

        version_string = names[5]
        idx = version_string.find(';')
        if idx >= 0:
          version_string = version_string[:idx]
        if tests.check('name/version'):
            match = re.match(r"Version (\d{1,5})\.(\d{1,5})", version_string)
            if match:
                major_version = match.group(1)
                minor_version = match.group(2)
                if ((0 <= int(major_version) <= 65535)
                    and (0 <= int(minor_version) <= 65535)):
                    accuracy = len(minor_version)
                    font_revision = printable_font_revision(font, accuracy)
                    if (tests.check('name/version/match_head') and
                        font_revision != major_version + "." + minor_version):
                        warn("Font Revision", "fontRevision in 'head' table is %s, "
                             "while font version in 'name' table is %s.%s." % (
                                 font_revision, major_version, minor_version))
                else:
                    if tests.check('name/version/out_of_range'):
                        warn("Version",
                             "Version string has numerical parts outside the range "
                             "[0, 65535]: '%s'." % version_string)
            else:
                if tests.check('name/version/expected_pattern'):
                    warn("Version", "Version string is irregular: '%s'." % names[5])

        if tests.check('name/postscript') and names[6] != expected_postscript_name:
            warn("Postscript name",
                 "Postscript name is '%s', but was expecting '%s'." % (
                     names[6], expected_postscript_name))

        if tests.check('name/trademark') and names[7] != "Noto is a trademark of Google Inc.":
            warn("Trademark",
                 "Trademark message doesn't match template: '%s'." % names[7])

        if tests.check('name/manufacturer') and 8 not in names:
            warn("Manufacturer",
                 "Manufacturer name in 'name' table is not set.")

        if tests.check('name/designer') and 9 not in names:
            warn("Designer", "Designer name in 'name' table is not set.")

        if tests.check('name/description') and 10 not in names:
            warn("Description",
                 "The description field in 'name' table is not set.")
        if tests.check('name/vendor_url'):
            if 11 not in names:
                warn("Vendor", "The Vendor URL field in 'name' table is not set.")
            elif names[11] != NOTO_NEW_URL:
                warn("Vendor",
                     "Vendor URL field doesn't match template: '%s'." % names[11])

        if tests.check('name/designer_url'):
            if 12 not in names:
                warn("Designer",
                     "The Designer URL field in 'name' table is not set.")
            elif not names[12].startswith('http://'):
                warn("Designer",
                     "The Designer URL field in 'name' is not an "
                     "http URL: '%s'." % names[12])

        if tests.check('name/license') and names[13] != SIL_LICENSE:
            warn("License",
                 "License message doesn't match template: '%s'." % names[13])

        if tests.check('name/license_url') and names[14] != SIL_LICENSE_URL:
            warn("License",
                 "License URL doesn't match template: '%s'." % names[14])

    def _check_needed_chars(cmap, char_filter):
        # TODO(roozbeh): check the glyph requirements for controls specified at
        # https://www.microsoft.com/typography/otspec/recom.htm

        needed_chars = set()
        if font_props.script == "Qaae":  # Emoji
            needed_chars = set()  # TODO: Check emoji coverage
        elif font_props.script == "Zsym":  # Symbols
            needed_chars = _symbol_set()
        elif font_props.script == "Latn":  # LGC really
            needed_chars = (
                unicode_data.defined_characters(scr="Latn")
                | unicode_data.defined_characters(scr="Grek")
                | unicode_data.defined_characters(scr="Cyrl"))
            needed_chars -= _symbol_set()
            needed_chars -= _cjk_set()
        elif font_props.style == 'Nastaliq':
            needed_chars = noto_data.urdu_set()
        else:
            needed_chars = unicode_data.defined_characters(scr=font_props.script)
            needed_chars -= _symbol_set()

        needed_chars &= unicode_data.defined_characters(version=font_props.char_version)

        if font_props.style != 'Nastaliq':
            try:
                needed_chars |= set(noto_data.EXTRA_CHARACTERS_NEEDED[font_props.script])
            except KeyError:
                pass

            try:
                needed_chars |= set(opentype_data.SPECIAL_CHARACTERS_NEEDED[font_props.script])
            except KeyError:
                pass

            try:
                needed_chars -= set(noto_data.CHARACTERS_NOT_NEEDED[font_props.script])
            except KeyError:
                pass

        # TODO: also check character coverage against Unicode blocks for
        # characters of script Common or Inherited

        if char_filter:
            # old_needed_size = len(needed_chars)
            needed_chars = set(itertools.ifilter(char_filter.accept, needed_chars))
            # TODO(dougfelt): figure out how to make this info available without messing up output
            # print 'filter needed char size: %d -> %d' % (old_needed_size, len(needed_chars))

        missing_chars = needed_chars - set(cmap.keys())
        if missing_chars:
            if len(missing_chars) > 100:
                warn("Chars",
                     "Over 100 characters are missing from the font: %s."
                     % ", ".join(printable_unicode_range(missing_chars).split(", ")[:5]) + "...")
            else:
                warn("Chars",
                     "The following characters are missing from the font: %s."
                         % printable_unicode_range(missing_chars))


    def check_cmap_table():
        cmap_table = font['cmap']
        cmaps = {}
        expected_tables = [(4, 3, 1), (12, 3, 10)]
        if font_props.is_cjk:
            expected_tables.extend([
                # Adobe says historically some programs used these to identify
                # the script in the font.  The encodingID is the quickdraw script
                # manager code.  These are dummy tables.
                (6, 1, 1),  # Japanese
                (6, 1, 2),  # Traditional Chinese
                (6, 1, 3),  # Korean
                (6, 1, 25), # Simplified Chinese
                # Adobe says these just point at the windows versions, so there
                # is no issue.
                (4, 0, 3),   # Unicode, BMP only
                (12, 0, 4),  # Unicode, Includes Non-BMP
                # Required for variation selectors.
                (14, 0, 5)]) # Unicode, Variation sequences
        for table in cmap_table.tables:
            if (table.format,
                table.platformID,
                table.platEncID) not in expected_tables:
                if tests.check('cmap/tables/unexpected'):
                    warn("cmap",
                         "'cmap' has a subtable of "
                         "(format=%d, platform=%d, encoding=%d), "
                         "which it shouldn't have." % (
                             table.format, table.platformID, table.platEncID))
            elif table != (12, 0, 4):
                cmaps[table.format] = table.cmap

        if tests.check('cmap/tables/missing') and 4 not in cmaps:
            warn("cmap",
                 "'cmap' does not have a format 4 subtable, but it should.")

        if 12 in cmaps:
            cmap = cmaps[12]
            # if there is a format 12 table, it should have non-BMP characters
            if tests.check('cmap/tables/format_12_has_bmp') and max(cmap.keys()) <= 0xFFFF:
                warn("cmap",
                     "'cmap' has a format 12 subtable but no "
                     "non-BMP characters.")

            # the format 4 table should be a subset of the format 12 one
            if tests.check('cmap/tables/format_4_subset_of_12') and 4 in cmaps:
                for char in cmaps[4]:
                    if char not in cmap:
                        warn("cmap",
                             "U+%04X is mapped in cmap's format 4 subtable but "
                             "not in the format 12 one." % char)
                    elif cmaps[4][char] != cmap[char]:
                        warn("cmap",
                             "U+%04X is mapped to %s in cmap's format 4 "
                             "subtable but to %s in the format 12 one." % (
                                 char, cmaps[4][char], cmap[char]))
        else:
            cmap = cmaps[4]


        if tests.check('cmap/required'):
            required_in_all_fonts = [
                0x0000, # .null
                0x000D, # CR
                0x0020] # space
            for code in required_in_all_fonts:
                if code not in cmap:
                    warn("cmap",
                         "U+%04X is not mapped in cmap, but it should be (see "
                         "https://www.microsoft.com/typography/otspec/recom.htm)."
                             % code)

        if not font_props.is_cjk and tests.check('cmap/script_required'):
            _check_needed_chars(cmap, tests.get_filter('cmap/script_required'))

        if tests.check('cmap/private_use'):
            privates_in_cmap = {char for char in cmap
                                if unicode_data.is_private_use(char)}
            if privates_in_cmap:
                warn("Chars",
                     "There should be no private use characters defined in the "
                     "font, but there are: %s."
                         % printable_unicode_range(privates_in_cmap))

        if tests.check('cmap/non_characters'):
            non_characters = frozenset(
                range(0xFDD0, 0xFDEF+1)
                + [0xFFFE + plane_no * 0x10000 for plane_no in range(0, 17)]
                + [0xFFFF + plane_no * 0x10000 for plane_no in range(0, 17)])
            non_characters_in_cmap = non_characters & set(cmap.keys())
            if non_characters_in_cmap:
                warn("Chars",
                     "There should be no non-characters defined in the font, but "
                     "there are: %s."
                         % printable_unicode_range(non_characters_in_cmap))

        if tests.check('cmap/disallowed_ascii') and not (
            font_props.script == "Qaae" or
            font_props.script == "Latn" or
            font_props.is_cjk):
            ascii_letters = noto_data.ascii_letters()
            contained_letters = ascii_letters & set(cmap.keys())
            if contained_letters:
                warn("Chars",
                    "There should not be ASCII letters in the font, but there are: %s."
                    % printable_unicode_range(contained_letters))

        return cmap


    def check_head_tables(cmap):
        if not tests.check('head'):
            return

        def check_ul_unicode_range():
            bitmap = font_data.get_os2_unicoderange_bitmap(font)
            expected_info = opentype_data.collect_unicoderange_info(cmap)
            expected_bitmap = font_data.unicoderange_info_to_bitmap(expected_info)
            difference = bitmap ^ expected_bitmap
            if not difference:
                return

            for bucket_index in range(128):
                if difference & (1 << bucket_index):
                    bucket_info = opentype_data.unicoderange_bucket_index_to_info(bucket_index)
                    range_name = opentype_data.unicoderange_bucket_info_name(bucket_info)
                    chars_in_bucket = sum(t[0] for t in expected_info if t[1][2] == bucket_index)
                    size_of_bucket = opentype_data.unicoderange_bucket_info_size(bucket_info)
                    set_unset = "not be set" if bitmap & (1 << bucket_index) else "be set"
                    warn("Range bit",
                         "ulUnicodeRange bit %d (%s) should %s (cmap has "
                         "%d of %d codepoints in this range)" %
                         (bucket_index, range_name, set_unset, chars_in_bucket, size_of_bucket))
            # print printable_unicode_range(set(cmap.keys()))
            # print "expected %s" % font_data.unicoderange_bitmap_to_string(expected_bitmap)
            # print "have %s" % font_data.unicoderange_bitmap_to_string(bitmap)

        hhea_table = font["hhea"]

        if tests.check('head/hhea'):
            if font_props.is_ui or deemed_ui:
                if tests.check('head/hhea/ascent') and hhea_table.ascent != ASCENT:
                    warn("Bounds",
                         "Value of ascent in 'hhea' table is %d, but should be %d."
                             % (hhea_table.ascent, ASCENT))
                if tests.check('head/hhea/descent') and hhea_table.descent != DESCENT:
                    warn("Bounds",
                         "Value of descent in 'hhea' table is %d, but should be %d."
                             % (hhea_table.descent, DESCENT))

            if tests.check('head/hhea/linegap') and hhea_table.lineGap != 0:
                warn("Line Gap",
                     "Value of lineGap in 'hhea' table is %d, but should be 0."
                         % hhea_table.lineGap)

        vhea_table = font.get("vhea")
        if tests.check('head/vhea') and vhea_table:
            if tests.check('head/vhea/linegap') and vhea_table.lineGap != 0:
                warn("Line Gap",
                     "Value of lineGap in 'vhea' table is %d, but should be 0."
                     % vhea_table.lineGap)

        os2_table = font["OS/2"]

        if tests.check('head/os2'):
            if tests.check('head/os2/fstype') and os2_table.fsType != 0:
                warn("OS/2",
                     "Value of fsType in the 'OS/2' table is 0x%04X, but should "
                     "be 0." % os2_table.fsType)
            if tests.check('head/os2/ascender') and os2_table.sTypoAscender != hhea_table.ascent:
                warn("OS/2",
                     "Value of sTypoAscender in 'OS/2' table (%d) is different "
                     "from the value of Ascent in 'hhea' table (%d), "
                     "but they should be equal." %
                     (os2_table.sTypoAscender, hhea_table.ascent))
            if tests.check('head/os2/descender') and os2_table.sTypoDescender != hhea_table.descent:
                warn("OS/2",
                     "Value of sTypoDescender in 'OS/2' table (%d) is different "
                     "from the value of Descent in 'hhea' table (%d), "
                     "but they should be equal." %
                     (os2_table.sTypoDescender, hhea_table.descent))
            if tests.check('head/os2/linegap') and os2_table.sTypoLineGap != 0:
                warn("OS/2", "Value of sTypoLineGap in 'OS/2' table is %d, but "
                     "should be 0." % os2_table.sTypoLineGap)

            if tests.check('head/os2/winascent') and os2_table.usWinAscent != hhea_table.ascent:
                warn("OS/2", "Value of usWinAscent in 'OS/2' table (%d) is "
                     "different from the value of Ascent in 'hhea' table (%d), "
                     "but they should be equal." %
                     (os2_table.usWinAscent, hhea_table.ascent))
            if tests.check('head/os2/windescent') and os2_table.usWinDescent != -hhea_table.descent:
                warn("OS/2",
                     "Value of usWinDescent in 'OS/2' table (%d) is different "
                     "from the opposite of value of Descent in 'hhea' table (%d), "
                     "but they should be opposites." %
                     (os2_table.usWinDescent, hhea_table.descent))
            if tests.check('head/os2/achvendid') and (
                font_props.is_google and os2_table.achVendID != 'GOOG'):
                warn("OS/2",
                     "Value of achVendID in the 'OS/2' table is %s, "
                     "but should be GOOG." %
                     os2_table.achVendID)

            if font_props.is_cjk:
                expected_weights = {
                    'black': 900,
                    'bold': 700,
                    'medium': 500,
                    'regular': 400,
                    'demilight': 350,
                    'light': 300,
                    'thin': 250
                    }
            else:
                expected_weights = {
                    'bold': 700,
                    'regular': 400
                }
            expected_weight = expected_weights.get(font_props.weight.lower())
            if not expected_weight:
                raise ValueError('unexpected weight: %s' % font_props.weight)

            if tests.check('head/os2/weight_class') and os2_table.usWeightClass != expected_weight:
                warn("OS/2",
                     "Value of usWeightClass in 'OS/2' table is %d, but should "
                     "be %d." % (os2_table.usWeightClass, expected_weight))

            if tests.check('head/os2/fsselection'):
                OS2_SEL_ITALIC_MASK = 1
                OS2_SEL_BOLD_MASK = 1 << 5
                OS2_SEL_REGULAR_MASK = 1 << 6
                OS2_SEL_USE_TYPO_METRICS_MASK = 1 << 7
                OS2_SEL_WWS_MASK = 1 << 8
                if os2_table.fsSelection & OS2_SEL_REGULAR_MASK:
                    if os2_table.fsSelection & OS2_SEL_ITALIC_MASK:
                        warn("OS/2",
                             "fsSelection Regular bit is set, so the Italic bit should be clear.")
                    if os2_table.fsSelection & OS2_SEL_BOLD_MASK:
                        warn("OS/2",
                             "fsSelection Regular bit is set, so the Bold bit should be clear.")

                if os2_table.fsSelection & OS2_SEL_USE_TYPO_METRICS_MASK:
                    warn("OS/2",
                         "UseTypoMetrics bit in fsSelection is set, but should be clear.")

            if tests.check('head/os2/unicoderange'):
                check_ul_unicode_range()


    def check_vertical_limits():
        if 'glyf' not in font:
            return
        if not tests.check('bounds'):
            return

        glyf_table = font['glyf']
        us_win_ascent = font['OS/2'].usWinAscent
        us_win_descent = font['OS/2'].usWinDescent
        typo_ascent = font['OS/2'].sTypoAscender
        typo_descent = font['OS/2'].sTypoDescender

        # Build win ansi glyph set.  These we compare against usWinAscent/Descent, the
        # rest we compare against sTypoAscender/Descender. Of course, these should be
        # the same, and it's still ok for glyphs to exceed the typo ascender/descender--
        # but it should be exceptional.
        tmp_gids = set()
        cmap = font_data.get_cmap(font)
        for cp in lint_config.parse_int_ranges(WIN_ANSI_CODEPOINTS, True):
          if cp in cmap:
            tmp_gids.add(font.getGlyphID(cmap[cp], requireReal=True))
        win_ansi_gids = frozenset(tmp_gids)

        font_ymin = None
        font_ymax = None
        for glyph_index in range(len(glyf_table.glyphOrder)):
            glyph_name = glyf_table.glyphOrder[glyph_index]
            glyph = glyf_table[glyph_name]
            # Compute the ink's yMin and yMax
            ymin, ymax = render.get_glyph_cleaned_extents(glyph, glyf_table)
            font_ymin = render.min_with_none(font_ymin, ymin)
            font_ymax = render.max_with_none(font_ymax, ymax)

            if not tests.check('bounds/glyph'):
                continue

            is_win_ansi = glyph_index in win_ansi_gids
            if is_win_ansi:
              ascent_limit = us_win_ascent
              ascent_name = 'usWinAscent'
              descent_limit = -us_win_descent
              descent_name = 'usWinDescent'
            else:
              ascent_limit = typo_ascent
              ascent_name = 'sTypoAscent'
              descent_limit = typo_descent
              descent_name = 'sTypoDescent'

            if font_props.is_ui or deemed_ui:
                if (tests.checkvalue('bounds/glyph/ui_ymax', glyph_index) and
                    ymax is not None and ymax > MAX_UI_HEIGHT):
                    warn(
                        "Bounds",
                        "Real yMax for glyph %d (%s) is %d, which is more than "
                        "%d." % (glyph_index, glyph_name, ymax, MAX_UI_HEIGHT))
                if (tests.checkvalue('bounds/glyph/ui_ymin', glyph_index) and
                    ymin is not None and ymin < MIN_UI_HEIGHT):
                    warn(
                        "Bounds",
                        "Real yMin for glyph %d (%s) is %d, which is less than "
                        "%d." % (glyph_index, glyph_name, ymin, MIN_UI_HEIGHT))

            if (tests.checkvalue('bounds/glyph/ymax', glyph_index) and ymax is not None and
                ymax > ascent_limit):
                warn(
                    "Bounds",
                    "Real yMax for glyph %d (%s) is %d, which is higher than "
                    "the font's %s (%d), resulting in clipping." %
                    (glyph_index, glyph_name, ymax, ascent_name, ascent_limit))
            if (tests.checkvalue('bounds/glyph/ymin', glyph_index) and ymin is not None and
                ymin < -us_win_descent):
                warn(
                    "Bounds",
                    "Real yMin for glyph %d (%s) is %d, which is lower than "
                    "the font's %s (%d), resulting in clipping." %
                    (glyph_index, glyph_name, ymin, descent_name, descent_limit))

        if tests.check('bounds/font'):
            if font_props.is_ui or deemed_ui:
                if tests.check('bounds/font/ui_ymax') and font_ymax > MAX_UI_HEIGHT:
                    warn("Bounds", "Real yMax is %d, but it should be less "
                         "than or equal to %d." % (font_ymax, MAX_UI_HEIGHT))
                if tests.check('bounds/font/ui_ymin') and font_ymin < MIN_UI_HEIGHT:
                    warn(
                        "Bounds",
                        "Real yMin is %d, but it should be greater than or equal "
                        "to %d." % (font_ymin, MIN_UI_HEIGHT))
            else:
                hhea_table = font["hhea"]
                if tests.check('bounds/font/ymax') and font_ymax > hhea_table.ascent:
                    warn("Bounds", "Real yMax %d, but it should be less "
                         "than or equal to the value of Ascent in 'hhea' table, "
                         "which is %d." % (font_ymax, hhea_table.ascent))
                if tests.check('bounds/font/ymin') and font_ymin < hhea_table.descent:
                    warn("Bounds", "Real yMin is %d, but it should be greater "
                         "than or equal to the value of Descent in 'hhea' table, "
                         "which is %d." % (font_ymin, hhea_table.descent))


    def check_for_intersections_and_off_curve_extrema():
        if 'glyf' not in font:
            return
        if not tests.check('paths'):
            return
        glyf_table = font['glyf']
        for glyph_index in range(len(glyf_table.glyphOrder)):
            glyph_name = glyf_table.glyphOrder[glyph_index]
            glyph = glyf_table[glyph_name]
            check_extrema = tests.check('paths/extrema')
            check_intersection = tests.check('paths/intersection')
            if glyph.numberOfContours not in [0, -1]:  # not empty or composite
                all_contours = []
                start_point = 0
                for contour in range(glyph.numberOfContours):
                    end_point = glyph.endPtsOfContours[contour]
                    # TODO(roozbeh): See if this matters, and potentially
                    # re-enable.
                    #
                    # if glyph.flags[start_point] == 0:
                    #   warn("Off-curve start", "The glyph '%s' has an "
                    #        "off-curve starting point in "its contour #%d."
                    #        % (glyph_name, contour+1))
                    curves_in_contour = []
                    for point in range(start_point, end_point + 1):
                        if glyph.flags[point] == 1:  # on-curve
                            next_point = point
                            while True:
                                next_point = next_circular_point(
                                    next_point, start_point, end_point)
                                if glyph.flags[next_point] == 1:  # on-curve
                                    break

                            curve = curve_between(
                                glyph.coordinates,
                                point, next_point,
                                start_point, end_point)

                            curves_in_contour.append(curve)

                            if not check_extrema:
                              continue
                            out_of_box = curve_has_off_curve_extrema(curve)
                            if out_of_box > 0:
                                warn("Extrema", "The glyph '%s' is missing "
                                     "on-curve extreme points in the segment "
                                     "between point %d=%s and point %d=%s "
                                     "by %f units."
                                     % (glyph_name,
                                        point,
                                        glyph.coordinates[point],
                                        next_point,
                                        glyph.coordinates[next_point],
                                        out_of_box),
                                      extrema_details)
                    start_point = end_point + 1
                    all_contours.append(curves_in_contour)

                if check_intersection:
                    result = curves_intersect(all_contours)
                    if result:
                        warn("Intersection",
                             "The glyph '%s' has intersecting "
                             "outlines: %s" % (glyph_name, result))

    def check_gdef_table(cmap):
        """Validate the GDEF table."""
        if not tests.check('gdef'):
            return
        mark_glyphs = [code for code in cmap
                       if unicode_data.category(code) == 'Mn']
        try:
            class_def = font["GDEF"].table.GlyphClassDef.classDefs
        except (KeyError, AttributeError):
            class_def = None

        if tests.check('gdef/classdef'):
            names_of_classes = [
                "default class",
                "base glyph",
                "ligature glyph",
                "mark glyph",
                "component glyph"]
            if mark_glyphs and not class_def:
                if tests.check('gdef/classdef/not_present'):
                    warn("Glyph Class",
                         "There is no GlyphClassDef subtable of GDEF table in the "
                         "font, while there are non-spacing combining characters: %s."
                         % printable_unicode_range(mark_glyphs))
            elif mark_glyphs and not is_indic:
                for code in mark_glyphs:
                    glyph = cmap[code]
                    if glyph not in class_def:
                        if tests.checkvalue('gdef/classdef/unlisted', code):
                            warn("Glyph Class",
                                 "Glyph %s (U+%04X %s) is a combining mark, but is not "
                                 "assigned a value in the GDEF/GlyphClassDef table."
                                 % (glyph, code, unicode_data.name(code)))
                    elif (tests.checkvalue('gdef/classdef/combining_mismatch', code) and
                          class_def[glyph] != 3):
                        warn("Glyph Class",
                             "Glyph %s (U+%04X %s) is a combining mark, but is "
                             "defined as class %d (%s) in the GDEF/GlyphClassDef "
                             "table." % (
                                 glyph,
                                 code,
                                 unicode_data.name(code),
                                 class_def[glyph],
                                 names_of_classes[class_def[glyph]]))

            if class_def and not is_indic:
                for code in cmap:
                    glyph = cmap[code]
                    if glyph in class_def:
                        klass = class_def[glyph]
                        if (tests.checkvalue('gdef/classdef/not_combining_mismatch', code) and
                            klass == 3
                            and unicode_data.category(code) != "Mn"
                            and code not in noto_data.ACCEPTABLE_AS_COMBINING):
                            warn("Glyph Class",
                                 "Glyph %s (U+%04X %s) is defined as class 3 "
                                 "(non-spacing) in the GDEF/GlyphClassDef table, "
                                 "but is of general category %s." % (
                                     cmap[code],
                                     code,
                                     unicode_data.name(code),
                                     unicode_data.category(code)))

        if tests.check('gdef/attachlist'):
            # check for duplicate attachment points in AttachList table
            # See https://code.google.com/p/noto/issues/detail?id=128#c20

            try:
                attach_point_list = font["GDEF"].table.AttachList.AttachPoint
            except (KeyError, AttributeError):
                attach_point_list = []

            for index, attach_point in enumerate(attach_point_list):
                points = attach_point.PointIndex
                if len(set(points)) != len(points):
                    if tests.check('gdef/attachlist/duplicates'):
                        warn("Attach List",
                             "Entry #%d in GDEF.AttachList has duplicate points,"
                             "resulting in being rejected as a web font." % index)
                elif sorted(points) != points:
                    if tests.check('gdef/attachlists/out_of_order'):
                        warn("Attach List",
                             "Points in entry #%d in GDEF.AttachList are not in "
                             "increasing order." % index)

        if tests.check('gdef/ligcaretlist'):
            # check that every ligature has a ligature caret in GDEF
            ligatures = []
            if class_def:
                for glyph in class_def:
                    if class_def[glyph] == 2:
                        ligatures.append(glyph)
            if ligatures:
                try:
                    lig_caret_list_coverage = (
                        font["GDEF"].table.LigCaretList.Coverage)
                except (KeyError, AttributeError):
                    lig_caret_list_coverage = None

                if not lig_caret_list_coverage:
                    if tests.check('gdef/ligcaretlist/not_present') and not is_indic:
                        warn(
                            "Ligature Class",
                            "There is no LigCaretList data in the GDEF table, but "
                            "there are ligatures defined in GDEF: %s."
                            % ", ".join(ligatures))
                else:
                    if set(lig_caret_list_coverage.glyphs) - set(ligatures):
                        if tests.check('gdef/ligcaretlist/not_ligature'):
                            warn("Ligature Class",
                                 "Some glyphs are defined to have ligature carets in "
                                 "GDEF table, but are not defined as ligatures in the "
                                 "table: %s." % ", ".join(sorted(
                                     set(lig_caret_list_coverage.glyphs) -
                                     set(ligatures))))
                    elif set(ligatures) - set(lig_caret_list_coverage.glyphs):
                        if tests.check('gdef/ligcaretlist/unlisted') and not is_indic:
                            warn("Ligature Class",
                                 "Some glyphs are defined as ligatures in "
                                 "the GDEF table, but don't have ligature carets: %s."
                                 % ", ".join(sorted(
                                     set(ligatures) -
                                     set(lig_caret_list_coverage.glyphs))))

    def check_gpos_and_gsub_tables():
        if not tests.check('complex'):
            return

        whitelist = [
          "Carian",
          "Cypriot",
          "Deseret",
          "Egyptian Hieroglyphs",
          "Imperial Aramaic",
          "Linear B",
          "Lisu",
          "Lycian",
          "Lydian",
          "Ogham",
          "Ol Chiki",
          "Old Italic",
          "Old Persian",
          "Old South Arabian",
          "Old Turkic",
          "Osmanya",
          "Phoenician",
          "Runic",
          "Shavian",
          "Cuneiform",
          "Tai Le",
          "Ugaritic",
          "Vai",
          "Yi",
        ]
        if not font_props.is_cjk and human_readable_script_name(font_props.script) in whitelist:
            return
        if tests.check('complex/gpos/missing') and ("GPOS" not in font):
            warn("GPOS", "There is no GPOS table in the font.")
        if tests.check('complex/gsub/missing') and ("GSUB" not in font):
            warn("GSUB", "There is no GSUB table in the font.")
        #TODO: Add more script-specific checks

    def check_for_bidi_pairs(cmap):
        """Checks for proper support of bidi mirroring in the font.

        For each bidi mirroring character in the font, we wake sure that: if it
        is in OMPL, its mirror pair should also be in the cmap, and the first
        character should not mapped by 'rtlm'. If the character is not in OMPL,
        it should be mapped by 'rtlm'.

        Only the first 'rtlm' feature in the font is used.
        """
        if not tests.check('bidi'):
            return

        # need to discuss this with Adobe

        rtlm = {}
        if "GSUB" in font:
            feature_record = font["GSUB"].table.FeatureList.FeatureRecord
            for record in feature_record:
                if record.FeatureTag == "rtlm":  # FIXME
                    for lookup_number in record.Feature.LookupListIndex:
                        lookup = font["GSUB"].table.LookupList.Lookup[
                            lookup_number]
                        lookup_type = lookup.LookupType
                        if lookup_type == 7:  # GSUB extension
                            assert lookup.SubTableCount == 1
                            lookup_type = lookup.SubTable[0].ExtensionLookupType
                            subtables = [lookup.SubTable[0].ExtSubTable]
                        else:
                            subtables = lookup.SubTable

                        assert lookup_type == 1, (
                            "Don't know how to handle 'rtlm' features with "
                            "lookup type other than 1.")
                        for subtable in subtables:
                            for key in subtable.mapping.keys():
                                rtlm[key] = subtable.mapping[key]
                    break

        ompl = opentype_data.OMPL
        for code in sorted(cmap):
            if (unicode_data.is_private_use(code)
                    or not unicode_data.mirrored(code)):
                if tests.check('bidi/rtlm_non_mirrored') and cmap[code] in rtlm:
                    warn("Bidi",
                         "The 'rtlm' feature in the font applies to the glyph "
                         "for U+%04X (%s), but it shouldn't, since the "
                         "character is not bidi mirroring." % (
                             code, cmap[code]))
                continue  # skip the rest of the tests

            # The following tests are only applied to bidi mirroring characters
            if code in ompl:
                if tests.check('bidi/ompl_rtlm') and cmap[code] in rtlm:
                    warn("Bidi",
                         "The 'rtlm' feature in the font applies to the glyph "
                         "for U+%04X (%s), but it shouldn't, since the "
                         "character is in the OMPL list." % (code, cmap[code]))

                mirrored_pair = ompl[code]
                if tests.check('bidi/ompl_missing_pair') and mirrored_pair not in cmap:
                    warn("Bidi",
                         "The character U+%04X (%s) is supported in the font, "
                         "but its bidi mirrored pair U+%04X (%s) is not." % (
                             code, unicode_data.name(code),
                             mirrored_pair, unicode_data.name(mirrored_pair)))
            else:
                if tests.check('bidi/rtlm_unlisted') and cmap[code] not in rtlm:
                    warn("Bidi", "No 'rtlm' feature is applied to the glyph "
                         "for U+%04X (%s), but one should be applied, since "
                         "the character is a bidi mirroring character that is "
                         "not in the OMPL list." % (
                             code, cmap[code]))

    def check_hints():
        if not 'glyf' in font:
            return
        if not tests.check('hints'):
            return
        expected_to_be_hinted = font_props.is_hinted
        expected_to_be_unhinted = not expected_to_be_hinted

        # There should be no fpgm, prep, or cvt tables in unhinted fonts
        if tests.check('hints/unexpected_tables') and expected_to_be_unhinted:
            for table_name in ['fpgm', 'prep', 'cvt']:
                if table_name in font:
                    warn("Hints",
                         "The font is supposed to be unhinted, but it has "
                         "a '%s' table." % table_name)

        glyf_table = font['glyf']
        for glyph_index in range(len(glyf_table.glyphOrder)):
            glyph_name = glyf_table.glyphOrder[glyph_index]
            glyph = glyf_table[glyph_name]
            if glyph.numberOfContours > 0:
                bytecode = glyph.program.bytecode
                if expected_to_be_unhinted:
                    if tests.check('hints/unexpected_bytecode') and bytecode:
                        warn("Hints",
                             "The font is supposed to be unhinted, but "
                             "glyph '%s' has hints." % glyph_name)
                else:
                    if not bytecode and tests.checkvalue('hints/missing_bytecode', glyph_index):
                        warn("Hints",
                             "The font is supposed to be hinted, but "
                             "glyph '%s' (%d) doesn't have hints." % (glyph_name, glyph_index))


    def check_explicit_advances():
        """Check some cases where we expect advances to be explicitly related."""
        if not tests.check('advances'):
            return

        cmap = font_data.get_cmap(font)

        def get_horizontal_advance(codepoint):
            return font_data.get_glyph_horizontal_advance(font, cmap[codepoint])

        def expect_width(codepoint, expected, low_divisor=None, high_divisor=None):
            # it is ok if the font does not support the tested codepoint
            if codepoint not in cmap:
                return
            # no low divisor means exact match of the expected advance
            if not low_divisor:
                low_divisor = 1
                slop = 0
            else:
                slop = 1
            adv = get_horizontal_advance(codepoint)
            if not high_divisor:
                exp = int(round(float(expected) / low_divisor))
                if abs(adv - exp) > slop:
                    glyph_name = cmap[codepoint]
                    glyph_id = font.getGlyphID(glyph_name)
                    warn("Advances",
                         "The advance of U+%04x (%s, glyph %d) is %d, but expected %d." %
                         (codepoint, glyph_name, glyph_id, adv, exp))
            else:
                # note name switch, since the higher divisor returns the lower value
                high_exp = int(round(float(expected) / low_divisor))
                low_exp =  int(round(float(expected) / high_divisor))
                if not (low_exp - slop <= adv <= high_exp + slop):
                    glyph_name = cmap[codepoint]
                    glyph_id = font.getGlyphID(glyph_name)
                    warn("Advances",
                         "The advance of U+%04x (%s, glyph %d) is %d, but expected between"
                         "%d and %d." % (codepoint, glyph_name, glyph_id, adv, low_exp,
                                         high_exp))

        digit_char = ord('0')
        period_char = ord('.')
        comma_char = ord(',')
        space_char = ord(' ')
        tab_char = ord('\t')
        nbsp_char = 0x00a0

        if digit_char in cmap:
            digit_width = get_horizontal_advance(digit_char)
            if tests.check('advances/digits'):
                for i in range(10):
                    digit = ord('0') + i
                    width = get_horizontal_advance(digit)
                    if width != digit_width:
                        warn("Advances",
                             "The advance of '%s' (%d) is different from that of '0' (%d)." %
                             (chr(digit), width, digit_width))

        if period_char in cmap:
            period_width = get_horizontal_advance(period_char)
            if tests.check('advances/comma_period') and comma_char in cmap:
                expect_width(comma_char, period_width)

        if tests.check('advances/whitespace'):
            if tab_char in cmap or nbsp_char in cmap:
                space_width = get_horizontal_advance(space_char);
                if tab_char in cmap:
                    # see https://www.microsoft.com/typography/otspec/recom.htm
                    expect_width(tab_char, space_width)
                if nbsp_char in cmap:
                    expect_width(nbsp_char, space_width)

            em_width = font['head'].unitsPerEm
            expect_width(0x2000, em_width, 2) # en_quad
            expect_width(0x2001, em_width)    # em_quad
            expect_width(0x2002, em_width, 2) # en_space
            expect_width(0x2003, em_width)    # em_space
            expect_width(0x2004, em_width, 3) # three-per-em space
            expect_width(0x2005, em_width, 4) # four-per-em space
            expect_width(0x2006, em_width, 6) # six-per-em space
            if digit_char in cmap:
                expect_width(0x2007, digit_width) # figure space
            if period_char in cmap:
                expect_width(0x2008, period_width) # punctuation space
            # see http://unicode.org/charts/PDF/U2000.pdf, but microsoft (below)
            # says French uses 1/8 em.
            expect_width(0x2009, em_width, 5, 6) # thin space
            # see http://www.microsoft.com/typography/developers/fdsspec/spaces.htm
            expect_width(0x200A, em_width, 10, 16) # hair space
            expect_width(0x200B, 0) # zero width space


    def check_stems(cmap):
        if not 'glyf' in font:
            return
        if not tests.check('stem'):
            return
        # Only implemented for Ogham, currently
        # FIXME: Add support for Arabic, Syriac, Mongolian, Phags-Pa,
        # Devanagari, Bengali, etc
        joins_to_right = set(range(0x1680, 0x169B+1))
        joins_to_left = set(range(0x1680, 0x169A+1) + [0x169C])
        all_joining = joins_to_right | joins_to_left

        glyf_table = font['glyf']
        metrics_dict = font['hmtx'].metrics
        for code in all_joining & set(cmap):
            glyph_name = cmap[code]
            advance_width, lsb = metrics_dict[glyph_name]
            if tests.check('stem/left_joining') and code in joins_to_left:
                if lsb != 0:
                    warn("Stem",
                         "The glyph for U+%04X (%s) is supposed to have a stem "
                         "connecting to the left, but its left side bearing "
                         "is %d instead of 0."
                         % (code, unicode_data.name(code), lsb))
            if tests.check('stem/right_joining') and code in joins_to_right:
                glyph = glyf_table[glyph_name]
                rsb = advance_width - (lsb + glyph.xMax - glyph.xMin)
                if rsb != -70:
                    warn("Stem",
                         "The glyph for U+%04X (%s) is supposed to have a stem "
                         "connecting to the right, but it's right side bearing "
                         "is %d instead of -70."
                         % (code, unicode_data.name(code), rsb))


    def check_accessiblity(cmap):
        """Test if all glyphs are accessible through cmap, decomps, or GSUB.

        This is done using the font subsetter. We ask the subsetter to subset
        for all Unicode characters in the cmap table, and see if every glyph is
        covered after subsetting.
        """
        if not tests.check('reachable'):
            return

        test_filter = tests.get_filter('reachable')
        glyph_name_to_id = font.getReverseGlyphMap().copy()

        all_glyphs = set(font.getGlyphOrder())
        subsetter = subset.Subsetter()
        subsetter.populate(unicodes=cmap.keys())
        subsetter._closure_glyphs(font)

        unreachable_glyphs = all_glyphs - subsetter.glyphs_all
        if unreachable_glyphs:
            reported_glyphs = set()
            reported_list = []
            for glyph_name in unreachable_glyphs:
                glyph_id = glyph_name_to_id[glyph_name]
                if not test_filter or test_filter.accept(glyph_id):
                    if glyph_name not in reported_glyphs:
                        reported_glyphs.add(glyph_name)
                        reported_list.append((glyph_name, glyph_id))
            if reported_list:
                report_info = ', '.join('%s (%d)' % t for t in sorted(reported_list))
                warn("Reachabily",
                     "The following %d glyphs are unreachable in the font: %s." %
                     (len(reported_glyphs), report_info))

    ### actual start of check_font fn

    # python 2.7 does not have nonlocal, so hack around it
    suppressed_err_count = [0]
    err_count = [0]

    font_path = os.path.expanduser(font_props.file_path)
    font = ttLib.TTFont(font_path)

    print font_props

    is_indic = font_props.script in {
        "Deva", "Beng", "Guru", "Gujr", "Orya",
        "Taml", "Telu", "Knda", "Mlym", "Sinh"}

    deemed_ui = (not font_props.is_ui) and font_props.script in noto_data.DEEMED_UI_SCRIPTS_SET

    fi = lint_config.FontInfo(
        filename=os.path.basename(font_props.file_path),
        name=font_props.family,
        style=font_props.style,
        script=font_props.script,
        variant=font_props.variant,
        weight=font_props.weight,
        monospace=font_props.is_mono,
        hinted=font_props.is_hinted,
        vendor=font_props.vendor,
        version=printable_font_revision(font, accuracy=3 if font_props.vendor == 'Adobe' else 2))
    tests = lint_spec.get_tests(fi)

    if filename_error:
        if filename_error == 'script' and tests.check('filename/script'):
            warn("File name",
                 "Style %s also needs a script mentioned in the "
                 "file name." % style)
        elif filename_error == 'name' and tests.check('filename/name'):
            warn("File name",
                 "File name '%s' does not match the Noto font naming guidelines."
                 % file_name)


    check_name_table()
    cmap = check_cmap_table()
    check_head_tables(cmap)
    check_vertical_limits()
    check_for_intersections_and_off_curve_extrema()
    check_gdef_table(cmap)
    check_gpos_and_gsub_tables()
    check_for_bidi_pairs(cmap)
    check_hints()
    check_explicit_advances()
    check_stems(cmap)

    # This must be done at the very end, since the subsetter may change the font
    check_accessiblity(cmap)

    warn("info",
         "supported characters: " + printable_unicode_range(cmap.keys()))

    if runlog:
        log = sorted(tests.runlog())
        count = len(log)
        if count:
          print 'Ran %d test%s:\n  %s' % (count, 's' if count != 1 else '',
                                        '\n  '.join(log))
        else:
          print 'Ran no tests.'
    if skiplog:
        log = sorted(tests.skiplog())
        count = len(log)
        if len(log):
          print 'Skipped %d test/group%s:\n  %s' % (count, 's' if count != 1 else '',
                                            '\n  '.join(log))
        else:
          print 'Skipped no tests'

    # TODO(roozbeh):
    # * Check that hintedness based on data in the glyf table
    #   matches metadata (file location, header data)
    # * Check GSUB coverage, based on script
    # * Check gasp values
    # * Add support for TTC fonts
    # * Check ulCodePageRange values


def get_lint_spec(spec_file, extra_specs):
  """Return a LintSpec from spec_file supplemented with extra_specs.
  If spec_file is None, only use extra_specs."""

  spec = None
  if spec_file is not 'None':
    spec = lint_config.parse_spec_file(spec_file)
  return lint_config.parse_spec(extra_specs, spec)


def parse_font_props(font_props_file):
  """Return a list of FontProps objects."""
  with open(font_props_file) as f:
    font_spec = f.read()
  spec_data = json.loads(font_spec)
  return [FontProps(**m) for m in spec_data]

def write_font_props(font_props):
  print json.dumps(font_props._asdict())

def main():
    default_config_file = notoconfig.values.get('lint_config')
    if not default_config_file:
      curdir = os.path.abspath(os.path.dirname(__file__))
      default_config_file = os.path.join(curdir, 'lint_config.txt')

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        help="produces csv output to import into a spreadsheet",
        action="store_true")
    parser.add_argument(
        "--info",
        help="includes informational messages in the output",
        action="store_true")
    parser.add_argument(
        "--suppress_extrema_details",
        dest="extrema_details",
        default=True,
        action="store_false",
        help="only summarize extrema issues")
    parser.add_argument(
        "--csv_header",
        help="write header line when generating csv output",
        action="store_true")
    parser.add_argument(
        "font_files",
        metavar="font",
        nargs="*",
        help="a font file to check, can omit if font_spec is provided")
    parser.add_argument(
        "--font_props_file",
        metavar="file",
        help="file containing json describing font file paths and expected properties")
    parser.add_argument(
        "--config_file",
        help="location of config file (default %s, 'None' for none)" % default_config_file,
        metavar='file',
        default=default_config_file)
    parser.add_argument(
        "--config",
        help="extra config spec to process after config file",
        metavar='lint_spec')
    parser.add_argument(
        "--runlog",
        help="show tags of run tests",
        action="store_true")
    parser.add_argument(
        "--skiplog",
        help="show tags of skipped tests",
        action="store_true")
    parser.add_argument(
        "--dump_font_props",
        help="write font props for files",
        action="store_true")

    arguments = parser.parse_args()

    if arguments.dump_font_props:
        for font_file_path in arguments.font_files:
            font_props, filename_error = font_properties_from_name(font_file_path)
            if filename_error:
                print '#Error for %s: %s' % (font_file_path, filename_error)
            else:
                write_font_props(font_props)
        return

    lint_spec = get_lint_spec(arguments.config_file, arguments.config)

    if arguments.csv and arguments.csv_header:
        print("Script,Style,Variant,Weight,Manufacturer,Category,Hint Status,"
            "File Name,Revision,Issue")

    for font_file_path in arguments.font_files:
        font_props, filename_error = font_properties_from_name(font_file_path)
        check_font(font_props,
                   filename_error,
                   lint_spec,
                   arguments.runlog,
                   arguments.skiplog,
                   arguments.csv,
                   arguments.info,
                   arguments.extrema_details)
    count = len(arguments.font_files)
    if arguments.font_props_file:
        font_props_list = parse_font_props(arguments.font_props_file)
        count += len(font_props_list)
        for font_props in font_props_list:
             check_font(font_props,
                        '',
                        lint_spec,
                        arguments.runlog,
                        arguments.skiplog,
                        arguments.csv,
                        arguments.info,
                        arguments.extrema_details)


    if not arguments.csv:
        file_count = len(arguments.font_files)
        if file_count == 1:
            print "Finished linting 1 file."
        else:
            print "Finished linting %d files." % file_count

if __name__ == "__main__":
    main()
