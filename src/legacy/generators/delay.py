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

from dataclasses import replace
from fractions import Fraction

from src.chord import Chord
from src.generators.base import ClipGenerator, exact_length
from src.legacy.generators.hold import _check_every
from src.note import Rest, _check_length
from src.song import _Validated


def _shorter(position, amount):
    if isinstance(position, Chord):
        return Chord([_shorter(note, amount) for note in position.notes])
    return replace(position, length=exact_length(position.length) - amount)


def _shortest_note(position):
    if isinstance(position, Chord):
        return min(exact_length(note.length) for note in position.notes)
    return exact_length(position.length)


class Delay(ClipGenerator):
    """Plays every Nth note or chord slightly late, which makes the music feel looser.

    The note still ends when it did before, so nothing after it moves. A note too short to
    start that late stays as it is. Rests don't count towards every.
    """

    amount = _Validated(_check_length)
    every = _Validated(_check_every)

    def __init__(self, amount, every=1):
        self.amount = amount
        self.every = every

    def _generate(self, clip):
        amount = exact_length(self.amount)
        notes = []
        played = 0
        for position in clip.played_notes():
            if isinstance(position, Rest):
                notes.append(position)
                continue
            played += 1
            if played % self.every == 0 and _shortest_note(position) > amount:
                notes += [Rest(amount), _shorter(position, amount)]
            else:
                notes.append(position)
        return notes, clip.length
