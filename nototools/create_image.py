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

def create_png(text, output_path, family='Noto Sans',
               language=None, rtl=False, vertical=False,
               width=1370, font_size=32, line_spacing=50,
               weight=pango.WEIGHT_NORMAL, style=pango.STYLE_NORMAL):

    """Creates a PNG image from a given text and font."""

    def draw_on_surface(surface):
        """Draw the string on a pre-created surface and return height."""
        pangocairo_ctx = pangocairo.CairoContext(cairo.Context(surface))
        layout = pangocairo_ctx.create_layout()

        pango_ctx = layout.get_context()
        if language is not None:
            pango_ctx.set_language(pango.Language(language))

        if rtl:
            if vertical:
                base_dir = pango.DIRECTION_TTB_RTL
            else:
                base_dir = pango.DIRECTION_RTL
            alignment = pango.ALIGN_RIGHT
        else:
            if vertical:
                base_dir = pango.DIRECTION_TTB_LTR
            else:
                base_dir = pango.DIRECTION_LTR
            alignment = pango.ALIGN_LEFT

        pango_ctx.set_base_dir(base_dir)
        layout.set_alignment(alignment)

        layout.set_width(width * pango.SCALE)
        layout.set_spacing((line_spacing-font_size) * pango.SCALE)

        # TODO: use ctypes to wrap fontconfig to avoid using the system's fonts
        font = pango.FontDescription()
        font.set_family(family)
        font.set_size(font_size * pango.SCALE)
        font.set_style(style)
        font.set_weight(weight)
        layout.set_font_description(font)

        layout.set_text(text)

#        # Doesn't work for some reason
#        pango_ctx.set_base_gravity(pango.GRAVITY_AUTO)
#        matrix = pango_ctx.get_matrix()
#        matrix.rotate(90)
#        pango_ctx.set_matrix(matrix)
#        layout.context_changed()

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

    temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
    calculated_height = draw_on_surface(temp_surface)

    real_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
        width, calculated_height)
    draw_on_surface(real_surface)

    real_surface.write_to_png(output_path)


def main():
    """Test sample Hindi and Arabic texts."""

    import codecs

    file_path = '../sample_texts/hi-Deva.txt'
    with codecs.open(file_path, 'r', encoding='UTF-8') as input_file:
        sample_text = input_file.read()
    create_png(sample_text.strip(), 'hindi.png',
        family='Noto Sans Devanagari', language='hi', rtl=False)

    file_path = '../sample_texts/ar-Arab.txt'
    with codecs.open(file_path, 'r', encoding='UTF-8') as input_file:
        sample_text = input_file.read()
    create_png(sample_text.strip(), 'arabic.png',
        family='Noto Naskh Arabic', language='ar', rtl=True)

    file_path = '../sample_texts/mn-Mong.txt'
    with codecs.open(file_path, 'r', encoding='UTF-8') as input_file:
        sample_text = input_file.read()
    create_png(sample_text.strip(), 'mong.png',
        family='Noto Sans Mongolian', language='mn', vertical=True, rtl=False)


if __name__ == '__main__':
    main()
