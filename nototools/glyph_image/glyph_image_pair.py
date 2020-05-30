#!/usr/bin/env python
#
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
# test reading bitmap dump

from __future__ import absolute_import
from __future__ import print_function

"""Find a good pairing of glyph images.

This uses the Hungarian matching algorithm, which takes a matrix of
row x column 'costs' and tries to pair each row with a column so as to
minimize the total cost.

The cost represents the mismatch between two glyph images rendered into
a common frame big enough to enclose any image.  This is computed as the
sum of the squares of the difference between corresponding pixels.

This is expensive to compute on full sized images (e.g. 128x128 pixel) so
we 'fingerprint' the images by using PIL to scale them down to 20x20 and
compute the cost function based on that. This gives us reasonable running
times (tens of seconds) for matches of of groups of around 300.

Before we start we exclude images already matched based on codepoint, as
we expect this is the intended pairing of those glyphs.  We also exclude
images that are an exact match, if any."""

import argparse
import collections
import sys
import time
from os import path

from fontTools import ttLib
from PIL import Image

from nototools import font_data

from nototools.glyph_image import glyph_image

PairInfo = collections.namedtuple(
    "PairInfo",
    "base_path base_hash target_path target_hash cp_pairs "
    "pri_pairs alt_base_pairs, alt_target_pairs",
)


