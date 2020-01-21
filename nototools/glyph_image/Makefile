# makefile for glyph-image

CFLAGS = -std=c99 -Wall -Wextra `pkg-config --cflags --libs freetype2`
LDFLAGS = -lm `pkg-config --libs freetype2`

glyph_image: glyph_image.c
	$(CC) $< -o $@ $(CFLAGS) $(LDFLAGS)
