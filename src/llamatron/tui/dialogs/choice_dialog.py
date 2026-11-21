# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Choice dialog: offers a list to pick from, and answers with the chosen item's place in it."""

from rich.text import Text

from llamatron.tui import drawing, keybindings
from llamatron.tui.cursor import Cursor, key_between, place_of, Search, shown_around
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import cursor_mark, fit, Style
from llamatron.user_strings import marks


class ChoiceDialog(Dialog):
    """Offers a list to pick from, and answers with the chosen item's place in it.

    Typing searches: the list shrinks to the options that contain what was typed, ignoring case,
    Bksp erases, Tab completes as far as every remaining option agrees, and Esc cancels. The place
    always counts in the whole list, so that the answer is the same whatever was typed.
    """

    KEYS = keybindings.ChoiceDialog

    SHOWN = 12

    def __init__(self, *, title, options, current=0, headings=()):
        """headings are the places of options that only head a group, or stand blank between groups: drawn dim, never chosen,
        passed over by the cursor and left out once anything is typed."""
        super().__init__()
        self.title = title
        self.options = list(options)
        self.headings = frozenset(headings)
        self.cursor = Cursor(place=max(min(current, len(self.options) - 1), 0))
        self.search = Search()
        self.settle()

    def keys(self):
        result = [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
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
        """Return the places of the options that contain what was typed, ignoring case, all of them with nothing typed, leaving out the headings."""
        return [place for place in self.search.places_matching(self.options) if place not in self.headings]

    def shown_places(self):
        """Return the places of the options the list shows: every match, and with nothing typed the headings among them."""
        if self.search.get_typed() or not self.headings:
            return self.matches()
        return list(range(len(self.options)))

    def under_cursor(self):
        """Return the option the cursor is on, as the picker shows it."""
        return self.options[self.cursor.get_place()]

    def key_toward(self, target):
        """Return the key that brings the cursor nearer an option, named as the picker shows it, or None when the cursor is on it."""
        return self.key_toward_place(place_of(screen=self, names=self.options, target=target))

    def key_toward_place(self, place):
        """Return the key that brings the cursor nearer the option at a place in the whole list, or None when the cursor is on it."""
        return key_between(here=self.cursor.get_place(), there=place)

    def move_cursor(self, name):
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
        shown = self.shown_places()
        at = shown.index(self.cursor.get_place()) if self.cursor.is_on_one_of(matches) else 0
        for place in shown_around(places=shown, at=at, room=self.SHOWN):
            text = fit(text=cursor_mark(place == self.cursor.get_place()) + str(self.options[place]), width=width)
            result.append(Text(text, style=Style.DIM) if place in self.headings else Text(text))
        return result
