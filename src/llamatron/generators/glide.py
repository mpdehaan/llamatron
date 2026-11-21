# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Glide generator: a row of on-or-off steps that makes the notes starting on the steps that are on glide into the next note, running at its own step from the clip's start."""

import math

from llamatron.generators.base import ClipGenerator
from llamatron.math import length
from llamatron.math.length import Length
from llamatron.music import sound as sound_values
from llamatron.music.sound import Sound


class StepRow(ClipGenerator):
    """What Glide and Shorten share: a row of on-or-off steps, each as long as step, from the clip's start, changing the single notes starting on a step that's on."""

    __slots__ = ('_steps', '_step', '_offset')

    def __init__(self, *, steps, step, continuation=None):
        self._steps = list(steps)
        self._step = step
        # How far into its run the clip starts, which a Restart that doesn't start over with the clip sets.
        self._offset = 0 if continuation is None else continuation.offset

    def is_on(self, time):
        """Return whether the row's step a time from the clip's start falls in is on."""
        return self._steps[math.floor((time + self._offset) / self._step) % len(self._steps)]

    def _generate(self, clip):
        sounds = clip.resolved_sounds()
        result = []
        now = length.ZERO
        for place, sound in enumerate(sounds):
            if sound[sound_values.KIND] == sound_values.NOTE and self.is_on(Length.rational(now)):
                result += self._changed(note=sound, following=sounds[place + 1:])
            else:
                result.append(sound)
            now = Length.add(now, sound[sound_values.LENGTH])
        return result, clip.get_length()

    def _changed(self, *, note, following):
        """Return the positions a note starting on a step that's on becomes."""
        raise NotImplementedError


class Glide(StepRow):
    """Holds a single note starting on a step that's on past its place, by the glide amount, into a next note of another pitch, as the pattern's Glide row does."""

    __slots__ = ('_amount',)

    def __init__(self, *, steps, step, glide_amount, continuation=None):
        super().__init__(steps=steps, step=step, continuation=continuation)
        self._amount = Length.of(glide_amount)

    def _changed(self, *, note, following):
        if _next_pitch(following) in (None, note[sound_values.MIDI]):
            return [note]
        return [Sound.held(Sound.with_length(note, Length.add(note[sound_values.LENGTH], self._amount)), note[sound_values.LENGTH])]


def _next_pitch(following):
    """Return the pitch of the next note, or None when a rest, a chord or the clip's end comes first."""
    for sound in following:
        if sound[sound_values.KIND] == sound_values.REST:
            return None
        return sound[sound_values.MIDI] if sound[sound_values.KIND] == sound_values.NOTE else None
    return None
