# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker draws a grid of steps (interface/forms/step_grid.py): its heading with the steps on screen at its right, its
rules in box characters, and its rows, a label column and a cell per step, the selected cell in reverse video."""

from rich.text import Text

from llamatron.interface.forms import step_grid
from llamatron.interface.forms.step_grid import GridHeading, GridRow, GridRule
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Align, Box, fit, Style

LABEL_WIDTH = 8
# The box characters at the left, between cells and at the right of each kind of rule.
RULE_JOINTS = {
    step_grid.TOP: (Box.TOP_LEFT, Box.TOP_TEE, Box.TOP_RIGHT),
    step_grid.ACROSS: (Box.LEFT_TEE, Box.CROSS, Box.RIGHT_TEE),
    step_grid.BOTTOM: (Box.BOTTOM_LEFT, Box.BOTTOM_TEE, Box.BOTTOM_RIGHT),
}


def grid_lines(*, lines, cell_width, width):
    """Return a grid's lines drawn at a width, each node as it looks and any other line as it was drawn."""
    return [grid_line(line=line, cell_width=cell_width, width=width) for line in lines]


def grid_line(*, line, cell_width, width):
    """Return one line of a grid drawn, by the drawer of its kind of node, or as it was drawn where it is no node of a grid."""
    drawer = DRAWERS.get(type(line))
    if drawer is None:
        return line
    return drawer(line, cell_width=cell_width, width=width)


def _rule(rule, *, cell_width, width):
    left, middle, right = RULE_JOINTS[rule.edge]
    cells = [Box.RULE * cell_width] * rule.count
    return Text(left + Box.RULE * LABEL_WIDTH + middle + middle.join(cells) + right, style=Style.DIM, no_wrap=True)


def _row(row, *, cell_width, width):
    line = Text(Box.BAR + fit(text=row.label, width=LABEL_WIDTH) + Box.BAR, no_wrap=True)
    for place, text in row.cells:
        style = Style.REVERSE if place == row.selected else (Style.BOLD if row.bold else Style.PLAIN)
        line.append(fit(text=text, width=cell_width, align=Align.CENTER), style=style)
        line.append(Box.BAR)
    return line


def _heading(heading, *, cell_width, width):
    style = Style.DIM if heading.dim else (Style.BOLD if heading.bold else Style.PLAIN)
    if not heading.steps_shown:
        return Text(heading.text, style=style)
    line = Text(fit(text=heading.text, width=width - len(heading.steps_shown) - 1) + drawing.SPACE, style=style, no_wrap=True)
    line.append(heading.steps_shown, style=Style.DIM)
    return line


# The drawer of each kind of node of a grid.
DRAWERS = {GridRow: _row, GridRule: _rule, GridHeading: _heading}
