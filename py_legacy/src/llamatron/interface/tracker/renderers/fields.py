# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a settings page's fields, the forms' nodes (interface/forms/), are drawn: each by what it says it is drawn as, a setting as
its label and value on one line with the cursor's mark before it, a button boxed, a heading, a row of cells, a table's row,
a draw's strip and a statement's line.
"""

from rich.text import Text

from llamatron.interface.forms import nodes, statement_rows
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.drawing import Box, cursor_mark, padded, Style
from llamatron.interface.tracker.renderers.statement_rows import first_statement_row_lines, statement_row_lines
from llamatron.user_strings import labels, legends, marks

# A strip's grid: how far in from the cursor's mark it starts, its label column's and each slot's room, wide enough for -99 with a
# space either side, and which of its five lines holds the values, where the cursor is.
STRIP_PAD = '    '
STRIP_INDENT = len(STRIP_PAD)
STRIP_LABEL_WIDTH = 7
STRIP_CELL_WIDTH = 5


def field_lines(field, *, page, here, label_width, width):
    """Return the lines a field is drawn as, the cursor on it where here is true, its label as wide as label_width."""
    return DRAWERS[field.DRAWN_AS](field, page=page, here=here, label_width=label_width, width=width)


def setting_line(field, *, page, here, label_width, width):
    """Return a setting's line: the cursor's mark, the label, bold under the cursor, and the value, with the picker's dim mark
    after a value whose Enter opens a list of choices, so that it isn't taken for one that's typed."""
    line = Text(no_wrap=True)
    line.append(cursor_mark(here))
    line.append(field.get_drawn_label(page).ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
    line.append(padded(field.value()))
    if field.enter_what == legends.What.CHOOSE:
        line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
    return [line]


def button_lines(button, *, page, here, label_width, width):
    """Return a button boxed as a page's buttons are, double-lined under the cursor: drawn so only where it stands among a tab's
    columns, since a page draws its own buttons in a row below its settings."""
    return [Text(drawing.INDENT) + line for line in button_row(buttons=[(button.key_name, button.label)], selected=0 if here else None)]


def heading_lines(heading, *, page, here, label_width, width):
    """Return a section's heading: its name after its open or closed mark, bold, and what it says of what is set inside, dim."""
    line = Text(no_wrap=True)
    line.append(cursor_mark(here))
    line.append(heading.get_drawn_label(page).ljust(label_width), style=Style.BOLD)
    line.append(padded(heading.value()), style=Style.DIM)
    return [line]


