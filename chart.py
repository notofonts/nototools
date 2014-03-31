#!/usr/bin/python

import sys
import cairo
import pycairoft
from fontTools import ttLib

def clamp(x, Min, Max):
	return max(Min, min(Max, x))

class Color:

	def __init__(self, r,g,b):
		self.rgb = (r,g,b)

	def __repr__(self):
		return 'Color(%g,%g,%g)' % self.rgb

	def __str__(self):
		return "#%02X%02X%02X" % tuple(int(255 * c) for c in self.rgb)

class Font:

	def __init__(self, fontfile):
		self.filename = fontfile
		self.ttfont = ttLib.TTFont(fontfile)
		cmap = self.ttfont['cmap']
		self.charset = set()
		self.charset.update(*[t.cmap.keys() for t in cmap.tables if t.isUnicode()])
		self.cairo_font_face = None

	def get_cairo_font_face(self):
		if self.cairo_font_face is None:
			self.cairo_font_face = pycairoft.create_cairo_font_face_for_file (
						self.filename)


	def __repr__(self):
		return 'Font("%s")' % self.filename

def assign_colors(fonts):
	n = len(fonts)
	mult = (n-1) // 2
	for i,font in enumerate(fonts):
		pos = (i * mult / float(n)) % 1. * 3
		r = clamp(1 - pos, 0, 1) + clamp(pos - 2, 0, 1)
		g = clamp(1 - abs(pos - 1), 0, 1)
		b = clamp(1 - abs(pos - 2), 0, 1)
		font.color = Color(r,g,b)

fonts = [Font(fontfile) for fontfile in sys.argv[1:]]
charset = set.union(*[f.charset for f in fonts])
assign_colors(fonts)

coverage = {c:[] for c in charset}
for font in fonts:
	for char in font.charset:
		coverage[char].append(font)

NUM_COLS = 128
FONT_SIZE = 5
PADDING = 0.3
CELL_SIZE = FONT_SIZE + 2 * PADDING
MARGIN = 1 * FONT_SIZE
LABEL_WIDTH = 8 * FONT_SIZE/2.

rows = set([u // NUM_COLS * NUM_COLS for u in charset])
num_rows = len(rows)

width  = NUM_COLS * CELL_SIZE + 2 * (2 * MARGIN + LABEL_WIDTH)
height = num_rows * CELL_SIZE + 2 * MARGIN

print "Generating chart.pdf at %.3gx%.3gin" % (width/72., height/72.)
surface = cairo.PDFSurface("chart.pdf", width, height)
cr = cairo.Context(surface)
noto_sans_lgc = pycairoft.create_cairo_font_face_for_file ("unhinted/NotoSans-Regular.ttf")
cr.set_font_face(noto_sans_lgc)

cr.set_font_size(FONT_SIZE)
cr.translate(MARGIN, MARGIN)
cr.save()
for row,row_start in enumerate(sorted(rows)):
	cr.translate(0, PADDING)
	cr.save()

	cr.set_source_rgb(0,0,0)
	cr.move_to(0,FONT_SIZE)
	cr.show_text ("U+%04X" % row_start)
	cr.translate(LABEL_WIDTH + MARGIN, 0)
	for char in range(row_start, row_start + NUM_COLS):
		cr.translate(PADDING, 0)
		for font in coverage.get(char, []):
			cr.rectangle(0, 0, FONT_SIZE, FONT_SIZE)
			cr.set_source_rgb(*font.color.rgb)
			cr.fill()
			break
		cr.translate(FONT_SIZE, 0)
		cr.translate(PADDING, 0)
	cr.set_source_rgb(0,0,0)
	cr.move_to(MARGIN,FONT_SIZE)
	cr.show_text ("U+%04X" % (row_start + NUM_COLS - 1))
	cr.translate(LABEL_WIDTH + 2 * MARGIN, 0)

	cr.restore()
	cr.translate(0, FONT_SIZE)
	cr.translate(0, PADDING)
cr.restore()
