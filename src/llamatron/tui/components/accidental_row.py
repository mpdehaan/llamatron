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
"""The accidental row: a sharp or flat on a note's degree, or neither."""

from llamatron.tui.components.cycle_row import CycleRow
from llamatron.tui.drawing import NOTHING
from llamatron.tui import keybindings


class AccidentalRow(CycleRow):
    """None, sharp, then flat, shown as # or b with nothing for a natural, since the user wanted the plain characters."""

    KEYS = keybindings.AccidentalRow

    __slots__ = ()
    def cell_text(self, *, step):
        value = self.value(step=step)
        return NOTHING if value is None or not self.is_note(step=step) else str(value)
