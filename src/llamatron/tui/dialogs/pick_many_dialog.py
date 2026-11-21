# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Pick Many dialog: a list where several choices can be picked at once, each marked on or off, for a
setting that holds a list, like the visualizers left out. Up and Down move, Space turns the choice under the
cursor on or off, Enter finishes and answers with the choices picked, and Esc cancels, changing nothing."""

from rich.text import Text

from llamatron.tui import drawing, keybindings
from llamatron.tui.cursor import Cursor
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import cursor_mark, fit
from llamatron.user_strings import marks


class PickManyDialog(Dialog):
    """Answers with the list of choices picked, in the options' order, or None when cancelled."""

    KEYS = keybindings.PickManyDialog
    # How many options show at once, the list scrolling to keep the cursor's in view.
    SHOWN = 12

    def __init__(self, *, title, options, names, picked):
        super().__init__()
        self.title = title
        self.options = options
        self.names = names
        self.picked = set(picked)
        self.cursor = Cursor(place=0)

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.FLIP, action=self.toggle),
            self.bind(self.KEYS.DONE, action=lambda: self.dismiss([option for option in self.options if option in self.picked])),
        ]

    def move_cursor(self, name):
        self.cursor.move(name=name, count=len(self.options))

    def toggle(self):
        self.picked ^= {self.options[self.cursor.get_place()]}

    def lines(self, width):
        start = max(min(self.cursor.get_place() - self.SHOWN // 2, len(self.options) - self.SHOWN), 0)
        result = []
        for place in range(start, min(start + self.SHOWN, len(self.options))):
            mark = marks.MSG_TOGGLE_ON if self.options[place] in self.picked else marks.MSG_FIELD_TOGGLE_OFF
            result.append(Text(fit(text=cursor_mark(place == self.cursor.get_place()) + mark + drawing.SPACE + self.names[place], width=width)))
        return result
