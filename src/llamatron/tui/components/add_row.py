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
"""A register's += row: how much a step adds to the register, or takes from it, within the register's Allowed Inc Max."""

from llamatron.composition.file_format import REGISTER_ADD_ROWS
from llamatron.strings.errors import ERR_AT_ALLOWED_INC_MAX
from llamatron.tui.components.control_row import ControlRow
from llamatron.tui import keybindings

# Which register each += row adds to, by the row's name.
REGISTER_OF_ROW = {row: name for name, row in REGISTER_ADD_ROWS.items()}


class AddRow(ControlRow):
    """The same keys as a number row, on every step, held from minus the register's Allowed Inc Max to plus it.

    The limit is the narrowest of the songs that play the pattern, or the current song's when
    none does, the user's design of 2026-11-11, so that [ and ] step through a short line.
    """

    KEYS = keybindings.AddRow

    __slots__ = ()

    def range(self):
        most = self.editor.document().allowed_inc_max(pattern=self.editor.item, register=REGISTER_OF_ROW[self.name])
        return -most, most

    def nudge(self, offset):
        low, high = self.range()
        moved = self.number_now() + offset
        if not low <= moved <= high:
            self.editor.refuse(ERR_AT_ALLOWED_INC_MAX.format(register=REGISTER_OF_ROW[self.name], most=high))
        self.set_value(max(min(moved, high), low))
