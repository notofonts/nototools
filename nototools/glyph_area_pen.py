# Copyright 2015 Google Inc. All Rights Reserved.
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


from fontTools.pens.basePen import BasePen


class GlyphAreaPen(BasePen):
    """Pen used for calculating the area of the contours in a glyph."""

    def __init__(self, glyph_set):
        super(GlyphAreaPen, self).__init__(glyph_set)
        self.area = 0

    def unload(self):
        """Return and then reset the calculated area."""

        area = self.area
        self.area = 0
        return area

    def _moveTo(self, pt):
        """Remember the first point in this contour, in case it's closed. Also
        set the initial value for p0 in this contour, which will always refer to
        the most recent point.
        """

        self.first = pt
        self.p0 = pt

    def _lineTo(self, pt):
        """Add the signed area beneath the line from the latest point to this
        one. Signed areas cancel each other based on the horizontal direction of
        the line.
        """

        (x0, y0), (x1, y1) = self.p0, pt
        self.area += (x1 - x0) * (y1 + y0) / 2.0
        self.p0 = pt

    def _qCurveToOne(self, p1, p2):
        """Add the signed area of this quadratic curve.
        https://github.com/Pomax/bezierinfo/issues/44
        """

        x0, y0 = self.p0
        x1, y1 = p1[0] - x0, p1[1] - y0
        x2, y2 = p2[0] - x0, p2[1] - y0
        self.area += (x2 * y1 - x1 * y2) / 3.0
        self.lineTo(p2)

    def _curveToOne(self, p1, p2, p3):
        """Add the signed area of this cubic curve.
        https://github.com/Pomax/bezierinfo/issues/44
        """

        x0, y0 = self.p0
        x1, y1 = p1[0] - x0, p1[1] - y0
        x2, y2 = p2[0] - x0, p2[1] - y0
        x3, y3 = p3[0] - x0, p3[1] - y0
        self.area += (
            x1 * (   -     y2 -     y3) +
            x2 * (y1          - 2 * y3) +
            x3 * (y1 + 2 * y2         )
        ) * 3.0 / 20
        self.lineTo(p3)

    def _closePath(self):
        """Add the area beneath this contour's closing line."""
        self.lineTo(self.first)
