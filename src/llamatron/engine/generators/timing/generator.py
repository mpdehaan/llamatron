# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a Timing generator does to a clip's notes: its Glide holds the notes starting on its lit steps into the next note, then its
Shorten plays the notes starting on its lit steps short, each row running at its own step from the clip's start. Its Rush and its
Drag move notes in time after every chain has run (engine/timing/nudge_plan.py), so they are no part of this."""

import math

from llamatron.engine.generators.base import ClipGenerator
from llamatron.math import length
from llamatron.math.length import Length
from llamatron.math.rational import Rational
from llamatron.model.values import sound as sound_values
from llamatron.model.values.sound import Sound

# Where a glide starts that carries on from nothing.
NO_OFFSET = 0


PERCENT = 100


class TimingGenerator(ClipGenerator):
    """Runs a Timing generator's parts that change notes, its Glide and then its Shorten, each a row of its own, on a clip; with
    neither lit, the clip's notes pass unchanged."""

    __slots__ = ('_rows',)

    def __init__(self, *, rows):
        """rows are the lit parts that change notes, in the order they run, each a StepRowGenerator."""
        self._rows = rows

    def generate(self, clip):
        if not self._rows:
            return super().generate(clip)
        for row in self._rows:
            clip = row.generate(clip)
        return clip

    def _generate(self, clip):
        return clip.resolved_sounds(), clip.get_length()


class StepRowGenerator(ClipGenerator):
    """What Glide and Shorten share: a row of on-or-off steps, each as long as step, from the clip's start, changing the single notes starting on a step that's on."""

    __slots__ = ('_steps', '_step', '_offset')

    def __init__(self, *, steps, step, continuation=None):
        self._steps = list(steps)
        self._step = step
        # How far into its run the clip starts, which a Restart that doesn't start over with the clip sets.
        self._offset = NO_OFFSET
        if continuation is not None:
            self._offset = continuation.offset

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


class Glide(StepRowGenerator):
    """Holds a single note starting on a step that's on past its place, by the glide amount, into a next note of another pitch, as the pattern's Glide row does."""

    __slots__ = ('_amount',)

    def __init__(self, *, steps, step, glide_amount, continuation=None):
        super().__init__(steps=steps, step=step, continuation=continuation)
        self._amount = Length.of(glide_amount)

    def _changed(self, *, note, following):
        if _next_pitch(following) in (None, note[sound_values.MIDI]):
            return [note]
        return [Sound.held(Sound.with_length(note, Length.add(note[sound_values.LENGTH], self._amount)), note[sound_values.LENGTH])]



class Shorten(StepRowGenerator):
    """Plays a single note starting on a step that's on for its shorten amount of its length, the rest of its place a rest."""

    __slots__ = ('_shorten',)

    def __init__(self, *, steps, step, shorten, continuation=None):
        super().__init__(steps=steps, step=step, continuation=continuation)
        self._shorten = shorten

    def _changed(self, *, note, following):
        short = Length.multiplied(note[sound_values.LENGTH], Length.of(Rational(self._shorten, PERCENT)))
        return [Sound.with_length(note, short), Sound.rest(Length.subtract(note[sound_values.LENGTH], short))]

def _next_pitch(following):
    """Return the pitch of the next note, or None when a rest, a chord or the clip's end comes first."""
    for sound in following:
        if sound[sound_values.KIND] == sound_values.REST:
            return None
        if sound[sound_values.KIND] != sound_values.NOTE:
            return None
        return sound[sound_values.MIDI]
    return None
