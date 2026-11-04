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

from bisect import bisect_right

from src.chord import Chord
from src.generators.base import ClipGenerator
from src.note import Degree, Note
from src.scale import Scale
from src.song import _Validated


def _check_amount(amount):
    # bool is a subclass of int, but True is not a real amount.
    if amount is not None and type(amount) is not int:
        raise ValueError(f'invalid amount: {amount!r} (must be an integer)')


def _check_scale(scale):
    if scale is not None and not isinstance(scale, Scale):
        raise ValueError(f'expected a Scale, got {scale!r}')


def _half_steps_for_scale_notes(note, scale, scale_notes):
    """Return how many half steps moves a note by a number of notes along a scale.

    A note that isn't in the scale keeps its distance from the scale note below it.
    """
    octaves, above_root = divmod(note.midi_number - scale.root.midi_number, 12)
    steps = scale.typ.value
    index = bisect_right(steps, above_root) - 1
    octaves_moved, new_index = divmod(index + scale_notes, len(steps))
    return (octaves_moved * 12) + steps[new_index] - steps[index]


class Transpose(ClipGenerator):
    """Moves every note in a clip up, or down if the amount is negative.

    Give exactly one of half_steps, whole_steps, octaves or scale_notes. Moving a Note
    by scale_notes needs a scale: the one given here if there is one, or else the
    clip's. To use a scale from a scene or song, pass in song.scale_at(scene, track).
    Degrees don't need one, because they remember the move until they're rendered.
    Rests stay as they are, and every note keeps its length.
    """

    half_steps = _Validated(_check_amount)
    whole_steps = _Validated(_check_amount)
    octaves = _Validated(_check_amount)
    scale_notes = _Validated(_check_amount)
    scale = _Validated(_check_scale)

    def __init__(self, *, half_steps=None, whole_steps=None, octaves=None, scale_notes=None,
                 scale=None):
        self.half_steps = half_steps
        self.whole_steps = whole_steps
        self.octaves = octaves
        self.scale_notes = scale_notes
        self.scale = scale
        self._check_one_amount()

    def _check_one_amount(self):
        amounts = [self.half_steps, self.whole_steps, self.octaves, self.scale_notes]
        if sum(amount is not None for amount in amounts) != 1:
            raise ValueError(
                'expected exactly one of half_steps, whole_steps, octaves or scale_notes'
            )

    def _generate(self, clip):
        # Checked again because the amounts can be edited after the constructor has run.
        self._check_one_amount()
        scale = clip.scale if self.scale is None else self.scale
        return [self._move(position, scale) for position in clip.notes], clip.length

    def _move(self, position, scale):
        if isinstance(position, Chord):
            return Chord([self._move(note, scale) for note in position.notes])
        if isinstance(position, Degree):
            return position.moved(
                half_steps=(self.half_steps or 0) + (self.whole_steps or 0) * 2,
                octaves=self.octaves or 0,
                scale_notes=self.scale_notes or 0,
            )
        if not isinstance(position, Note):
            return position
        if self.half_steps is not None:
            return position.half_step(self.half_steps)
        if self.whole_steps is not None:
            return position.whole_step(self.whole_steps)
        if self.octaves is not None:
            return position.octave(self.octaves)
        if scale is None:
            raise ValueError('moving a Note by scale_notes needs a scale, but none was found')
        return position.half_step(_half_steps_for_scale_notes(position, scale, self.scale_notes))
