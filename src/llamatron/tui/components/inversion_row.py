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
"""The Inversion row of the pattern editor: how many of a step's chord's lowest notes move up an octave."""

from llamatron.composition.file_format import Row
from llamatron.tui.components.cycle_row import CycleRow
from llamatron.tui.drawing import NOTHING
from llamatron.tui import keybindings


class InversionRow(CycleRow):
    """Blank for root position, then 1, 2 and 3; a step with no chord can't take one, since one note has no inversion."""

    KEYS = keybindings.InversionRow

    __slots__ = ()

    def blocked(self, *, step=None):
        return not self.is_note(step=step) or self.editor.value(row=Row.CHORD, step=step) is None

    def cell_text(self, *, step):
        value = self.value(step=step)
        return NOTHING if self.blocked(step=step) or value is None else str(value)
