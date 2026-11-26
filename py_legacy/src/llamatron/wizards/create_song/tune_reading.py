# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A pattern read back as a tune's lines, with the octave and the velocity its notes are written against, so that a tune a
person wrote in the pattern editor can be given back to the song wizard."""

from collections import Counter

from llamatron.music_theory.composing import notation
from llamatron.user_strings import errors


def commonest(values):
    """Return the commonest of values, leaving out nothing."""
    present = [value for value in values if value is not None]
    counts = Counter(present)
    most = counts.most_common(1)
    value, _ = most[0]
    return value


def plainest_velocity(loud):
    """Return the velocity a tune is written against: the one from which the most notes are plain or a stress, the commonest of those."""
    present = [value for value in loud if value is not None]
    counts = Counter(present)
    said = {base: _notes_plain_or_stressed(counts=counts, base=base) for base in counts}
    return max(counts, key=lambda base: (said[base], counts[base]))


def tune_lines(*, pattern, bar, velocities=None):
    """Return a pattern as a tune's lines, with the octave and velocity the notes are written against; velocities stands in
    for the pattern's own."""
    reading = PatternAsTune(pattern=pattern, velocities=velocities)
    return reading.lines(bar=bar)


class PatternAsTune:
    """A pattern read back as a tune's lines: its rows, the octave and velocity its notes are written against, and each rest
    and note in turn, a line ending at a rest or once it is long enough at a bar's start."""

    __slots__ = ('_pattern', '_steps', '_degree', '_accidental', '_octaves', '_tie', '_loud', '_octave', '_velocity')

    def __init__(self, *, pattern, velocities):
        steps = pattern[notation.STEPS]
        empty = [None] * steps
        self._pattern = pattern
        self._steps = steps
        self._degree = pattern[notation.DEGREE]
        self._accidental = pattern.get(notation.ACCIDENTAL) or empty
        self._octaves = pattern.get(notation.OCTAVE) or empty
        self._tie = pattern.get(notation.TIE) or [False] * steps
        self._loud = velocities or pattern.get(notation.VELOCITY) or empty
        if not _holds_a_value(self._degree) or not _holds_a_value(self._loud):
            raise notation.NotWritable(errors.ERR_NOT_A_TUNE)
        self._octave = commonest(self._octaves)
        self._velocity = plainest_velocity(self._loud)

    def lines(self, *, bar):
        """Return the tune's lines, the octave and the velocity its notes are written against."""
        lines = [[]]
        started = 0
        place = 0
        while place < self._steps:
            if self._degree[place] is None:
                end = self._end_of(place=place, tied=False)
                lines[-1].append({notation.REST: end - place})
                if end < self._steps:
                    lines.append([])
                    started = end
            else:
                if lines[-1] and place % bar == 0 and place - started >= notation.LONGEST_LINE_IN_BARS * bar:
                    lines.append([])
                    started = place
                end = self._end_of(place=place, tied=True)
                lines[-1].append(self._note(place=place, end=end))
            place = end
        kept = [line for line in lines if line]
        return kept, self._octave, self._velocity

    def _end_of(self, *, place, tied):
        """Return the step after a rest or a note that starts at a place: a rest runs on over empty steps that are not tied, and
        a note over empty steps that are."""
        end = place + 1
        while end < self._steps and self._degree[end] is None and bool(self._tie[end]) == tied:
            end += 1
        return end

    def _note(self, *, place, end):
        """Return the note at a place, lasting until end, written against the tune's octave and velocity."""
        note = {notation.DEGREE: self._degree[place], notation.STEPS: end - place}
        if self._octaves[place] != self._octave:
            note[notation.OCTAVE] = self._octaves[place] - self._octave
        if self._accidental[place]:
            note[notation.ACCIDENTAL] = notation.ACCIDENTAL_WORDS[self._accidental[place]]
        move = self._loud[place] - self._velocity
        if move in notation.STRESS_OF_MOVE:
            note[notation.STRESS] = notation.STRESS_OF_MOVE[move]
        elif move:
            note[notation.VELOCITY] = self._loud[place]
        for name in notation.OTHER_ROWS:
            row = self._pattern.get(name)
            if row and row[place] is not None:
                note[name] = row[place]
        return note


def _holds_a_value(values):
    """Return whether a row holds any value but nothing."""
    for value in values:
        if value is not None:
            return True
    return False


def _notes_plain_or_stressed(*, counts, base):
    """Return how many notes are plain or a stress against a velocity, from how many notes there are at each velocity."""
    total = 0
    for value, count in counts.items():
        if value == base or value - base in notation.STRESS_OF_MOVE:
            total += count
    return total
