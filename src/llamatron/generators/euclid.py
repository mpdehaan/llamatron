# llamatron: a music program
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
"""The Euclidean mask: a clip's notes kept only where they start on a hit of a Euclidean rhythm, the rest becoming rests of their length, the user's design of 2026-11-11."""

import math

from llamatron.composition.euclid import rhythm
from llamatron.generators.base import ClipGenerator
from llamatron.music.sound import KIND, LENGTH, REST, Sound
from llamatron.support.length import ZERO, Length


class EuclidMask(ClipGenerator):
    """Keeps a clip's notes that start on a hit of a rhythm of so many hits over so many steps, each step as long as step, from the clip's start."""

    __slots__ = ('_hits_and_misses', '_step', '_offset')

    def __init__(self, *, hits, steps, step, rotate=0, continuation=None):
        self._hits_and_misses = rhythm(hits=hits, steps=steps, rotate=rotate)
        self._step = step
        # How far into its run the clip starts, which a Restart that doesn't start over with the clip sets.
        self._offset = 0 if continuation is None else continuation.offset

    def is_hit(self, time):
        """Return whether the step a time from the clip's start falls in is a hit."""
        return self._hits_and_misses[math.floor((time + self._offset) / self._step) % len(self._hits_and_misses)]

    def _generate(self, clip):
        result = []
        now = ZERO
        for sound in clip.resolved_sounds():
            hit = sound[KIND] == REST or self.is_hit(Length.rational(now))
            result.append(sound if hit else Sound.rest(sound[LENGTH]))
            now = Length.add(now, sound[LENGTH])
        return result, clip.get_length()
