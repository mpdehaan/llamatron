# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a finished clip strums its chords, worked out by the Realizer and played by the exporters' timing (engine/timing/timing.py)."""

from typing import NamedTuple


class StrumPlan(NamedTuple):
    """A clip's strum in the grid's own terms: its direction; the gap between two strings in whole notes, at its scene's tempo; its fade and loose timing as percentages; how many top notes an upstroke catches, or None for all; how long a beat lasts, for a direction by the beat; the seed its loose timing draws from; and where its run stands as the clip starts."""

    direction: str
    gap: object
    fade: int
    loose_timing: int
    upstroke_count: object
    beat: object
    seed: int
    # How far into its run the clip starts, and how many chords the run strummed in the track's clips before, for a Strum generator whose Restart carries on.
    offset: object = 0
    chords_before: int = 0
