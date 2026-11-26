# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The grid an editor of steps draws: a label column and a cell per step on screen, scrolling sideways, which the one-row editors and
the chord editor share, made of the forms' nodes of a grid (interface/forms/step_grid.py) and drawn by its renderer."""

from llamatron.interface.forms.step_grid import GridHeading, GridRow, GridRule
from llamatron.interface.tracker.renderers import step_grid as step_grid_renderer

GRID_MARGIN = 4


class StepGrid:
    """Draws a StepEditor's steps as a grid. A page of this kind names CELL_WIDTH, how wide a cell is drawn."""

    __slots__ = ()

    CELL_WIDTH = None

    # Drawing: the grid is a label column and one cell per step shown.

    def steps_shown(self, width):
        """Return how many steps fit across the screen."""
        return max((width - step_grid_renderer.LABEL_WIDTH - GRID_MARGIN) // (self.CELL_WIDTH + 1), 1)

    def scroll_to_cursor(self, width):
        """Move the window of steps so that the cursor's step is on it, and return its first and last steps (the last excluded)."""
        return self.window_of_steps(self.steps_shown(width))

    def grid_rule(self, *, edge, count):
        """Return a rule along or across the grid: the label column, then one cell per step shown."""
        return GridRule(edge=edge, count=count)

    def grid_line(self, *, label, cells, selected=None, bold=False):
        """Return one line of the grid: its label and a cell per step, the selected one in reverse video."""
        return GridRow(label=label, cells=tuple(cells), selected=selected, bold=bold)

    def with_steps_shown(self, *, text, first, last, dim=False, bold=False):
        """Return the line over the grid, with which steps are on screen at its right when the row is wider than the screen."""
        return GridHeading(text=text, dim=dim, bold=bold, steps_shown=self.steps_shown_text(first=first, last=last))

    def drawn(self, *, lines, width):
        """Return the grid's lines as the tracker draws them, a line that is no node of a grid as it was drawn."""
        return step_grid_renderer.grid_lines(lines=lines, cell_width=self.CELL_WIDTH, width=width)
