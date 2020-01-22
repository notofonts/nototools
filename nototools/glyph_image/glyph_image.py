# Copyright 2017 Google Inc. All rights reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import math
import re
import sys

from PIL import Image

"""Work with glyph image data files generated by glyph_image.

GlyphImage represents a single bitmap image read from the file.

GlyphImageCollection represents the entire file, it contains an object
representing the file header and a map from glyph index to GlyphImages.

This also contains utilities for working with image data and image
'frames' e.g. the bounding box of an image.  In particular it has methods
for computing the union of frames, rendering an image into a frame and
annotating it with ascent/descent/advance lines, and rendering a 'comparison'
of two images that highlights differences in red/green after aligning
images at their origins.
"""


Frame = collections.namedtuple('Frame', 'l t w h')
Advance = collections.namedtuple('Advance', 'int frac')
FileHeader = collections.namedtuple('FileHeader', 'file name upem ascent descent size font_glyphs num_glyphs')


class GlyphImage(object):
    def __init__(self, file_header, index, adv, frame, data=None):
        self.file_header = file_header
        self.index = index
        self.adv = adv
        self.frame = frame
        if data is None:
            data = [0] * (frame.w * frame.h)
        self.data = data

    def __lt__(self, rhs):
        return self.index < rhs.index

    def __repr__(self):
        return 'index: %3d, adv: %3d+%3d, ltwh: %3d %3d %3d %3d' % ((self.index,) + self.adv + self.frame)

    def get(self, x, y, val):
        """Return data at x, y if x, y in frame, else return val."""
        fr = self.frame
        if frame_contains(fr, x, y):
            val = self.data[(y - fr.t) * fr.w + x - fr.l]
        return val

    def metrics_frame(self):
        header = self.file_header
        adv = self.adv
        ascent = int(math.ceil(header.ascent * header.size / header.upem))
        descent = int(math.ceil(header.descent * header.size / header.upem))
        advance = adv.int + int(math.ceil(adv.frac / 64))
        return Frame(0, -ascent, advance, ascent + descent)

    def render(self, dframe, decorate=0):
        """Create data for dframe, and copy the overlapping part of this and
        dframe aligning at origin.  If decorate is nonzero, render metrics."""

        # might be able to use PIL
        sframe = self.frame

        data = [0] * (dframe.w * dframe.h)
        l = max(sframe.l, dframe.l)
        t = max(sframe.t, dframe.t)
        r = min(sframe.l + sframe.w, dframe.l + dframe.w)
        b = min(sframe.t + sframe.h, dframe.t + dframe.h)
        src_o = (t - sframe.t) * sframe.w + l - sframe.l
        dst_o = (t - dframe.t) * dframe.w + l - dframe.l

        src_d = src_o
        dst_d = dst_o
        for _ in range(b - t):
            src_ix = src_d
            dst_ix = dst_d
            for _ in range(r - l):
                data[dst_ix] = self.data[src_ix]
                src_ix += 1
                dst_ix += 1
            src_d += sframe.w
            dst_d += dframe.w

        if decorate > 0 and len(data) > 0:
            mf = self.metrics_frame()
            asc_t = max(mf.t, dframe.t)
            dsc_b = min(mf.t + mf.h, dframe.t + dframe.h)
            adv_r = min(mf.l + mf.w, dframe.l + dframe.w)

            dst_ix = (asc_t - dframe.t) * dframe.w + 0 - dframe.l
            for _ in range(dsc_b - asc_t):
                data[dst_ix] = max(data[dst_ix], decorate)
                dst_ix += dframe.w

            if adv_r:
                dst_ix = (0 - dframe.t) * dframe.w + 0 - dframe.l
                count = adv_r
            else:
                # mark baseline for zero advance glyphs
                adv_l = max(-3, dframe.l)
                dst_ix = (0 - dframe.t) * dframe.w + (adv_l - dframe.l)
                count = 4 - adv_l
            for _ in range(count):
                data[dst_ix] = max(data[dst_ix], decorate)
                dst_ix += 1

        return data

    def image_str(self):
        lines = []
        ix = 0
        for _ in range(self.frame.h):
            line = [':']
            for _ in range(self.frame.w):
                val = self.data[ix]
                ix += 1
                line.append('  ' if val == 0 else '%02x' % val)
            lines.append(''.join(line).rstrip())
        return '\n'.join(lines)


