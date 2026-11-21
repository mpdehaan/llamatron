# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The sounds of a clip as parts a generator can reshape one by one: where each starts, how long its place is and how long it is heard.

A clip is a run of sounds, each as long as its place in the run. A generator that delivers a
tune, or plays a part as a musician would, changes how long a note is heard inside its place and
how loud it is, and leaves where it starts alone: a Part holds one sound for that, and gives back
the sounds that fill the same place when the generator is done.
"""

from llamatron.math import length as length_values
from llamatron.math.length import Length
from llamatron.model.values import midi, sound as sound_values
from llamatron.model.values.sound import Sound

# What stands for the pitch of a sound that has none of its own to compare.
NO_PITCH = -1


class Part:
    """One sound of a clip while it is reshaped: where it starts, how long its place is and how long it is heard, in whole notes, and how many times it is struck."""

    __slots__ = ('start', 'place', 'heard', 'sound', 'strikes')

    def __init__(self, *, start, sound):
        self.start = start
        self.place = Length.rational(sound[sound_values.LENGTH])
        self.sound = sound[sound_values.HELD_SOUND] if sound[sound_values.KIND] == sound_values.HELD else sound
        self.heard = Length.rational(self.sound[sound_values.LENGTH])
        # A note struck more than once sounds that many times over the time it is heard, each as long as the others.
        self.strikes = 1

    def is_note(self):
        """Return whether the sound is a note or a chord of them, which phrasing changes; a rest and a phrase are left as they are."""
        return self.sound[sound_values.KIND] in (sound_values.NOTE, sound_values.CHORD)

    def pitch(self):
        """Return the highest pitch that sounds, to tell a note from the note after it."""
        if self.sound[sound_values.KIND] == sound_values.CHORD:
            return max((note[sound_values.MIDI] for note in self.sound[sound_values.NOTES] if note[sound_values.KIND] == sound_values.NOTE), default=NO_PITCH)
        return self.sound[sound_values.MIDI]

    def loudness(self):
        """Return how loud the sound is, the loudest of a chord's notes, or None for a sound with no loudness of its own."""
        notes = self.sound[sound_values.NOTES] if self.sound[sound_values.KIND] == sound_values.CHORD else [self.sound]
        loudest = [note[sound_values.VELOCITY] for note in notes if note[sound_values.KIND] == sound_values.NOTE and note[sound_values.VELOCITY] is not None]
        return max(loudest) if loudest else None

    def lowest(self):
        """Return the lowest pitch that sounds, or None for a sound with no pitch."""
        notes = self.sound[sound_values.NOTES] if self.sound[sound_values.KIND] == sound_values.CHORD else [self.sound]
        pitches = [note[sound_values.MIDI] for note in notes if note[sound_values.KIND] == sound_values.NOTE]
        return min(pitches) if pitches else None

    def silence(self):
        """Make the sound a rest as long as its place."""
        self.sound = Sound.rest(Length.of(self.place))
        self.heard = self.place
        self.strikes = 1

    def moved_by(self, half_steps):
        """Move every note of the sound by a number of half steps, or leave the sound where any note would pass out of the MIDI range."""
        try:
            if self.sound[sound_values.KIND] == sound_values.CHORD:
                self.sound = Sound.chord([Sound.half_step(note, half_steps) if note[sound_values.KIND] == sound_values.NOTE else note for note in self.sound[sound_values.NOTES]])
            elif self.sound[sound_values.KIND] == sound_values.NOTE:
                self.sound = Sound.half_step(self.sound, half_steps)
        except ValueError:
            pass

    def louder_by(self, steps):
        """Change how loud the sound is by steps of velocity, held to what MIDI allows; a note with no loudness of its own is left."""
        if self.sound[sound_values.KIND] == sound_values.CHORD:
            self.sound = Sound.chord([louder(note=note, steps=steps) for note in self.sound[sound_values.NOTES]])
        else:
            self.sound = louder(note=self.sound, steps=steps)

    def sounds(self):
        """Return the sounds that take this one's place: itself as heard, held where it outlasts its place and followed by a rest where it stops short."""
        if not self.is_note():
            return [Sound.with_length(self.sound, Length.of(self.place))] if self.sound[sound_values.KIND] in (sound_values.REST, sound_values.PHRASE) else [self._as_placed(self.sound)]
        if self.strikes > 1:
            struck = [lasting(sound=self.sound, heard=self.heard / self.strikes)] * self.strikes
            return struck if self.heard >= self.place else [*struck, Sound.rest(Length.of(self.place - self.heard))]
        played = lasting(sound=self.sound, heard=self.heard)
        if self.heard == self.place:
            return [played]
        if self.heard > self.place:
            return [Sound.held(played, Length.of(self.place))]
        return [played, Sound.rest(Length.of(self.place - self.heard))]

    def _as_placed(self, sound):
        """Return a sound phrasing does not change, in its place: held again where it was held."""
        return sound if self.heard == self.place else Sound.held(sound, Length.of(self.place))


def parts_of(sounds):
    """Return each sound of a clip as a part, with the time it starts at from the clip's start."""
    parts = []
    now = length_values.ZERO
    for sound in sounds:
        parts.append(Part(start=Length.rational(now), sound=sound))
        now = Length.add(now, sound[sound_values.LENGTH])
    return parts


def lasting(*, sound, heard):
    """Return a note or a chord heard for a time, a chord's shorter notes no longer than that."""
    length = Length.of(heard)
    if sound[sound_values.KIND] == sound_values.CHORD:
        return Sound.chord([Sound.with_length(note, length) for note in sound[sound_values.NOTES]])
    return Sound.with_length(sound, length)


def louder(*, note, steps):
    """Return a note louder or softer by steps of velocity, within what MIDI allows; any other sound, and a note with no loudness yet, as it is."""
    if note[sound_values.KIND] != sound_values.NOTE or note[sound_values.VELOCITY] is None:
        return note
    velocity = max(midi.MIN_VELOCITY, min(midi.MAX_VELOCITY, note[sound_values.VELOCITY] + steps))
    return Sound.note(length=note[sound_values.LENGTH], midi=note[sound_values.MIDI], velocity=velocity, glide=note[sound_values.GLIDE], name=note[sound_values.NAME])
