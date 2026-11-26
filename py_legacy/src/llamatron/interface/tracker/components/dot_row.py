# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Dot row: a gate made dotted, half as long again, or a triplet, two thirds."""

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.cycle_row import CycleRow


class DotRow(CycleRow):
    """None, dotted, then triplet; a rest shows nothing, since it has no gate."""

    KEYS = keybindings.DotRow

    __slots__ = ()
    def cell_text(self, *, step):
        value = self.value(step=step)
        return drawing.NOTHING if not self.is_note(step=step) or value is None else str(value)