class GlyphImageCollection(object):
    def __init__(self, file_header, image_dict):
        self.file_header = file_header
        self.image_dict = image_dict
        self._cframe = None
        self._cmframe = None
        self._max_index = None

    def max_glyphindex(self):
        if self._max_index is None:
            gi = None
            for k in self.image_dict:
                if gi is None or k > gi:
                    gi = k
            self._max_index = gi
        return self._max_index

    def common_frame(self, include_metrics=False):
        fr = self._cmframe if include_metrics else self._cframe
        if fr is None:
            frames = [gi.frame for gi in self.image_dict.values()]
            if include_metrics:
                frames.extend(gi.metrics_frame() for gi in self.image_dict.values())
            fr = union_frames(frames)
            if include_metrics:
                self._cmframe = fr
            else:
                self._cframe = fr
        return fr


class LineStripper(object):
    def __init__(self, it):
        self.it = it

    def __iter__(self):
        return self

    def next(self):
        while True:
            line = next(self.it)
            ix = line.find('#')
            if ix >= 0:
                line = line[:ix].rstrip()
            if line:
                return line


_glyph_header_re = re.compile(
    r'^>\s*glyph:\s*(\d+)\s*;' r'\s*(\d+)(?:\s*,\s*(\d+))?\s*;' r'\s*(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s*$'
)


def write_file_header(file_header, fd):
    for k in FileHeader._fields:
        print('> %s: %s' % (k, getattr(file_header, k)), file=fd)


def write_glyph_image(im, glyph_header_only, fd):
    # > glyph: 0;64,1;6 -92 52 92
    adv_string = str(im.adv.int)
    if im.adv.frac:
        adv_string += ',%d' % im.adv.frac
    print('> glyph: %d;%s;%d %d %d %d' % ((im.index, adv_string) + im.frame), file=fd)
    if not glyph_header_only:
        print(im.image_str(), file=fd)


def _next_file_header(it):
    def get_val(k):
        regex = r'>\s*%s:\s*(.*)\s*$' % k
        line = next(it)
        m = re.match(regex, line)
        if not m:
            raise Exception('regex %s failed to match "%s"' % (k, line))
        val = m.group(1)
        if k not in ['name', 'file']:
            val = int(val)
        return val

    return FileHeader._make([get_val(k) for k in FileHeader._fields])


def _next_glyph_image(it, file_header):
    glyph_header = next(it).strip()
    m = _glyph_header_re.match(glyph_header)
    if not m:
        raise Exception('could not match glyph header "%s"' % glyph_header)
    args = m.groups()
    index = int(args[0])
    adv_int = int(args[1])
    adv_frac = int(args[2]) if args[2] else 0
    adv = Advance(adv_int, adv_frac)
    frame = Frame._make([int(a) for a in m.groups()[3:]])
    image = GlyphImage(file_header, index, adv, frame)
    row_base = 0
    for _ in range(image.frame.h):
        line = next(it).rstrip()
        assert line.startswith(':')
        ix = 0
        row_data = line[1:]
        while row_data:
            if ix >= image.frame.w:
                raise Exception('line has more than %d values: "%s"' % (image.frame.w, line))
            if row_data[:2] != '  ':
                image.data[row_base + ix] = int(row_data[:2], 16)
            row_data = row_data[2:]
            ix += 1
        row_base += image.frame.w
    return image


def read_file(filename):
    with open(filename, 'r') as f:
        it = LineStripper(f)
        file_header = _next_file_header(it)
        image_dict = {}
        for _ in range(file_header.num_glyphs):
            im = _next_glyph_image(it, file_header)
            image_dict[im.index] = im
        return GlyphImageCollection(file_header, image_dict)


