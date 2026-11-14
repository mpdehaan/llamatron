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

"""The Pick Many dialog: a list where several choices can be picked at once, each marked on or off, the user's design for a
setting that holds a list, like the visualizers left out. Up and Down move, Space turns the choice under the
cursor on or off, Enter finishes and answers with the choices picked, and Esc cancels, changing nothing."""

from rich.text import Text

from llamatron.strings.marks import MSG_FIELD_TOGGLE_OFF, MSG_TOGGLE_ON
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import SPACE, cursor_mark, fit
from llamatron.tui.key_table import cursor_moved
from llamatron.tui import keybindings


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
        self.place = 0

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.FLIP, action=self.flip),
            self.bind(self.KEYS.DONE, action=lambda: self.dismiss([option for option in self.options if option in self.picked])),
        ]

    def move(self, name):
        self.place = cursor_moved(place=self.place, name=name, count=len(self.options))

    def flip(self):
        self.picked ^= {self.options[self.place]}

    def lines(self, width):
        start = max(min(self.place - self.SHOWN // 2, len(self.options) - self.SHOWN), 0)
        result = []
        for place in range(start, min(start + self.SHOWN, len(self.options))):
            mark = MSG_TOGGLE_ON if self.options[place] in self.picked else MSG_FIELD_TOGGLE_OFF
            result.append(Text(fit(text=cursor_mark(place == self.place) + mark + SPACE + self.names[place], width=width)))
        return result
