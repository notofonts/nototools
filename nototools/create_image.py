#!/usr/bin/python
# -*- coding: utf-8-unix -*-
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

"""Create sample images given a font and text."""

__author__ = 'roozbeh@google.com (Roozbeh Pournader)'

import argparse
import os
import os.path
fonts_conf = os.path.abspath(os.path.join (os.path.dirname(__file__), "fonts.conf"))
os.putenv("FONTCONFIG_FILE", fonts_conf)

import cairo
import pango
import pangocairo

class DrawParams:
    """Parameters used for rendering text in draw_on_surface and its callers"""

    def __init__(self, family='Noto Sans',
                 language=None, rtl=False, vertical=False,
                 width=1370, font_size=32, line_spacing=50,
                 weight=pango.WEIGHT_NORMAL, style=pango.STYLE_NORMAL):
        self.family = family
        self.language = language
        self.rtl = rtl
        self.vertical = vertical
        self.width = width
        self.font_size = font_size
        self.line_spacing = line_spacing
        self.weight = weight
        self.style = style

def draw_on_surface(surface, text, params):
    """Draw the string on a pre-created surface and return height."""
    pangocairo_ctx = pangocairo.CairoContext(cairo.Context(surface))
    layout = pangocairo_ctx.create_layout()

    pango_ctx = layout.get_context()
    if params.language is not None:
        pango_ctx.set_language(pango.Language(params.language))

    if params.rtl:
        if params.vertical:
            base_dir = pango.DIRECTION_TTB_RTL
        else:
            base_dir = pango.DIRECTION_RTL
        alignment = pango.ALIGN_RIGHT
    else:
        if params.vertical:
            base_dir = pango.DIRECTION_TTB_LTR
        else:
            base_dir = pango.DIRECTION_LTR
        alignment = pango.ALIGN_LEFT

    pango_ctx.set_base_dir(base_dir)
    layout.set_alignment(alignment)

    layout.set_width(params.width * pango.SCALE)
    layout.set_spacing((params.line_spacing - params.font_size) * pango.SCALE)

    font = pango.FontDescription()
    font.set_family(params.family)
    font.set_size(params.font_size * pango.SCALE)
    font.set_style(params.style)
    font.set_weight(params.weight)
    layout.set_font_description(font)

    layout.set_text(text)

#    # Doesn't work for some reason
#    pango_ctx.set_base_gravity(pango.GRAVITY_AUTO)
#    matrix = pango_ctx.get_matrix()
#    matrix.rotate(90)
#    pango_ctx.set_matrix(matrix)
#    layout.context_changed()

    extents = layout.get_pixel_extents()
    top_usage = min(extents[0][1], extents[1][1], 0)
    bottom_usage = max(extents[0][3], extents[1][3])

    pangocairo_ctx.set_antialias(cairo.ANTIALIAS_GRAY)
    pangocairo_ctx.set_source_rgb(1, 1, 1)  # White background
    pangocairo_ctx.paint()

    pangocairo_ctx.translate(0, -top_usage)
    pangocairo_ctx.set_source_rgb(0, 0, 0)  # Black text color
    pangocairo_ctx.show_layout(layout)

    return bottom_usage - top_usage


def create_svg(text, output_path, **kwargs):
    """Creates an SVG image from the given text."""

    params = DrawParams(**kwargs);
    temp_surface = cairo.SVGSurface(None, 0, 0)
    calculated_height = draw_on_surface(temp_surface, text, params)

    real_surface = cairo.SVGSurface(output_path, params.width, calculated_height)
    draw_on_surface(real_surface, text, params)
    real_surface.flush()
    real_surface.finish()


def create_png(text, output_path, **kwargs):
    """Creates a PNG image from the given text."""

    params = DrawParams(**kwargs)
    temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
    calculated_height = draw_on_surface(temp_surface, text, params)

    real_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
        params.width, calculated_height)
    draw_on_surface(real_surface, text, params)
    real_surface.write_to_png(output_path)


def create_img(text, output_path, **kwargs):
    """Creates a PNG or SVG image based on the output_path extension,
       from the given text"""
    ext = (os.path.splitext(output_path)[1]).lower()
    if ext == '.png':
        create_png(text, output_path, **kwargs)
    elif ext == '.svg':
        create_svg(text, output_path, **kwargs)
    else:
        print 'extension % not supported' % ext


