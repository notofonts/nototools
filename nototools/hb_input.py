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



from fontTools.ttLib import TTFont

from nototools import summary


class HbInputGenerator(object):
    """Provides functions to generate harbuzz input.

    The input is returned as a list of strings, suitable for passing into
    subprocess.call or something similar.
    """

    def __init__(self, path, reverse_cmap=None):
        self.path = path
        self.font = TTFont(path)
        self.reverse_cmap = reverse_cmap or build_reverse_cmap(self.font)

    def all_inputs(self):
        """Generate harfbuzz inputs for all glyphs in a given font."""

        inputs = []
        glyph_names = self.font.getGlyphOrder()
        for name in glyph_names:
            inputs.append([self.path] + self.input_from_name(name))
        return inputs

    def input_from_name(self, name, allow_arg=True):
        """Given glyph name, return input to harbuzz to render this glyph, not
        including the font path itself.

        Sometimes this will simply be the glyph itself, other times a feature
        may need to be active, or a string of glyphs used (for ligatures or
        contextual substitutions).

        If `allow_arg` is false, no feature argument will be added (used if
        called recursively).
        """

        # see if this glyph has a simple unicode mapping
        if name in self.reverse_cmap:
            return [unichr(self.reverse_cmap[name])]

        # nope, check the substitution features
        gsub = self.font['GSUB'].table
        for lookup_index, lookup in enumerate(gsub.LookupList.Lookup):
            for st in lookup.SubTable:

                # see if this glyph can be a single-glyph substitution
                if lookup.LookupType == 1:
                    for glyph, subst in st.mapping.items():
                        if subst == name:
                            return self._input_with_context(
                                glyph, lookup_index, allow_arg)

                # see if this glyph is a ligature
                elif lookup.LookupType == 4:
                    for prefix, ligatures in st.ligatures.items():
                        for ligature in ligatures:
                            if ligature.LigGlyph == name:
                                glyphs = [prefix] + ligature.Component
                                return self._sequence_from_glyph_names(glyphs)


    def _input_with_context(self, glyph, lookup_index, allow_arg=True):
        """Given font, input glyph, and lookup index, return input to harfbuzz
        to render the input glyph with the referred-to lookup activated.
        """

        gsub = self.font['GSUB'].table

        # try to get a feature tag to activate this lookup
        if allow_arg:
            for feature in gsub.FeatureList.FeatureRecord:
                if lookup_index in feature.Feature.LookupListIndex:
                    fea_arg = ['--features=%s' % feature.FeatureTag]
                    return fea_arg + self.input_from_name(glyph)

        # try for a chaining substitution
        for lookup in gsub.LookupList.Lookup:
            for st in lookup.SubTable:
                if lookup.LookupType != 6:
                    continue
                for sub_lookup in st.SubstLookupRecord:
                    if sub_lookup.LookupListIndex != lookup_index:
                        continue
                    if st.LookAheadCoverage:
                        glyphs = [glyph, st.LookAheadCoverage[0].glyphs[0]]
                    elif st.BacktrackCoverage:
                        glyphs = [st.BacktrackCoverage[0].glyphs[0], glyph]
                    else:
                        continue
                    return self._sequence_from_glyph_names(glyphs)

        raise ValueError('Lookup list index %d not found.' % lookup_index)


    def _sequence_from_glyph_names(self, glyphs):
        """Return a sequence of glyphs from glyph names."""

        return [''.join(
            ''.join(self.input_from_name(glyph_name, allow_arg=False))
            for glyph_name in glyphs)]


def build_reverse_cmap(font):
    """Build a dictionary mapping glyph names to unicode values."""

    return {n: v for v, n in summary.get_largest_cmap(font).items()}
