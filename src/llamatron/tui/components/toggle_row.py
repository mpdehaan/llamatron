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
"""A row that's on or off for each step, like Glide, Grab and the registers' uses."""

from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.drawing import NOTHING
from llamatron.strings.marks import MSG_TOGGLE_OFF, MSG_TOGGLE_ON
from llamatron.tui import keybindings


class ToggleRow(PatternRow):
    """Space or Enter switches the step's value, and Bksp switches it off."""

    KEYS = keybindings.ToggleRow

    __slots__ = ()

    def keys(self):
        return [
            self.bind(self.KEYS.TOGGLE, action=self.toggle),
            self.bind(self.KEYS.CLEAR, action=lambda: self.set_value(False)),
        ]

    def toggle(self):
        self.set_value(not self.value())

    def cell_text(self, *, step):
        if not self.is_note(step=step) and not self.on_rests():
            return NOTHING
        return MSG_TOGGLE_ON if self.value(step=step) else MSG_TOGGLE_OFF
