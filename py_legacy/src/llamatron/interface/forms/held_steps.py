# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How far a held [ or ] steps a gauge: a key held down repeats, and the repeats come close together, so a run of presses each
soon after the last, on one field, steps by more and more, and a pause or another field starts again at one."""

import time

# Presses closer together than this are one key held down; the keyboard repeats about every 30 to 50 ms.
HELD_SECONDS = 0.12
# After how many repeats a held key steps by how many times as much.
SPEEDS = ((40, 10), (25, 5), (12, 2))


class HeldSteps:
    """The run of presses on one field, and when the last came, by a clock in seconds that tests may give."""

    __slots__ = ('_label', '_last', '_presses', '_clock')

    def __init__(self, *, clock=time.monotonic):
        self._label = None
        self._last = None
        self._presses = 0
        self._clock = clock

    def times(self, label):
        """Note a press on the field of a label, and return how many times its step it moves: one until the key has been held
        a while, then more."""
        now = self._clock()
        if label == self._label and self._last is not None and now - self._last < HELD_SECONDS:
            self._presses += 1
        else:
            self._presses = 0
        self._label = label
        self._last = now
        for presses, speed in SPEEDS:
            if self._presses >= presses:
                return speed
        return 1
