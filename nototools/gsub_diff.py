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


"""Provides GsubDiffFinder, which finds differences in GSUB tables.

GsubDiffFinder takes in two paths, to font binaries from which ttxn output is
made. It provides `find_gsub_diffs` which compares the OpenType substitution
rules in these files, reporting the differences via a returned string.
"""


import re
import subprocess
import tempfile


class GsubDiffFinder(object):
    """Provides methods to report diffs in GSUB content between ttxn outputs."""

    def __init__(self, file_a, file_b, output_lines=20):
        ttxn_file_a = tempfile.NamedTemporaryFile()
        ttxn_file_b = tempfile.NamedTemporaryFile()
        subprocess.call(['ttxn', '-q', '-t', 'GSUB', '-o', ttxn_file_a.name,
                                                     '-f', file_a])
        subprocess.call(['ttxn', '-q', '-t', 'GSUB', '-o', ttxn_file_b.name,
                                                     '-f', file_b])
        self.text_a = ttxn_file_a.read()
        self.text_b = ttxn_file_b.read()
        self.file_a = file_a
        self.file_b = file_b
        self.output_lines = output_lines

    def find_gsub_diffs(self):
        """Report differences in substitution rules."""
        new = [self._format_rule(r, '+') for r in self.find_new_rules()]
        missing = [self._format_rule(r, '-') for r in self.find_missing_rules()]
        diffs = missing + new
        # ('+', 'smcp', 'Q', 'by', Q.sc')
        # Sort order:
        # 1. Feature tag
        # 2. Glyph name before substitution
        # 3. Glyph name after substitution
        diffs.sort(key=lambda t:(t[1], t[2], t[4]))
        report = ['%d differences in GSUB rules' % len(diffs)]
        report.extend(' '.join(diff) for diff in diffs)
        return '\n'.join(report[:self.output_lines + 1])

    def find_new_rules(self):
        rules_a = self._get_gsub_rules(self.text_a, self.file_a)
        rules_b = self._get_gsub_rules(self.text_b, self.file_b)
        return [r for r in rules_b if r not in rules_a]

    def find_missing_rules(self):
        rules_a = self._get_gsub_rules(self.text_a, self.file_a)
        rules_b = self._get_gsub_rules(self.text_b, self.file_b)
        return [r for r in rules_a if r not in rules_b]

    def _get_gsub_rules(self, text, file):
        """
        Parse the ttxn GSUB table in the following manner:

        1. Get features
        2. Get feature content
        3. Extract lookup rules from feature content

        Following substitutions are currently implemented:
        - Type 1: Single substitutions
        - Type 2: Multiple substitutions
        - Type 3: Alternate substitutions
        - Type 4: Ligature substitutionss

        TODO: LookupTypes 5, 6, 8 still need implementing
        """
        rules = []
        features = self._get_gsub_features(text)
        for feature in features:
            content = self._get_feature_content(text, feature)
            lookups_rules = self._get_lookups_rules(text, content[0], feature)
            rules += lookups_rules
        return rules

    def _get_gsub_features(self, text):
        features = set()
        feature_name_rx = r'feature (\w+) {'

        for name in re.findall(feature_name_rx, text):
            features.add(name)
        return list(features)

    def _get_feature_content(self, text, feature):
        contents_rx = r'feature %s {(.*?)} %s;'
        contents = re.findall(contents_rx % (feature, feature), text, re.S)
        return contents

    def _get_lookups_rules(self, text, content, feature):
        """Ignore rules which use "'". These are contextual and not in
        lookups 1-4"""
        rule_rx = r"[^C] sub (.*[^\']) (by|from) (.*);"
        rules = re.findall(rule_rx, content)
        parsed_rules = self._parse_gsub_rules(rules, feature)
        return parsed_rules

    def _parse_gsub_rules(self, rules, feature):
        """
        Parse GSUB sub LookupTypes 1, 2, 3, 4, 7. Return list of tuples with
        the following tuple sequence.

        (feature, [input glyphs], operator, [output glyphs])

        Type 1 Single Sub:
        sub a by a.sc;
        sub b by b.sc;
        [
            (feat, ['a'], 'by' ['a.sc']),
            (feat, ['b'], 'by' ['b.cs'])
        ]


        Type 2 Multiple Sub:
        sub f_f by f f;
        sub f_f_i by f f i;
        [
            (feat, ['f_f'], 'by', ['f', 'f']),
            (feat, ['f_f_i'], 'by', ['f', 'f', 'i'])
        ]

        Type 3 Alternative Sub:
        sub ampersand from [ampersand.1 ampersand.2 ampersand.3];
            [
                (feat, ['ampersand'], 'from', ['ampersand.1']),
                (feat, ['ampersand'], 'from', ['ampersand.2']),
                (feat, ['ampersand'], 'from', ['ampersand.3'])
            ]

        Type 4 Ligature Sub:
        sub f f by f_f;
        sub f f i by f_f_i;
        [
            (feat, ['f', 'f'] 'by' ['f_f]),
            (feat, ['f', 'f', 'i'] 'by' ['f_f_i'])
        ]

        http://www.adobe.com/devnet/opentype/afdko/topic_feature_file_syntax.html#4.e
        """
        parsed = []
        for idx, (left, op, right) in enumerate(rules):

            left_group, right_group = [], []
            if left.startswith('[') and left.endswith(']'):
                left = self._gsub_rule_group_to_string(left)

            if right.startswith('[') and right.endswith(']'):
                right = self._gsub_rule_group_to_string(right)

            if op == 'by': # parse LookupType 1, 2, 4
                parsed.append((feature, left.split(), op, right.split()))
            elif op == 'from': # parse LookupType 3
                for glyph in right.split(): # 'a.alt a.sc' -> ['a.alt', 'a.sc']
                    parsed.append((feature, left.split(), op, [glyph]))
        return parsed

    def _format_rule(self, rule, sign):
        """Unnest the tuple rule sequence to more report friendly format"""
        s = [sign]
        for item in rule:
            if not isinstance(item, str):
                for sub_item in item:
                    s.append(sub_item)
            else:
                s.append(item)
        return s

    def _gsub_rule_group_to_string(self, seq):
        """[a a.sc a.sups] --> 'a a.sc a.sups'"""
        return seq[1:-1]
