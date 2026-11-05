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
from llamatron.generators.base import ClipGenerator, _cut, exact_length, fit_to_length
from llamatron.note import Rest
from llamatron.song import _Validated


def _check_factors(factors):
    if not isinstance(factors, (list, tuple)) or not factors:
        raise ValueError(f'expected a list of factors, got {factors!r}')
    for factor in factors:
        # bool is a subclass of int, but True is not a real factor.
        if type(factor) not in (int, float, Fraction) or not isfinite(factor) or factor <= 0:
            raise ValueError(f'invalid factor: {factor!r} (must be a positive number)')


def _scaled(position, factor):
    """Return a Note, Degree or Chord with its length multiplied by factor."""
    if isinstance(position, Chord):
        return Chord([_scaled(note, factor) for note in position.notes])
    return replace(position, length=exact_length(position.length) * factor)


class DurationChange(ClipGenerator):
    """Multiplies the length of each note or chord by the next factor, in a repeating cycle.

    With [0.25, 1, 2], the first note is a quarter as long, the second stays the same
    and the third is twice as long. A chord uses one factor for all of its notes, and
    rests don't use up a factor. Every note still starts when it did before: a shorter
    note is followed by a new rest, and a longer one plays through any rests after it
    but stops when the next note starts, or at the end of the clip.
    """

    factors = _Validated(_check_factors)

    def __init__(self, factors):
        self.factors = factors

    def _generate(self, clip):
        positions = clip.resolved_notes()
        if clip.length is not None:
            positions = fit_to_length(positions, clip.length)

        result = []
        played = 0
        overhang = Fraction(0)
        for index, position in enumerate(positions):
            slot = exact_length(position.length)
            if isinstance(position, Rest):
                if slot > overhang:
                    result.append(Rest(slot - overhang) if overhang else position)
                overhang = max(overhang - slot, Fraction(0))
                continue

            factor = exact_length(self.factors[played % len(self.factors)])
            played += 1
            room = slot + self._rests_after(positions, index)
            result.append(_cut(_scaled(position, factor), room))
            new_length = min(slot * factor, room)
            if new_length < slot:
                result.append(Rest(slot - new_length))
            overhang = max(new_length - slot, Fraction(0))
        return result, clip.length

    def _rests_after(self, positions, index):
        """Return the total length of the rests between a position and the next note."""
        total = Fraction(0)
        for position in positions[index + 1:]:
            if not isinstance(position, Rest):
                break
            total += exact_length(position.length)
        return total
