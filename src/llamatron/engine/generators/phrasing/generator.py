# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Plays a tune as a singer or a horn player would deliver it: in lines, with a breath after each, a rise and fall, and its notes choppy or flowing.

A tune written step by step fills every bar at one loudness. A player delivers it in lines,
the sentences of the tune: each line grows toward its main note and falls away, a breath
follows it, and its notes run together or stand apart. The tune's pattern stays as written:
the phrasing is made as the clip plays, so another delivery is another setting and never
another tune. No note is left out, no pitch changes and nothing is drawn by chance.
"""

from llamatron.engine.generators.base import ClipGenerator
from llamatron.engine.generators.parts import parts_of
from llamatron.math.rational import Rational

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
        voiced = parts_of(clip.resolved_sounds())
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


def _share(*, start, first, last):
    """Return how far a time is from a first time to a last, from 0 to 1, which is 1 where the two are one time."""
    return Rational(1) if last == first else (start - first) / (last - first)


def _weight(part):
    """Return what makes one note more a line's main note than another: its length, then its pitch, then how late it starts."""
    return (part.heard, part.pitch(), part.start)
