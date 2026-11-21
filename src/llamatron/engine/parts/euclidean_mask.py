# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Euclidean mask: a clip's notes kept only where they start on a hit of a Euclidean rhythm, the rest becoming rests of their length."""

import math

from llamatron.engine.generators.base import ClipGenerator
from llamatron.math import length
from llamatron.math.length import Length
from llamatron.model.objects.euclid import rhythm
from llamatron.model.values import sound as sound_values
from llamatron.model.values.sound import Sound


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
        now = length.ZERO
        for sound in clip.resolved_sounds():
            hit = sound[sound_values.KIND] == sound_values.REST or self.is_hit(Length.rational(now))
            result.append(sound if hit else Sound.rest(sound[sound_values.LENGTH]))
            now = Length.add(now, sound[sound_values.LENGTH])
        return result, clip.get_length()
