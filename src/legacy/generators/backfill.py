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

import random
from fractions import Fraction
from itertools import pairwise
from math import isfinite

from src.chord import Chord
from src.generators.arp import _check_seed
from src.generators.base import ClipGenerator, exact_length, fit_to_length
from src.legacy.generators.transpose import _check_scale
from src.note import Degree, Note, Rest
from src.song import _Validated


def _check_probabilities(probabilities):
    if not isinstance(probabilities, (list, tuple)) or not probabilities:
        raise ValueError(f'expected a list of probabilities, got {probabilities!r}')
    for probability in probabilities:
        # bool is a subclass of int, but True is not a real probability.
        if (type(probability) not in (int, float, Fraction)
                or not isfinite(probability) or not 0 <= probability <= 1):
            raise ValueError(f'invalid probability: {probability!r} (must be from 0 to 1)')


def _pitch(position, scale):
    """Return the MIDI number of a note, degree or chord, using a chord's lowest note."""
    if isinstance(position, Chord):
        return min(note.midi_number for note in position.notes)
    if isinstance(position, Degree):
        return position.to_note(scale).midi_number
    return position.midi_number


def _plain_degree(position):
    """Return (octave, place in the scale) for a Degree that can be used without a scale."""
    if isinstance(position, Degree) and position.half_steps == 0:
        return position.octave, position.number + position.scale_notes
    return None


class Backfill(ClipGenerator):
    """Adds a note halfway through some of the gaps between neighboring notes.

    Each gap uses the next probability in a repeating cycle, so [0, 0, 0.5, 1] never fills
    the first two gaps, has an even chance of filling the third, and always fills the
    fourth. The new note starts halfway between the two notes' start times, lasts as long
    as the first note, and is the scale note closest to their halfway pitch, with ties going
    to the lower note. Nothing is added if no scale note lies strictly between the two
    pitches or the new note wouldn't fit in the silence. The gap after the last note is
    never filled. A chord's lowest note is its pitch.

    Between two degrees in the same octave, the new note is the middle degree, which needs
    no scale. Otherwise this uses the scale given here, or else the clip's. To use a scale
    from a scene or song, pass in song.scale_at(scene, track). Set a seed to get the same
    result every time, though repeated runs usually want a different seed or none.
    """

    probabilities = _Validated(_check_probabilities)
    scale = _Validated(_check_scale)
    seed = _Validated(_check_seed)

    def __init__(self, probabilities, scale=None, seed=None):
        self.probabilities = probabilities
        self.scale = scale
        self.seed = seed

    def _generate(self, clip):
        positions = clip.resolved_notes()
        if clip.length is not None:
            positions = fit_to_length(positions, clip.length)

        played = []
        total = Fraction(0)
        for position in positions:
            if not isinstance(position, Rest):
                played.append((total, position))
            total += exact_length(position.length)

        scale = clip.scale if self.scale is None else self.scale
        generator = random.Random(self.seed)
        added = []
        for index, (first, second) in enumerate(pairwise(played)):
            probability = self.probabilities[index % len(self.probabilities)]
            if generator.random() < probability:
                new = self._new_position(first, second, scale)
                if new is not None:
                    added.append(new)

        if not added:
            return clip.notes, clip.length

        result = []
        now = Fraction(0)
        for start, position in sorted(played + added, key=lambda item: item[0]):
            if start > now:
                result.append(Rest(start - now))
            result.append(position)
            now = start + exact_length(position.length)
        if total > now:
            result.append(Rest(total - now))
        return result, clip.length

    def _new_position(self, first, second, scale):
        """Return (start, position) for a note between two others, or None if none fits."""
        first_start, first_position = first
        second_start, second_position = second
        length = first_position.length
        start = (first_start + second_start) / 2
        # The new note is as long as the first one and starts halfway, so if the first note
        # ends by the halfway point, the new one also ends by the time the second one starts.
        if first_start + exact_length(length) > start:
            return None

        first_place = _plain_degree(first_position)
        second_place = _plain_degree(second_position)
        if first_place and second_place and first_place[0] == second_place[0]:
            new = self._middle_degree(first_place, second_place, length)
        else:
            new = self._middle_note(first_position, second_position, length, scale)
        return None if new is None else (start, new)

    def _middle_degree(self, first_place, second_place, length):
        """Return the Degree between two places in one octave, or None if they're neighbors."""
        octave = first_place[0]
        low, high = sorted((first_place[1], second_place[1]))
        if high - low < 2:
            return None
        middle = (low + high) // 2
        if middle >= 1:
            return Degree(middle, length, octave=octave)
        return Degree(1, length, octave=octave, scale_notes=middle - 1)

    def _middle_note(self, first, second, length, scale):
        """Return the scale note closest to the halfway pitch between two positions, or None."""
        if scale is None:
            raise ValueError('filling a gap between these notes needs a scale, but none was found')
        low, high = sorted((_pitch(first, scale), _pitch(second, scale)))
        steps = set(scale.typ.value)
        candidates = [
            pitch for pitch in range(low + 1, high)
            if (pitch - scale.root.midi_number) % 12 in steps
        ]
        if not candidates:
            return None
        halfway = Fraction(low + high, 2)
        pitch = min(candidates, key=lambda candidate: (abs(candidate - halfway), candidate))
        return scale.degree_of(Note.from_midi_number(pitch, length)).to_note(scale)
