from __future__ import absolute_import
from __future__ import print_function

import sys

athresh = 100
border = 20

segf = sys.argv[1]
if len(sys.argv) > 2:
    pref = sys.argv[2]
else:
    pref = '/tmp/cut'
rects = []
starts = {}
for l in open(segf).readlines():
    ls = l.split()
    if len(ls) == 6 and ls[-1] == 'rect':
        r = list(map(int, ls[:4]))
        area = (r[2] - r[0]) * (r[3] - r[1])
        if area > athresh:
            rpad = [r[0] - border, r[1] - border, r[2] + border, r[3] + border]
            if rpad[1] not in starts:
                starts[rpad[1]] = []
            starts[rpad[1]].append(len(rects))
            rects.append(rpad)

l = sys.stdin.readline()
if l != 'P5\n':
    raise Exception('expected pgm file')
while 1:
    l = sys.stdin.readline()
    if l[0] != '#':
        break
x, y = map(int, l.split())
l = sys.stdin.readline()

active = {}
for j in range(y):
    if j in starts:
        for ix in starts[j]:
            r = rects[ix]
            ofn = pref + '%04d.pgm' % ix
            of = open(ofn, 'w')
            active[ix] = of
            print('P5', file=of)
            print(r[2] - r[0], r[3] - r[1], file=of)
            print('255', file=of)
    buf = sys.stdin.read(x)
    for ix, of in active.items():
        r = rects[ix]
        of.write(buf[r[0]:r[2]])
        if j == r[3] - 1:
            of.close()
            del active[ix]
