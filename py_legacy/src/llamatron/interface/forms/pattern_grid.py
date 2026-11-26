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


# The piano roll's rows. How a row's label is drawn where it is neither the cursor's nor a degree's in range: dim.
DIM_LABEL = 'dim label'
# The column of a cell that holds a note's mark, its sharp, flat or G, in the middle, or the bar's last column when the bar is
# shorter, and how wide the edge before each step is.
MARK_COLUMN = CELL_WIDTH // 2
EDGE_WIDTH = 1
# What stands at a step's left edge on the roll: the divider, a double one at a beat; a note's bar running through, solid or
# hollow; a chord's added note's thin line running through; or one of the cursor's double bars.
DIVIDER_EDGE = 'divider'
NOTE_EDGE = 'note edge'
HOLLOW_EDGE = 'hollow edge'
GHOST_EDGE = 'ghost edge'
CURSOR_EDGE = 'cursor edge'
# What a cell of the roll holds: a note's bar, a chord's added note's thin line, nothing, or a place outside the track's range.
NOTE_CELL = 'note'
GHOST_CELL = 'ghost'
EMPTY_CELL = 'empty'
OUT_OF_RANGE_CELL = 'out of range'


@dataclass(frozen=True, slots=True, kw_only=True)
class RollCell:
    """One cell of the piano roll: what it holds; for a note, its mark (a sharp, flat or G) or None, and whether its bar is
    hollow, as for a note an inversion plays an octave up; how many columns a bar or line fills, fewer where the note's gate
    ends inside the step; and whether the cursor is on it."""

    kind: str
    mark: object = None
    hollow: bool = False
    columns: int = CELL_WIDTH
    selected: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class RollRow:
    """One row of the piano roll: its label and how it is drawn, each step shown as the edge before it and its cell, the
    steps that start a beat, and the edge after the last step, the grid's right border."""

    label: str
    label_kind: str
    steps: tuple = dataclass_field(default_factory=tuple)
    beats: frozenset = frozenset()
    last_edge: str = DIVIDER_EDGE


# The cells most of the roll is, made once and shared, since a row is drawn again whenever the set changes.
EMPTY = RollCell(kind=EMPTY_CELL)
EMPTY_UNDER_CURSOR = RollCell(kind=EMPTY_CELL, selected=True)
OUT_OF_RANGE = RollCell(kind=OUT_OF_RANGE_CELL)
