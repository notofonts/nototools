#!/usr/bin/env python
#
# Copyright 2016 Google Inc. All rights reserved.
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

"""Dump cmap info from noto font familes in lint_cmap_reqs format."""

import argparse
import collections
import sys

from nototools import cmap_data
from nototools import lint_config
from nototools import noto_fonts


def report_set_differences(name_to_cpset, out=sys.stderr):
    """Report differences, assuming they are small."""

    # this does ok with 2 or 3 highly overlapping sets, but it will
    # be unintelligible in other cases.

    additional = ""
    while len(name_to_cpset):
        common = None
        if len(name_to_cpset) > 1:
            for name, cpset in name_to_cpset.items():
                if common is None:
                    common = cpset.copy()
                else:
                    common &= cpset
        if common:
            name = ", ".join(sorted(name_to_cpset))
            out.write("%d%s in common among %s:\n" % (len(common), additional, name))
            out.write("%s\n" % lint_config.write_int_ranges(common))

            for name, cpset in sorted(name_to_cpset.items()):
                extra = cpset - common
                if extra:
                    name_to_cpset[name] = extra
                else:
                    out.write("%s has no additional\n" % name)
                    del name_to_cpset[name]
            additional = " additional"
            continue

        for name, cpset in sorted(name_to_cpset.items()):
            out.write("%s has %d%s:\n" % (name, len(cpset), additional))
            out.write("%s\n" % lint_config.write_int_ranges(cpset))
        break


def font_cmap_data(paths):
    """Return CmapData for (almost) all the noto font families."""
    args = [("paths", paths)] if paths else None
    metadata = cmap_data.create_metadata("noto_font_cmaps", args)

    def use_in_web(font):
        return (
            not font.subset
            and not font.fmt == "ttc"
            and not font.script in {"CJK", "HST"}
            and not font.family in {"Arimo", "Cousine", "Tinos"}
        )

    if not paths:
        paths = noto_fonts.NOTO_FONT_PATHS
    fonts = filter(use_in_web, noto_fonts.get_noto_fonts(paths=paths))
    families = noto_fonts.get_families(fonts)

    ScriptData = collections.namedtuple("ScriptData", "family_name,script,cpset")
    script_to_data = collections.defaultdict(list)
    for family in families.values():
        script = family.rep_member.script
        family_name = family.name
        cpset = family.charset
        script_to_data[script].append(ScriptData(family_name, script, cpset))

    def report_data_error(index, script_data):
        sys.stderr.write(
            "  %d: %s, %d, %s\n"
            % (
                index,
                script_data.family_name,
                script_data.script,
                len(script_data.cpset),
                lint_config.write_int_ranges(script_data.cpset),
            )
        )

    script_to_cmap = {}
    for script in sorted(script_to_data):
        data = script_to_data[script]
        selected_cpset = data[0].cpset
        if len(data) > 1:
            differ = False
            for i in range(1, len(data)):
                test_data = data[i]
                for j in range(i):
                    if data[j].cpset != test_data.cpset:
                        differ = True
                if len(test_data.cpset) > len(selected_cpset):
                    selected_cpset = test_data.cpset
            if differ:
                sys.stderr.write("\nscript %s cmaps differ\n" % script)
                differences = {i.family_name: i.cpset for i in data}
                report_set_differences(differences)
        script_to_cmap[script] = selected_cpset

    tabledata = cmap_data.create_table_from_map(script_to_cmap)
    return cmap_data.CmapData(metadata, tabledata)


def main():
    DEFAULT_OUTFILE = "font_cmaps_temp.xml"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--outfile",
        help='output file to write ("%s" if no name provided)' % DEFAULT_OUTFILE,
        metavar="name",
        nargs="?",
        default=None,
        const=DEFAULT_OUTFILE,
    )
    parser.add_argument(
        "-p",
        "--paths",
        help="list of directory paths to search for noto fonts "
        "(default is standard noto phase2 paths)",
        metavar="path",
        nargs="*",
        default=None,
    )
    args = parser.parse_args()

    cmapdata = font_cmap_data(args.paths)
    if args.outfile:
        cmap_data.write_cmap_data_file(cmapdata, args.outfile, pretty=True)
    else:
        print(cmap_data.write_cmap_data(cmapdata, pretty=True).decode("utf-8"))


if __name__ == "__main__":
    main()
