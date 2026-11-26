# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a table of statements is drawn: a grid of five columns, each as wide as its widest value with a space each side and the
picker's mark, its lines' cells between bars, a rule under each line, and the grid's top and bottom edges.
"""

from rich.text import Text

from llamatron.interface.forms import statement_rows
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Box, cursor_mark, padded, Style
from llamatron.user_strings import legends, marks

# How wide each column of the grid is inside its bars: the widest value a cell of it shows, a space each side, the picker's
# mark and a space after it.
CELL_WIDTHS = [len(padded(drawing.NOTHING)) + len(padded(marks.MSG_PICKER_MARK)) - 1 + width for width in statement_rows.PART_WIDTHS]


def first_statement_row_lines(row, *, page, here, label_width, width):
    """Return the grid's top edge, the row's line of cells and the rule under it."""
    top = grid_rule(left=Box.TOP_LEFT, joint=Box.TOP_TEE, right=Box.TOP_RIGHT)
    return [top, cells_line(row, page=page, here=here), rule_under(row)]


def statement_row_lines(row, *, page, here, label_width, width):
    """Return the row's line of cells, the cell under the cursor in reverse video, and the rule under it."""
    return [cells_line(row, page=page, here=here), rule_under(row)]

def cells_line(row, *, page, here):
    """Return the line of the row's cells between the grid's bars, a column the line doesn't fill left blank."""
    line = Text(cursor_mark(here), no_wrap=True)
    line.append(Box.BAR)
    for place, cell_width in enumerate(CELL_WIDTHS):
        line.append_text(cell_text(row, page=page, here=here, place=place).copy())
        line.append(drawing.SPACE * (cell_width - cell_text(row, page=page, here=here, place=place).cell_len))
        line.append(Box.BAR)
    return line

def cell_text(row, *, page, here, place):
    """Return what a cell of the row shows: its value, padded, in reverse video under the cursor, and the picker's mark where
    it opens a list; nothing in a column the line doesn't fill."""
    text = Text(no_wrap=True)
    if place >= len(row.cells):
        return text
    cell = row.cells[place]
    on_cell = here and place == min(page.cell, len(row.cells) - 1)
    text.append(padded(str(cell.value()).rstrip()), style=Style.REVERSE if on_cell else Style.PLAIN)
    if cell.enter_what == legends.What.CHOOSE:
        text.append(marks.MSG_PICKER_MARK, style=Style.DIM)
    return text

def rule_under(row):
    """Return the rule under the row: between rows, or the grid's bottom edge under the last."""
    if row.last:
        return grid_rule(left=Box.BOTTOM_LEFT, joint=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT)
    return grid_rule(left=Box.LEFT_TEE, joint=Box.CROSS, right=Box.RIGHT_TEE)


def grid_rule(*, left, joint, right):
    """Return a rule across the grid of statements, with its ends and the joints where the columns' bars meet it."""
    rule = left + joint.join(Box.RULE * width for width in CELL_WIDTHS) + right
    return Text(drawing.INDENT + rule, no_wrap=True)
