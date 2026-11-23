# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The fields a settings page is made of, as plain nodes that say what a setting is and what its keys do, with nothing of how
they are drawn: a Field is one setting, and the kinds of Field say what most settings are.

A Field is a label, the text of its value, and what Left and Right, Enter and Bksp do there, each a function, so any setting
can be written as one. Most settings are one of a few kinds, each a class that is given what the setting is and works the
functions out: a Toggle is on or off, a NameField renames, a NumberField is a whole number between two ends and a ChoiceField is one of a
fixed list. A Button is a row that acts on Enter, and a Heading opens and closes the section under it. A page makes
its fields afresh for every key and every drawing, so a kind is given the value as it is now rather than a function that reads
it. The tracker draws a node through its renderers (interface/tracker/renderers/), the only code that knows how it looks.
"""

from dataclasses import dataclass
from typing import Callable

from llamatron.user_strings import labels, legends, marks

# How the tracker draws a field: the setting's label and value on one line, or by the field's own lines(), for the kinds
# still to move here from interface/tracker/screens/shared/field.py.
SETTING_LINE = 'setting line'
OWN_LINES = 'own lines'
# A button, boxed as a page's buttons are, and a section's heading with its open or closed mark.
BUTTON = 'button'
HEADING = 'heading'
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


def within(*, number, lowest, highest):
    """Return a number kept between two ends, either of which may be None for no end."""
    if lowest is not None:
        number = max(number, lowest)
    if highest is not None:
        number = min(number, highest)
    return number



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
