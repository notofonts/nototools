from __future__ import absolute_import
from __future__ import print_function

import os
import sys

glyphmap = {}
for ln in open(sys.argv[1]).readlines():
    fnglyph = ln.strip().split(': ')
    if len(fnglyph) == 2:
        fn, name = fnglyph
        pgmf = fn[:-4] + '.pgm'
        if name not in glyphmap:
            glyphmap[name] = []
        glyphmap[name].append(pgmf)
for name in glyphmap.keys():
    cmd = '~/garden/font/blend ' + ' '.join(glyphmap[name]) + ' | pnmtopng > ' + name + '.png'
    print(cmd)
    os.system(cmd)
