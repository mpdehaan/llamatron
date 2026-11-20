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
"""A draw's Reset row in the Use Draws section: a step that sends the draw back to its start, or a serial draw to a new round, before it draws."""

from llamatron.tui import keybindings
from llamatron.tui.components.toggle_row import ToggleRow


class DrawResetRow(ToggleRow):
    """A toggle on every step, since a step with no note can reset a draw for the steps after it."""

    KEYS = keybindings.DrawResetRow

    __slots__ = ()

    def on_rests(self):
        return True
