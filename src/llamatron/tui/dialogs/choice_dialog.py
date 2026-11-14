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

from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import cursor_mark, fit, NOTHING, SPACE, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key, SPACE_CHARACTER
from llamatron.strings.marks import MSG_SEARCH_SHOWN
from llamatron.tui import keybindings


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
        self.place = max(min(current, len(self.options) - 1), 0)
        self.typed = NOTHING

    def keys(self):
        result = [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.CHOOSE, action=self.choose),
            self.bind(self.KEYS.SEARCH, action=self.type_character, wants_key=True),
        ]
        if self.typed:
            result += [
                self.bind(self.KEYS.ERASE, action=self.erase),
                self.bind(self.KEYS.COMPLETE, action=self.complete),
            ]
        return result

    def cancel(self):
        self.dismiss(None)

    def choose(self):
        if self.place in self.matches():
            self.dismiss(self.place)

    def takes_text(self):
        return True

    def matches(self):
        """Return the places of the options that contain what was typed, ignoring case: all of them with nothing typed."""
        return places_matching(options=self.options, text=self.typed)

    def move(self, name):
        matches = self.matches()
        if not matches:
            return
        if self.place not in matches:
            self.place = matches[0]
            return
        self.place = matches[cursor_moved(place=matches.index(self.place), name=name, count=len(matches))]

    def type_character(self, name):
        self.typed += SPACE_CHARACTER if name == Key.SPACE else name
        self.settle()

    def erase(self):
        self.typed = self.typed[:-1]
        self.settle()

    def complete(self):
        self.typed = completed(options=self.options, matches=self.matches(), typed=self.typed)
        self.settle()

    def settle(self):
        """Keep the highlight on a match, moving it to the first one when what was typed left it out."""
        matches = self.matches()
        if matches and self.place not in matches:
            self.place = matches[0]

    def lines(self, width):
        matches = self.matches()
        result = []
        if self.typed:
            result.append(Text(fit(text=SPACE + MSG_SEARCH_SHOWN.format(text=self.typed), width=width), style=Style.DIM))
        at = matches.index(self.place) if self.place in matches else 0
        start = max(min(at - self.SHOWN // 2, len(matches) - self.SHOWN), 0)
        for place in matches[start:start + self.SHOWN]:
            result.append(Text(fit(text=cursor_mark(place == self.place) + str(self.options[place]), width=width)))
        return result


# Searching a list, which the list pages share.

def places_matching(*, options, text):
    """Return the places of the options whose text contains what was typed, ignoring case: every place when nothing was."""
    wanted = text.casefold()
    return [place for place, option in enumerate(options) if wanted in str(option).casefold()]


def completed(*, options, matches, typed):
    """Return what was typed, completed as far as every matching option agrees from its start, like a shell does.

    Matching is by containing, so completion only grows what was typed when every match starts
    with it; otherwise what was typed stays as it is.
    """
    names = [str(options[place]) for place in matches]
    if not names or not all(name.casefold().startswith(typed.casefold()) for name in names):
        return typed
    first = names[0]
    length = len(typed)
    while length < len(first) and all(name.casefold().startswith(first[:length + 1].casefold()) for name in names):
        length += 1
    return first[:length]
