# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The notes a Hocket hands a clip, which the exporters' timing adds to the clip's own (exporters/timing.py)."""

from typing import NamedTuple


class HandedNote(NamedTuple):
    """One note a Hocket hands a clip from its source track: when it starts and ends, in whole notes from the clip's start, as the source plays it before any groove, and its MIDI number and velocity."""

    start: object
    end: object
    midi_number: int
    velocity: int
