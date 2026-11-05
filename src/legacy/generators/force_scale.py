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
from src.legacy.generators.transpose import _check_scale
from src.note import Note
from src.scale import Scale
from src.song import _Validated


def _check_required_scale(scale):
    if not isinstance(scale, Scale):
        raise ValueError(f'expected a Scale, got {scale!r}')
    _check_scale(scale)


def nearest_in_scale(pitch, scale):
    """Return the MIDI number of the closest note in a scale, with ties going lower."""
    steps = set(scale.typ.value)
    for distance in range(12):
        for candidate in (pitch - distance, pitch + distance):
            if 0 <= candidate <= 127 and (candidate - scale.root.midi_number) % 12 in steps:
                return candidate
    return pitch


class ForceScale(ClipGenerator):
    """Moves every note that isn't in a scale to the closest note that is.

    Notes already in the scale, degrees and rests are left alone. A note in a chord is moved
    the same way, so a D major chord forced into C major becomes D minor. The new clip's scale
    is this scale.
    """

    scale = _Validated(_check_required_scale)

    def __init__(self, scale):
        self.scale = scale

    def _generate(self, clip):
        return [self._move(position) for position in clip.notes], clip.length

    def _new_scale(self, clip):
        return self.scale

    def _move(self, position):
        if isinstance(position, Chord):
            return Chord([self._move(note) for note in position.notes])
        if not isinstance(position, Note):
            return position
        pitch = nearest_in_scale(position.midi_number, self.scale)
        if pitch == position.midi_number:
            return position
        note = Note.from_midi_number(pitch, position.length)
        return self.scale.degree_of(note).to_note(self.scale)
