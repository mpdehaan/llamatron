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

"""The Tension row of the pattern editor: the notes added on top of a step's chord, like a flat ninth (the user's design)."""

from llamatron.composition.file_format import Row
from llamatron.strings.marks import MSG_TENSIONS_COUNTED, MSG_TENSIONS_IN_CELL_SEPARATOR, MSG_UNSET_MARK
from llamatron.tui.components.chord_row import ChordRow
from llamatron.tui.drawing import NOTHING
from llamatron.tui import keybindings

# The widest a step's tensions are written out in a cell; more are counted.
CELL_ROOM = 5


class TensionRow(ChordRow):
    """Enter opens the Chord dialog on its tensions, Space or ] and [ step through each tension alone, and Bksp clears; a step with no chord can't take one, since a single note has no tensions."""

    KEYS = keybindings.TensionRow

    __slots__ = ()

    def blocked(self, *, step=None):
        return not self.is_note(step=step) or self.editor.value(row=Row.CHORD, step=step) is None

    def options(self):
        return [None, *[(tension,) for tension in self.described().get_choices()]]

    def cell_text(self, *, step):
        if self.blocked(step=step):
            return NOTHING
        value = self.value(step=step)
        if value is None:
            return MSG_UNSET_MARK
        for separator in (MSG_TENSIONS_IN_CELL_SEPARATOR, NOTHING):
            if len(separator.join(value)) <= CELL_ROOM:
                return separator.join(value)
        return MSG_TENSIONS_COUNTED.format(count=len(value))
