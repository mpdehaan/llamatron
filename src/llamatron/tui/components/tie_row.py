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

"""The Tie row: a toggle on the empty steps after a note, each tied step marked like any toggle that's on.

A tie is stored only on an empty step, which holds the note before it to the step's end. The user
chose the plain toggle mark on 2026-11-08 over a bar running through the dividers, which read
badly and broke the beat lines. A note's own step can't take a tie, so its cell is blocked
like any cell that can't take a value: the user decided on 2026-11-08 that a note never draws a tie
of its own, since ties are optional and only ever added on the steps after a note, in place of a
longer gate.
"""

from llamatron.tui.components.toggle_row import ToggleRow
from llamatron.tui import keybindings


class TieRow(ToggleRow):
    """A toggle on empty steps only: a step with a note can't hold a tie, since a tie holds the note before it, so it's blocked there."""

    KEYS = keybindings.TieRow

    __slots__ = ()

    def on_rests(self):
        return True

    def blocked(self, *, step=None):
        return self.is_note(step=step)

    def tied(self, step):
        return 0 <= step < self.editor.steps() and bool(self.value(step=step))
