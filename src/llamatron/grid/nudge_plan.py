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
"""How a finished clip's notes are rushed early or dragged late, worked out by the renderer from the Rush and Drag generators its chains name and played by the exporters' timing (exporters/timing.py), on top of the groove."""

import math
from typing import NamedTuple

from llamatron.support.rational import Rational

PERCENT = 100


class MovingRow(NamedTuple):
    """One Rush's or Drag's row: its steps, each on or off, how long each step is in whole notes, how far a note on a step that's on moves as a share of a step, later for a drag and earlier for a rush, and how far into its run the clip starts."""

    steps: list
    step: object
    amount: object
    offset: object

    def moved(self, time):
        """Return how much later a note starting at a time from the clip's start plays by this row, early being less than nothing."""
        return self.step * self.amount if self.steps[math.floor((time + self.offset) / self.step) % len(self.steps)] else 0


class NudgePlan(NamedTuple):
    """A clip's rushes and drags together: every row its chains name, each moving the notes starting on its steps that are on, the moves added up, so that a step that both rushes and drags moves by the difference."""

    rows: list

    def moved(self, time):
        """Return how much later a note starting at a time from the clip's start plays, early being less than nothing."""
        return sum((row.moved(time) for row in self.rows), Rational(0))


def amount_moved(*, percent, later):
    """Return how far a row moves a note, as a signed share of a step: later for a drag, earlier for a rush."""
    share = Rational(percent, PERCENT)
    return share if later else -share