class HungarianMatcher(object):
    """Implements the 'Hungarian matching' algorithm to return the 'best'
    pairing of rows with columns (which might differ in number) based on
    the costs in the data matrix."""

    def __init__(self, data, rows, cols, dbg=False):
        if len(data) != rows * cols:
            raise ValueError(
                "data length %d != rows %d x cols %d (%d)"
                % (len(data), rows, cols, rows * cols)
            )

        self.data = data
        self.rows = rows
        self.cols = cols
        self.dbg = dbg

        self._marked = [0] * len(data)
        self._covered_rows = [False] * rows
        self._covered_cols = [False] * cols

    def run(self):
        self._setup()

        if self.dbg:
            self._print_dbg()
        fn = self._3_cover_starred_zeros
        while fn is not None:
            fn = fn()
            if self.dbg:
                self._print_dbg()

        return self._get_starred_zero_pairs()

    def _print_dbg(self):
        marks = [" ", "*", "'"]
        print(
            "  "
            + " ".join(
                "%4s" % ("x" if self._covered_cols[c] else "") for c in range(self.cols)
            )
        )
        n = 0
        for r in range(self.rows):
            print("x" if self._covered_rows[r] else " ",)
            print(
                " ".join(
                    "%3d%1s" % (self.data[m], marks[self._marked[m]])
                    for m in range(n, n + self.cols)
                )
            )
            n += self.cols

    def _get_starred_zero_pairs(self):
        pairs = []
        rows = self.rows
        cols = self.cols
        marked = self._marked

        n = 0
        for r in range(rows):
            for c in range(cols):
                if marked[n] == 1:
                    pairs.append((r, c))
                n += 1
        return pairs

    def _setup(self):
        data = self.data
        rows = self.rows
        cols = self.cols
        marked = self._marked

        # Step 1. Find the smallest element in each row, and subtract it from
        # every element in the row.
        if self.dbg:
            print("step 1")
        n = 0
        for r in range(rows):
            lim = n + cols
            min_val = min(data[n:lim])
            for m in range(n, lim):
                data[m] -= min_val
            n = lim

        # Step 2. Scan each row for a zero in a column with no starred zero,
        # and star it.
        if self.dbg:
            print("step 2")
        starred_cols = [False] * cols
        n = 0
        for r in range(rows):
            m = n
            for c in range(cols):
                if data[m] == 0 and not starred_cols[c]:
                    starred_cols[c] = True
                    marked[m] = 1
                    break
                m += 1
            n += cols

    def _3_cover_starred_zeros(self):
        # Step 3.  Cover each column with a starred zero.
        # If after this all columns are covered,
        # or more columns than rows are covered, we're done.
        # Otherwise go to step 4 prime_uncovered_zeros.

        rows = self.rows
        cols = self.cols
        marked = self._marked
        covered_cols = self._covered_cols

        if self.dbg:
            print("step 3")
        n = 0
        for r in range(rows):
            for c in range(cols):
                if marked[n] == 1:
                    covered_cols[c] = True
                n += 1

        count = sum(covered_cols)
        return None if count >= min(rows, cols) else self._4_prime_uncovered_zeros

    def _4_prime_uncovered_zeros(self):
        # Step 4. Find an uncovered zero and prime it.
        # If there is no unstarred zero in its row,
        # stop, and go to step 5 build prime star path and adjust.
        # Else cover this row and uncover this column.
        # Continue until there are no uncovered zeros, then go to step 6

        data = self.data
        rows = self.rows
        cols = self.cols
        marked = self._marked
        covered_rows = self._covered_rows
        covered_cols = self._covered_cols

        def find_and_prime_uncovered_zero():
            n = 0
            for r in range(rows):
                if not covered_rows[r]:
                    m = n
                    for c in range(cols):
                        if not covered_cols[c] and data[m] == 0:
                            marked[m] = 2
                            return r, c
                        m += 1
                n += cols
            return -1, -1

        def find_star_in_row(row):
            n = row * cols
            for c in range(cols):
                if marked[n] == 1:
                    return c
                n += 1
            return -1

        if self.dbg:
            print("step 4")
        while True:
            r, c = find_and_prime_uncovered_zero()
            if r < 0:
                return self._6_find_smallest_uncovered_and_adjust
            starred_col = find_star_in_row(r)
            if starred_col < 0:
                self._path = [(r, c)]
                return self._5_build_prime_star_path_and_adjust
            else:
                covered_rows[r] = True
                covered_cols[starred_col] = False

    def _5_build_prime_star_path_and_adjust(self):
        # Step 5.  Construct a series of alternating primed and starred zeros.
        # Start with the uncovered primed zero found by step 4
        # prime_uncovered_zeros.
        data = self.data
        rows = self.rows
        cols = self.cols
        marked = self._marked
        path = self._path

        def find_star_in_col(col):
            n = col
            for r in range(rows):
                if marked[n] == 1:
                    return r
                n += cols
            return -1

        def find_prime_in_row(row):
            n = row * cols
            for c in range(cols):
                if marked[n] == 2:
                    return c
                n += 1
            raise ValueError("should not happen")

        if self.dbg:
            print("step 5")
        while True:
            r, c = path[-1]
            starred_row = find_star_in_col(c)
            if starred_row < 0:
                break
            path.append((starred_row, c))
            primed_col = find_prime_in_row(starred_row)
            path.append((starred_row, primed_col))

        # change each zero in path: primed -> starred, starred -> unmarked
        for r, c in path:
            n = r * cols + c
            v = marked[n]
            marked[n] = 1 if v == 2 else 0

        # erase all primes
        for n in range(len(data)):
            if marked[n] == 2:
                marked[n] = 0

        # clear all covers
        self._covered_cols = [False] * cols
        self._covered_rows = [False] * rows

        return self._3_cover_starred_zeros

    def _6_find_smallest_uncovered_and_adjust(self):
        # Step 6.  Find the smallest uncovered value.
        # Add it to each covered row
        # and subtract it from each uncovered column.
        data = self.data
        rows = self.rows
        cols = self.cols
        covered_cols = self._covered_cols
        covered_rows = self._covered_rows

        if self.dbg:
            print("step 6")
        n = 0
        v = None
        for r in range(rows):
            if not covered_rows[r]:
                m = n
                for c in range(cols):
                    if not covered_cols[c]:
                        t = data[m]
                        if v is None or t < v:
                            v = t
                    m += 1
            n += cols

        n = 0
        for r in range(rows):
            row_delta = v if covered_rows[r] else 0
            for c in range(cols):
                delta = row_delta - (0 if covered_cols[c] else v)
                if delta:
                    data[n] += delta
                n += 1

        return self._4_prime_uncovered_zeros


# Test call of the matcher.
def _test_matcher():
    matrix = [1, 2, 3, 2, 4, 6, 3, 6, 9]
    m = HungarianMatcher(matrix, 3, 3, dbg=True)
    pairs = m.run()
    for p in pairs:
        print("row %d, col %d" % p)


def _get_cp_to_glyphix(font):
    # so, i should use glyph names, then the cmap is exactly what I want, no?
    cmap = font_data.get_cmap(font)  # cp to glyph name
    name_to_index = {g: i for i, g in enumerate(font.getGlyphOrder())}
    return {cp: name_to_index[cmap[cp]] for cp in cmap}


def _fingerprint(data, frame, size):
    # python 2
    data_str = "".join(chr(p) for p in data)
    im = Image.fromstring("L", (frame.w, frame.h), data_str, "raw", "L", 0, 1)
    im = im.resize(size, resample=Image.BILINEAR)
    return list(im.getdata())


