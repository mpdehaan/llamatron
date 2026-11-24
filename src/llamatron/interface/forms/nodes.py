# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields a settings page is made of, as plain nodes that say what a setting is and what its keys do, with nothing of how
they are drawn: a Field is one setting, and the kinds of Field say what most settings are.

A Field is a label, the text of its value, and what Left and Right, Enter and Bksp do there, each a function, so any setting
can be written as one. Most settings are one of a few kinds, each a class that is given what the setting is and works the
functions out: a Toggle is on or off, a NameField renames, a NumberField is a whole number between two ends and a ChoiceField is one of a
fixed list, and a TextField is a line of text. A Button is a row that acts on Enter, and a Heading opens and closes the section under it. A page makes
its fields afresh for every key and every drawing, so a kind is given the value as it is now rather than a function that reads
it. The tracker draws a node through its renderers (interface/tracker/renderers/), the only code that knows how it looks.
"""

from dataclasses import dataclass
import math
from typing import Callable

from llamatron.model.schema import limits
from llamatron.user_strings import labels, legends, marks

# How the tracker draws each kind of field (interface/tracker/renderers/fields.py): a setting's label and value on one line, a
# button, boxed as a page's buttons are, a section's heading with its open or closed mark, a row of cells, a table's row and
# its first row with the table's caption, and a draw's strip of slots.
SETTING_LINE = 'setting line'
BUTTON = 'button'
HEADING = 'heading'
CELLS = 'cells'
TABLE_ROW = 'table row'
CAPTIONED_TABLE_ROW = 'captioned table row'
STRIP = 'strip'
# What stands between two cells of a row of cells.
CELL_GAP = '  '
# Which of the five lines of a strip's grid holds its values, where the cursor is.
STRIP_VALUE_LINE = 3
# A button's value, and a heading's with nothing set inside: no text.
NOTHING = ''
NOTHING_SET = NOTHING
# Where a picker opens when the value isn't one of the choices.
FIRST_CHOICE = 0


def stepped(*, values, current, offset):
    """Return the next value in a list, starting from the middle if the current one isn't there."""
    text = str(current)
    place = values.index(text) if text in values else len(values) // 2
    return values[max(min(place + offset, len(values) - 1), 0)]


def octave_moved(*, octave, offset):
    """Return an octave moved by an offset, kept within the file's range."""
    return max(min(octave + offset, limits.MAX_OCTAVE), limits.MIN_OCTAVE)


def within(*, number, lowest, highest):
    """Return a number kept between two ends, either of which may be None for no end."""
    if lowest is not None:
        number = max(number, lowest)
    if highest is not None:
        number = min(number, highest)
    return number


# A built-in sound's gauge: how many cells it has, and how far [ and ] step a time in milliseconds below each length.
GAUGE_CELLS = 12
TIME_STRIDES = ((20, 1), (100, 5), (500, 10), (2000, 50))
LONGEST_TIME_STRIDE = 100


