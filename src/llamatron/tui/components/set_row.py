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
"""A register's = row: the value a step sets the register to before anything adds to it, or blank to leave the register as it is."""

from llamatron.composition.file_format import REGISTER_SET_ROWS
from llamatron.tui.components.control_row import ControlRow
from llamatron.tui import keybindings

# Which register each = row sets, by the row's name.
REGISTER_OF_ROW = {row: name for name, row in REGISTER_SET_ROWS.items()}


class SetRow(ControlRow):
    """The number line runs from blank up through the current song's register, the user's design of 2026-11-11.

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
