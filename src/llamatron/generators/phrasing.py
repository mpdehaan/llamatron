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

"""Plays a tune as a singer or a horn player would deliver it: in lines, with a breath after each, a rise and fall, and its notes choppy or flowing.

A tune written step by step fills every bar at one loudness. A player delivers it in lines,
the sentences of the tune: each line grows toward its main note and falls away, a breath
follows it, and its notes run together or stand apart. The tune's pattern stays as written:
the phrasing is made as the clip plays, so another delivery is another setting and never
another tune. No note is left out, no pitch changes and nothing is drawn by chance.
"""

from llamatron.generators.base import ClipGenerator
from llamatron.music.midi import MAX_VELOCITY, MIN_VELOCITY
from llamatron.music.sound import CHORD, GLIDE, HELD, HELD_SOUND, KIND, LENGTH, MIDI, NAME, NOTE, NOTES, PHRASE, REST, VELOCITY, Sound
from llamatron.support.length import ZERO, Length
from llamatron.support.rational import Rational

EIGHTH = Rational(1, 8)
QUARTER = Rational(1, 4)
# How long the breath after a line is.
NO_BREATH = 'none'
QUICK_BREATH = 'quick'
DEEP_BREATH = 'deep'
BREATHS = (NO_BREATH, QUICK_BREATH, DEEP_BREATH)
BREATH_LENGTHS = {NO_BREATH: Rational(0), QUICK_BREATH: EIGHTH, DEEP_BREATH: QUARTER}
# A breath never takes more than this part of the note it shortens.
MOST_OF_A_NOTE_BREATHED = Rational(1, 2)
# How far a line's loudness rises to its main note and falls away.
NO_RISE = 'none'
LITTLE_RISE = 'a little'
BIG_RISE = 'a lot'
RISES = (NO_RISE, LITTLE_RISE, BIG_RISE)
# How far a line's loudness rises to its main note, in steps of velocity. The main note is as loud as written and the rest of the
# line softer, since a note written at full loudness has nowhere to rise to.
RISE_DEPTHS = {NO_RISE: 0, LITTLE_RISE: 10, BIG_RISE: 22}
# Where a line's first note and its last note sit on the rise, whose top is the main note at 1: the last note lowest.
FIRST_NOTE_PART = Rational(-2, 5)
LAST_NOTE_PART = Rational(-4, 5)
# A note that starts a bar is a little louder still, by this part of the rise.
BAR_START_PART = Rational(1, 5)
# How the notes inside a line are joined.
CHOPPY_NOTES = 'choppy'
NOTES_AS_WRITTEN = 'as written'
FLOWING_NOTES = 'flowing'
JOINS = (CHOPPY_NOTES, NOTES_AS_WRITTEN, FLOWING_NOTES)
# Choppy: a note up to this long sounds for half of itself, and a longer note gives up an eighth.
LONGEST_HALVED_NOTE = QUARTER
# Flowing: a note held up to a note of its own pitch stops this far short, so that the second is heard to start.
GAP_BEFORE_SAME_PITCH = Rational(1, 32)
# The parts of a bar a line's main note may start on: the bar's start and its middle.
PARTS_OF_BAR = 2
# What stands for the pitch of a sound that has none of its own to compare.
NO_PITCH = -1


