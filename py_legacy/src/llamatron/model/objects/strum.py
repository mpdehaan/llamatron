# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Strum: a chord's notes sounding one after another, as a guitarist's pick crosses the strings. A Guitarify in Strum mode gives
its strum, which the Realizer plays at the very end of a clip, after its chains and its shapes (engine/timing/strum_plan.py)."""

from typing import NamedTuple


class StrumValues(NamedTuple):
    """A strum with every part filled in: its direction, its spread in milliseconds, its fade and loose timing as percentages, and
    how many top notes an upstroke catches, or None for all."""

    direction: str
    milliseconds: int
    fade: int
    loose_timing: int
    upstroke_count: object
