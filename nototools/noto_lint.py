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
import math
import re

from fontTools import subset
from fontTools import ttLib
from fontTools.misc import arrayTools
from fontTools.misc import bezierTools
from fontTools.pens import basePen

from nototools import noto_data
from nototools import opentype_data
from nototools import render
from nototools import unicode_data


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
                # print 'curve back', piece
                return True

    all_pieces = sum(all_contours, [])
    if len(set(all_pieces)) != len(all_pieces):
        # print 'repetition'
        return True  # No piece should be repeated

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
            # print 'intersection', piece1, piece2
            return True

    return False


def name_records(font):
    name_table = font["name"]
    names = {}
    for record in name_table.names:
        assert (record.platformID,
                record.platEncID,
                record.langID) == (3, 1, 0x409)
        names[record.nameID] = unicode(record.string, "UTF-16BE")
    return names


def font_version(font):
    names = name_records(font)
    return names[5]


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
]

FONT_WEIGHTS = [
    "Regular",
    "Bold",
    "Italic",
    "BoldItalic",
]

FONT_VARIANTS = [
    "UI",
    # The next three are for Syriac
    "Eastern",
    "Western",
    "Estrangela",
]

HARD_CODED_FONT_INFO = {
    "AndroidEmoji.ttf": ("Sans", "Qaae", None, "Regular"),
    "DroidEmoji.ttf": ("Sans", "Qaae", None, "Regular"),
    "NotoNaskh-Regular.ttf": ("Naskh", "Arab", None, "Regular"),
    "NotoNaskh-Bold.ttf": ("Naskh", "Arab", None, "Bold"),
    "NotoNaskhUI-Regular.ttf": ("Naskh", "Arab", "UI", "Regular"),
    "NotoNaskhUI-Bold.ttf": ("Naskh", "Arab", "UI", "Bold"),
    "NotoSansCypriotSyllabary-Regular.ttf": ("Sans", "Cprt", None, "Regular"),
    "NotoSansEmoji-Regular.ttf": ("Sans", "Qaae", None, "Regular"),
    "NotoSansKufiArabic-Regular.ttf": ("Kufi", "Arab", None, "Regular"),
    "NotoSansKufiArabic-Bold.ttf": ("Kufi", "Arab", None, "Bold"),
    "NotoSansPahlavi-Regular.ttf": ("Sans", "Phli", None, "Regular"),
    "NotoSansParthian-Regular.ttf": ("Sans", "Prti", None, "Regular"),
    "NotoSansSumeroAkkadianCuneiform-Regular.ttf": (
        "Sans", "Xsux", None, "Regular"),
    "NotoSansSymbols-Regular.ttf": ("Sans", "Zsym", None, "Regular"),
}

MAX_UI_HEIGHT = 2163
MIN_UI_HEIGHT = -555
ASCENT = 2189
DESCENT = -600


_last_printed_file_name = None

