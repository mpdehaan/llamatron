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
"""A condition row: how AX has to compare with another register, less, more or the same, for the step's note to sound, or blank for no comparison."""

from llamatron.tui.components.cycle_row import CycleRow
from llamatron.tui.drawing import NOTHING
from llamatron.tui import keybindings


class ConditionRow(CycleRow):
    """Space or Enter cycles blank, <, > and =, [ and ] step back and forward, and Bksp clears.

    Only a note can be silenced, so an empty step can't hold a condition and shows the light
    slash, as Probability does there. A step sounds only when every condition it has holds.
    """

    KEYS = keybindings.ConditionRow

    __slots__ = ()

    def cell_text(self, *, step):
        value = self.value(step=step)
        return NOTHING if value is None or not self.is_note(step=step) else value