def test():
    """Test sample Hindi and Arabic texts."""

    import codecs

    def test(text_file, output_file, **kwargs):
        file_path = '../sample_texts/' + text_file
        with codecs.open(file_path, 'r', encoding='UTF-8') as input_file:
            sample_text = input_file.read().strip()
        create_img(sample_text, output_file, **kwargs)

    test('hi-Deva.txt', 'hindi.png', family='Noto Sans Devanagari',
         language='hi')
    test('ar-Arab.txt', 'arabic.svg', family='Noto Naskh Arabic',
         language='ar', rtl=True)
    test('mn-Mong.txt', 'mong.png', family='Noto Sans Mongolian',
         language='mn', vertical=True)


_weight_map = {
    'ultralight': pango.WEIGHT_ULTRALIGHT,
    'light': pango.WEIGHT_LIGHT,
    'normal': pango.WEIGHT_NORMAL,
    'bold': pango.WEIGHT_BOLD,
    'ultrabold': pango.WEIGHT_ULTRABOLD,
    'heavy': pango.WEIGHT_HEAVY
  }


def _get_weight(weight_name):
  if not weight_name:
    return pango.WEIGHT_NORMAL
  weight = _weight_map.get(weight_name)
  if weight:
    return weight
  raise ValueError('could not recognize weight \'%s\'\naccepted values are %s' %
                  ( weight_name, ', '.join(sorted(_weight_map.keys()))))


_italic_map = {
    'italic': pango.STYLE_ITALIC,
    'oblique': pango.STYLE_OBLIQUE,
    'normal': pango.STYLE_NORMAL
  }

def _get_style(style_name):
  if not style_name:
    return pango.STYLE_NORMAL
  style = _italic_map.get(style_name)
  if style:
    return style
  raise ValueError('could not recognize style \'%s\'\naccepted values are %s' %
                   (style_name, ', '.join(sorted(_italic_map.keys()))))


def render_codes(code_list, font_name, weight_name, style_name, font_size, lang, ext):
    text = u''.join([unichr(int(s, 16)) for s in code_list])
    render_text(text, font_name, weight_name, style_name, font_size, lang, ext)


def render_text(text, font_name, weight_name, style_name, font_size, lang, ext):
    font = font_name or 'Noto Sans'
    font_size = font_size or 32
    name_strs = ['%x' % ord(cp) for cp in text]
    name_strs.append(font.replace(' ', ''))
    if weight_name:
      name_strs.append(weight_name)
    if style_name:
      name_strs.append(style_name)
    name_strs.append(str(font_size))
    if lang:
      name_strs.append(lang)
    outfile_name = 'sample_' + '_'.join(name_strs) + '.' + ext
    weight = _get_weight(weight_name)
    style = _get_style(style_name)
    create_img(text, outfile_name, family=font, weight=weight, style=style,
               language=lang, font_size=font_size)
    print 'generated ' + outfile_name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='generate test images')
    parser.add_argument('--codes', metavar='hex', nargs='+',
                        help='list of hex codepoints to render')
    parser.add_argument('--text', metavar='str', help='text to render, can include unicode escapes')
    parser.add_argument('-f', '--font', metavar='name', help='name of noto font to use')
    parser.add_argument('-b', '--bold', metavar='wt', help="pango weight name", default=None)
    parser.add_argument('-i', '--italic', metavar='it', help="pango style name", default=None)
    parser.add_argument('-s', '--size', metavar='int', type=int, help='point size (default 32)',
                        default=32)
    parser.add_argument('-l', '--lang', metavar='lang', help='language code')
    parser.add_argument('-t', '--type', metavar='ext', help='svg (default) or png', default='svg')

    args = parser.parse_args()
    if args.test:
      test()
      return
    if args.codes and args.text:
      print 'choose either codes or text'
      return
    if args.codes:
      render_codes(args.codes, args.font, args.bold, args.italic,
                   args.size, args.lang, args.type)
    elif args.text:
      render_text(args.text.decode('unicode-escape'), args.font, args.bold, args.italic,
                  args.size, args.lang, args.type)
    else:
      print 'nothing to do'


if __name__ == '__main__':
    main()
