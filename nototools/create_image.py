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

import cairo
import pango
import pangocairo
import os.path

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

    @staticmethod
    def get(**kw):
        """Get a DrawParams from an arbitray set of keywords.
           If 'params' is a keyword, its value is a DrawParams and any other
           keywords update it with new/different values."""

        if 'params' in kw:
            p = kw['params']
            for k in kw.keys():
                if k != 'params':
                    setattr(p, k, kw[k])
        else:
            p = DrawParams()
            p.__dict__.update(kw)
        return p

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

    # TODO: use ctypes to wrap fontconfig to avoid using the system's fonts
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

    params = DrawParams.get(**kwargs);
    temp_surface = cairo.SVGSurface(None, 0, 0)
    calculated_height = draw_on_surface(temp_surface, text, params)

    real_surface = cairo.SVGSurface(output_path, params.width, calculated_height)
    draw_on_surface(real_surface, text, params)
    real_surface.flush()
    real_surface.finish()

def create_png(text, output_path, **kwargs):
    """Creates a PNG image from the given text."""

    params = DrawParams.get(**kwargs)
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
        print 'extension', ext, 'not supported'


def main():
    """Test sample Hindi and Arabic texts."""

    import codecs

    def test(text_file, output_file, **kwargs):
        file_path = '../sample_texts/' + text_file
        with codecs.open(file_path, 'r', encoding='UTF-8') as input_file:
            sample_text = input_file.read()
        create_img(sample_text.strip(), output_file,
            family='Noto Sans Devanagari', language='hi')

    test('hi-Deva.txt', 'hindi.png', family='Noto Sans Devanagari',
         language='hi')
    test('ar-Arab.txt', 'arabic.svg', family='Noto Naskh Arabic',
         language='ar', rtl=True)
    test('mn-Mong.txt', 'mong.png', family='Noto Sans Mongolian',
         language='mn', vertical=True)

if __name__ == '__main__':
    main()