def gauge_shown(*, place, lowest, highest, said=None):
    """Return a number drawn as a horizontal gauge with the number after it, as the players' gauges are: a block for each place up to the number's,
    and what is said of the number, such as where it comes from, in place of the bare number."""
    drawn = marks.MSG_WIZARD_GAUGE_FULL * (place - lowest + 1) + marks.MSG_WIZARD_GAUGE_EMPTY * (highest - place)
    return marks.MSG_WIZARD_PLAYER_GAUGE_SHOWN.format(gauge=drawn, place=place if said is None else said)


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
    # What the page draws in place of the label, where a column's heading says the rest: Start under Ramp In for Velocity in
    # start. The label stays the field's name, which the key map, help, a typed value's prompt and the tests know it by.
    shown_label: str = None

    # Which of the lines a field draws holds the cursor, and whether a blank line may follow the field.
    SELECTED_LINE = 0
    MAY_LEAVE_A_GAP = True
    # Whether it stands for a tab box among a page's fields, or is the row of tabs, which a page draws with the box.
    IS_TAB_BOX = False
    IS_TAB_ROW = False
    # How the tracker draws it (interface/tracker/renderers/fields.py): its label and value on one line, or, for a kind not yet
    # moved here, by its own lines().
    DRAWN_AS = SETTING_LINE

    def is_toggle(self):
        """Return whether the setting is on or off, which answers to Space and Enter alike."""
        return False

    def get_drawn_label(self, page):
        """Return the label as the page draws it: its shown label where it has one."""
        if self.shown_label is not None:
            return self.shown_label
        return self.label

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
class GaugeField(NumberField):
    """A number of a built-in sound drawn as a horizontal gauge, of GAUGE_CELLS cells unless it says, then its value in its unit, a format
    of number: [ and ] step it, by more as it grows where it is logarithmic, a time in milliseconds or a frequency in hertz,
    whose gauge then fills by the logarithm so that small values can be told apart; Enter types it. Both ends are needed."""

    unit: str = marks.MSG_SOUND_PERCENT_SHOWN
    logarithmic: bool = False
    # How many cells the gauge has: fewer where it stands in a narrow box, as an effect block's do.
    cells: int = GAUGE_CELLS
    # How far a logarithmic gauge steps below each bound, and above the last: a time's strides unless it says.
    strides: tuple = TIME_STRIDES
    longest_stride: int = LONGEST_TIME_STRIDE

    def __post_init__(self):
        self.value = self.drawn
        self.adjust = self.step
        self.enter = self.ask

    def drawn(self):
        number = self.counted_from()
        filled = round(self.share(number) * self.cells)
        gauge = marks.MSG_SOUND_GAUGE_FULL * filled + marks.MSG_SOUND_GAUGE_EMPTY * (self.cells - filled)
        return marks.MSG_SOUND_GAUGE.format(gauge=gauge, value=self.unit.format(number=number))

    def share(self, number):
        """Return how much of the gauge a number fills, from 0 to 1."""
        if self.logarithmic:
            return math.log1p(number - self.lowest) / math.log1p(self.highest - self.lowest)
        return (number - self.lowest) / (self.highest - self.lowest)

    def step(self, offset):
        """Step by the gauge's stride, by more while [ or ] is held down."""
        self.set_within(self.counted_from() + offset * self.stride() * self.page.held_steps.times(self.label))

    def stride(self):
        """Return how far [ and ] step: one, or for a time a step that grows with it, so that a long time is reached in few presses."""
        number = self.counted_from()
        if not self.logarithmic:
            return 1
        for below, stride in self.strides:
            if number < below:
                return stride
        return self.longest_stride


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
            self.page.ask_grouped(title=self.label, grouped=self.grouped, current=self.current, then=lambda place: self.set(self.grouped.value_at(place)))
            return
        opens_on = str(self.current if self.picked is None else self.picked)
        place = self.choices.index(opens_on) if opens_on in self.choices else FIRST_CHOICE
        self.page.ask_choice(title=self.label, options=self.names or self.choices, current=place, then=lambda chosen: self.set(self.choices[chosen]))


@dataclass(slots=True, kw_only=True)
class Button(Field):
    """A row that runs an action on Enter, like Save on the File page, so that nobody has to remember its key.

    It shows the key it stands for the way the main screen's menu does, and nothing else: a
    button's name says what it does, or the dialog it opens will. A button reached only with the
    arrows has no key's name. A page's buttons always come
    after its settings, and the page draws them below the settings after one blank line, so that
    what edits the set and what acts on it never run together.
    """

    DRAWN_AS = BUTTON

    key_name: str = NOTHING
    value: Callable = lambda: NOTHING

    # A button among a tab's columns is drawn boxed, its name on the box's middle line.
    SELECTED_LINE = 1


