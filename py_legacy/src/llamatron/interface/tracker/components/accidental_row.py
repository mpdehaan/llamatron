# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The accidental row: a sharp or flat on a note's degree, or neither."""

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.cycle_row import CycleRow


class AccidentalRow(CycleRow):
    """None, sharp, then flat, shown as # or b with nothing for a natural, in plain characters."""

    KEYS = keybindings.AccidentalRow

    __slots__ = ()
    def cell_text(self, *, step):
        value = self.value(step=step)
        return drawing.NOTHING if value is None or not self.is_note(step=step) else str(value)
