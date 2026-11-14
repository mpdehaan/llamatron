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
"""The grid an editor of steps draws: a label column and a cell per step on screen, scrolling sideways, which the one-row editors and the chord editor share."""

from rich.text import Text

from llamatron.tui.drawing import Align, Box, fit, SPACE, Style

LABEL_WIDTH = 8
GRID_MARGIN = 4


class StepGrid:
    """Draws a StepEditor's steps as a grid. A page of this kind names CELL_WIDTH, how wide a cell is drawn."""

    __slots__ = ()

    CELL_WIDTH = None

    # Drawing: the grid is a label column and one cell per step shown.

    def steps_shown(self, width):
        """Return how many steps fit across the screen."""
        return max((width - LABEL_WIDTH - GRID_MARGIN) // (self.CELL_WIDTH + 1), 1)

    def scroll_to_cursor(self, width):
        """Move the window of steps so that the cursor's step is on it, and return its first and last steps (the last excluded)."""
        return self.window_of_steps(self.steps_shown(width))

    def grid_rule(self, *, left, middle, right, count):
        """Return a rule above, below or across the grid: the label column, then one cell per step shown."""
        cells = [Box.RULE * self.CELL_WIDTH] * count
        return Text(left + Box.RULE * LABEL_WIDTH + middle + middle.join(cells) + right, style=Style.DIM, no_wrap=True)

    def grid_line(self, *, label, cells, selected=None, bold=False):
        """Return one line of the grid: its label and a cell per step, the selected one in reverse video."""
        line = Text(Box.BAR + fit(text=label, width=LABEL_WIDTH) + Box.BAR, no_wrap=True)
        for place, text in cells:
            style = Style.REVERSE if place == selected else (Style.BOLD if bold else Style.PLAIN)
            line.append(fit(text=text, width=self.CELL_WIDTH, align=Align.CENTER), style=style)
            line.append(Box.BAR)
        return line

    def with_steps_shown(self, *, text, style, width, first, last):
        """Return a line above the grid, with which steps are on screen dim at its right when the row is wider than the screen."""
        shown = self.steps_shown_text(first=first, last=last)
        if not shown:
            return Text(text, style=style)
        line = Text(fit(text=text, width=width - len(shown) - 1) + SPACE, style=style, no_wrap=True)
        line.append(shown, style=Style.DIM)
        return line
