# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A row's clock: how many seconds into a row a moment of its music falls, at the row's tempo and every change of tempo inside it.

A row with one tempo is one multiplication, as it always was. A row whose scene ramps its tempo
holds a tempo for each beat of the ramp, and a moment is found among them.
"""

from bisect import bisect_right

from llamatron.support.rational import Rational

# What a tempo counts, quarter notes per minute, and the seconds in a minute.
QUARTERS_PER_WHOLE = 4
SECONDS_PER_MINUTE = 60
ROW_START = 0.0


def seconds_per_whole(tempo):
    """Return how long a whole note lasts, in seconds, at a tempo in quarter notes per minute."""
    return QUARTERS_PER_WHOLE * SECONDS_PER_MINUTE / tempo


class RowClock:
    """The tempos of one row in order, each from a time in whole notes counted from the row's start, the first from the start itself."""

    __slots__ = ('_starts', '_seconds', '_wholes')

    def __init__(self, tempos):
        # When each tempo starts, in whole notes and in seconds, and the seconds a whole note takes at it.
        self._starts = []
        self._seconds = []
        self._wholes = []
        seconds = ROW_START
        for start, tempo in tempos:
            start = float(start)
            if self._starts:
                seconds += (start - self._starts[-1]) * self._wholes[-1]
            self._starts.append(start)
            self._seconds.append(seconds)
            self._wholes.append(seconds_per_whole(tempo))

    def has_one_tempo(self):
        return len(self._starts) == 1

    def seconds_at(self, time):
        """Return how many seconds into the row a time in whole notes falls."""
        if len(self._starts) == 1:
            # A Rational's parts are divided here, as float() of it does, without the call: a score asks this about 600,000 times. The
            # player asks with a float too.
            if type(time) is Rational:
                return time.numerator / time.denominator * self._wholes[0]
            return float(time) * self._wholes[0]
        time = float(time)
        place = max(bisect_right(self._starts, time) - 1, 0)
        return self._seconds[place] + (time - self._starts[place]) * self._wholes[place]

    def whole_at(self, seconds):
        """Return how many whole notes into the row a moment in seconds falls, the other way round from seconds_at."""
        if len(self._starts) == 1:
            return seconds / self._wholes[0]
        place = max(bisect_right(self._seconds, seconds) - 1, 0)
        return self._starts[place] + (seconds - self._seconds[place]) / self._wholes[place]

    def seconds_per_whole_at(self, seconds):
        """Return how long a whole note lasts at a moment of the row, in seconds."""
        return self._wholes[max(bisect_right(self._seconds, seconds) - 1, 0)]
