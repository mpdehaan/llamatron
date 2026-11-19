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

"""The Choice dialog: offers a list to pick from, and answers with the chosen item's place in it."""

from rich.text import Text

from llamatron.strings import marks
from llamatron.tui import drawing, keybindings
from llamatron.tui.cursor import Cursor, key_between, place_of, Search, shown_around
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import cursor_mark, fit, Style


class ChoiceDialog(Dialog):
    """Offers a list to pick from, and answers with the chosen item's place in it.

    Typing searches: the list shrinks to the options that contain what was typed, ignoring case,
    Bksp erases, Tab completes as far as every remaining option agrees, and Esc cancels. The place
    always counts in the whole list, so that the answer is the same whatever was typed.
    """

    KEYS = keybindings.ChoiceDialog

    SHOWN = 12

    def __init__(self, *, title, options, current=0):
        super().__init__()
        self.title = title
        self.options = list(options)
        self.cursor = Cursor(place=max(min(current, len(self.options) - 1), 0))
        self.search = Search()

    def keys(self):
        result = [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.CHOOSE, action=self.choose),
            self.bind(self.KEYS.SEARCH, action=self.type_character, wants_key=True),
        ]
        if self.search.get_typed():
            result += [
                self.bind(self.KEYS.ERASE, action=self.erase),
                self.bind(self.KEYS.COMPLETE, action=self.complete),
            ]
        return result

    def cancel(self):
        self.dismiss(None)

    def choose(self):
        if self.cursor.get_place() in self.matches():
            self.dismiss(self.cursor.get_place())

    def takes_text(self):
        return True

    def matches(self):
        """Return the places of the options that contain what was typed, ignoring case: all of them with nothing typed."""
        return self.search.places_matching(self.options)

    def under_cursor(self):
        """Return the option the cursor is on, as the picker shows it."""
        return self.options[self.cursor.get_place()]

    def key_toward(self, target):
        """Return the key that brings the cursor nearer an option, named as the picker shows it, or None when the cursor is on it."""
        return self.key_toward_place(place_of(screen=self, names=self.options, target=target))

    def key_toward_place(self, place):
        """Return the key that brings the cursor nearer the option at a place in the whole list, or None when the cursor is on it."""
        return key_between(here=self.cursor.get_place(), there=place)

    def move(self, name):
        self.cursor.move_among(name=name, places=self.matches())

    def type_character(self, name):
        self.search.type_key(name)
        self.settle()

    def erase(self):
        self.search.erase()
        self.settle()

    def complete(self):
        self.search.complete(self.options)
        self.settle()

    def settle(self):
        """Keep the highlight on a match, moving it to the first one when what was typed left it out."""
        self.cursor.keep_among(self.matches())

    def lines(self, width):
        matches = self.matches()
        result = []
        if self.search.get_typed():
            result.append(Text(fit(text=drawing.SPACE + marks.MSG_SEARCH_SHOWN.format(text=self.search.get_typed()), width=width), style=Style.DIM))
        at = matches.index(self.cursor.get_place()) if self.cursor.is_on_one_of(matches) else 0
        for place in shown_around(places=matches, at=at, room=self.SHOWN):
            result.append(Text(fit(text=cursor_mark(place == self.cursor.get_place()) + str(self.options[place]), width=width)))
        return result
