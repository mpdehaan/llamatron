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

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.note import Rest, _check_length
from llamatron.song import _Validated


def _check_every(every):
    # bool is a subclass of int, but True is not a real count.
    if type(every) is not int or every < 1:
        raise ValueError(f'invalid every: {every!r} (must be a positive integer)')


def _longer(position, extra):
    if isinstance(position, Chord):
        return Chord([_longer(note, extra) for note in position.notes])
    return replace(position, length=exact_length(position.length) + extra)


class Hold(ClipGenerator):
    """Makes every Nth note or chord slightly longer, without multiplying anything.

    The extra length comes out of any rest after the note, so every note still starts on time.
    A note with no rest after it has no room to grow, so it stays as it is. Rests don't count
    towards every.
    """

    length = _Validated(_check_length)
    every = _Validated(_check_every)

    def __init__(self, length, every=1):
        self.length = length
        self.every = every

    def _generate(self, clip):
        positions = clip.played_notes()
        extra = exact_length(self.length)
        notes = []
        played = 0
        taken = Fraction(0)
        for index, position in enumerate(positions):
            if isinstance(position, Rest):
                remaining = exact_length(position.length) - taken
                taken = Fraction(0)
                if remaining > 0:
                    notes.append(Rest(remaining))
                continue
            played += 1
            following = positions[index + 1] if index + 1 < len(positions) else None
            room = exact_length(following.length) if isinstance(following, Rest) else Fraction(0)
            taken = min(extra, room) if played % self.every == 0 else Fraction(0)
            notes.append(_longer(position, taken) if taken else position)
        return notes, clip.length
