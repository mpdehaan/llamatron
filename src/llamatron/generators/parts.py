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

"""The sounds of a clip as parts a generator can reshape one by one: where each starts, how long its place is and how long it is heard.

A clip is a run of sounds, each as long as its place in the run. A generator that delivers a
tune, or plays a part as a musician would, changes how long a note is heard inside its place and
how loud it is, and leaves where it starts alone: a Part holds one sound for that, and gives back
the sounds that fill the same place when the generator is done.
"""

from llamatron.music import midi
from llamatron.music.sound import CHORD, GLIDE, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NAME, NOTE, NOTES, PHRASE, REST, VELOCITY, Sound
from llamatron.support.length import ZERO, Length

# What stands for the pitch of a sound that has none of its own to compare.
NO_PITCH = -1


class Part:
    """One sound of a clip while it is reshaped: where it starts, how long its place is and how long it is heard, in whole notes, and how many times it is struck."""

    __slots__ = ('start', 'place', 'heard', 'sound', 'strikes')

    def __init__(self, *, start, sound):
        self.start = start
        self.place = Length.rational(sound[LENGTH])
        self.sound = sound[HELD_SOUND] if sound[KIND] == HELD else sound
        self.heard = Length.rational(self.sound[LENGTH])
        # A note struck more than once sounds that many times over the time it is heard, each as long as the others.
        self.strikes = 1

    def is_note(self):
        """Return whether the sound is a note or a chord of them, which phrasing changes; a rest and a phrase are left as they are."""
        return self.sound[KIND] in (NOTE, CHORD)

    def pitch(self):
        """Return the highest pitch that sounds, to tell a note from the note after it."""
        if self.sound[KIND] == CHORD:
            return max((note[MIDI] for note in self.sound[NOTES] if note[KIND] == NOTE), default=NO_PITCH)
        return self.sound[MIDI]

    def loudness(self):
        """Return how loud the sound is, the loudest of a chord's notes, or None for a sound with no loudness of its own."""
        notes = self.sound[NOTES] if self.sound[KIND] == CHORD else [self.sound]
        loudest = [note[VELOCITY] for note in notes if note[KIND] == NOTE and note[VELOCITY] is not None]
        return max(loudest) if loudest else None

    def lowest(self):
        """Return the lowest pitch that sounds, or None for a sound with no pitch."""
        notes = self.sound[NOTES] if self.sound[KIND] == CHORD else [self.sound]
        pitches = [note[MIDI] for note in notes if note[KIND] == NOTE]
        return min(pitches) if pitches else None

    def silence(self):
        """Make the sound a rest as long as its place."""
        self.sound = Sound.rest(Length.of(self.place))
        self.heard = self.place
        self.strikes = 1

    def moved_by(self, half_steps):
        """Move every note of the sound by a number of half steps, or leave the sound where any note would pass out of the MIDI range."""
        try:
            if self.sound[KIND] == CHORD:
                self.sound = Sound.chord([Sound.half_step(note, half_steps) if note[KIND] == NOTE else note for note in self.sound[NOTES]])
            elif self.sound[KIND] == NOTE:
                self.sound = Sound.half_step(self.sound, half_steps)
        except ValueError:
            pass

    def louder_by(self, steps):
        """Change how loud the sound is by steps of velocity, held to what MIDI allows; a note with no loudness of its own is left."""
        if self.sound[KIND] == CHORD:
            self.sound = Sound.chord([louder(note=note, steps=steps) for note in self.sound[NOTES]])
        else:
            self.sound = louder(note=self.sound, steps=steps)

    def sounds(self):
        """Return the sounds that take this one's place: itself as heard, held where it outlasts its place and followed by a rest where it stops short."""
        if not self.is_note():
            return [Sound.with_length(self.sound, Length.of(self.place))] if self.sound[KIND] in (REST, PHRASE) else [self._as_placed(self.sound)]
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
    now = ZERO
    for sound in sounds:
        parts.append(Part(start=Length.rational(now), sound=sound))
        now = Length.add(now, sound[LENGTH])
    return parts


def lasting(*, sound, heard):
    """Return a note or a chord heard for a time, a chord's shorter notes no longer than that."""
    length = Length.of(heard)
    if sound[KIND] == CHORD:
        return Sound.chord([Sound.with_length(note, length) for note in sound[NOTES]])
    return Sound.with_length(sound, length)


def louder(*, note, steps):
    """Return a note louder or softer by steps of velocity, within what MIDI allows; any other sound, and a note with no loudness yet, as it is."""
    if note[KIND] != NOTE or note[VELOCITY] is None:
        return note
    velocity = max(midi.MIN_VELOCITY, min(midi.MAX_VELOCITY, note[VELOCITY] + steps))
    return Sound.note(length=note[LENGTH], midi=note[MIDI], velocity=velocity, glide=note[GLIDE], name=note[NAME])
