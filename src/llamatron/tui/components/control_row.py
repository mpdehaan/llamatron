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
"""A number row that a rest can hold too: the CC rows, which send a value at the start of a step, and the register adds."""

from llamatron.tui.components.number_row import NumberRow
from llamatron.tui import keybindings


class ControlRow(NumberRow):
    """The same keys as a number row, on every step, since a rest can send a CC value or add to a register."""

    KEYS = keybindings.ControlRow

    __slots__ = ()

    def on_rests(self):
        return True
