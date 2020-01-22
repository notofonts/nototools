from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from math import *


def plot_elastica(a, c):
    s = 500
    cmd = 'moveto'
    dx = 0.001
    x, y = 0, 0
    if c * c > 2 * a * a:
        g = sqrt(c * c - 2 * a * a)
        x = g + 0.01
    if c == 0:
        x = 0.001
    try:
        for _ in range(1000):
            print(6 + s * x, 200 + s * y, cmd)
            cmd = 'lineto'
            x += dx
            if 1 and c * c > 2 * a * a:
                print((c * c - x * x) * (x * x - g * g))
                dy = (
                    dx
                    * (x * x - 0.5 * c * c - 0.5 * g * g)
                    / sqrt((c * c - x * x) * (x * x - g * g))
                )
            else:
                dy = (
                    dx
                    * (a * a - c * c + x * x)
                    / sqrt((c * c - x * x) * (2 * a * a - c * c + x * x))
                )
            y += dy
    except ValueError:
        pass
    print('stroke')


plot_elastica(1, 0)
print('showpage')
