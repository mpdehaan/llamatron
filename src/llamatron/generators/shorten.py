# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Shorten generator: a row of on-or-off steps that makes the notes starting on the steps that are on play short, a share of their length with a rest after."""

from llamatron.generators.glide import StepRow
from llamatron.math.length import Length
from llamatron.math.rational import Rational
from llamatron.music import sound
from llamatron.music.sound import Sound

PERCENT = 100


class Shorten(StepRow):
    """Plays a single note starting on a step that's on for its shorten amount of its length, the rest of its place a rest."""

    __slots__ = ('_shorten',)

    def __init__(self, *, steps, step, shorten, continuation=None):
        super().__init__(steps=steps, step=step, continuation=continuation)
        self._shorten = shorten

    def _changed(self, *, note, following):
        short = Length.multiplied(note[sound.LENGTH], Length.of(Rational(self._shorten, PERCENT)))
        return [Sound.with_length(note, short), Sound.rest(Length.subtract(note[sound.LENGTH], short))]
