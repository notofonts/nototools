# Synthesize a procedure to numerically integrate the 3rd order poly spiral

from __future__ import division
from __future__ import print_function

tex = False

if tex:
    mulsym = ' '
else:
    mulsym = ' * '


class Poly:
    def __init__(self, p0, coeffs):
        self.p0 = p0
        self.coeffs = coeffs

    def eval(self, x):  # TODO: method was broken. Investigate remove possibility.
        y = x ** self.p0
        z = 0
        for c in self.coeffs:
            z += y * c
            y *= x
        return z


def add(poly0, poly1, nmax):
    lp0 = len(poly0.coeffs)
    lp1 = len(poly1.coeffs)
    p0 = min(poly0.p0, poly1.p0)
    n = min(max(poly0.p0 + lp0, poly1.p1 + lp1), nmax) - p0
    if n <= 0:
        return Poly(0, [])
    coeffs = []
    for i in range(n):
        c = 0
        if poly0.p0 - p0 <= i < lp0 + poly0.p0 - p0:
            c += poly0.coeffs[i + p0 - poly0.p0]
        if poly1.p0 - p0 <= i < lp1 + poly1.p0 - p0:
            c += poly1.coeffs[i + p0 - poly1.p0]
        coeffs.append(c)
    return Poly(p0, coeffs)


def pr(string):
    if tex:
        print(string, '\\\\')
    else:
        print('\t' + string + ';')


def prd(string):
    if tex:
        print(string, '\\\\')
    else:
        print('\tdouble ' + string + ';')


def polymul(p0, p1, degree, basename, suppress_odd=False):
    result = []
    for i in range(min(degree, len(p0) + len(p1) - 1)):
        terms = []
        for j in range(i + 1):
            if j < len(p0) and i - j < len(p1):
                t0 = p0[j]
                t1 = p1[i - j]
                if t0 is not None and t1 is not None:
                    terms.append(t0 + mulsym + t1)
        if not terms:
            result.append(None)
        else:
            var = basename % i  # type: str
            if (j % 2 == 0) or not suppress_odd:
                prd(var + ' = ' + ' + '.join(terms))
            result.append(var)
    return result


def polysquare(p0, degree, basename):
    result = []
    for i in range(min(degree, 2 * len(p0) - 1)):
        terms = []
        for j in range((i + 1) // 2):
            if i - j < len(p0):
                t0 = p0[j]
                t1 = p0[i - j]
                if t0 is not None and t1 is not None:
                    terms.append(t0 + mulsym + t1)
        if len(terms) >= 1:
            if tex and len(terms) == 1:
                terms = ['2 ' + terms[0]]
            else:
                terms = ['2' + mulsym + '(' + ' + '.join(terms) + ')']
        if (i % 2) == 0:
            t = p0[i / 2]
            if t is not None:
                if tex:
                    terms.append(t + '^2')
                else:
                    terms.append(t + mulsym + t)
        if not terms:
            result.append(None)
        else:
            var = basename % i  # type: str
            prd(var + ' = ' + ' + '.join(terms))
            result.append(var)
    return result


def mkspiro(degree):
    if tex:
        us = ['u = 1']
        vs = ['v =']
    else:
        us = ['u = 1']
        vs = ['v = 0']
    if tex:
        tp = [None, 't_{11}', 't_{12}', 't_{13}', 't_{14}']
    else:
        tp = [None, 't1_1', 't1_2', 't1_3', 't1_4']
    if tex:
        prd(tp[1] + ' = k_0')
        prd(tp[2] + ' = \\frac{k_1}{2}')
        prd(tp[3] + ' = \\frac{k_2}{6}')
        prd(tp[4] + ' = \\frac{k_3}{24}')
    else:
        prd(tp[1] + ' = km0')
        prd(tp[2] + ' = .5 * km1')
        prd(tp[3] + ' = (1./6) * km2')
        prd(tp[4] + ' = (1./24) * km3')
    tlast = tp
    coef = 1.
    for i in range(1, degree - 1):
        tmp = []
        tcoef = coef
        # print(tlast)
        for j in range(len(tlast)):
            c = tcoef / (j + 1)
            if (j % 2) == 0 and tlast[j] is not None:
                if tex:
                    tmp.append('\\frac{%s}{%.0f}' % (tlast[j], 1. / c))
                else:
                    if c < 1e-9:
                        cstr = '%.16e' % c
                    else:
                        cstr = '(1./%d)' % int(.5 + (1. / c))
                    tmp.append(cstr + ' * ' + tlast[j])
            tcoef *= .5
        if tmp:
            sign = ('+', '-')[(i // 2) % 2]
            var = ('u', 'v')[i % 2]
            if tex:
                if i == 1:
                    pref = ''
                else:
                    pref = sign + ' '
                string = pref + (' ' + sign + ' ').join(tmp)
            else:
                string = var + ' ' + sign + '= ' + ' + '.join(tmp)
            if var == 'u':
                us.append(string)
            else:
                vs.append(string)
        if i < degree - 1:
            if tex:
                basename = 't_{%d%%d}' % (i + 1)
            else:
                basename = 't%d_%%d' % (i + 1)
            if i == 1:
                tnext = polysquare(tp, degree - 1, basename)
                t2 = tnext
            elif i == 3:
                tnext = polysquare(t2l, degree - 1, basename)
            elif (i % 2) == 0:
                tnext = polymul(tlast, tp, degree - 1, basename, True)
            else:
                tnext = polymul(t2l, t2, degree - 1, basename)
            t2l = tlast
            tlast = tnext
        coef /= (i + 1)
    if tex:
        pr(' '.join(us))
        pr(' '.join(vs))
    else:
        for u in us:
            pr(u)
        for v in vs:
            pr(v)


if __name__ == '__main__':
    mkspiro(12)
