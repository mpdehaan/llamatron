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
from typing import Callable

from llamatron.strings.labels import MSG_NAME_LABEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_FIELD_TOGGLE_OFF, MSG_SECTION_SET, MSG_TOGGLE_ON
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import NOTHING
from llamatron.tui.screens.shared import stepped

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


@dataclass(slots=True, kw_only=True)
class Field:
    """One setting on a page. A missing function means that key does nothing there."""

    label: str
    value: Callable
    adjust: Callable = None
    enter: Callable = None
    enter_what: str = What.EDIT
    clear: Callable = None
    clear_what: str = What.CLEAR

    def is_toggle(self):
        """Return whether the setting is on or off, which answers to Space and Enter alike."""
        return False


@dataclass(slots=True, kw_only=True)
class Toggle(Field):
    """A setting that is on or off: Space or Enter switches it, and it shows the dot when it is on.

    on is whether it is on now, and set(on) stores the other state.
    """

    on: bool
    set: Callable
    shown_on: str = MSG_TOGGLE_ON
    shown_off: str = MSG_FIELD_TOGGLE_OFF
    value: Callable = None
    enter_what: str = What.TOGGLE

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
    label: str = MSG_NAME_LABEL
    enter_what: str = What.RENAME

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
        self.set(within(number=self.counted_from() + offset, lowest=self.lowest, highest=self.highest))

    def ask(self):
        value = self.counted_from() if self.typed is None else self.typed
        self.page.ask_number(title=self.title or self.label, value=value, then=self.set, low=self.lowest, high=self.highest)


@dataclass(slots=True, kw_only=True)
class ChoiceField(Field):
    """One of a fixed list of choices: Left and Right step through them, stopping at both ends, and Enter picks from a list.

    current is the choice now, and set(choice) stores one. names are what the picker calls the
    choices where those aren't the choices themselves, shown the text of the value where that
    isn't the choice, and picked the choice the picker opens on where that isn't the current one.
    """

    page: object
    choices: list
    current: object
    set: Callable
    names: list = None
    shown: object = None
    picked: object = None
    value: Callable = None
    enter_what: str = What.CHOOSE

    def __post_init__(self):
        self.value = self.text
        self.adjust = self.step
        self.enter = self.pick

    def text(self):
        return self.current if self.shown is None else self.shown

    def step(self, offset):
        self.set(stepped(values=self.choices, current=self.current, offset=offset))

    def pick(self):
        opens_on = str(self.current if self.picked is None else self.picked)
        place = self.choices.index(opens_on) if opens_on in self.choices else FIRST_CHOICE
        dialog = ChoiceDialog(title=self.label, options=self.names or self.choices, current=place)
        self.page.ask(dialog=dialog, then=lambda chosen: self.set(self.choices[chosen]))


@dataclass(slots=True, kw_only=True)
class Button(Field):
    """A row that runs an action on Enter, like Save on the File page, so that nobody has to remember its key.

    It shows the key it stands for the way the main screen's menu does, and nothing else: a
    button's name says what it does, or the dialog it opens will. A page's buttons always come
    after its settings, and the page draws them below the settings after one blank line, so that
    what edits the set and what acts on it never run together.
    """

    key_name: str
    value: Callable = lambda: NOTHING


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

    def __post_init__(self):
        self.value = self.shown
        self.enter = self.toggle

    def is_toggle(self):
        return True

    def shown(self):
        return MSG_SECTION_SET if self.is_set() else NOTHING_SET
