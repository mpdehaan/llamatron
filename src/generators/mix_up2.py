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
from itertools import pairwise

from src.generators.arp import _check_seed
from src.generators.backfill import _check_probabilities
from src.generators.base import ClipGenerator
from src.note import Rest
from src.song import _Validated


class MixUp2(ClipGenerator):
    """Swaps each note with the next note, using a repeating list of probabilities.

    Working from first to last, step 1 may swap the first and second notes, step 2 the
    second and third, and so on, so a note that has just been swapped can move again. With
    [1, 0], the first two notes swap, the next step does nothing, and then the cycle
    starts again. Steps only count notes and chords. Rests stay where they are and don't
    use up a probability, and the last note has no next note to swap with. Notes keep
    their own lengths, so swapping different lengths moves the notes after them. Set a
    seed to get the same result every time.
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
        for step, (first, second) in enumerate(pairwise(note_places)):
            probability = self.probabilities[step % len(self.probabilities)]
            if generator.random() < probability:
                positions[first], positions[second] = positions[second], positions[first]
        return positions, clip.length
