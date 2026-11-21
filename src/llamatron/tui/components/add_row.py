# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A register's += row: how much a step adds to the register, or takes from it, within the register's Allowed Inc Max."""

from llamatron.model.vocabulary import file_format
from llamatron.tui import keybindings
from llamatron.tui.components.control_row import ControlRow
from llamatron.user_strings import errors

# Which register each += row adds to, by the row's name.
REGISTER_OF_ROW = {row: name for name, row in file_format.REGISTER_ADD_ROWS.items()}


class AddRow(ControlRow):
    """The same keys as a number row, on every step, held from minus the register's Allowed Inc Max to plus it.

    The limit is the narrowest of the songs that play the pattern, or the current song's when
    none does, so that [ and ] step through a short line.
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
            self.editor.refuse(errors.ERR_AT_ALLOWED_INC_MAX.format(register=REGISTER_OF_ROW[self.name], most=high))
        self.set_value(max(min(moved, high), low))
