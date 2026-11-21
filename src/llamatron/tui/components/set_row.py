# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A register's = row: the value a step sets the register to before anything adds to it, or blank to leave the register as it is."""

from llamatron.model.schema import file_format
from llamatron.tui import keybindings
from llamatron.tui.components.control_row import ControlRow

# Which register each = row sets, by the row's name.
REGISTER_OF_ROW = {row: name for name, row in file_format.REGISTER_SET_ROWS.items()}


class SetRow(ControlRow):
    """The number line runs from blank up through the current song's register.

    Blank, which sets nothing, sits just below the register's minimum: ] on a blank step gives the
    minimum, [ on the minimum gives blank again, and ] stops at the maximum. Digits type a value,
    Enter asks for one, and Bksp clears the step back to blank. A value outside the register's
    range can be typed, since a pattern plays in every song, and a song's register holds it to
    its range as it plays.
    """

    KEYS = keybindings.SetRow

    __slots__ = ()

    def register(self):
        """Return the current song's Register this row sets."""
        return self.editor.document().song().get_register(REGISTER_OF_ROW[self.name])

    def nudge(self, offset):
        register = self.register()
        lowest = register.get_minimum()
        current = self.value()
        if current is None:
            if offset > 0:
                self.set_value(lowest)
            return
        moved = current + offset
        self.set_value(None if moved < lowest else min(moved, max(register.get_maximum(), current)))
