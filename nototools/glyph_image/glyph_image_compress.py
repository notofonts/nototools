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

"""Utilities for rle-style compression on glyph image data."""

# Not really better than zip compression, as it turns out.  This is
# not currently used.

import argparse
from os import path

from nototools.glyph_image import glyph_image


# basic idea here is that most runs are of white or black, so only rle-encode
# those and don't bother with the rest.
def rle(data):
    # all values except ff and 00 are single bytes.  these two
    # values are followed by a single-byte count
    output = []
    i = 0
    lim = len(data)
    while i < lim:
        v = data[i]
        i += 1
        output.append(v)
        if v == 0 or v == 0xFF:
            j = i
            nlim = min(i + 255, lim)
            while j < nlim and data[j] == v:
                j += 1
            output.append(j - i)
            i = j
    return output


def expand_rle(compressed_data):
    output = []
    i = 0
    lim = len(compressed_data)
    while i < lim:
        v = compressed_data[i]
        i += 1
        output.append(v)
        if v == 0 or v == 0xFF:
            c = compressed_data[i]
            i += 1
            while c > 0:
                output.append(v)
                c -= 1
    return output


def compare_rle(expanded_data, original_data):
    olen = len(original_data)
    elen = len(expanded_data)
    if olen != elen:
        return False, "original len %d, expanded len %d" % (olen, elen)
    for i in range(olen):
        v = original_data[i]
        ev = expanded_data[i]
        if v != ev:
            return False, "mismatch %d (%d) at %d" % (v, ev, i)
    return True, None


# Basic idea here is that we can have short runs of black/white once we
# get inside the glyphs, and that the extra rle count gets excessive.
# so if we quantize the data to 128 values, we can use the remaining 128
# values to encode the color (black or white) and the count, so these
# runs will only take one byte.  Also since runs of white are longer we
# need less range for the black runs than for the white runs.  The
# problem of course is we lose the precision in the data.
def rle2(data):
    # lossy, we halve the values to 128 and take the upper range and
    # convert 32 of it to runs of black and 96 of it to runs of white.
    output = []
    i = 0
    lim = len(data)
    while i < lim:
        v = data[i]
        if not (v == 0 or v == 0xFF):
            output.append(v / 2)
            i += 1
        else:
            if v == 0xFF:
                nlim = min(i + 32, lim)
                base = 128
            else:
                nlim = min(i + 96, lim)
                base = 128 + 32
            j = i + 1
            while j < nlim and data[j] == v:
                j += 1
            # print('run of %d at %d len %d' % (v, i, j - i))
            output.append(base + j - i - 1)
            i = j
    return output


def expand_rle2(compressed_data):
    output = []
    for v in compressed_data:
        if v < 128:
            output.append(v * 2 if v else 1)
        elif v < 160:
            for i in range(v - 127):
                output.append(0xFF)
        else:
            for i in range(v - 159):
                output.append(0)
    return output


def compare_rle2(expanded_data, original_data):
    olen = len(original_data)
    elen = len(expanded_data)
    if olen != elen:
        return False, "original len %d, expanded len %d" % (olen, elen)
    for i in range(olen):
        v = original_data[i]
        if v == 0 or v == 0xFF:
            if expanded_data[i] != v:
                return False, "mismatch %d at %d" % (v, i)
        else:
            ev = expanded_data[i]
            if not (v == ev or v == ev + 1):
                return False, "mismatch %d (%d) at %d" % (v, ev, i)
    return True, None


_base64_enc = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+/"
_base64_inv = [None] * 128
for i, c in enumerate(_base64_enc):
    _base64_inv[ord(c)] = i


def base64_encode(data):
    output = []

    def add_triple(triple):
        v0, v1, v2 = triple[:3]
        output.append(_base64_enc[v0 >> 2])
        output.append(_base64_enc[((v0 & 3) << 4) + (v1 >> 4)])
        output.append(_base64_enc[((v1 & 0xF) << 2) + (v2 >> 6)])
        output.append(_base64_enc[v2 & 0x3F])

    def add_final_triple(short_triple):
        vals = len(short_triple)
        v0 = short_triple[0]
        v1 = short_triple[1] if vals > 1 else 0
        output.append(_base64_enc[v0 >> 2])
        output.append(_base64_enc[((v0 & 3) << 4) + (v1 >> 4)])
        if vals == 1:
            output.append("=")
            output.append("=")
        else:
            v2 = short_triple[2] if vals > 2 else 0
            output.append(_base64_enc[((v1 & 0xF) << 2) + (v2 >> 6)])
            if vals == 2:
                output.append("=")
            else:
                output.append(_base64_enc[v2 & 0x3F])

    lim = int(len(data) / 3) * 3
    for i in range(0, lim, 3):
        add_triple(data[i:])
    if lim < len(data):
        add_final_triple(data[lim:])

    return "".join(output)


