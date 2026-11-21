# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The rows that use a register, +Note and +Vel: each step adds the register, subtracts it or does neither, and a rest can hold them.

No register setting is ever locked out for want of a note on
the step, so these work on every step like the register changes do; on a step with no note the
render has nothing to move and ignores them. They are three-way, where
they had been toggles: a cell shows + for add, - for subtract and nothing for off.
"""

from llamatron.model.schema.file_format import RegisterUse
from llamatron.tui import keybindings
from llamatron.tui.components.cycle_row import CycleRow
from llamatron.user_strings import marks

# What a cell shows for each use.
USE_MARKS = {RegisterUse.ADD: marks.MSG_REGISTER_ADDS, RegisterUse.SUBTRACT: marks.MSG_REGISTER_SUBTRACTS, RegisterUse.OFF: marks.MSG_TOGGLE_OFF}


class RegisterRow(CycleRow):
    """Space or Enter cycles add, subtract and off on any step, [ and ] step back and forward, and Bksp turns the use off."""

    KEYS = keybindings.RegisterRow

    __slots__ = ()

    def on_rests(self):
        return True

    def cell_text(self, *, step):
        value = self.value(step=step)
        return marks.MSG_TOGGLE_OFF if value is None else USE_MARKS[value]