@dataclass(slots=True, kw_only=True)
class Heading(Field):
    """A section's heading on a settings page, like the rows view's: Space or Enter opens or closes it, and the fields after it, up to the next heading, show only while it is open.

    label is the section's name, which the page draws after its open or closed mark, is_set()
    says whether any field inside holds a value, so that a closed heading never hides one
    silently, and toggle() opens or closes it.
    """

    DRAWN_AS = HEADING

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

    def shown(self):
        if self.said is not None:
            return self.said()
        return marks.MSG_SECTION_SET if self.is_set() else NOTHING_SET


@dataclass(slots=True, kw_only=True)
class Cells(Field):
    """A row of settings side by side under one label, as a piece of the kit's on or off and its sound: Left and Right move
    between the cells, and each cell answers Space, Enter and Bksp as the field it is would. A cell is never stepped, since
    Left and Right move here."""

    DRAWN_AS = CELLS

    cells: list
    value: Callable = None

    def __post_init__(self):
        self.value = self.shown

    MAY_LEAVE_A_GAP = False

    def shown(self):
        """Return every cell's value, in order, as the row reads."""
        return CELL_GAP.join(str(cell.value()) for cell in self.cells)

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

    DRAWN_AS = TABLE_ROW


@dataclass(slots=True, kw_only=True)
class CaptionedTableRow(TableRow):
    """A table's first row, which draws the table's caption above itself: the caption at the labels' place, in bold, and each
    column's heading over its column."""

    caption: str
    headings: list

    SELECTED_LINE = 1
    DRAWN_AS = CAPTIONED_TABLE_ROW


@dataclass(slots=True, kw_only=True)
class Strip(SteppedCells):
    """A strip of numbered slots, a draw's, drawn after a blank line as a grid boxed in dim lines with a row numbering the slots
    over a row of their values: Left and Right move between the slots, and [ and ] step the slot under the cursor, which answers
    Enter and Bksp as the NumberField it is. The grid scrolls to keep the cursor's slot in view. lit is the place of the slot
    to light while a song plays, the one the draw last took its value from, or None."""

    lit: object = None

    # The strip is drawn after a blank line, and the cursor is on its row of values, the fourth of the grid's five lines.
    SELECTED_LINE = 1 + STRIP_VALUE_LINE
    DRAWN_AS = STRIP


@dataclass(slots=True, kw_only=True)
class TextField(Field):
    """A line of text, like a set's title: Enter asks the page for it, starting from what it says now, and Bksp blanks it; a
    blank one shows (none), as every empty field does.

    current() reads the text, set_text(text) stores it, blank text clearing it, and blank is what a cleared field stores.
    """

    page: object
    current: Callable
    set_text: Callable
    blank: str = NOTHING
    value: Callable = None
    enter_what: str = legends.What.EDIT
    clear_what: str = marks.MSG_NONE_SHOWN

    def __post_init__(self):
        self.value = self.shown
        self.enter = self.ask
        self.clear = self.blanked

    def shown(self):
        return self.current() or marks.MSG_NONE_SHOWN

    def ask(self):
        self.page.ask_text(title=self.label, value=self.current(), then=self.set_text)

    def blanked(self):
        self.set_text(self.blank)


@dataclass(slots=True, kw_only=True)
class SettingNumberField(NumberField):
    """A whole number that is a setting of something in the set, by the setting's file name: its range is the setting's own,
    said once where the setting is described, and the number is stored through the document, which the holder checks; Bksp
    leaves the setting out. in_effect is the number shown and stepped from where that is not the number written, as a track's
    accent is its default until one is set."""

    document: object
    holder: object
    name: str
    in_effect: object = None
    number: object = None
    set: Callable = None

    def __post_init__(self):
        described = self.holder.SETTINGS[self.name]
        self.number = self.holder.get_written(self.name) if self.in_effect is None else self.in_effect
        self.lowest = described.get_lowest()
        self.highest = described.get_highest()
        self.set = self.store
        self.clear = self.left_out
        NumberField.__post_init__(self)

    def store(self, number):
        self.document.set_setting(holder=self.holder, name=self.name, value=number)

    def left_out(self):
        self.store(None)