def frame_contains(fr, x, y):
    return fr.l <= x < (fr.l + fr.w) and fr.t <= y < (fr.t + fr.h)


def frame_is_empty(frame):
    return frame is None or frame.w <= 0 or frame.h <= 0


def union_frames(frames):
    l, t, r, b = None, None, None, None
    for fr in frames:
        if fr is None:
            continue
        if l is None:
            l, t, r, b = fr.l, fr.t, fr.l + fr.w, fr.t + fr.h
        else:
            if fr.l < l:
                l = fr.l
            if fr.t < t:
                t = fr.t
            nr = fr.l + fr.w
            if nr > r:
                r = nr
            nb = fr.t + fr.h
            if nb > b:
                b = nb
    return Frame(l, t, r - l, b - t) if l is not None else None


def pad_frame(frame, pad):
    if pad:
        fr = frame

        if isinstance(pad, int) or len(pad) == 1:
            p0 = pad if isinstance(pad, int) else pad[0]
            pl, pt, pr, pb = p0, p0, p0, p0
        elif len(pad) == 2:
            p0, p1 = pad
            pl, pt, pr, pb = p0, p1, p0, p1
        elif len(pad) == 4:
            pl, pt, pr, pb = pad
        else:
            raise ValueError('bad pad length: %d' % len(pad))

        frame = Frame(fr.l - pl, fr.t - pt, fr.w + pl + pr, fr.h + pt + pb)
    return frame


def compute_frame(gi1, gi2, include_metrics=False, pad=None):
    """The frame is the union the union of the two input frames,
    plus their metrics frames if include_metrics is True.
    If pad is specified it should contain 1, 2, or 4 values to
    add to the left, top, right, and bottom of the computed frame."""

    if gi1 is None or gi2 is None:
        gi = gi1 or gi2
        if gi is None:
            raise ValueError('both arguments are None')
        return pad_frame(gi.metrics_frame() if include_metrics else gi.frame, pad)

    frames = [gi1.frame, gi2.frame]
    if include_metrics:
        frames.extend([gi1.metrics_frame(), gi2.metrics_frame()])
    return pad_frame(union_frames(frames), pad)


def create_compare_image(gi1, gi2, frame, decorate=False):
    """Return an image comparing the two glyphs rendered at the origin, and
    a similarity metric showing the percentage of marked pixels with matching
    values.  The image is an RGB image with the red channel matching gi1, the
    green channel matching gi2, and the blue channel the minimum of the red and
    blue channels.  The result is a grayscale image tinged red where gi1 is
    darker and green where gi2 is darker.  If decorate is True, the images
    are rendered with gray decoration showing the ascent, descent, and advance.
    """
    if frame_is_empty(frame):
        return None

    metrics_line_color = 0x80 if decorate else 0

    def render(gi):
        if gi is None:
            return [0] * (frame.w * frame.h)
        else:
            return gi.render(frame, decorate=metrics_line_color)

    red_data = render(gi1)
    green_data = render(gi2)

    matched = 0
    marked = 0
    image = Image.new('RGB', (frame.w, frame.h))
    data = list(image.getdata())
    for i in range(len(data)):
        rd = red_data[i]
        gn = green_data[i]
        if rd or gn:
            marked += max(rd, gn)
            matched += min(rd, gn)
        red = 255 - rd
        green = 255 - gn
        data[i] = (red, green, min(red, green))
    image.putdata(data)

    similarity = 100 if not marked else int(matched * 100 / marked)

    return image, similarity


def test(glyph_image_file):
    image_collection = read_file(glyph_image_file)
    write_file_header(image_collection.file_header, sys.stdout)
    for ix in sorted(image_collection.image_dict):
        im = image_collection.image_dict[ix]
        write_glyph_image(im, True, sys.stdout)


# a file generated by the glyph_image executable,
# e.g. 'glyph_image/gujarati_test.txt'
if __name__ == '__main__':
    print('input file: %s' % sys.argv[1])
    test(sys.argv[1])
