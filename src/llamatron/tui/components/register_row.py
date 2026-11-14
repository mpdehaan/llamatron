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

"""The rows that use a register, +Note and +Vel: each step adds the register, subtracts it or does neither, and a rest can hold them.

The user decided on 2026-11-08 that no register setting is ever locked out for want of a note on
the step, so these work on every step like the register changes do; on a step with no note the
render has nothing to move and ignores them. On 2026-11-09 the user made them three-way, where
they had been toggles: a cell shows + for add, - for subtract and nothing for off.
"""

from llamatron.composition.file_format import RegisterUse
from llamatron.tui.components.cycle_row import CycleRow
from llamatron.strings.marks import MSG_REGISTER_ADDS, MSG_REGISTER_SUBTRACTS, MSG_TOGGLE_OFF
from llamatron.tui import keybindings

# What a cell shows for each use.
USE_MARKS = {RegisterUse.ADD: MSG_REGISTER_ADDS, RegisterUse.SUBTRACT: MSG_REGISTER_SUBTRACTS, RegisterUse.OFF: MSG_TOGGLE_OFF}


class RegisterRow(CycleRow):
    """Space or Enter cycles add, subtract and off on any step, [ and ] step back and forward, and Bksp turns the use off."""

    KEYS = keybindings.RegisterRow

    __slots__ = ()

    def on_rests(self):
        return True

    def cell_text(self, *, step):
        value = self.value(step=step)
        return MSG_TOGGLE_OFF if value is None else USE_MARKS[value]