def cells_lines(row, *, page, here, label_width, width):
    """Return the row's line: its label, then its cells side by side, the cell under the cursor in reverse video as a grid's
    is, and a cell that opens a list with the picker's mark."""
    line = Text(no_wrap=True)
    line.append(cursor_mark(here))
    line.append(row.get_drawn_label(page).ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
    for place, cell in enumerate(row.cells):
        on_cell = here and place == min(page.cell, len(row.cells) - 1)
        line.append(padded(cell.value()), style=Style.REVERSE if on_cell else Style.PLAIN)
        if cell.enter_what == legends.What.CHOOSE:
            line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
        line.append(nodes.CELL_GAP)
    return [line]


def table_row_lines(row, *, page, here, label_width, width):
    """Return the row's line: its label, then each cell padded to its column's width, the cell under the cursor in reverse video."""
    line = Text(no_wrap=True)
    line.append(cursor_mark(here))
    line.append(row.get_drawn_label(page).ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
    for place, cell in enumerate(row.cells):
        on_cell = here and place == min(page.cell, len(row.cells) - 1)
        line.append(padded(cell.value()).ljust(row.widths[place] + len(padded(drawing.NOTHING))), style=Style.REVERSE if on_cell else Style.PLAIN)
        line.append(nodes.CELL_GAP)
    return [line]


def captioned_table_row_lines(row, *, page, here, label_width, width):
    """Return the caption's line, then the row's own."""
    caption = Text(no_wrap=True)
    caption.append(cursor_mark(False))
    caption.append(row.caption.ljust(label_width), style=Style.BOLD)
    for place, heading in enumerate(row.headings):
        caption.append(padded(heading).ljust(row.widths[place] + len(padded(drawing.NOTHING))), style=Style.BOLD)
        caption.append(nodes.CELL_GAP)
    return [caption, *table_row_lines(row, page=page, here=here, label_width=label_width, width=width)]


def strip_lines(strip, *, page, here, label_width, width):
    """Return a blank line and the strip's grid, five lines: its top edge, the slots' numbers, the rule between, the slots'
    values with the cursor's slot in reverse video, and its bottom edge, as many slots as fit the width, scrolled to keep the
    cursor's in view."""
    count = len(strip.cells)
    shown = max(min((width - STRIP_INDENT - STRIP_LABEL_WIDTH - 2) // (STRIP_CELL_WIDTH + 1), count), 1)
    page.cell = max(min(page.cell, count - 1), 0)
    first = max(min(page.cell - shown // 2, count - shown), 0) if here else 0
    places = range(first, first + shown)
    cells = Box.RULE * STRIP_CELL_WIDTH
    edges = [
        (Box.TOP_LEFT, Box.TOP_TEE, Box.TOP_RIGHT), (Box.LEFT_TEE, Box.CROSS, Box.RIGHT_TEE), (Box.BOTTOM_LEFT, Box.BOTTOM_TEE, Box.BOTTOM_RIGHT),
    ]
    top, rule, bottom = [
        Text(STRIP_PAD + left + Box.RULE * STRIP_LABEL_WIDTH + tee + tee.join([cells] * shown) + right, style=Style.DIM, no_wrap=True) for left, tee, right in edges
    ]
    numbers = Text(STRIP_PAD, no_wrap=True)
    numbers.append(Box.BAR + padded(labels.MSG_DRAW_STRIP_SLOT_ROW).ljust(STRIP_LABEL_WIDTH), style=Style.DIM)
    values = Text(cursor_mark(here) + STRIP_PAD[len(cursor_mark(here)):], no_wrap=True)
    values.append(Box.BAR + padded(labels.MSG_DRAW_STRIP_VALUE_ROW).ljust(STRIP_LABEL_WIDTH), style=Style.DIM)
    for place in places:
        numbers.append(Box.BAR, style=Style.DIM)
        numbers.append(slot_text(place + 1), style=Style.DIM)
        values.append(Box.BAR, style=Style.DIM)
        values.append(slot_text(strip.cells[place].value()), style=slot_style(on_cursor=here and place == page.cell, lit=place == strip.lit))
    numbers.append(Box.BAR, style=Style.DIM)
    values.append(Box.BAR, style=Style.DIM)
    return [Text(drawing.NOTHING), top, numbers, rule, values, bottom]


def slot_style(*, on_cursor, lit):
    """Return how a slot of a strip is drawn: in reverse video under the cursor, in the draws' light while a song plays, both at once, or plain."""
    if on_cursor and lit:
        return Style.DRAW_LIGHT_REVERSED
    if on_cursor:
        return Style.REVERSE
    return Style.DRAW_LIGHT if lit else Style.PLAIN


def slot_text(value):
    """Return a slot's number or value as its cell of a strip shows it, right-justified with a space after it."""
    return marks.MSG_DRAW_STRIP_CELL.format(value=value)


# How each kind of node is drawn, by what it says it is drawn as: a setting's line, a button, a heading, a row of cells, a
# table's row and its first, and a strip, each given the width there is.
DRAWERS = {
    nodes.SETTING_LINE: setting_line, nodes.BUTTON: button_lines, nodes.HEADING: heading_lines, nodes.CELLS: cells_lines,
    nodes.TABLE_ROW: table_row_lines, nodes.CAPTIONED_TABLE_ROW: captioned_table_row_lines, nodes.STRIP: strip_lines,
    statement_rows.STATEMENT_ROW: statement_row_lines, statement_rows.FIRST_STATEMENT_ROW: first_statement_row_lines,
}