def _get_ix_to_fingerprint(collection, unmatched, frame, size):
    ix_to_fingerprint = {}
    for i in unmatched:
        data = collection.image_dict[i].render(frame)
        ix_to_fingerprint[i] = _fingerprint(data, frame, size)
    return ix_to_fingerprint


def _diff_fingerprints(base_fp, target_fp):
    diffs = [b - t for b, t in zip(base_fp, target_fp)]
    return sum(d * d for d in diffs)


def _get_image_diff_pairs(
    base_collection, base_unmatched, target_collection, target_unmatched
):
    """Returns three lists of pair tuples.  Each pair tuple is base ix,
    target ix, difference value.  If the number of base and target differ,
    some are paired with '-1' and for these the difference will also be
    -1.

    The first list is the 'primary pairing', chosen to generate the lowest
    overall difference across all pairs.  The other two lists are 'alternate
    pairings' for some base or target glyphs.  These provide an alternate
    pair for a base or target in which the difference is lower than in the
    primary pairing."""

    # We determine the common frame, and render each unmatched image
    # into that frame.  We reduce this to a 'fingerprint' and employ a
    # distance metric based on the sum of the squares of the differences
    # between corresponding pixels in base and target fingerprints.

    log = False
    if log:
        print(
            "get image diff pairs, %d base, %d target"
            % (len(base_unmatched), len(target_unmatched))
        )

        base_time = time.time()

        def elapsed():
            return "%6d" % int(round((time.time() - base_time) * 1000.0))

    # Use common frame for all glyphs.  Among other things this means we
    # don't need to scale the cost, since the scale for all pairs is the same.
    fr = glyph_image.union_frames(
        [base_collection.common_frame(), target_collection.common_frame()]
    )

    # fingerprint size, might want to control
    fp_size = (20, 20)

    if log:
        print(elapsed(), "get data")
    base_ix_to_fingerprint = _get_ix_to_fingerprint(
        base_collection, base_unmatched, fr, fp_size
    )
    target_ix_to_fingerprint = _get_ix_to_fingerprint(
        target_collection, target_unmatched, fr, fp_size
    )

    if log:
        print(elapsed(), "compute diffs")

    pri_pairs = []

    best_base_diffs = {}
    best_target_diffs = {}

    # This is a little extra work just for comparison.  We look for exact
    # matches between glyphs, and if we find any, we assume these must be
    # intentional and remove them from consideration (not sure if the matching
    # algorithm might split them if it makes the cost over all matches lower).
    # We also record, for each base and target, the closest corresponding
    # target / base, in case this differs from what ended up being chosen.
    diff_pool = {}
    exact_matches = []
    for base_ix, base_fp in sorted(base_ix_to_fingerprint.items()):
        if log:
            print(elapsed(), "diff base %d" % base_ix)
        exact_match = None
        best_diff = None
        if not target_ix_to_fingerprint:
            if log:
                print("  no remaining targets")
            break
        for target_ix, target_fp in sorted(target_ix_to_fingerprint.items()):
            diff = _diff_fingerprints(base_fp, target_fp)
            if diff == 0:
                exact_match = (base_ix, target_ix)
                if log:
                    print("  exact match", target_ix)
                break

            if best_diff is None or diff < best_diff[0]:
                best_diff = (diff, target_ix)
            diff_pool[(base_ix, target_ix)] = diff

        if exact_match:
            exact_matches.append(exact_match)
            del target_ix_to_fingerprint[exact_match[1]]
        if best_diff:  # might be no targets left
            best_base_diffs[base_ix] = best_diff
            if log:
                print("  best diff base %d target %d" % best_diff)

    # ok, now remove the exact match base indexes
    for base_ix, target_ix in sorted(exact_matches):
        del base_ix_to_fingerprint[base_ix]
        pri_pairs.append((base_ix, target_ix, 0))

    # now both maps exclude the exact matches
    # of the remaining, we have the best matches for the base,
    # but not for target
    for target_ix in target_ix_to_fingerprint:
        best_diff = None
        for base_ix in base_ix_to_fingerprint:
            try:
                diff = diff_pool[(base_ix, target_ix)]
                if best_diff is None or diff < best_diff[0]:
                    best_diff = (diff, base_ix)
            except:
                continue
        if best_diff:
            best_target_diffs[target_ix] = best_diff

    # for jollies, let's see how many of these match, that is, the
    # row and col in the pair are each closer to the other than to any
    # other col or row.
    reciprocal_pairs = []
    for base_ix, (diff, t) in sorted(best_base_diffs.items()):
        other = best_target_diffs[t]
        if other is not None and other[1] == base_ix:
            reciprocal_pairs.append((base_ix, t, diff))
            if log:
                print("reciprocal pair: %d target %d diff %d" % (base_ix, t, diff))

    # We've collected the 'cost' for all pairs.
    # If there are no rows or targets, nothing left to match.  Else use the
    # HungarianMatcher to match these.  We need to map the remaining glyphs
    # in each group to a contiguous range from 0-n to call the matcher, then
    # map back when we're done.
    if base_ix_to_fingerprint and target_ix_to_fingerprint:
        row_to_base = sorted(base_ix_to_fingerprint.keys())
        col_to_target = sorted(target_ix_to_fingerprint.keys())
        nrows = len(row_to_base)
        ncols = len(col_to_target)
        base_to_row = {b: i for i, b in enumerate(row_to_base)}
        target_to_col = {t: i for i, t in enumerate(col_to_target)}

        if log:
            print(elapsed(), "match remaining %d x %d" % (nrows, ncols))

        max_diff = 255 * fr.w * fr.h
        mat = [max_diff] * (nrows * ncols)
        for (b, t), d in diff_pool.items():
            # later exact matches might have removed either
            if b in base_to_row and t in target_to_col:
                n = base_to_row[b] * ncols + target_to_col[t]
                mat[n] = d

        matcher = HungarianMatcher(mat, nrows, ncols)
        rcpairs = matcher.run()

        if log:
            print(elapsed(), "report paired")

        btpairs = [(row_to_base[r], col_to_target[c]) for r, c in sorted(rcpairs)]
        for b, t in btpairs:
            del base_ix_to_fingerprint[b]
            del target_ix_to_fingerprint[t]
            pri_pairs.append((b, t, diff_pool[(b, t)]))

    # A little sanity check.  If a row/col are a reciprocal pair, usually
    # the Hungarian matcher will return it, though not always.
    missing_rp_count = 0
    for p in reciprocal_pairs:
        if p not in pri_pairs:
            missing_rp_count += 1
            if log:
                print("!! missing reciprocal pair %s" % str(p))
    if log and missing_rp_count:
        num = len(reciprocal_pairs)
        print(
            "missing %d of %d reciprocal pair%s"
            % (missing_rp_count, num, "" if num == 1 else "s")
        )

    if log:
        print(elapsed(), "report unmatched")

    # All unmatched rows or cols report difference as -1
    for base_ix in sorted(base_ix_to_fingerprint):
        pri_pairs.append((base_ix, -1, -1))
    for target_ix in sorted(target_ix_to_fingerprint):
        pri_pairs.append((-1, target_ix, -1))

    if log:
        print(elapsed(), "matched primary pairs")

    # For all primary pairs, look up the best match for the base and target.
    # If the diff < the current match, add that to the alternate.  This way we
    # can see what 'better' pairs the matching algorithm decided to discard.
    alt_base_pairs = []
    alt_target_pairs = []
    for b, t, d in pri_pairs:
        if d == 0:
            continue
        best_base_alt = best_base_diffs.get(b)
        if best_base_alt and (d < 0 or best_base_alt[0] < d):
            alt_base_pairs.append((b, best_base_alt[1], best_base_alt[0]))
        best_target_alt = best_target_diffs.get(t)
        if best_target_alt and (d < 0 or best_target_alt[0] < d):
            alt_target_pairs.append((best_target_alt[1], t, best_target_alt[0]))
    alt_base_pairs = sorted(alt_base_pairs, key=lambda t: t[0])
    alt_target_pairs = sorted(alt_target_pairs, key=lambda t: t[1])

    if log:
        print(elapsed(), "done")

    return pri_pairs, alt_base_pairs, alt_target_pairs


