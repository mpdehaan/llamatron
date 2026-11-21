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

from llamatron.strings import labels, legends, marks
from llamatron.tui import drawing
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import Box, cursor_mark, padded, Style
from llamatron.tui.screens.shared.shared import stepped

# Where a picker opens when the value isn't one of the choices.
FIRST_CHOICE = 0


def within(*, number, lowest, highest):
    """Return a number kept between two ends, either of which may be None for no end."""
    if lowest is not None:
        number = max(number, lowest)
    if highest is not None:
        number = min(number, highest)
    return number


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
class Field:
    """One setting on a page. A missing function means that key does nothing there."""

    label: str
    value: Callable
    adjust: Callable = None
    enter: Callable = None
    enter_what: str = legends.What.EDIT
    clear: Callable = None
    clear_what: str = legends.What.CLEAR

    # Which of the lines a field draws holds the cursor, and whether a blank line may follow the field.
    SELECTED_LINE = 0
    MAY_LEAVE_A_GAP = True

    def is_toggle(self):
        """Return whether the setting is on or off, which answers to Space and Enter alike."""
        return False

    def get_drawn_label(self, page):
        """Return the label as the page draws it."""
        return self.label

    def lines(self, *, page, here, label_width, width):
        """Return the lines the field is drawn as: the cursor's mark, the label, bold under the cursor, and the value, with the
        picker's dim mark after a value whose Enter opens a list of choices, so that it isn't taken for one that's typed."""
        line = Text(no_wrap=True)
        line.append(cursor_mark(here))
        line.append(self.label.ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
        line.append(padded(self.value()))
        if self.enter_what == legends.What.CHOOSE:
            line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
        return [line]

    def row_keys(self, page):
        """Return the keys of the row the field stands on, before its own: [ and ] step a value that steps."""
        if self.adjust is None:
            return []
        return [page.bind(page.KEYS.MORE, action=lambda: self.adjust(1)), page.bind(page.KEYS.LESS, action=lambda: self.adjust(-1))]

    def keys(self, page):
        """Return the keys that act on the field: Space and Enter alike for a toggle, as the pattern editor's toggle rows, else
        Enter, and Bksp."""
        bound = []
        if self.enter and self.is_toggle():
            bound.append(page.bind(page.KEYS.TOGGLE, action=self.enter))
        elif self.enter:
            bound.append(page.bind(page.KEYS.ENTER, action=self.enter, what=self.enter_what))
        if self.clear:
            bound.append(page.bind(page.KEYS.CLEAR, action=self.clear, what=self.clear_what))
        return bound


@dataclass(slots=True, kw_only=True)
class Toggle(Field):
    """A setting that is on or off: Space or Enter switches it, and it shows the dot when it is on.

    on is whether it is on now, and set(on) stores the other state.
    """

    on: bool
    set: Callable
    shown_on: str = marks.MSG_TOGGLE_ON
    shown_off: str = marks.MSG_FIELD_TOGGLE_OFF
    value: Callable = None
    enter_what: str = legends.What.TOGGLE

    def __post_init__(self):
        self.value = self.shown
        self.enter = self.switch

    def is_toggle(self):
        return True

    def shown(self):
        return self.shown_on if self.on else self.shown_off

    def switch(self):
        self.set(not self.on)


@dataclass(slots=True, kw_only=True)
class NameField(Field):
    """The name of what the page shows: Enter runs the page's rename."""

    rename: Callable
    label: str = labels.MSG_NAME_LABEL
    enter_what: str = legends.What.RENAME

    def __post_init__(self):
        self.enter = self.rename


@dataclass(slots=True, kw_only=True)
class NumberField(Field):
    """A whole number: Left and Right step it, Enter types it, and both keep it between its lowest and its highest.

    number is the number now, or None when the setting has none, and Left, Right and the prompt
    then start from start. set(number) stores one. Either end may be None for no end. shown is
    the text of the value where that isn't the number alone, typed what the prompt opens with
    where that isn't the number, and title the prompt's title where that isn't the label.
    """

    page: object
    number: object
    set: Callable
    lowest: object = None
    highest: object = None
    start: object = None
    shown: object = None
    typed: object = None
    title: str = None
    value: Callable = None

    def __post_init__(self):
        self.value = self.text
        self.adjust = self.step
        self.enter = self.ask

    def counted_from(self):
        """Return the number that stepping and typing start from: the number, or the start when there is none."""
        return self.start if self.number is None else self.number

    def text(self):
        return self.counted_from() if self.shown is None else self.shown

    def step(self, offset):
        self.set_within(self.counted_from() + offset)

    def set_within(self, number):
        """Set a number, kept within the field's lowest and highest."""
        self.set(within(number=number, lowest=self.lowest, highest=self.highest))

    def ask(self):
        value = self.counted_from() if self.typed is None else self.typed
        self.page.ask_number(title=self.title or self.label, value=value, then=self.set, low=self.lowest, high=self.highest)


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
        line.append(self.label.ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
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
class Strip(Cells):
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

    def row_keys(self, page):
        """Return Left and Right, which move between the slots, and [ and ], which step the slot under the cursor."""
        bound = Cells.row_keys(self, page)
        cell = page.cell_field()
        if cell is not None and cell.adjust:
            bound += [page.bind(page.KEYS.SLOT_MORE, action=lambda: cell.adjust(1)), page.bind(page.KEYS.SLOT_LESS, action=lambda: cell.adjust(-1))]
        return bound


@dataclass(slots=True, kw_only=True)
class Button(Field):
    """A row that runs an action on Enter, like Save on the File page, so that nobody has to remember its key.

    It shows the key it stands for the way the main screen's menu does, and nothing else: a
    button's name says what it does, or the dialog it opens will. A button reached only with the
    arrows has no key's name. A page's buttons always come
    after its settings, and the page draws them below the settings after one blank line, so that
    what edits the set and what acts on it never run together.
    """

    key_name: str = drawing.NOTHING
    value: Callable = lambda: drawing.NOTHING


@dataclass(slots=True, kw_only=True)
class Heading(Field):
    """A section's heading on a settings page, like the rows view's: Space or Enter opens or closes it, and the fields after it, up to the next heading, show only while it is open.

    label is the section's name, which the page draws after its open or closed mark, is_set()
    says whether any field inside holds a value, so that a closed heading never hides one
    silently, and toggle() opens or closes it.
    """

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
