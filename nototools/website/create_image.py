#!/usr/bin/python
# -*- coding: UTF-8 -*-
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


def create_png(text, output_path, family='Noto Sans', language=None, rtl=False,
               width=1370, height=200, font_size=16, line_spacing=25):

    """Creates a PNG image from a given text and font."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cairo_ctx = cairo.Context(surface)

    cairo_ctx.set_source_rgb(1, 1, 1)  # White background
    cairo_ctx.paint()

    cairo_ctx.translate(0, 0)

    cairo_ctx.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

    pangocairo_ctx = pangocairo.CairoContext(cairo_ctx)
    layout = pangocairo_ctx.create_layout()

    pango_ctx = layout.get_context()
    if language is not None:
        pango_ctx.set_language(pango.Language(language))
    if rtl:
        pango_ctx.set_base_dir(pango.DIRECTION_RTL)
    else:
        pango_ctx.set_base_dir(pango.DIRECTION_LTR)    

    layout.set_width(width * pango.SCALE)
    layout.set_spacing((line_spacing-font_size) * pango.SCALE)

    font = pango.FontDescription()
    font.set_family(family)
    font.set_size(font_size * pango.SCALE)
    layout.set_font_description(font)

    layout.set_text(text)

    cairo_ctx.set_source_rgb(0, 0, 0)  # Black text color
    pangocairo_ctx.update_layout(layout)
    pangocairo_ctx.show_layout(layout)

    surface.write_to_png(output_path)


def main():
    """Test sample Hindi text."""
    
    import codecs
    
    file_path = '../../sample_texts/hi-Deva.txt'
    with codecs.open(file_path, 'r', encoding='UTF-8') as input_file:
        sample_text = input_file.read()
    create_png(sample_text, 'hindi.png',
        family='Noto Sans Devanagari', language='hi', rtl=False)


if __name__ == '__main__':
    main()
