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

GposDiffFinder takes in two paths, to plaintext files containing the output of
ttxn. It provides `find_gsub_diffs` which compares the OpenType substitution
rules in these files, reporting the differences via a returned string.
"""


import re


class GsubDiffFinder(object):
    """Provides methods to report diffs in GSUB content between ttxn outputs."""

    def __init__(self, file_a, file_b, output_lines=20):
        with open(file_a) as ifile:
            self.text_a = ifile.read()
        with open(file_b) as ifile:
            self.text_b = ifile.read()
        self.file_a = file_a
        self.file_b = file_b
        self.output_lines = output_lines

    def find_gsub_diffs(self):
        """Report differences in substitution rules."""

        rules_a = self._get_gsub_rules(self.text_a, self.file_a)
        rules_b = self._get_gsub_rules(self.text_b, self.file_b)

        diffs = []
        report = ['']  # first line replaced by difference count
        for rule in rules_a:
            if rule not in rules_b:
                diffs.append(('-',) + rule)
        for rule in rules_b:
            if rule not in rules_a:
                diffs.append(('+',) + rule)
        diffs.sort(self._compare_no_sign)
        report = ['%d differences in GSUB rules' % len(diffs)]
        report.extend(' '.join(diff) for diff in diffs)
        return '\n'.join(report[:self.output_lines + 1])

    def _get_gsub_rules(self, text, filename):
        """Get substitution rules in this ttxn output."""

        feature_name_rx = r'feature (\w+) {'
        contents_rx = r'feature %s {(.*?)} %s;'
        rule_rx = r'sub ([\w.]+) by ([\w.]+);'

        rules = set()
        for name in re.findall(feature_name_rx, text):
            contents = re.findall(contents_rx % (name, name), text, re.S)
            assert len(contents) == 1, 'Multiple %s features in %s' % (
                name, filename)
            contents = contents[0]
            for lhs, rhs in re.findall(rule_rx, contents):
                rules.add((name, lhs, rhs))
        return rules

    def _compare_no_sign(self, left, right):
        """Compare items of form (sign, data...) ignoring the sign."""

        return cmp(left[1:], right[1:])