def _get_cp_pairs(base_font, target_font):
    """Return a list of tuples of base glyph ix, target glyph ix,
    codepoint for all codepoints in either font.  When a codepoint
    is in only one font, the id for the other glyph is -1."""

    base_cp_map = _get_cp_to_glyphix(base_font)
    target_cp_map = _get_cp_to_glyphix(target_font)

    pairs = []
    base_keys = set(base_cp_map.keys())
    target_keys = set(target_cp_map.keys())
    matched = base_keys & target_keys
    for k in sorted(matched):
        pairs.append((base_cp_map[k], target_cp_map[k], k))
    for k in sorted(base_keys - matched):
        pairs.append((base_cp_map[k], -1, k))
    for k in sorted(target_keys - matched):
        pairs.append((-1, target_cp_map[k], k))
    return pairs


def get_collection_pairs(base_collection, target_collection):
    """Returns a PairInfo representing a pairing of the two collections.
    This requires that the fonts referenced in the collections exist
    at their respective paths, since it reads codepoint information from
    those fonts.  It first calculates which pairs correspond due to
    codepoint, and removes them from the set of glyphs to match.  Then
    it calls _get_image_diff_pairs with the remainder."""

    base_font_path = base_collection.file_header.file
    target_font_path = target_collection.file_header.file
    base_font = ttLib.TTFont(base_font_path)
    target_font = ttLib.TTFont(target_font_path)

    cp_pairs = _get_cp_pairs(base_font, target_font)

    base_unmatched = set(range(1, base_collection.file_header.num_glyphs))
    target_unmatched = set(range(1, target_collection.file_header.num_glyphs))
    for base_ix, target_ix, _ in cp_pairs:
        if base_ix in base_unmatched:
            base_unmatched.remove(base_ix)
        if target_ix in target_unmatched:
            target_unmatched.remove(target_ix)
    pri_pairs, alt_base_pairs, alt_target_pairs = _get_image_diff_pairs(
        base_collection, base_unmatched, target_collection, target_unmatched
    )

    base_hash = filehash(base_font_path)
    target_hash = filehash(target_font_path)

    return PairInfo(
        base_font_path,
        base_hash,
        target_font_path,
        target_hash,
        cp_pairs,
        pri_pairs,
        alt_base_pairs,
        alt_target_pairs,
    )


