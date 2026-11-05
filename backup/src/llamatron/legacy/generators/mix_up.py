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

from llamatron.generators.arp import _check_seed
from llamatron.legacy.generators.backfill import _check_probabilities
from llamatron.generators.base import ClipGenerator
from llamatron.note import Rest
from llamatron.song import _Validated


class MixUp(ClipGenerator):
    """Swaps notes with randomly chosen other notes, using a repeating list of probabilities.

    Each note uses the next probability in the cycle, so [0, 0, 1] always swaps the third
    note with another one. Every step works on the notes as they are by then, so a later
    swap can undo an earlier one: two notes with [1] swap and then swap back. Steps only
    count notes and chords. Rests stay where they are and don't use up a probability.
    Notes keep their own lengths, so swapping different lengths moves the notes between
    them. Set a seed to get the same result every time.
    """

    probabilities = _Validated(_check_probabilities)
    seed = _Validated(_check_seed)

    def __init__(self, probabilities, seed=None):
        self.probabilities = probabilities
        self.seed = seed

    def _generate(self, clip):
        positions = list(clip.notes)
        note_places = [
            place for place, position in enumerate(positions)
            if not isinstance(position, Rest)
        ]
        generator = random.Random(self.seed)
        for step, place in enumerate(note_places):
            probability = self.probabilities[step % len(self.probabilities)]
            others = [other for other in note_places if other != place]
            if others and generator.random() < probability:
                partner = generator.choice(others)
                positions[place], positions[partner] = positions[partner], positions[place]
        return positions, clip.length
