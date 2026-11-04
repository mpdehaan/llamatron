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

from src.generators.base import ClipGenerator
from src.song import _Validated


def _check_swaps(swaps):
    # bool is a subclass of int, but True is not a real count.
    if type(swaps) is not int or swaps < 0:
        raise ValueError(f'invalid swaps: {swaps!r} (must be an integer of 0 or more)')


def _check_seed(seed):
    if seed is not None and type(seed) is not int:
        raise ValueError(f'invalid seed: {seed!r} (must be an integer or None)')


class MixUp(ClipGenerator):
    """Swaps two randomly chosen positions in a clip, a number of times.

    Notes, chords and rests can all be swapped, and they keep their own lengths,
    so the rhythm can change but the total duration doesn't. Set a seed to get the
    same result every time.
    """

    swaps = _Validated(_check_swaps)
    seed = _Validated(_check_seed)

    def __init__(self, swaps, seed=None):
        self.swaps = swaps
        self.seed = seed

    def _generate(self, clip):
        notes = list(clip.notes)
        if len(notes) >= 2:
            generator = random.Random(self.seed)
            for _ in range(self.swaps):
                first, second = generator.sample(range(len(notes)), 2)
                notes[first], notes[second] = notes[second], notes[first]
        return notes, clip.length
