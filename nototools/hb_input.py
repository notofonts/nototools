# Copyright 2016 Google Inc. All Rights Reserved.
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



"""Provides a functions to generate harbuzz input.

The input is returned as a list of strings, suitable for passing into
subprocess.call or something similar.
"""


from fontTools.ttLib import TTFont

from nototools import summary


def all_hb_inputs(path, output_dir):
    """Generate harfbuzz inputs for all glyphs in a given font."""

    inputs = []
    font = TTFont(path)
    reverse_cmap = build_reverse_cmap(font)
    glyph_names = font.getGlyphOrder()
    for name in glyph_names:
        inputs.append([path] + hb_input_from_name(font, name, reverse_cmap))
    return inputs


def build_reverse_cmap(font):
    """Build a dictionary mapping glyph names to unicode values."""

    return {n: v for v, n in summary.get_largest_cmap(font).items()}


def hb_input_from_name(font, name, reverse_cmap=None, allow_arg=True):
    """Given font and glyph name, return input to harbuzz to render this glyph,
    not including the font path itself.

    Sometimes this will simply be the glyph itself, other times a feature may
    need to be active, or a string of glyphs used (for ligatures or contextual
    substitutions).

    A reverse cmap is used to check if the glyph has a unicode encoding; this
    can be pre-built and passed in. If `allow_arg` is false, no feature argument
    will be added (used if called recursively).
    """

    # see if this glyph has a simple unicode mapping
    if reverse_cmap is None:
        reverse_cmap = build_reverse_cmap(font)
    if name in reverse_cmap:
        return [unichr(reverse_cmap[name])]

    # nope, check the substitution features
    gsub = font['GSUB'].table
    for lookup_index, lookup in enumerate(gsub.LookupList.Lookup):
        for st in lookup.SubTable:

            # see if this glyph can be a single-glyph substitution
            if lookup.LookupType == 1:
                for in_glyph, subst in st.mapping.items():
                    if subst == name:
                        return _input_with_context(font, in_glyph, lookup_index,
                                                   allow_arg)

            # see if this glyph is a ligature
            elif lookup.LookupType == 4:
                for prefix, ligatures in st.ligatures.items():
                    for ligature in ligatures:
                        if ligature.LigGlyph == name:
                            in_glyphs = [prefix] + ligature.Component
                            return _sequence_from_glyph_names(font, in_glyphs)


def _input_with_context(font, in_glyph, lookup_index, allow_arg=True):
    """Given font, input glyph, and lookup index, return input to harfbuzz to
    render the input glyph with the referred-to lookup activated.
    """

    gsub = font['GSUB'].table

    # try to get a feature tag to activate this lookup
    if allow_arg:
        for feature in gsub.FeatureList.FeatureRecord:
            if lookup_index in feature.Feature.LookupListIndex:
                fea_arg = ['--features=%s' % feature.FeatureTag]
                return fea_arg + hb_input_from_name(font, in_glyph)

    # try for a chaining substitution
    for lookup in gsub.LookupList.Lookup:
        for st in lookup.SubTable:
            if lookup.LookupType != 6:
                continue
            for sub_lookup in st.SubstLookupRecord:
                if sub_lookup.LookupListIndex != lookup_index:
                    continue
                if st.LookAheadCoverage:
                    in_glyphs = [in_glyph, st.LookAheadCoverage[0].glyphs[0]]
                elif st.BacktrackCoverage:
                    in_glyphs = [st.BacktrackCoverage[0].glyphs[0], in_glyph]
                else:
                    continue
                return _sequence_from_glyph_names(font, in_glyphs)

    raise ValueError('Lookup list index %d not found.' % lookup_index)


def _sequence_from_glyph_names(font, in_glyphs):
    """Return a quoted sequence of glyphs from glyph names."""

    return [''.join(
        ''.join(hb_input_from_name(font, glyph_name, allow_arg=False))
        for glyph_name in in_glyphs)]
