# llamatron: a Python language and framework for producing MIDI clips.
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

from dataclasses import replace
from fractions import Fraction
from math import isfinite

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.song import _Validated


def _check_factor(factor):
    # bool is a subclass of int, but True is not a real factor.
    if type(factor) not in (int, float, Fraction) or not isfinite(factor) or factor <= 0:
        raise ValueError(f'invalid factor: {factor!r} (must be a positive number)')


def _stretched(position, factor):
    if isinstance(position, Chord):
        return Chord([_stretched(note, factor) for note in position.notes])
    return replace(position, length=exact_length(position.length) * factor)


class Stretch(ClipGenerator):
    """Makes everything in a clip longer or shorter by the same factor, keeping its shape.

    Stretch(Fraction(4, 3)) makes a measure of 6/8 last as long as a measure of 4/4, so
    two songs in different meters can line up. Stretch(2) plays at half speed.
    """

    factor = _Validated(_check_factor)

    def __init__(self, factor):
        self.factor = factor

    def _generate(self, clip):
        factor = exact_length(self.factor)
        notes = [_stretched(position, factor) for position in clip.resolved_notes()]
        length = None if clip.length is None else exact_length(clip.length) * factor
        return notes, length
