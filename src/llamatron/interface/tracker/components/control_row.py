# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A number row that a rest can hold too: the CC rows, which send a value at the start of a step, and the register adds."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.components.number_row import NumberRow


class ControlRow(NumberRow):
    """The same keys as a number row, on every step, since a rest can send a CC value or add to a register."""

    KEYS = keybindings.ControlRow

    __slots__ = ()

    def on_rests(self):
        return True
