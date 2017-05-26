// Collect glyph images from a font into a text file.  The format is:
// '#' starts a comment line
// '> <name>:' is a field of font data, either a number or string
// '> glyphs: NNN' starts a list of NNN (decimal) glyph records, in each:
// '>' is a glyph header, the space-separated values are:
//   glyph index, advance (26.6), left offset, top offset, width, height
// the advance has the int and frac separated by '+'
// unlike in fonts, up is negative
// this is followed by 'height' lines, and on each line there is a ':' followed
// by 'width' pairs of characters.  The pair is two spaces for a value of 0,
// otherwise two hex digits representing a value between 1-255.  This
// is a linear gray 'coverage' map where 0 represents not covered and
// 255 represents fully covered.
//
// This format is big but easy to inspect, and it would compress well if
// we cared.
//
// requires freetype2
// gcc --std=c99 -I /usr/local/include/freetype2 glyph_image.c -L /usr/local/lib -lfreetype -o glyph_image
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include <ft2build.h>
#include FT_FREETYPE_H

int render(
    const char* face_name, int size, int first_glyph_index,
    int last_glyph_index) {

  char buf[32];

  FT_Library library;
  int error = FT_Init_FreeType(&library);
  if (error) {
    fprintf(stderr, "failed to init freetype\n");
    return error;
  }
  FT_Face face;
  error = FT_New_Face(library, face_name, 0, &face);
  if (error) {
    fprintf(stderr, "failed to create face for '%s'\n", face_name);
    return error;
  }

  if (size < 4) {
    fprintf(stderr, "size %d too small", size);
    return 100;
  }

  error = FT_Set_Pixel_Sizes(face, 0, size);
  if (error) {
    fprintf(stderr, "failed to set size %d\n", size);
    return error;
  }

  if (first_glyph_index < 0) {
    first_glyph_index = 0;
  } else if (first_glyph_index >= face->num_glyphs) {
    first_glyph_index = face->num_glyphs - 1;
  }

  if (last_glyph_index == -1 || last_glyph_index >= face->num_glyphs) {
    last_glyph_index = face->num_glyphs - 1;
  } else if (last_glyph_index < first_glyph_index) {
    last_glyph_index = first_glyph_index;
  }

  time_t raw_time = time(NULL);
  strftime(buf, sizeof(buf)/sizeof(char), "%F %T", localtime(&raw_time));
  printf("# generated on %s\n", buf);
  printf("> file: %s\n", face_name);
  printf("> name: %s-%s\n", face->family_name, face->style_name);
  printf("> upem: %d\n", face->units_per_EM);
  printf("> ascent: %d\n", face->ascender);
  printf("> descent: %d\n", -face->descender);

  printf("> size: %d\n", size);
  printf("> font_glyphs: %ld\n", face->num_glyphs);

  printf("# first: %d\n", first_glyph_index);
  printf("# last: %d\n", last_glyph_index);
  printf("> num_glyphs: %d\n", last_glyph_index - first_glyph_index + 1);

  int load_flags = FT_LOAD_DEFAULT;
  int render_mode = FT_RENDER_MODE_NORMAL;
  for (int glyph_index = first_glyph_index; glyph_index <= last_glyph_index;
       glyph_index++) {

    error = FT_Load_Glyph(face, glyph_index, load_flags);
    if (error) {
      fprintf(stderr, "failed to load glyph %d\n", glyph_index);
      return error;
    }
    error = FT_Render_Glyph(face->glyph, render_mode);
    if (error) {
      fprintf(stderr, "failed to render glyph %d\n", glyph_index);
      return error;
    }
    FT_GlyphSlot slot = face->glyph;
    FT_Bitmap *bm = &slot->bitmap;
    int adv = (int)slot->advance.x;
    int adv_int = adv >> 6;
    int adv_frac = adv % 0x3f;
    if (adv_frac) {
      sprintf(buf, "%d,%d", adv_int, adv_frac);
    } else {
      sprintf(buf, "%d", adv_int);
    }
    printf(
        "> glyph: %d;%s;%d %d %d %d\n", glyph_index, buf,
        slot->bitmap_left, -slot->bitmap_top, bm->width, bm->rows);
    unsigned char *p = bm->buffer;
    for (unsigned int rc = 0; rc < bm->rows; ++rc, p += bm->pitch) {
      printf(":");
      int max_cc = bm->width - 1;
      while (max_cc >= 0 && *(p + max_cc) == 0) {
        --max_cc;
      }
      for (int cc = 0; cc < max_cc; ++cc) {
        int v = *(p + cc);
        if (v) {
          printf("%02x", v);
        } else {
          printf("  ");
        }
      }
      printf("\n");
    }
  }
  printf("# EOF\n");

  return 0;
}


int main(int argc, const char **argv) {
  if (argc < 2) {
    fprintf(
        stderr, "%s font-name [pixel-height [first-glyph [last-glyph]]]\n",
        argv[0]);
    return -1;
  }
  const char * font_path = argv[1];
  int pixel_height = 48;
  int first_glyph = 0;
  int last_glyph = -1;
  if (argc > 2) {
    pixel_height = atoi(argv[2]);
    if (pixel_height < 1 || pixel_height > 1000) {
      fprintf(stderr, "bad pixel height '%s'\n", argv[2]);
      return -1;
    }
  }
  if (argc > 3) {
    first_glyph = atoi(argv[3]);
  }
  if (argc > 4) {
    last_glyph = atoi(argv[4]);
  }

  return render(font_path, pixel_height, first_glyph, last_glyph);
}
