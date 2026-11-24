# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pattern editor's grid, as plain nodes with nothing of how it is drawn: its rules, the line of step numbers and the rows
view's rows, each step a column, the steps that start a beat marked, which both views of the pattern editor are made of. The
tracker draws them (interface/tracker/renderers/pattern_grid.py), the only code that knows how they look."""

from dataclasses import dataclass, field as dataclass_field

# How wide a cell of the grid is, which every value fits.
CELL_WIDTH = 5

# Where a rule runs: the grid's top and bottom edges; across the grid between rows with dividers on both sides; closing the
# dividers over a row that has none, as a section's heading, or opening them under one; unbroken between two such rows; and
# the piano roll's double rule under the step numbers.
TOP = 'top'
INNER = 'inner'
BOTTOM = 'bottom'
CLOSING = 'closing'
OPENING = 'opening'
PLAIN = 'plain'
HEADING = 'heading'
# How a row's label is drawn: plain, bold on the cursor's row, or reversed for the cursor on a section's heading.
PLAIN_LABEL = 'plain label'
BOLD_LABEL = 'bold label'
REVERSED_LABEL = 'reversed label'


@dataclass(frozen=True, slots=True, kw_only=True)
class PatternRule:
    """A rule across the grid: where it runs, the steps on screen, from first to last (the last left out), the steps that start
    a beat, whose joints are double, the step whose cell the cursor's box edges on this side, or None, and whether its joints
    are drawn at all, which a rule with no dividers on either side has none of."""

    kind: str
    first: int
    last: int
    beats: frozenset = frozenset()
    boxed: object = None
    joints: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class StepNumbers:
    """The line of step numbers over the grid: the steps on screen, the steps that start a beat, drawn bold, and the step that
    sounds now, in the read head's light, or None."""

    first: int
    last: int
    beats: frozenset = frozenset()
    sounding: object = None


@dataclass(frozen=True, slots=True, kw_only=True)
class RowLines:
    """The lines of one row of the rows view: a label for each line, each drawn as its LABEL kind says; whether the row is a
    section's heading, which has no cells; each step's cells, a text for each line, from first to last; the steps that start a
    beat; the cursor's step and line, or None; and the steps that cannot hold a value, whose marks are dim."""

    labels: tuple
    label_kinds: tuple
    heading: bool = False
    cells: tuple = dataclass_field(default_factory=tuple)
    first: int = 0
    last: int = 0
    beats: frozenset = frozenset()
    selected: object = None
    blocked: frozenset = frozenset()