class Phrasing(ClipGenerator):
    """Delivers a clip's tune in lines: the notes of each line joined, a breath after the line, and the line's loudness rising to its main note."""

    __slots__ = ('_line', '_bar', '_breath', '_rise', '_join')

    def __init__(self, *, line, bar, breath, rise, join, continuation=None):
        # How long a line and a bar last, in whole notes.
        self._line = line
        self._bar = bar
        self._breath = breath
        self._rise = rise
        self._join = join

    def _generate(self, clip):
        voiced = _voiced(clip.resolved_sounds())
        for line in self._lines_of(voiced):
            self._join_notes(line)
            self._take_breath(line)
            self._shape_loudness(line)
        sounds = []
        for part in voiced:
            sounds += part.sounds()
        return sounds, clip.get_length()

    def _lines_of(self, voiced):
        """Return the notes of each line that has any, in order: a note belongs to the line it starts in."""
        lines = {}
        for part in voiced:
            if part.is_note():
                lines.setdefault(int(part.start // self._line), []).append(part)
        return [lines[number] for number in sorted(lines)]

    def _join_notes(self, line):
        """Make a line's notes choppy or flowing: all but its last note when flowing, which the breath follows."""
        if self._join == CHOPPY_NOTES:
            for part in line:
                part.heard = part.heard / 2 if part.heard <= LONGEST_HALVED_NOTE else part.heard - EIGHTH
        elif self._join == FLOWING_NOTES:
            for part, after in zip(line, line[1:]):
                reach = after.start - part.start
                if reach > part.heard:
                    part.heard = reach - GAP_BEFORE_SAME_PITCH if after.pitch() == part.pitch() else reach

    def _take_breath(self, line):
        """Shorten a line's last note for the breath after the line, by no more than the note can spare and by nothing where the tune already rests or the note sounds on into the next line."""
        last = line[-1]
        line_end = (last.start // self._line + 1) * self._line
        silence = line_end - (last.start + last.heard)
        wanted = BREATH_LENGTHS[self._breath] - silence
        if silence >= 0 and wanted > 0:
            last.heard -= min(wanted, last.heard * MOST_OF_A_NOTE_BREATHED)

    def _shape_loudness(self, line):
        """Make a line rise to its main note and fall away: its main note as loud as written, the notes before it softer the earlier they come, the notes after it softer still, the last lowest, and a note that starts a bar a little louder than its place gives."""
        depth = RISE_DEPTHS[self._rise]
        if not depth:
            return
        main = self._main_note(line)
        first = line[0].start
        last = line[-1].start
        for part in line:
            if part.start <= main.start:
                share = _share(start=part.start, first=first, last=main.start)
                height = FIRST_NOTE_PART + (1 - FIRST_NOTE_PART) * share
            else:
                share = _share(start=part.start, first=main.start, last=last)
                height = 1 + (LAST_NOTE_PART - 1) * share
            if (part.start / self._bar).is_whole():
                height += BAR_START_PART
            part.louder_by(round((height - 1) * depth))

    def _main_note(self, line):
        """Return the note a line grows toward: its longest note that starts on a bar's start or middle in the line's second half, the higher and then the later of two as long; else the longest of that half, else of the line."""
        middle = (line[0].start // self._line) * self._line + self._line / 2
        late = [part for part in line if part.start >= middle]
        strong = [part for part in late if (part.start / (self._bar / PARTS_OF_BAR)).is_whole()]
        return max(strong or late or line, key=_weight)


class _Part:
    """One sound of a clip while it is phrased: where it starts, how long its place is and how long it is heard, in whole notes."""

    __slots__ = ('start', 'place', 'heard', 'sound')

    def __init__(self, *, start, sound):
        self.start = start
        self.place = Length.rational(sound[LENGTH])
        self.sound = sound[HELD_SOUND] if sound[KIND] == HELD else sound
        self.heard = Length.rational(self.sound[LENGTH])

    def is_note(self):
        """Return whether the sound is a note or a chord of them, which phrasing changes; a rest and a phrase are left as they are."""
        return self.sound[KIND] in (NOTE, CHORD)

    def pitch(self):
        """Return the highest pitch that sounds, to tell a note from the note after it."""
        if self.sound[KIND] == CHORD:
            return max((note[MIDI] for note in self.sound[NOTES] if note[KIND] == NOTE), default=NO_PITCH)
        return self.sound[MIDI]

    def louder_by(self, steps):
        """Change how loud the sound is by steps of velocity, held to what MIDI allows; a note with no loudness of its own is left."""
        if self.sound[KIND] == CHORD:
            self.sound = Sound.chord([_louder(note=note, steps=steps) for note in self.sound[NOTES]])
        else:
            self.sound = _louder(note=self.sound, steps=steps)

    def sounds(self):
        """Return the sounds that take this one's place: itself as heard, held where it outlasts its place and followed by a rest where it stops short."""
        if not self.is_note():
            return [Sound.with_length(self.sound, Length.of(self.place))] if self.sound[KIND] in (REST, PHRASE) else [self._as_placed(self.sound)]
        played = _lasting(sound=self.sound, heard=self.heard)
        if self.heard == self.place:
            return [played]
        if self.heard > self.place:
            return [Sound.held(played, Length.of(self.place))]
        return [played, Sound.rest(Length.of(self.place - self.heard))]

    def _as_placed(self, sound):
        """Return a sound phrasing does not change, in its place: held again where it was held."""
        return sound if self.heard == self.place else Sound.held(sound, Length.of(self.place))


def _voiced(sounds):
    """Return each sound of a clip as a part, with the time it starts at from the clip's start."""
    parts = []
    now = ZERO
    for sound in sounds:
        parts.append(_Part(start=Length.rational(now), sound=sound))
        now = Length.add(now, sound[LENGTH])
    return parts


def _share(*, start, first, last):
    """Return how far a time is from a first time to a last, from 0 to 1, which is 1 where the two are one time."""
    return Rational(1) if last == first else (start - first) / (last - first)


def _weight(part):
    """Return what makes one note more a line's main note than another: its length, then its pitch, then how late it starts."""
    return (part.heard, part.pitch(), part.start)


def _lasting(*, sound, heard):
    """Return a note or a chord heard for a time, a chord's shorter notes no longer than that."""
    length = Length.of(heard)
    if sound[KIND] == CHORD:
        return Sound.chord([Sound.with_length(note, length) for note in sound[NOTES]])
    return Sound.with_length(sound, length)


def _louder(*, note, steps):
    """Return a note louder or softer by steps of velocity, within what MIDI allows; any other sound, and a note with no loudness yet, as it is."""
    if note[KIND] != NOTE or note[VELOCITY] is None:
        return note
    velocity = max(MIN_VELOCITY, min(MAX_VELOCITY, note[VELOCITY] + steps))
    return Sound.note(length=note[LENGTH], midi=note[MIDI], velocity=velocity, glide=note[GLIDE], name=note[NAME])
