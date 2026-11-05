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

from src.chord import Chord
from src.generators.base import ClipGenerator
from src.legacy.generators.counterpoint import _check_note
from src.note import Note
from src.song import _Validated


class Register(ClipGenerator):
    """Moves notes by octaves until they're all between low and high, keeping their names.

    This gives a part its own space, so that it doesn't overlap the other parts. Notes in a
    chord move separately, so a chord may be rearranged, but it still has the same notes. The
    range must cover at least 12 half steps, so that every note has somewhere to go. Rests and
    degrees are left alone.
    """

    low = _Validated(_check_note)
    high = _Validated(_check_note)

    def __init__(self, low, high):
        self.low = low
        self.high = high

    def _generate(self, clip):
        if self.high.midi_number - self.low.midi_number < 11:
            raise ValueError(f'the range must cover an octave, but got {self.low!r} to {self.high!r}')
        return [self._move(position) for position in clip.notes], clip.length

    def _move(self, position):
        if isinstance(position, Chord):
            return Chord([self._move(note) for note in position.notes])
        if not isinstance(position, Note):
            return position
        pitch = position.midi_number
        while pitch > self.high.midi_number:
            pitch -= 12
        while pitch < self.low.midi_number:
            pitch += 12
        return position if pitch == position.midi_number else Note.from_midi_number(pitch, position.length)
