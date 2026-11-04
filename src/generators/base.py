# noose6: a Python language and framework for producing MIDI clips.
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

from abc import ABC, abstractmethod
from dataclasses import replace
from fractions import Fraction

from src.chord import Chord
from src.note import Rest
from src.song import POSITION_TYPES, Clip


def exact_length(length):
    """Return a length as an exact fraction.

    Lengths like 1/12 are slightly inexact as floats, so without this, three of them
    would fall just short of a quarter note and leave a tiny extra note or rest.
    """
    return Fraction(length).limit_denominator(1_000_000)


def _cut(position, length):
    """Return a position that lasts no longer than length."""
    if exact_length(position.length) <= length:
        return position
    if isinstance(position, Chord):
        return Chord([_cut(note, length) for note in position.notes])
    return replace(position, length=length)


def fit_to_length(positions, length):
    """Return positions that last exactly length, cutting notes off or adding a final rest."""
    result = []
    remaining = exact_length(length)
    for position in positions:
        if remaining <= 0:
            break
        result.append(_cut(position, remaining))
        remaining -= min(exact_length(position.length), remaining)
    if remaining > 0:
        result.append(Rest(remaining))
    return result


class ClipGenerator(ABC):
    """Makes a new Clip from an existing one, which is left unchanged.

    To write a generator, implement _generate. The new clip keeps the original's
    name, scale and note_length, and gets its own id. Degrees stay as degrees, so the
    new clip still follows whichever scale applies when it's rendered. Use
    clip.resolved_notes() if a generator needs to know how long each position is.
    """

    def generate(self, clip):
        """Return a new Clip made from this one."""
        if not isinstance(clip, Clip):
            raise ValueError(f'expected a Clip, got {clip!r}')
        # A clip's list can be appended to directly, so its contents are checked again here.
        for position in clip.notes:
            if not isinstance(position, POSITION_TYPES):
                raise ValueError(f'expected a Note, Chord, Rest or Degree, got {position!r}')
        notes, length = self._generate(clip)
        return Clip(
            name=clip.name, notes=notes, scale=self._new_scale(clip), length=length,
            note_length=clip.note_length,
        )

    def _new_scale(self, clip):
        """Return the new clip's scale, which is the original's unless a generator changes it."""
        return clip.scale

    @abstractmethod
    def _generate(self, clip):
        """Return the new clip's list of notes and its length."""
