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
"""Fields: whole-number arrays the visualizer's modes simulate, and the soft shapes they draw into them, shared by every mode.

The ripple is the classic demo-scene water: two height fields, each step making every cell half
the sum of its four neighbours less its value the step before, then damping it, so that waves
spread, cross and bounce off the edges. A soft disc is a kernel of weights from 0 to 256, made once
for each radius, added into a field at a place, clipped at the field's edges. A blur spreads a
field into its neighbours, as colour bleeds in water.
"""

import numpy

# A soft disc's weights run from nothing at its rim to this at its middle, so that a sum stays whole numbers.
FULL_WEIGHT = 256
WEIGHT_SHIFT = 8


def ripple_step(*, current, previous, damping_shift):
    """Return the next height field from the current one and the one before, damped by a shift: each cell loses itself shifted right by damping_shift."""
    padded = numpy.pad(current, 1)
    neighbours = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    following = (neighbours >> 1) - previous
    following -= following >> damping_shift
    return following


class Discs:
    """Soft discs by radius, each a square kernel of weights, made the first time a radius is asked for."""

    __slots__ = ('_kernels',)

    def __init__(self):
        self._kernels = {}

    def kernel(self, radius):
        """Return the weights of a soft disc of a radius in cells, falling from FULL_WEIGHT at its middle to nothing at its rim."""
        if radius not in self._kernels:
            span = numpy.arange(-radius, radius + 1)
            distance = numpy.hypot(span[:, None], span[None, :])
            falling = numpy.clip(1.0 - distance / (radius + 1), 0.0, 1.0)
            self._kernels[radius] = (falling * falling * FULL_WEIGHT).astype(numpy.int32)
        return self._kernels[radius]

    def add(self, *, field, row, column, radius, amount):
        """Add a soft disc into a field at a place, its middle adding amount, which may be an array of one value per channel, clipped at the field's edges."""
        kernel = self.kernel(radius)
        rows, columns = field.shape[:2]
        top = row - radius
        left = column - radius
        first_row = max(top, 0)
        first_column = max(left, 0)
        last_row = min(top + kernel.shape[0], rows)
        last_column = min(left + kernel.shape[1], columns)
        if first_row >= last_row or first_column >= last_column:
            return
        piece = kernel[first_row - top:last_row - top, first_column - left:last_column - left]
        if field.ndim == 3:
            field[first_row:last_row, first_column:last_column] += (piece[:, :, None] * numpy.asarray(amount)[None, None, :]) >> WEIGHT_SHIFT
        else:
            field[first_row:last_row, first_column:last_column] += (piece * amount) >> WEIGHT_SHIFT


def blurred(field):
    """Return a field spread a little into its four neighbours: half of each cell kept and half shared from around it, the edges repeating."""
    padded = numpy.pad(field, ((1, 1), (1, 1), (0, 0)) if field.ndim == 3 else 1, mode='edge')
    around = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    return (field * 4 + around) >> 3
