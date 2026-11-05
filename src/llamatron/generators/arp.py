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

import random
from dataclasses import replace
from enum import Enum, auto

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator, exact_length, fit_to_length
from llamatron.note import _check_length
from llamatron.song import _Validated


class ChordOrder(Enum):
    """The order in which Arp plays a chord's notes."""

    UP = auto()
    DOWN = auto()
    UP_DOWN = auto()
    DOWN_UP = auto()
    RANDOM = auto()


def _check_order(order):
    if not isinstance(order, ChordOrder):
        raise ValueError(f'expected a ChordOrder, got {order!r}')


def _check_seed(seed):
    if seed is not None and type(seed) is not int:
        raise ValueError(f'invalid seed: {seed!r} (must be an integer or None)')


def _lowest_to_highest(chord):
    """Return a chord's notes from lowest to highest, with each pitch only once."""
    by_pitch = {}
    for note in chord.notes:
        by_pitch.setdefault(note.midi_number, note)
    return [by_pitch[midi_number] for midi_number in sorted(by_pitch)]


class Arp(ClipGenerator):
    """Plays each chord one note at a time, every step long, for as long as the chord lasts.

    Single notes and rests are left as they are. If the clip has a set length, the
    result starts again from the beginning until it fills that length, and anything
    past the end is cut off. Set a seed to get the same RANDOM result every time.
    """

    step = _Validated(_check_length)
    order = _Validated(_check_order)
    seed = _Validated(_check_seed)

    def __init__(self, step, order=ChordOrder.UP, seed=None):
        self.step = step
        self.order = order
        self.seed = seed

    def _generate(self, clip):
        generator = random.Random(self.seed)
        original = clip.resolved_notes()
        positions = self._arpeggiate(original, generator)
        if clip.length is None:
            return positions, None

        total = sum(exact_length(position.length) for position in positions)
        while positions and total < exact_length(clip.length):
            more = self._arpeggiate(original, generator)
            positions += more
            total += sum(exact_length(position.length) for position in more)
        return fit_to_length(positions, clip.length), clip.length

    def _arpeggiate(self, positions, generator):
        result = []
        for position in positions:
            if isinstance(position, Chord):
                result += self._arpeggiate_chord(position, generator)
            else:
                result.append(position)
        return result

    def _arpeggiate_chord(self, chord, generator):
        notes = _lowest_to_highest(chord)
        pattern = self._pattern(notes)
        result = []
        step = exact_length(self.step)
        remaining = exact_length(chord.length)
        index = 0
        while remaining > 0:
            note = generator.choice(notes) if pattern is None else pattern[index % len(pattern)]
            length = self.step if step <= remaining else remaining
            result.append(replace(note, length=length))
            remaining -= min(step, remaining)
            index += 1
        return result

    def _pattern(self, notes):
        """Return the notes in the order they repeat, or None if the order is random."""
        down = notes[::-1]
        if self.order is ChordOrder.UP:
            return notes
        if self.order is ChordOrder.DOWN:
            return down
        # The turning points aren't repeated, so C E G becomes C E G E and then C E G E again.
        if self.order is ChordOrder.UP_DOWN:
            return notes + notes[-2:0:-1]
        if self.order is ChordOrder.DOWN_UP:
            return down + down[-2:0:-1]
        return None