def check_font(file_name, csv_flag=False, info_flag=False):
    def warn(category, message):
        global _last_printed_file_name

        interesting_part_of_file_name = ",".join(file_name.split("/")[-2:])
        if interesting_part_of_file_name != _last_printed_file_name:
            _last_printed_file_name = interesting_part_of_file_name
            if not csv_flag:
                print "Automatic testing for '%s', %s:" % (
                    interesting_part_of_file_name,
                    printable_font_versions(font))

        if not info_flag and category is "info":
            return

        if csv_flag:
            print ('%s,%s,%s,%s,%s,%s,%s,%s,"%s"' % (
                unicode_data.human_readable_script_name(script),
                style,
                variant if variant else '',
                weight,
                name_records(font)[8].split()[0],
                category,
                interesting_part_of_file_name,
                printable_font_revision(font),
                message)).encode('UTF-8')
        else:
            if category is "info":
                print "[informational]",
            print message.encode('UTF-8')

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
        names = name_records(font)

        # Check family name
        expected_family_name = 'Noto ' + style
        if script != 'Latn':
            expected_family_name += (
                ' ' + unicode_data.human_readable_script_name(script))
        if variant:
            expected_family_name += ' ' + variant
        if weight == 'BoldItalic':
            expected_subfamily_name = 'Bold Italic'
        else:
            expected_subfamily_name = weight

        expected_full_name = expected_family_name
        expected_postscript_name = expected_family_name.replace(' ', '')
        if weight != 'Regular':
            expected_full_name += ' ' + expected_subfamily_name
            expected_postscript_name += (
                '-' + expected_subfamily_name.replace(' ', ''))

        if not re.match(
            r'Copyright 201\d Google Inc. All Rights Reserved.$', names[0]):
            warn("Copyright",
                 "Copyright message doesn't match template: '%s'." % names[0])

        if names[1] != expected_family_name:
            warn("Family name",
                 "Font family name is '%s', but was expecting '%s'." % (
                     names[1], expected_family_name))

        if names[2] != expected_subfamily_name:
            warn("Sub-family name",
                 "Font subfamily name is '%s', but was expecting '%s'." % (
                     names[2], expected_subfamily_name))

        if names[4] != expected_full_name:
            warn("Font name",
                 "Full font name is '%s', but was expecting '%s'." % (
                     names[4], expected_full_name))

        # TODO(roozbeh): Make sure the description field contains information on
        # whether or not the font is hinted

        match = re.match(r"Version (\d{1,5})\.(\d{1,5})", names[5])
        if match:
            major_version = match.group(1)
            minor_version = match.group(2)
            if ((0 <= int(major_version) <= 65535)
                and (0 <= int(minor_version) <= 65535)):
                match_end = names[5][match.end():]
                is_hinted = "/hinted" in file_name or "_hinted" in file_name
                if ((is_hinted and match_end != "") or
                    (not is_hinted and match_end not in ["", " uh"])):
                    warn(
                        "Version",
                        "Version string '%s' has extra characters at its end." %
                        names[5])
                accuracy = len(minor_version)
                font_revision = printable_font_revision(font, accuracy)
                if font_revision != major_version+"."+minor_version:
                    warn("Font Revision", "fontRevision in 'head' table is %s, "
                         "while font version in 'name' table is %s.%s." % (
                             font_revision, major_version, minor_version))
            else:
                warn("Version",
                     "Version string has numerical parts out of "
                     "[0, 65535]: '%s'." % names[5])
        else:
            warn("Version", "Version string is irregular: '%s'." % names[5])

        if names[6] != expected_postscript_name:
            warn("Postscript name",
                 "Postscript name is '%s', but was expecting '%s'." % (
                     names[6], expected_postscript_name))

        if (names[7] != "Noto is a trademark of Google Inc. and may be "
                         "registered in certain jurisdictions."):
            warn("Trademark",
                 "Trademark message doesn't match template: '%s'." % names[7])

        if 8 not in names:
            warn("Manufacturer",
                 "Manufacturer name in 'name' table is not set.")

        if 9 not in names:
            warn("Designer", "Designer name in 'name' table is not set.")

        if 10 not in names:
            warn("Description",
                 "The description field in 'name' table is not set.")

        if 11 not in names:
            warn("Vendor", "The Vendor URL field in 'name' table is not set.")
        elif names[11] != 'http://code.google.com/p/noto/':
            warn("Vendor",
                 "Vendor URL field doesn't match template: '%s'." % names[11])

        if 12 not in names:
            warn("Designer",
                 "The Designer URL field in 'name' tables is not set.")
        elif not names[12].startswith('http://'):
            warn("Designer",
                 "The Designer URL field in 'name' is not an "
                 "http URL: '%s'." % names[12])

        if names[13] != "Licensed under the Apache License, Version 2.0":
            warn("License",
                 "License message doesn't match template: '%s'." % names[13])

        if names[14] != "http://www.apache.org/licenses/LICENSE-2.0":
            warn("License",
                 "License URL doesn't match template: '%s'." % names[14])


    def check_cmap_table():
        cmap_table = font['cmap']
        cmaps = {}
        for table in cmap_table.tables:
            if (table.format,
                table.platformID,
                table.platEncID) not in [(4, 3, 1), (12, 3, 10)]:
                warn("cmap",
                     "'cmap' has a subtable of "
                     "(format=%d, platform=%d, encoding=%d), "
                     "which it shouldn't have." % (
                         table.format, table.platformID, table.platEncID))
            else:
                cmaps[table.format] = table.cmap

        if 4 not in cmaps:
            warn("cmap",
                 "'cmap' does not have a format 4 subtable, but it should.")

        if 12 in cmaps:
            cmap = cmaps[12]
            # if there is a format 12 table, it should have non-BMP characters
            if max(cmap.keys()) <= 0xFFFF:
                warn("cmap",
                     "'cmap' has a format 12 subtable but no "
                     "non-BMP characters.")

            # the format 4 table should be a subset of the format 12 one
            if 4 in cmaps:
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

        # TODO(roozbeh): check the glyph requirements for controls specified at
        # https://www.microsoft.com/typography/otspec/recom.htm

        needed_chars = set()
        if script == "Qaae":  # Emoji
            needed_chars = set()  # TODO: Check emoji coverage
        elif script == "Zsym":  # Symbols
            needed_chars = _symbol_set()
        elif script == "Latn":  # LGC really
            needed_chars = (
                unicode_data.defined_characters(scr="Latn")
                | unicode_data.defined_characters(scr="Grek")
                | unicode_data.defined_characters(scr="Cyrl"))
            needed_chars -= _symbol_set()
            needed_chars -= _cjk_set()
        else:
            needed_chars = unicode_data.defined_characters(scr=script)
            needed_chars -= _symbol_set()

        needed_chars &= unicode_data.defined_characters(version=6.0)

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

        # TODO: also check character coverage against Unicode blocks for
        # characters of script Common or Inherited

        missing_chars = needed_chars - set(cmap.keys())
        if missing_chars:
            warn("Chars",
                 "The following characters are missing from the font: %s."
                     % printable_unicode_range(missing_chars))

        privates_in_cmap = {char for char in cmap
                            if unicode_data.is_private_use(char)}
        if privates_in_cmap:
            warn("Chars",
                 "There should be no private use characters defined in the "
                 "font, but there are: %s."
                     % printable_unicode_range(privates_in_cmap))

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

        return cmap


    def check_head_tables(cmap):
        def check_ul_unicode_range():
            bitmap = (os2_table.ulUnicodeRange1 |
                      os2_table.ulUnicodeRange2 << 32 |
                      os2_table.ulUnicodeRange3 << 64 |
                      os2_table.ulUnicodeRange4 << 96)

            # Number of characters supported in the cmap for each range
            # in ulUnicodeRange
            chars_in_range = [0] * 128
            for code in cmap:
                if code > 0xFFFF: # The special bit for non-BMP characters
                    chars_in_range[57] += 1
                try:
                    chars_in_range[
                        opentype_data.ul_unicode_range_bit[code]] += 1
                except KeyError:
                    # No bit needed for the character
                    pass

            expected_bitmap = 0L
            for bit in range(
                    max(opentype_data.ul_unicode_range_count.keys())+1):
                if chars_in_range[bit] > 0:
                    expected_bitmap |= 1 << bit

                # If we need to be more precise, we can use following algorithm:
                # # The special bits for non-BMP characters, and private
                # # use areas
                # if bit in [57, 60, 90]:
                #    if chars_in_range[bit] > 0:
                #      expected_bitmap |= 1 << bit
                #  elif chars_in_range[bit] >= (
                #        0.5 * opentype_data.ul_unicode_range_count[bit]):
                #    expected_bitmap |= 1 << bit

            difference = bitmap ^ expected_bitmap
            if difference:
                for bit in range(0, 128):
                    if difference & (1 << bit):
                        if bitmap & (1 << bit):
                            warn("Range bit",
                                 "ulUnicodeRange bit %d for %s expected to be "
                                 "not set, while it was set [defined Unicode "
                                 "chars in ranges=%d, cmapped chars in "
                                 "ranges=%d]." % (
                                     bit,
                                     ', '.join(
                                         opentype_data.ul_unicode_range_names[
                                             bit]),
                                     opentype_data.ul_unicode_range_count[bit],
                                     chars_in_range[bit]))
                        else:
                            if bit == 57:
                                characters = set(cmap) - set(range(0, 0x10000))
                            else:
                                characters = (set(cmap) &
                                    opentype_data.ul_unicode_range_set[bit])
                            characters = printable_unicode_range(characters)
                            warn(
                                "Range bit",
                                "ulUnicodeRange bit %d for %s expected to be "
                                "set, while it was not set [supported "
                                "characters in the ranges: %s]." % (
                                    bit,
                                    ", ".join(
                                        opentype_data.ul_unicode_range_names[
                                            bit]),
                                    characters))

        hhea_table = font["hhea"]

        if is_ui or deemed_ui:
            if hhea_table.ascent != ASCENT:
                warn("Bounds",
                     "Value of ascent in 'hhea' table is %d, but should be %d."
                         % (hhea_table.ascent, ASCENT))
            if hhea_table.descent != DESCENT:
                warn("Bounds",
                     "Value of descent in 'hhea' table is %d, but should be %d."
                         % (hhea_table.descent, DESCENT))

        if hhea_table.lineGap != 0:
            warn("Line Gap",
                 "Value of lineGap in 'hhea' table is %d, but should be 0."
                     % hhea_table.lineGap)

        os2_table = font["OS/2"]

        if os2_table.fsType != 0:
            warn("OS/2",
                 "Value of fsType in the 'OS/2' table is 0x%04X, but should "
                 "be 0." % os2_table.fsType)
        if os2_table.sTypoAscender != hhea_table.ascent:
            warn("OS/2",
                 "Value of sTypoAscender in 'OS/2' table (%d) is different "
                 "from the value of Ascent in 'hhea' table (%d), "
                 "but they should be equal." %
                 (os2_table.sTypoAscender, hhea_table.ascent))
        if os2_table.sTypoDescender != hhea_table.descent:
            warn("OS/2",
                 "Value of sTypoDescender in 'OS/2' table (%d) is different "
                 "from the value of Descent in 'hhea' table (%d), "
                 "but they should be equal." %
                 (os2_table.sTypoDescender, hhea_table.descent))
        if os2_table.sTypoLineGap != 0:
            warn("OS/2", "Value of sTypoLineGap in 'OS/2' table is %d, but "
                 "should be 0." % os2_table.sTypoLineGap)

        if os2_table.usWinAscent != hhea_table.ascent:
            warn("OS/2", "Value of usWinAscent in 'OS/2' table (%d) is "
                 "different from the value of Ascent in 'hhea' table (%d), "
                 "but they should be equal." %
                 (os2_table.usWinAscent, hhea_table.ascent))
        if os2_table.usWinDescent != -hhea_table.descent:
            warn("OS/2",
                 "Value of sTypoDescender in 'OS/2' table (%d) is different "
                 "from the opposite of value of Descent in 'hhea' table (%d), "
                 "but they should be opposites." %
                 (os2_table.usWinDescent, hhea_table.descent))

        if 'Bold' in weight:
            expected_weight = 700
        else:
            expected_weight = 400

        if os2_table.usWeightClass != expected_weight:
            warn("OS/2",
                 "Value of usWeightClass in 'OS/2' table is %d, but should "
                 "be %d." % (os2_table.usWeightClass, expected_weight))

        # Do not check for now
        # check_ul_unicode_range()


    def check_vertical_limits():
        glyf_table = font['glyf']
        us_win_ascent = font['OS/2'].usWinAscent
        us_win_descent = font['OS/2'].usWinDescent
        font_ymin = None
        font_ymax = None
        for glyph_index in range(len(glyf_table.glyphOrder)):
            glyph_name = glyf_table.glyphOrder[glyph_index]
            glyph = glyf_table[glyph_name]
            # Compute the ink's yMin and yMax
            ymin, ymax = render.get_glyph_cleaned_extents(glyph, glyf_table)
            font_ymin = render.min_with_none(font_ymin, ymin)
            font_ymax = render.max_with_none(font_ymax, ymax)

            if is_ui or deemed_ui:
                if ymax is not None and ymax > MAX_UI_HEIGHT:
                    warn(
                        "Bounds",
                        "Real yMax for glyph %d (%s) is %d, which is more than "
                        "%d." % (glyph_index, glyph_name, ymax, MAX_UI_HEIGHT))
                if ymin is not None and ymin < MIN_UI_HEIGHT:
                    warn(
                        "Bounds",
                        "Real yMin for glyph %d (%s) is %d, which is less than "
                        "%d." % (glyph_index, glyph_name, ymin, MIN_UI_HEIGHT))

            if ymax is not None and ymax > us_win_ascent:
                warn(
                    "Bounds",
                    "Real yMax for glyph %d (%s) is %d, which is higher than "
                    "the font's usWinAscent (%d), resulting in clipping." %
                    (glyph_index, glyph_name, ymax, us_win_ascent))
            if ymin is not None and ymin < -us_win_descent:
                warn(
                    "Bounds",
                    "Real yMin for glyph %d (%s) is %d, which is lower than "
                    "the font's usWinDescent (%d), resulting in clipping." %
                    (glyph_index, glyph_name, ymin, us_win_descent))

        if is_ui or deemed_ui:
            if font_ymax > MAX_UI_HEIGHT:
                warn("Bounds", "Real yMax is %d, but it should be less "
                     "than or equal to %d." % (font_ymax, MAX_UI_HEIGHT))
            if font_ymin < MIN_UI_HEIGHT:
                warn(
                    "Bounds",
                    "Real of yMin in 'head' table is %d, but it should be "
                    "greater than or equal to %d." % (font_ymin, MIN_UI_HEIGHT))
        else:
            hhea_table = font["hhea"]
            if font_ymax > hhea_table.ascent:
                warn("Bounds", "Real yMax %d, but it should be less"
                     "than or equal to the value of Ascent in 'hhea' table, "
                     "which is %d." % (font_ymax, hhea_table.ascent))
            if font_ymin < hhea_table.descent:
                warn("Bounds", "Real yMin is %d, but it should be greater "
                     "than or equal to the value of Descent in 'hhea' table, "
                     "which is %d." % (font_ymin, hhea_table.descent))


    def check_for_intersections_and_off_curve_extrema():
        glyf_table = font['glyf']
        for glyph_index in range(len(glyf_table.glyphOrder)):
            glyph_name = glyf_table.glyphOrder[glyph_index]
            glyph = glyf_table[glyph_name]
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
                                        out_of_box))
                    start_point = end_point + 1
                    all_contours.append(curves_in_contour)

                if curves_intersect(all_contours):
                    warn("Inersection",
                         "The glyph '%s' has intersecting "
                         "outlines." % glyph_name)

    def check_gdef_table(cmap):
        """Validate the GDEF table."""
        mark_glyphs = [code for code in cmap
                       if unicode_data.category(code) == 'Mn']
        try:
            class_def = font["GDEF"].table.GlyphClassDef.classDefs
        except (KeyError, AttributeError):
            class_def = None

        names_of_classes = [
            "default class",
            "base glyph",
            "ligature glyph",
            "mark glyph",
            "component glyph"]
        if mark_glyphs and not class_def:
            warn("Glyph Class",
                 "There is no GlyphClassDef subtable of GDEF table in the "
                 "font, while there are non-spacing combining characters: %s."
                 % printable_unicode_range(mark_glyphs))
        elif mark_glyphs and not is_indic:
            for code in mark_glyphs:
                glyph = cmap[code]
                if glyph not in class_def:
                    warn("Glyph Class",
                         "Glyph %s (U+%04X %s) is a combining mark, but is not "
                         "assigned a value in the GDEF/GlyphClassDef table."
                         % (glyph, code, unicode_data.name(code)))
                elif class_def[glyph] != 3:
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
                if cmap[code] in class_def:
                    klass = class_def[cmap[code]]
                    if klass == 3 and unicode_data.category(code) != "Mn":
                        warn("Glyph Class",
                             "Glyph %s (U+%04X %s) is defined as class 3 "
                             "(non-spacing) in the GDEF/GlyphClassDef table, "
                             "but is of general category %s." % (
                                 cmap[code],
                                 code,
                                 unicode_data.name(code),
                                 unicode_data.category(code)))

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
                if not is_indic:
                    warn(
                        "Ligature Class",
                        "There is no LigCaretList data in the GDEF table, but "
                        "there are ligatures defined in GDEF: %s."
                        % ", ".join(ligatures))
            else:
                if set(lig_caret_list_coverage.glyphs) - set(ligatures):
                    warn("Ligature Class",
                         "Some glyphs are defined to have ligature carets in "
                         "GDEF table, but are not defined as ligatures in the "
                         "table: %s." % ", ".join(sorted(
                             set(lig_caret_list_coverage.glyphs) -
                             set(ligatures))))
                elif (set(ligatures) - set(lig_caret_list_coverage.glyphs)
                      and not is_indic):
                    warn("Ligature Class",
                         "Some glyphs are defined as ligatures in "
                         "the GDEF table, but don't have ligature carets: %s."
                         % ", ".join(sorted(
                             set(ligatures) -
                             set(lig_caret_list_coverage.glyphs))))

    def check_gpos_and_gsub_tables():
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
        if unicode_data.human_readable_script_name(script) in whitelist:
            return
        if "GPOS" not in font:
            warn("GPOS", "There is no GPOS table in the font.")
        if "GSUB" not in font:
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
        rtlm = {}
        if "GSUB" in font:
            feature_record = font["GSUB"].table.FeatureList.FeatureRecord
            for record in feature_record:
                if record.FeatureTag == "rtlm":  # FIXME
                    for lookup_number in record.Feature.LookupListIndex:
                        lookup = font["GSUB"].table.LookupList.Lookup[
                            lookup_number]
                        assert lookup.LookupType == 1, (
                            "Dan't know how to handle 'rtlm' features with "
                            "lookup type other than 1.")
                        for subtable in lookup.SubTable:
                            for key in subtable.mapping.keys():
                                rtlm[key] = subtable.mapping[key]
                    break

        ompl = opentype_data.OMPL
        for code in sorted(cmap):
            if (unicode_data.is_private_use(code)
                    or not unicode_data.mirrored(code)):
                if cmap[code] in rtlm:
                    warn("BiDi",
                         "The 'rtlm' feature in the font applies to the glyph "
                         "for U+%04X (%s), but it shouldn't, since the "
                         "character is not bidi mirroring." % (
                             code, cmap[code]))
                continue  # skip the rest of the tests

            # The following tests are only applied to bidi mirroring characters
            if code in ompl:
                if cmap[code] in rtlm:
                    warn("BiDi",
                         "The 'rtlm' feature in the font applies to the glyph "
                         "for U+%04X (%s), but it shouldn't, since the "
                         "character is in the OMPL list." % (code, cmap[code]))

                mirrored_pair = ompl[code]
                if mirrored_pair not in cmap:
                    warn("BiDi",
                         "The character U+%04X (%s) is supported in the font, "
                         "but its bidi mirrored pair U+%04X (%s) is not." % (
                             code, unicode_data.name(code),
                             mirrored_pair, unicode_data.name(mirrored_pair)))
            else:
                if cmap[code] not in rtlm:
                    warn("BiDi", "No 'rtlm' feature is applied to the glyph "
                         "for U+%04X (%s), but one should be applied, since "
                         "the character is a bidi mirroring character that is "
                         "not in the OMPL list." % (
                             code, cmap[code]))

    def check_hints():
        expected_to_be_hinted = '/hinted' in file_name or '_hinted' in file_name
        expected_to_be_unhinted = not expected_to_be_hinted

        # There should be no fpgm, prep, or cvt tables in unhinted fonts
        if expected_to_be_unhinted:
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
                if bytecode and expected_to_be_unhinted:
                    warn("Hints",
                         "The font is supposed to be unhinted, but "
                         "glyph '%s' has hints." % glyph_name)
                elif expected_to_be_hinted and not bytecode:
                    warn("Hints",
                         "The font is supposed to be hinted, but "
                         "glyph '%s' doesn't have hints." % glyph_name)

    def check_stems(cmap):
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
            if code in joins_to_left:
                if lsb != 0:
                    warn("Stem",
                         "The glyph for U+%04X (%s) is supposed to have a stem "
                         "connecting to the left, but it's left side bearing "
                         "is %d instead of 0."
                         % (code, unicode_data.name(code), lsb))
            if code in joins_to_right:
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
        all_glyphs = set(font.getGlyphOrder())
        subsetter = subset.Subsetter()
        subsetter.populate(unicodes=cmap.keys())
        subsetter._closure_glyphs(font)

        unreachable_glyphs = all_glyphs - subsetter.glyphs_all
        if unreachable_glyphs:
            warn("Reachabily",
                 "The following glyphs are unreachable in the font: %s." %
                 ", ".join(sorted(unreachable_glyphs)))

    def make_compact_scripts_regex(scripts=None):
        """Creates a regular expression that accepts all compact scripts names.
        """
        if scripts == None:
            scripts = unicode_data.all_scripts()
        scripts = {unicode_data.human_readable_script_name(script)
                   for script in scripts}
        # Capitalize N'Ko properly
        if 'Nko' in scripts:
            scripts.remove('Nko')
            scripts.add('NKo')
        scripts = {script.replace('_', '') for script in scripts}
        return '|'.join(scripts)


    font = ttLib.TTFont(file_name)

    just_the_file_name = file_name.split("/")[-1]
    fontname_regex = (
        "Noto"
        + "(?P<style>" + "|".join(FONT_STYLES) + ")"
        + "(?P<script>" + make_compact_scripts_regex() + ")?"
        + "(?P<variant>" + "|".join(FONT_VARIANTS) + ")?"
        + "-"
        + "(?P<weight>" + "|".join(FONT_WEIGHTS) + ")"
        + ".ttf$")
    match = re.match(fontname_regex, just_the_file_name)
    if match:
        style, compact_script, variant, weight = match.groups()
        if compact_script:
            script = unicode_data.script_code(compact_script)
            assert script != "Zzzz"
        elif style in ["Sans", "Serif"]:
            script = "Latn"  # LGC really
        else:
            style, script, variant, weight = HARD_CODED_FONT_INFO[
                just_the_file_name]
            warn("File name",
                 "Style %s also needs a script mentioned in the "
                 "file name." % style)
    else:
        style, script, variant, weight = HARD_CODED_FONT_INFO[
            just_the_file_name]
        warn("File name",
             "File name '%s' does not match the Noto font naming guidelines."
             % just_the_file_name)

    is_ui = (variant == "UI")

    is_indic = script in {
        "Deva", "Beng", "Guru", "Gujr", "Orya",
        "Taml", "Telu", "Knda", "Mlym", "Sinh"}

    deemed_ui = (not is_ui) and script in noto_data.DEEMED_UI_SCRIPTS_SET

    check_name_table()
    cmap = check_cmap_table()
    check_head_tables(cmap)
    check_vertical_limits()
    check_for_intersections_and_off_curve_extrema()
    check_gdef_table(cmap)
    check_gpos_and_gsub_tables()
    check_for_bidi_pairs(cmap)
    check_hints()
    check_stems(cmap)

    # This must be done at the very end, since the subsetter may change the font
    check_accessiblity(cmap)

    warn("info",
         "supported characters: " + printable_unicode_range(cmap.keys()))

    # TODO(roozbeh):
    # * Check that hintedness based on data in the glyf table
    #   matches metadata (file location, header data)
    # * Check GSUB coverage, based on script
    # * Check gasp values
    # * Add support for TTC fonts
    # * Check ulCodePageRange values


def main():
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
        "font_files",
        metavar="font",
        nargs="+",
        help="a font file to check")
    arguments = parser.parse_args()

    for font_file_name in arguments.font_files:
        check_font(font_file_name, arguments.csv, arguments.info)


if __name__ == "__main__":
    main()