def generate_pairs(base_glyphs, target_glyphs):
    if not path.isfile(base_glyphs):
        raise Exception("base glyph image file %s does not exist" % base_glyphs)
    if not path.isfile(target_glyphs):
        raise Exception("target glyph image file %s does not exist" % target_glyphs)

    base_collection = glyph_image.read_file(base_glyphs)
    target_collection = glyph_image.read_file(target_glyphs)
    return get_collection_pairs(base_collection, target_collection)


def filehash(filepath):
    import hashlib

    data = open(filepath, "rb").read()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def date_str(timestamp=None):
    import datetime

    if timestamp is None:
        import time

        timestamp = time.time()
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def write_pair_info(pair_info, output_file):
    """Write pair_info to a file."""

    def _write_data(fd):
        fd.write("# %s\n" % date_str())
        fd.write("> base: %s\n" % pair_info.base_path)
        fd.write("> base_hash: %s\n" % pair_info.base_hash)
        fd.write("> target: %s\n" % pair_info.target_path)
        fd.write("> target_hash: %s\n" % pair_info.target_hash)
        if pair_info.cp_pairs is not None:
            fd.write("> cp_pairs: %d\n" % len(pair_info.cp_pairs))
            for p in pair_info.cp_pairs:
                fd.write("%d;%d;%04x\n" % p)
        if pair_info.pri_pairs is not None:
            fd.write("> pri_pairs: %d\n" % len(pair_info.pri_pairs))
            for p in pair_info.pri_pairs:
                fd.write("%d;%d;%d\n" % p)
        if pair_info.alt_base_pairs is not None:
            fd.write("> alt_base_pairs: %d\n" % len(pair_info.alt_base_pairs))
            for p in pair_info.alt_base_pairs:
                fd.write("%d;%d;%d\n" % p)
        if pair_info.alt_target_pairs is not None:
            fd.write("> alt_target_pairs: %d\n" % len(pair_info.alt_target_pairs))
            for p in pair_info.alt_target_pairs:
                fd.write("%d;%d;%d\n" % p)

    if output_file:
        with open(output_file, "w") as f:
            _write_data(f)
    else:
        _write_data(sys.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b", "--base", help="base glyph image data file", metavar="file", required=True
    )
    parser.add_argument(
        "-t",
        "--target",
        help="target glyph image data file",
        metavar="file",
        required=True,
    )
    parser.add_argument("-o", "--output", help="name of output file", metavar="file")
    args = parser.parse_args()

    write_pair_info(generate_pairs(args.base, args.target), args.output)


if __name__ == "__main__":
    main()
    # _test_matcher()
