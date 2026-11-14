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
"""The Glide generator: a row of on-or-off steps that makes the notes starting on the steps that are on glide into the next note, running at its own step from the clip's start, the user's design of 2026-11-11."""

import math

from llamatron.generators.base import ClipGenerator
from llamatron.music.sound import KIND, LENGTH, MIDI, NOTE, REST, Sound
from llamatron.support.length import ZERO, Length


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
        now = ZERO
        for place, sound in enumerate(sounds):
            if sound[KIND] == NOTE and self.is_on(Length.rational(now)):
                result += self._changed(note=sound, following=sounds[place + 1:])
            else:
                result.append(sound)
            now = Length.add(now, sound[LENGTH])
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
        if _next_pitch(following) in (None, note[MIDI]):
            return [note]
        return [Sound.held(Sound.with_length(note, Length.add(note[LENGTH], self._amount)), note[LENGTH])]


def _next_pitch(following):
    """Return the pitch of the next note, or None when a rest, a chord or the clip's end comes first."""
    for sound in following:
        if sound[KIND] == REST:
            return None
        return sound[MIDI] if sound[KIND] == NOTE else None
    return None
