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

from enum import Enum, auto
from fractions import Fraction
from math import isfinite

from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.note import Degree
from llamatron.song import Clip, _Validated


class BlendMode(Enum):
    """Where the target comes in from as Blend moves one clip towards another."""

    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


def _check_mode(mode):
    if not isinstance(mode, BlendMode):
        raise ValueError(f'expected a BlendMode, got {mode!r}')


def _check_target(target):
    if not isinstance(target, Clip):
        raise ValueError(f'expected a Clip, got {target!r}')


def _check_amount(amount):
    # bool is a subclass of int, but True is not a real amount.
    if type(amount) not in (int, float, Fraction) or not isfinite(amount) or not 0 <= amount <= 100:
        raise ValueError(f'invalid amount: {amount!r} (must be from 0 to 100)')


def _concrete(clip):
    """Return a copy of a clip with degrees turned into notes of its own scale.

    Slices from two songs can't share one scale, so degrees have to be settled here.
    """
    notes = []
    for position in clip.notes:
        if isinstance(position, Degree):
            if clip.scale is None:
                raise ValueError(f'{position!r} needs a scale, but the clip has none')
            position = position.to_note(clip.scale)
        notes.append(position)
    return Clip(notes=notes, length=clip.length, note_length=clip.note_length)


class Blend(ClipGenerator):
    """Moves a clip towards a target clip of the same total length.

    An amount of 0 plays this clip, and 100 plays the target. LEFT, RIGHT and MIDDLE bring in the
    target from one side, from the other, or from the center out, with the amount setting how
    much of the clip's length it covers. There's no randomness, and the edges move to the nearest
    note in this clip, so its notes aren't cut.
    """

    target = _Validated(_check_target)
    amount = _Validated(_check_amount)
    mode = _Validated(_check_mode)

    def __init__(self, target, amount, mode=BlendMode.LEFT):
        self.target = target
        self.amount = amount
        self.mode = mode

    def _generate(self, clip):
        total = clip.total_length()
        if self.target.total_length() != total:
            raise ValueError(
                f'the clips must be the same length, but they last {total} and {self.target.total_length()}'
            )
        return self._sweep(_concrete(clip), _concrete(self.target), total), clip.length

    def region(self, clip):
        """Return where the target plays in the result, from start to end in whole notes."""
        total = clip.total_length()
        source = _concrete(clip)
        share = total * Fraction(self.amount).limit_denominator(1_000_000) / 100
        if self.mode is BlendMode.LEFT:
            start, end = Fraction(0), share
        elif self.mode is BlendMode.RIGHT:
            start, end = total - share, total
        else:
            start, end = (total - share) / 2, (total + share) / 2
        start, end = self._nearest_edge(source, start, total), self._nearest_edge(source, end, total)
        if end <= start:
            return (Fraction(0), Fraction(0)) if share < total else (Fraction(0), total)
        return start, end

    def _sweep(self, source, target, total):
        start, end = self.region(source)
        if end <= start:
            return source.notes
        if start == 0 and end == total:
            return target.notes
        notes = []
        if start > 0:
            notes += source.section(0, start).notes
        notes += target.section(start, end).notes
        if end < total:
            notes += source.section(end, total).notes
        return notes

    def _nearest_edge(self, source, time, total):
        """Return the start of the note in the source closest to a time."""
        edges = [Fraction(0), total]
        now = Fraction(0)
        for position in source.played_notes():
            edges.append(now)
            now += exact_length(position.length)
        return min(edges, key=lambda edge: (abs(edge - time), edge))
