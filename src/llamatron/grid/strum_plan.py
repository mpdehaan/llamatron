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
"""How a finished clip strums its chords, worked out by the renderer and played by the exporters' timing (exporters/timing.py)."""

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
