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
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Box, cursor_mark, padded, Style
from llamatron.interface.tracker.screens.shared.shared import stepped
from llamatron.user_strings import labels, legends, marks

# Where a picker opens when the value isn't one of the choices.
FIRST_CHOICE = 0


# A heading with nothing set inside shows no value.
NOTHING_SET = ''


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
class ChoiceField(Field):
    """One of a fixed list of choices: Left and Right step through them, stopping at both ends, and Enter picks from a list.

    current is the choice now, and set(choice) stores one. names are what the picker calls the
    choices where those aren't the choices themselves, shown the text of the value where that
    isn't the choice, and picked the choice the picker opens on where that isn't the current one.
    grouped, a GroupedChoices, is the picker's list in groups under headings, where the choices are offered so.
    """

    page: object
    choices: list
    current: object
    set: Callable
    names: list = None
    shown: object = None
    picked: object = None
    grouped: object = None
    value: Callable = None
    enter_what: str = legends.What.CHOOSE

    def __post_init__(self):
        self.value = self.text
        self.adjust = self.step
        self.enter = self.pick

    def text(self):
        return self.current if self.shown is None else self.shown

    def step(self, offset):
        self.set(stepped(values=self.choices, current=self.current, offset=offset))

    def pick(self):
        if self.grouped is not None:
            self.page.ask(dialog=self.grouped.dialog(title=self.label, current=self.current), then=lambda place: self.set(self.grouped.value_at(place)))
            return
        opens_on = str(self.current if self.picked is None else self.picked)
        place = self.choices.index(opens_on) if opens_on in self.choices else FIRST_CHOICE
        dialog = ChoiceDialog(title=self.label, options=self.names or self.choices, current=place)
        self.page.ask(dialog=dialog, then=lambda chosen: self.set(self.choices[chosen]))


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

@dataclass(slots=True, kw_only=True)
class Button(Field):
    """A row that runs an action on Enter, like Save on the File page, so that nobody has to remember its key.

    It shows the key it stands for the way the main screen's menu does, and nothing else: a
    button's name says what it does, or the dialog it opens will. A button reached only with the
    arrows has no key's name. A page's buttons always come
    after its settings, and the page draws them below the settings after one blank line, so that
    what edits the set and what acts on it never run together.
    """

    DRAWN_AS = nodes.OWN_LINES

    key_name: str = drawing.NOTHING
    value: Callable = lambda: drawing.NOTHING

    # A button among a tab's columns is drawn boxed, its name on the box's middle line.
    SELECTED_LINE = 1

    def lines(self, *, page, here, label_width, width):
        """Return the button boxed as a page's buttons are, double-lined under the cursor: drawn so only where it stands among a
        tab's columns, since a page draws its own buttons in a row below its settings."""
        return [Text(drawing.INDENT) + line for line in button_row(buttons=[(self.key_name, self.label)], selected=0 if here else None)]


@dataclass(slots=True, kw_only=True)
class Heading(Field):
    """A section's heading on a settings page, like the rows view's: Space or Enter opens or closes it, and the fields after it, up to the next heading, show only while it is open.

    label is the section's name, which the page draws after its open or closed mark, is_set()
    says whether any field inside holds a value, so that a closed heading never hides one
    silently, and toggle() opens or closes it.
    """

    DRAWN_AS = nodes.OWN_LINES

    is_set: Callable = None
    toggle: Callable = None
    value: Callable = None
    enter_what: str = None
    # A heading over the few fields a page is for starts open, and is closed by hand.
    starts_open: bool = False
    # What the heading says after its name in place of the mark of a value inside, as a list's heading says how many it holds.
    said: Callable = None

    def __post_init__(self):
        self.value = self.shown
        self.enter = self.toggle

    MAY_LEAVE_A_GAP = False

    def is_toggle(self):
        return True

    def get_drawn_label(self, page):
        """Return the section's name after its open or closed mark."""
        mark = marks.MSG_SECTION_OPEN_MARK if page.is_open(self) else marks.MSG_SECTION_CLOSED_MARK
        return labels.MSG_SECTION_LABEL.format(mark=mark, name=self.label)

    def lines(self, *, page, here, label_width, width):
        line = Text(no_wrap=True)
        line.append(cursor_mark(here))
        line.append(self.get_drawn_label(page).ljust(label_width), style=Style.BOLD)
        line.append(padded(self.value()), style=Style.DIM)
        return [line]

    def shown(self):
        if self.said is not None:
            return self.said()
        return marks.MSG_SECTION_SET if self.is_set() else NOTHING_SET


def gauge_shown(*, place, lowest, highest, said=None):
    """Return a number drawn as a horizontal gauge with the number after it, as the players' gauges are: a block for each place up to the number's,
    and what is said of the number, such as where it comes from, in place of the bare number."""
    drawn = marks.MSG_WIZARD_GAUGE_FULL * (place - lowest + 1) + marks.MSG_WIZARD_GAUGE_EMPTY * (highest - place)
    return marks.MSG_WIZARD_PLAYER_GAUGE_SHOWN.format(gauge=drawn, place=place if said is None else said)