def base64_decode(encoded_data):
    output = []
    temp = [0] * 3  # used by add_quad

    def val(c):  # type: (str) -> int
        return _base64_inv[ord(c)]

    def add_quad(quad):
        n = val(quad[0])
        v = n << 2
        n = val(quad[1])
        temp[0] = v + (n >> 4)
        v = (n << 4) & 0xFF
        n = val(quad[2])
        temp[1] = v + (n >> 2)
        v = (n << 6) & 0xFF
        n = val(quad[3])
        temp[2] = v + n
        output.extend(temp)

    def add_final_quad(quad):
        n = val(quad[0])
        v = n << 2
        n = val(quad[1])
        output.append(v + (n >> 4))
        if len(quad) > 2 and quad[2] != "=":
            v = (n << 4) & 0xFF
            n = val(quad[2])
            output.append(v + (n >> 2))
            if len(quad) > 3:
                assert quad[3] == "="

    i = 0
    lim = len(encoded_data)
    try:
        while i < lim:
            add_quad(encoded_data[i:])
            i += 4
    except:
        add_final_quad(encoded_data[i:])

    return output


def wrap_str(s, wrap_len):
    return "\n".join(s[i : i + wrap_len] for i in range(0, len(s), wrap_len))


def _test_b64():
    test_data = [0xE6, 0xD5, 0xC4, 0xB3]
    for i in range(len(test_data)):
        temp = test_data[i:]
        enc = base64_encode(temp)
        print("%s: %s" % (" ".join("%02x" % v for v in temp), enc))
        res = base64_decode(enc)
        print(" --> %s" % (" ".join("%02x" % v for v in res)))


# e.g. glyph_image/gujarati_test_old.txt
def _test(image_file):
    """Compare size of our rle encoding with that of our lossy rle encoding."""
    coll = glyph_image.read_file(image_file)
    for ix, im in sorted(coll.image_dict.items())[:15]:
        data = im.data
        print("glyph %d (%d)" % (ix, len(data)))
        rle1_data = rle(data)
        rle2_data = rle2(data)

        rle1_len = len(rle1_data)
        rle2_len = len(rle2_data)
        pct = 0 if rle1_len == 0 else int(rle2_len * 100 / rle1_len)
        print("  rle %d, lossy rle %d (%2d%%)" % (rle1_len, rle2_len, pct))

        expanded_rle1 = expand_rle(rle1_data)
        rle1_ok, msg = compare_rle(expanded_rle1, data)
        if not rle1_ok:
            print("failed to expand rle data, %s" % msg)

        expanded_rle2 = expand_rle2(rle2_data)
        rle2_ok, msg = compare_rle2(expanded_rle2, data)
        if not rle2_ok:
            print("failed to expand rle2 data, %s" % msg)
        else:
            enc_rle2 = base64_encode(rle2_data)
            # print(wrap_str(enc_rle2, 80))
            temp = base64_decode(enc_rle2)
            enc_rle2_ok, msg = compare_rle(temp, rle2_data)


def compress(input_file, output_file, comp):
    print("compress" if comp else "uncompress")
    print(" input: %s" % input_file)
    print("output: %s" % output_file)

    if comp:
        coll = glyph_image.read_file(input_file)
        with open(output_file, "w") as f:
            glyph_image.write_file_header(coll.file_header, f)
            for _, im in sorted(coll.image_dict.items()):
                glyph_image.write_glyph_image(im, True, f)
                rle_data = rle(im.data)
                rle_data_b64 = base64_encode(rle_data)
                b64_len = len(rle_data_b64)
                print("> rle %d" % b64_len, file=f)
                print(wrap_str(rle_data_b64, 80), file=f)
    else:
        print("uncompress not supported")


def default_compress(input_file, output_file, comp):
    """Default output_file and compress based on input_file extension.
    Compressed files have a .b64 extension, uncompressed files have
    a .txt' extension."""

    assert input_file is not None
    base, ext = path.splitext(path.basename(input_file))

    print('base "%s" ext "%s"' % (base, ext))
    if comp is None:
        if ext == ".txt":
            comp = True
        elif ext == ".b64":
            comp = False
        else:
            raise Exception("don't know whether to compress/decompress %s" % input_file)

    if output_file is None:
        if comp:
            if ext == ".b64":
                raise Exception(
                    "won't compress already compressed file %s" % input_file
                )
            elif ext == ".txt":
                output_file = base + ".b64"
            else:
                output_file = input_file + ".b64"
        else:
            if ext == ".txt":
                raise Exception("won't uncompress uncompressed file %s" % input_file)
            elif ext == ".b64":
                output_file = base + ".txt"
            else:
                output_file = input_file + ".txt"
    else:
        obase, oext = path.splitext(path.basename(output_file))
        if oext == ".txt":
            if comp:
                raise Exception("compressed files shouldn't end in .txt")
        elif oext == ".b64":
            if not comp:
                raise Exception("uncompressed files shouldn't end in .b64")
        elif not oext:
            output_file = output_file + (".b64" if comp else ".txt")

    compress(input_file, output_file, comp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input_file",
        help="glyph image file to input",
        metavar="file",
        required=True,
    )
    parser.add_argument("-o", "--output_file", help="file to output", metavar="file")
    parser.add_argument(
        "-c",
        "--compress",
        help="compress (based on input extension)",
        type=bool,
        nargs="?",
        const=True,
        metavar="tf",
    )
    parser.add_argument(
        "-t", "--test", help="run test compression on input file", action="store_true"
    )
    args = parser.parse_args()

    if args.test:
        _test(args.input_file)
    else:
        default_compress(args.input_file, args.output_file, args.compress)


if __name__ == "__main__":
    main()
