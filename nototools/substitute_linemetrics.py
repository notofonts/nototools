# Copyright 2017 Google Inc. All Rights Reserved.
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

"""Substitutes the line metrics in a font by using the one in another font.
"""
from argparse import ArgumentParser

from fontTools.ttLib import TTFont


def main(arg=None):
    parser = ArgumentParser()
    parser.add_argument('source', help='Path to font whose line metrics will be replaced.')
    parser.add_argument('linemetrics', help='Path to font whose line metrics will be used.')
    parser.add_argument(
        '-o',
        '--output',
        dest='output',
        default='output.ttf',
        help='Path to output font file. The line metrics of output are\
        extracted from <linemetrics> and all other data are copied from <source>',
    )
    args = parser.parse_args(arg)
    font = TTFont(args.linemetrics)
    metrics = read_line_metrics(font)
    font.close()

    font = TTFont(args.source)
    set_line_metrics(font, metrics)
    font.save(args.output)
    font.close()


def read_line_metrics(font):
    metrics = {
        'ascent': font['hhea'].ascent,
        'descent': font['hhea'].descent,
        'usWinAscent': font['OS/2'].usWinAscent,
        'usWinDescent': font['OS/2'].usWinDescent,
        'sTypoAscender': font['OS/2'].sTypoAscender,
        'sTypoDescender': font['OS/2'].sTypoDescender,
        'sxHeight': font['OS/2'].sxHeight,
        'sCapHeight': font['OS/2'].sCapHeight,
        'sTypoLineGap': font['OS/2'].sTypoLineGap,
    }
    return metrics


def set_line_metrics(font, metrics):
    font['hhea'].ascent = metrics['ascent']
    font['hhea'].descent = metrics['descent']
    font['OS/2'].usWinAscent = metrics['usWinAscent']
    font['OS/2'].usWinDescent = metrics['usWinDescent']
    font['OS/2'].sTypoAscender = metrics['sTypoAscender']
    font['OS/2'].sTypoDescender = metrics['sTypoDescender']
    font['OS/2'].sxHeight = metrics['sxHeight']
    font['OS/2'].sCapHeight = metrics['sCapHeight']
    font['OS/2'].sTypoLineGap = metrics['sTypoLineGap']


if __name__ == '__main__':
    main()
