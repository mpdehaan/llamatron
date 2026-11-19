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

"""Interplay: what an instrument's lead plays in a section where another lead, most often a singer, has the tune.

The lines are made from the tune's own lines, so that the instrument plays where the tune leaves room: a fill starts once
the tune's last note of a line has landed, and ends with the line."""

import random

from llamatron.macro_composer import melody
from llamatron.macro_composer.melody import StepWalk, chord_notes, nearest_chord_rung
from llamatron.macro_composer import notation

# What a player beside the tune does in a section.
WAITS = 'waits'
FILLS = 'fills between lines'
ANSWERS = 'answers every line'
DOUBLES = 'plays the hook with the tune'
RIFF = 'plays a riff under the tune'
WAYS = (WAITS, FILLS, ANSWERS, DOUBLES, RIFF)
# The ways drawn anew each time a section returns, so that a second verse's fills are not the first's.
DRAWN_ANEW = (FILLS, ANSWERS)
# How busy the fills, the answers and the riff are.
LEAST_BUSY = 0
MOST_BUSY = 20
USUAL_BUSY = 8
# A fill's and a riff's shortest note is this share of a bar, and a fill shorter than this many of them is left out.
NOTES_IN_BAR = 8
SHORTEST_FILL = 2
# A fill, where an answer takes all the room there is, lasts at most this share of a bar and comes at the end of every so many lines.
FILL_SHARE_OF_BAR = 2
FILL_EVERY = 2
# A fill starts this far up the ladder from home, so that it sits over the tune and not on it.
FILL_STARTS = (2, 3, 4)
# What a line's fill is seeded by: the song's seed, how busy, the section, and the line's place, so that every place of the gauge is heard.
FILL_SEED = 'fill {} {} {} {}'
RIFF_SEED = 'riff {} {}'
# How likely each place of a riff's bar sounds: a quarter of the time at the least busy and three quarters at the most; its first place always sounds.
RIFF_CHANCES = 40
RIFF_LEAST = 10
# A riff sits this far down the ladder from home, under the tune.
RIFF_BELOW = 2


def room_in(line):
    """How many steps at the end of a line the tune leaves: its rests there, and its last note but for the step the note lands on.
    A line the tune is silent through is all room."""
    room = 0
    for note in reversed(line):
        if notation.REST in note:
            room += note[notation.REST]
            continue
        return room + note[notation.STEPS] - 1
    return room


def steps_in(line):
    return sum(note.get(notation.REST, note.get(notation.STEPS, 0)) for note in line)


def lengths_of(*, steps, unit, busy):
    """The lengths of a fill's notes, in steps: more and shorter notes the busier, the last note taking what is left over."""
    places = steps // unit
    count = max(1, min(places, round(places * (busy + 1) / (MOST_BUSY + 1))))
    each = places // count
    lengths = [each * unit] * count
    lengths[-1] += steps - sum(lengths)
    return lengths


class UnderLead:
    """What one instrument plays under a tune through a song: asked for a section's lines, given the tune's."""

    __slots__ = ('_busy', '_walk', '_ladder', '_home', '_grid', '_scale_type', '_seed')

    def __init__(self, *, busy, habits, grid, scale_type, seed):
        self._busy = busy
        self._grid = grid
        self._scale_type = scale_type
        self._seed = seed
        self._walk = StepWalk(habits=habits, chords=[], scale_type=scale_type, seed=seed, answers=True)
        self._ladder = self._walk.ladder()
        self._home = self._walk.home()

    def unit(self):
        """The shortest note, in steps."""
        return max(1, self._grid // NOTES_IN_BAR)

    def lines(self, *, way, tune, chords, section):
        """A section's lines beside its tune's lines, each as long as the tune's, played a way: the riff, the tune itself, or fills
        or answers where the tune leaves room."""
        if way == RIFF:
            return [self.riff_line(chords=self.chords_under(chords=chords, tune=tune, count=count)) for count, line in enumerate(tune)]
        if way == DOUBLES:
            return [[dict(note) for note in line] for line in tune]
        every = 1 if way == ANSWERS else FILL_EVERY
        made = []
        for count, line in enumerate(tune):
            wanted = (count + 1) % every == 0 or count == len(tune) - 1
            under = self.chords_under(chords=chords, tune=tune, count=count)
            made.append(self.filled(way=way, line=line, chord=under[-1], dice=random.Random(FILL_SEED.format(self._seed, self._busy, section, count))) if wanted else [{notation.REST: steps_in(line)}])
        return made

    def chords_under(self, *, chords, tune, count):
        """The chord under each bar of a line of the tune."""
        before = sum(steps_in(line) for line in tune[:count]) // self._grid
        return [chords[(before + bar) % len(chords)] for bar in range(max(1, steps_in(tune[count]) // self._grid))]

    def filled(self, *, way, line, chord, dice):
        """A line that is silent until the tune leaves room, and then a short run that ends on a note of the chord."""
        whole = steps_in(line)
        unit = self.unit()
        room = room_in(line) // unit * unit
        if way != ANSWERS:
            room = min(room, self._grid // FILL_SHARE_OF_BAR)
        if room < SHORTEST_FILL * unit:
            return [{notation.REST: whole}]
        lengths = lengths_of(steps=room, unit=unit, busy=self._busy)
        place = self._walk.within(self._home + dice.choice(FILL_STARTS))
        notes = []
        for count, steps in enumerate(lengths):
            if count:
                place = self._walk.within(place + dice.choice(melody.MOVES))
            if count == len(lengths) - 1:
                place = nearest_chord_rung(ladder=self._ladder, place=place, wanted=chord_notes(chord=chord, scale_type=self._scale_type))
            notes.append({**self._ladder[place][1], notation.STEPS: steps})
        return ([{notation.REST: whole - room}] if whole > room else []) + notes

    def riff_bar(self):
        """The riff's one bar, the same through the song: for each place of the bar, how far up the chord its note is, or None for a place that is silent or held through."""
        dice = random.Random(RIFF_SEED.format(self._seed, self._busy))
        return [dice.choice((0, 0, 1, 2)) if place == 0 or dice.randrange(RIFF_CHANCES) < RIFF_LEAST + self._busy else None for place in range(self._grid // self.unit())]

    def riff_line(self, *, chords):
        """The riff under a line of the tune, a bar at a time, its notes those of the chord under the bar, low on the ladder."""
        unit = self.unit()
        bar = self.riff_bar()
        notes = []
        for chord in chords:
            wanted = chord_notes(chord=chord, scale_type=self._scale_type)
            low = self._walk.within(self._home - RIFF_BELOW)
            rungs = [place for place in range(low, len(self._ladder)) if self._ladder[place][0] % melody.NOTES_IN_OCTAVE in wanted] or [low]
            for up in bar:
                if up is None and notes and notation.STEPS in notes[-1]:
                    notes[-1][notation.STEPS] += unit
                elif up is None:
                    notes.append({notation.REST: unit})
                else:
                    notes.append({**self._ladder[rungs[min(up, len(rungs) - 1)]][1], notation.STEPS: unit})
            left = self._grid - unit * len(bar)
            if left:
                notes.append({notation.REST: left})
        return notes
