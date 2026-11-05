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

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.song import _Validated


def _check_times(times):
    # bool is a subclass of int, but True is not a real count.
    if type(times) is not int or times < 1:
        raise ValueError(f'invalid times: {times!r} (must be a positive integer)')


def _divide(position, times):
    """Return a position that lasts 1/times as long."""
    if isinstance(position, Chord):
        return Chord([_divide(note, times) for note in position.notes])
    return replace(position, length=exact_length(position.length) / times)


class Repeater(ClipGenerator):
    """Plays each note, chord and rest several times in the time it originally took.

    Repeater(2) turns a whole note into two half notes, so the new clip lasts as
    long as the original and keeps its length.
    """

    times = _Validated(_check_times)

    def __init__(self, times):
        self.times = times

    def _generate(self, clip):
        notes = [
            _divide(position, self.times)
            for position in clip.resolved_notes()
            for _ in range(self.times)
        ]
        return notes, clip.length
