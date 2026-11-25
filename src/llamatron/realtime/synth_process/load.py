# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How busy the built-in synths are, shared between processes: the synth daemon reports its load twice a second to the
sender process that owns it, which writes it here, in a small block of shared memory the tracker made, and the tracker
reads it as it draws the screen, so that no report crosses the sender's pipe, which carries only answers.
"""

from typing import NamedTuple

LOAD = 0
PEAK = 1
VOICES = 2
DROPOUTS = 3
LATE_NOTES = 4
REPORTED = 5
SLOTS = 6
DOUBLE = 'd'


class LoadReport(NamedTuple):
    """The daemon's last report: the share of the time its audio thread was busy, its longest chunk's share of the chunk's
    time, its sounding voices, the dropouts and the late notes since it started."""

    load: float
    peak: float
    voices: int
    dropouts: int
    late_notes: int


class SharedLoad:
    """The shared block: made by the tracker with its spawn context, handed to the sender process, written by the sender's
    reader of the daemon, read by the tracker."""

    __slots__ = ('_values',)

    def __init__(self, *, context):
        self._values = context.Array(DOUBLE, SLOTS, lock=False)

    def write(self, report):
        """Keep a report as the daemon gives it, a mapping of its names."""
        values = self._values
        values[LOAD] = report.get('load', 0.0)
        values[PEAK] = report.get('peak', 0.0)
        values[VOICES] = report.get('voices', 0)
        values[DROPOUTS] = report.get('dropouts', 0)
        values[LATE_NOTES] = report.get('late_notes', 0)
        values[REPORTED] = 1.0

    def read(self):
        """Return the last report, or None before the first."""
        values = self._values
        if not values[REPORTED]:
            return None
        return LoadReport(load=values[LOAD], peak=values[PEAK], voices=int(values[VOICES]), dropouts=int(values[DROPOUTS]), late_notes=int(values[LATE_NOTES]))
