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

"""The Scale row of the pattern editor: the scale type a step's degree and chord are drawn from, on the clip's root, which is how a chord is borrowed (the user's design)."""

from llamatron.composition.naming import words
from llamatron.strings.marks import MSG_UNSET_MARK
from llamatron.tui.components.chord_row import ChordRow
from llamatron.tui.scale_categories import SCALE_TYPES_IN_ORDER
from llamatron.tui.drawing import NOTHING
from llamatron.tui import keybindings

# How much of a scale type's name a cell shows; the status line and the Chord dialog say it whole.
CELL_ROOM = 5


class ChordScaleRow(ChordRow):
    """Enter opens the Chord dialog on its scales, Space or ] and [ step through the scale types, and Bksp clears, which is the clip's own scale."""

    KEYS = keybindings.ChordScaleRow

    __slots__ = ()

    def options(self):
        return [None, *SCALE_TYPES_IN_ORDER]

    def cell_text(self, *, step):
        if self.blocked(step=step):
            return NOTHING
        value = self.value(step=step)
        return MSG_UNSET_MARK if value is None else words(value).title()[:CELL_ROOM]
