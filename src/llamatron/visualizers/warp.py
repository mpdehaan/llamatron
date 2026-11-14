# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The rotozoom: a picture sampled through a turn and a zoom about its middle, shared by every mode that moves its view.

The places each output cell samples are worked out with numpy for the whole picture at once, from
a grid of the output's places made once for each size, and nearest-cell sampling keeps it a matter
of indexing; the averaging down to big pixels after it smooths the steps. A zoom above one keeps the
turned picture's corners inside the field, so no empty edge shows.
"""

import math

import numpy


class Rotozoom:
    """Samples pictures of one size through a turn and a zoom, keeping the grid of the output's places for that size."""

    __slots__ = ('_shape', '_rows', '_columns')

    def __init__(self):
        self._shape = None
        self._rows = None
        self._columns = None

    def sampled(self, *, picture, angle, zoom):
        """Return a picture turned by an angle in radians and zoomed by a factor about its middle, the same size, each cell the nearest one it lands on."""
        rows, columns = picture.shape[:2]
        if self._shape != (rows, columns):
            self._shape = (rows, columns)
            self._rows, self._columns = numpy.mgrid[0:rows, 0:columns].astype(numpy.float32)
            self._rows -= (rows - 1) / 2
            self._columns -= (columns - 1) / 2
        cosine = math.cos(angle) / zoom
        sine = math.sin(angle) / zoom
        source_rows = self._rows * cosine - self._columns * sine + (rows - 1) / 2
        source_columns = self._rows * sine + self._columns * cosine + (columns - 1) / 2
        row_places = numpy.clip(numpy.rint(source_rows), 0, rows - 1).astype(numpy.intp)
        column_places = numpy.clip(numpy.rint(source_columns), 0, columns - 1).astype(numpy.intp)
        return picture[row_places, column_places]
