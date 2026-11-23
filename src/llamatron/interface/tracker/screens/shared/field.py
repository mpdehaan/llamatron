# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The widgets a field page is made of: a Field is one setting, a Button is a row that does something on Enter, and the kinds of Field say what most settings are.

A Field is a label, the text of its value, and what Left and Right, Enter and Bksp do there,
each a function, so any setting can be written as one. Most settings are one of four kinds,
though, and each kind is a class that is given what the setting is and works the functions out:
a Toggle is on or off, a NameField renames, a NumberField is a whole number between two ends
and a ChoiceField is one of a fixed list. A setting with rules of its own, like one end of a
track's octave range, which is typed in the set's octave labels, stays a plain Field.

A page makes its fields afresh for every key and every drawing, so a kind is given the value
as it is now rather than a function that reads it.
"""

from dataclasses import dataclass
from rich.text import Text
from typing import Callable

from llamatron.interface.forms import nodes
from llamatron.interface.forms.nodes import Field
from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Box, cursor_mark, padded, Style
from llamatron.user_strings import labels, legends, marks





# What stands between two cells of a row of cells.
CELL_GAP = '  '

# A strip's grid: how far in from the cursor's mark it starts, its label column's and each slot's room, wide enough for -99 with a
# space either side, and which of its five lines holds the values, where the cursor is.
STRIP_PAD = '    '
STRIP_INDENT = len(STRIP_PAD)
STRIP_LABEL_WIDTH = 7
STRIP_CELL_WIDTH = 5
STRIP_VALUE_LINE = 3


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


@dataclass(slots=True, kw_only=True)
class Cells(Field):
    """A row of settings side by side under one label, as a piece of the kit's on or off and its sound: Left and Right move
    between the cells, and each cell answers Space, Enter and Bksp as the field it is would. A cell is never stepped, since
    Left and Right move here."""

    DRAWN_AS = nodes.OWN_LINES

    cells: list
    value: Callable = None

    def __post_init__(self):
        self.value = self.shown

    MAY_LEAVE_A_GAP = False

    def shown(self):
        """Return every cell's value, in order, as the row reads."""
        return CELL_GAP.join(str(cell.value()) for cell in self.cells)

    def lines(self, *, page, here, label_width, width):
        """Return the row's line: its label, then its cells side by side, the cell under the cursor in reverse video as a grid's
        is, and a cell that opens a list with the picker's mark."""
        line = Text(no_wrap=True)
        line.append(cursor_mark(here))
        line.append(self.get_drawn_label(page).ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
        for place, cell in enumerate(self.cells):
            on_cell = here and place == min(page.cell, len(self.cells) - 1)
            line.append(padded(cell.value()), style=Style.REVERSE if on_cell else Style.PLAIN)
            if cell.enter_what == legends.What.CHOOSE:
                line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
            line.append(CELL_GAP)
        return [line]

    def row_keys(self, page):
        """Return Left and Right, which move between the cells; a cell is never stepped, since they move here."""
        return [page.bind(page.KEYS.ALONG_CELLS, action=page.move_along_cells, wants_key=True)]


@dataclass(slots=True, kw_only=True)
class SteppedCells(Cells):
    """A row of settings side by side under one label whose cells step: Left and Right move between the cells, and [ and ] step
    the cell under the cursor, which answers Enter and Bksp as the field it is, as a drift's two versions of one value. The page's
    keys say SLOT_LESS and SLOT_MORE for [ and ]."""

    def row_keys(self, page):
        """Return Left and Right, which move between the cells, and [ and ], which step the cell under the cursor."""
        bound = Cells.row_keys(self, page)
        cell = page.cell_field()
        if cell is not None and cell.adjust:
            bound += [page.bind(page.KEYS.SLOT_MORE, action=lambda: cell.adjust(1)), page.bind(page.KEYS.SLOT_LESS, action=lambda: cell.adjust(-1))]
        return bound


@dataclass(slots=True, kw_only=True)
class TableRow(SteppedCells):
    """A row of a table of settings: SteppedCells whose every cell takes its column's width, the room of the column's heading or
    its widest value, so that the table's rows line up and its columns never move."""

    widths: list

    def lines(self, *, page, here, label_width, width):
        """Return the row's line: its label, then each cell padded to its column's width, the cell under the cursor in reverse video."""
        line = Text(no_wrap=True)
        line.append(cursor_mark(here))
        line.append(self.get_drawn_label(page).ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
        for place, cell in enumerate(self.cells):
            on_cell = here and place == min(page.cell, len(self.cells) - 1)
            line.append(padded(cell.value()).ljust(self.widths[place] + len(padded(drawing.NOTHING))), style=Style.REVERSE if on_cell else Style.PLAIN)
            line.append(CELL_GAP)
        return [line]


@dataclass(slots=True, kw_only=True)
class CaptionedTableRow(TableRow):
    """A table's first row, which draws the table's caption above itself: the caption at the labels' place, in bold, and each
    column's heading over its column."""

    caption: str
    headings: list

    SELECTED_LINE = 1

    def lines(self, *, page, here, label_width, width):
        """Return the caption's line, then the row's own."""
        caption = Text(no_wrap=True)
        caption.append(cursor_mark(False))
        caption.append(self.caption.ljust(label_width), style=Style.BOLD)
        for place, heading in enumerate(self.headings):
            caption.append(padded(heading).ljust(self.widths[place] + len(padded(drawing.NOTHING))), style=Style.BOLD)
            caption.append(CELL_GAP)
        return [caption, *TableRow.lines(self, page=page, here=here, label_width=label_width, width=width)]


@dataclass(slots=True, kw_only=True)
class Strip(SteppedCells):
    """A strip of numbered slots, a draw's, drawn after a blank line as a grid boxed in dim lines with a row numbering the slots
    over a row of their values: Left and Right move between the slots, and [ and ] step the slot under the cursor, which answers
    Enter and Bksp as the NumberField it is. The grid scrolls to keep the cursor's slot in view. lit is the place of the slot
    to light while a song plays, the one the draw last took its value from, or None."""

    lit: object = None

    # The strip is drawn after a blank line, and the cursor is on its row of values.
    SELECTED_LINE = 1 + STRIP_VALUE_LINE

    def lines(self, *, page, here, label_width, width):
        """Return a blank line and the strip's grid, five lines: its top edge, the slots' numbers, the rule between, the slots'
        values with the cursor's slot in reverse video, and its bottom edge, as many slots as fit the width, scrolled to keep the
        cursor's in view."""
        count = len(self.cells)
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
            values.append(slot_text(self.cells[place].value()), style=slot_style(on_cursor=here and place == page.cell, lit=place == self.lit))
        numbers.append(Box.BAR, style=Style.DIM)
        values.append(Box.BAR, style=Style.DIM)
        return [Text(drawing.NOTHING), top, numbers, rule, values, bottom]

def gauge_shown(*, place, lowest, highest, said=None):
    """Return a number drawn as a horizontal gauge with the number after it, as the players' gauges are: a block for each place up to the number's,
    and what is said of the number, such as where it comes from, in place of the bare number."""
    drawn = marks.MSG_WIZARD_GAUGE_FULL * (place - lowest + 1) + marks.MSG_WIZARD_GAUGE_EMPTY * (highest - place)
    return marks.MSG_WIZARD_PLAYER_GAUGE_SHOWN.format(gauge=drawn, place=place if said is None else said)
