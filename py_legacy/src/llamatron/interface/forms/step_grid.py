# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A grid of steps, as plain nodes with nothing of how it is drawn: the line over it, its rules and its rows, a label and a
cell per step on screen, which the one-row editors and the chord editor are made of. The tracker draws them
(interface/tracker/renderers/step_grid.py), the only code that knows how they look; a line that is not a node passes through
as it was drawn."""

from dataclasses import dataclass, field as dataclass_field

# Where a rule runs: along the grid's top edge, across it between two groups of rows, or along its bottom edge.
TOP = 'top'
ACROSS = 'across'
BOTTOM = 'bottom'
NO_TEXT = ''


@dataclass(frozen=True, slots=True, kw_only=True)
class GridHeading:
    """The line over a grid: its words, drawn dim or bold, and which steps are on screen, said dim at its right where the row
    is wider than the screen, or NO_TEXT where every step shows."""

    text: str
    dim: bool = False
    bold: bool = False
    steps_shown: str = NO_TEXT


@dataclass(frozen=True, slots=True, kw_only=True)
class GridRule:
    """A rule along or across the grid: where it runs, and how many steps' cells it crosses."""

    edge: str
    count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class GridRow:
    """One line of the grid: its label, and a cell per step on screen, each (step, text); the selected step's cell, or None,
    and whether the row is drawn bold."""

    label: str
    cells: tuple = dataclass_field(default_factory=tuple)
    selected: object = None
    bold: bool = False
