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
"""Phrasing: a tune made to breathe as it plays.

A sung line ends before its bars do, and the singer breathes; lines are not all one length,
a longer line and then a shorter; and now and then a note comes an eighth early. The tune's
pattern stays whole: the breath is cut as the clip plays, so another breath is another setting
and never another tune. No pitch changes and nothing is drawn by chance. A note that starts
where the pattern says its steps are whole, a hook's notes, is left exactly as written.
"""

from llamatron.generators.base import ClipGenerator
from llamatron.music.sound import CHORD, HELD, HELD_SOUND, KIND, LENGTH, NOTES, PHRASE, REST, Sound
from llamatron.support.length import ZERO, Length
from llamatron.support.rational import Rational

EIGHTH = Rational(1, 8)
# How long the breaths are.
NO_BREATH = 'off'
SHORT_BREATH = 'short'
MEDIUM_BREATH = 'medium'
LONG_BREATH = 'long'
BREATHS = (NO_BREATH, SHORT_BREATH, MEDIUM_BREATH, LONG_BREATH)
# The breath after a longer line and after a shorter one, in eighths.
BREATH_AFTER_LONGER = {NO_BREATH: 0, SHORT_BREATH: 2, MEDIUM_BREATH: 3, LONG_BREATH: 4}
BREATH_AFTER_SHORTER = {NO_BREATH: 0, SHORT_BREATH: 4, MEDIUM_BREATH: 5, LONG_BREATH: 6}
# Which lines are the shorter ones.
LONG_THEN_SHORT = 'long, short'
SHORT_THEN_LONG = 'short, long'
EVEN_LINES = 'even'
LINE_LENGTHS = (LONG_THEN_SHORT, SHORT_THEN_LONG, EVEN_LINES)
# How many lines of every four may have a note come early, and the order the four take one in as more are asked for.
FEWEST_EARLY = 0
MOST_EARLY = 4
EARLY_ORDER = (1, 3, 0, 2)
# A note comes early only after a note at least this many eighths long, which gives the eighth up.
EIGHTHS_GIVING_WAY = 2
# The parts of a bar a note comes early to: the bar's start and its middle.
PARTS_OF_BAR = 2


