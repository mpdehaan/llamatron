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
from src.note import Note
from src.scale import Scale
from src.song import _Validated


def _check_scale(scale):
    if not isinstance(scale, Scale):
        raise ValueError(f'expected a Scale, got {scale!r}')


class TransposeScale(ClipGenerator):
    """Moves a clip from one scale to another, keeping each note on the same scale degree.

    With C major as the input and C blues as the output, E4 is degree 3 of the input,
    so it becomes F4, which is degree 3 of the output. Notes become degrees, and the new
    clip's scale is the output scale, so changing that scale later changes the notes.
    Chords can't hold degrees yet, so they become notes of the output scale straight away.
    Degrees and rests stay as they are, and everything keeps its length.
    """

    input_scale = _Validated(_check_scale)
    output_scale = _Validated(_check_scale)

    def __init__(self, input_scale, output_scale):
        self.input_scale = input_scale
        self.output_scale = output_scale

    def _generate(self, clip):
        return [self._move(position) for position in clip.notes], clip.length

    def _new_scale(self, clip):
        return self.output_scale

    def _move(self, position):
        if isinstance(position, Note):
            return self.input_scale.degree_of(position)
        if isinstance(position, Chord):
            return Chord([
                self.input_scale.degree_of(note).to_note(self.output_scale)
                for note in position.notes
            ])
        return position