class Phrasing(ClipGenerator):
    """Ends each line of a clip early for a breath, the shorter lines sooner, and brings a note of some lines an eighth early."""

    __slots__ = ('_line', '_bar', '_breath', '_line_lengths', '_early', '_whole')

    def __init__(self, *, line, bar, breath, line_lengths, early, whole=(), continuation=None):
        # How long a line and a bar last, in whole notes.
        self._line = line
        self._bar = bar
        self._breath = breath
        self._line_lengths = line_lengths
        self._early = early
        # The stretches of the clip, as (start, end) from its start in whole notes, whose notes are left as written.
        self._whole = tuple(whole)

    def _generate(self, clip):
        placed = self._placed(clip.resolved_sounds())
        placed = self._with_breaths(placed)
        placed = self._with_early_notes(placed)
        return [sound for _, sound in placed], clip.get_length()

    def _placed(self, sounds):
        """Return each sound with the time it starts at, from the clip's start in whole notes."""
        placed = []
        now = ZERO
        for sound in sounds:
            placed.append((Length.rational(now), sound))
            now = Length.add(now, sound[LENGTH])
        return placed

    def _line_of(self, start):
        """Return which line of the clip a time is in, counted from 0."""
        return int(start // self._line)

    def _is_shorter(self, line):
        """Return whether a line is one of the shorter lines, which end in the longer breath."""
        if self._line_lengths == EVEN_LINES:
            return False
        return bool(line % 2) == (self._line_lengths == LONG_THEN_SHORT)

    def _breath_starts(self, line):
        """Return the time a line's breath begins, which is the line's end where it takes none."""
        eighths = (BREATH_AFTER_SHORTER if self._is_shorter(line) else BREATH_AFTER_LONGER)[self._breath]
        return (line + 1) * self._line - eighths * EIGHTH

    def _is_whole(self, start):
        """Return whether a sound starting at a time is left as written."""
        return any(first <= start < last for first, last in self._whole)

    def _is_left_alone(self, *, start, sound):
        return sound[KIND] in (REST, PHRASE) or self._is_whole(start)

    def _with_breaths(self, placed):
        """Return the sounds with each line's breath cut: a note that starts in the breath is a rest, and a note that sounds into the breath stops where the breath begins."""
        result = []
        for start, sound in placed:
            breath = self._breath_starts(self._line_of(start))
            if self._is_left_alone(start=start, sound=sound) or start + _sounds_for(sound) <= breath:
                result.append((start, sound))
            elif start >= breath:
                result.append((start, Sound.rest(sound[LENGTH])))
            else:
                result += _stopped(start=start, sound=sound, stop=breath)
        return result

    def _with_early_notes(self, placed):
        """Return the sounds with one note of each line that takes one brought an eighth early: the first that starts a bar or its middle, inside its line, after a note long enough to give the eighth up."""
        result = list(placed)
        moved = set()
        for place in range(1, len(result)):
            start, sound = result[place]
            before_start, before = result[place - 1]
            line = self._line_of(start)
            if line in moved or EARLY_ORDER.index(line % MOST_EARLY) >= self._early or self._line_of(before_start) != line:
                continue
            if self._is_left_alone(start=start, sound=sound) or self._is_left_alone(start=before_start, sound=before):
                continue
            if not (start / (self._bar / PARTS_OF_BAR)).is_whole() or Length.rational(before[LENGTH]) < EIGHTHS_GIVING_WAY * EIGHTH:
                continue
            result[place - 1] = (before_start, _resized(sound=before, by=-EIGHTH))
            result[place] = (start - EIGHTH, _resized(sound=sound, by=EIGHTH))
            moved.add(line)
        return result


def _sounds_for(sound):
    """Return how long a sound is heard, which for a held sound is longer than its place."""
    heard = sound[HELD_SOUND] if sound[KIND] == HELD else sound
    return Length.rational(heard[LENGTH])


def _lasting(*, sound, length):
    """Return a note, degree or chord that is heard for a length."""
    if sound[KIND] == CHORD:
        return Sound.chord([Sound.with_length(note, Length.shorter(note[LENGTH], length)) for note in sound[NOTES]])
    return Sound.with_length(sound, length)


def _stopped(*, start, sound, stop):
    """Return a sound that stops at a time, with the rest that fills what is left of its place, each with the time it starts at."""
    heard = Length.of(stop - start)
    if sound[KIND] == HELD:
        inner = _lasting(sound=sound[HELD_SOUND], length=heard)
        # A held sound that still outlasts its place stays held, and one that no longer does is a plain sound and a rest.
        if not Length.less(heard, sound[LENGTH]):
            return [(start, Sound.held(inner, sound[LENGTH]))]
        return [(start, inner), (stop, Sound.rest(Length.subtract(sound[LENGTH], heard)))]
    return [(start, _lasting(sound=sound, length=heard)), (stop, Sound.rest(Length.subtract(sound[LENGTH], heard)))]


def _resized(*, sound, by):
    """Return a sound whose place, and what is heard of it, is longer or shorter by an amount."""
    change = Length.of(abs(by))
    resize = Length.add if by > 0 else Length.subtract
    if sound[KIND] == HELD:
        inner = sound[HELD_SOUND]
        return Sound.held(_lasting(sound=inner, length=resize(inner[LENGTH], change)) if by > 0 else inner, resize(sound[LENGTH], change))
    if sound[KIND] == CHORD:
        return Sound.chord([Sound.with_length(note, resize(note[LENGTH], change)) for note in sound[NOTES]])
    return Sound.with_length(sound, resize(sound[LENGTH], change))
