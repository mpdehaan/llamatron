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
"""The Grab row: a toggle that works on every step, and makes an empty step a note.

The user decided on 2026-11-08 that a grab can be marked on an empty step: marking it gives the
step the root in the default octave as a note of its own, which the grab overrides at render, so
that the step has a velocity, a gate and the rest like any note and the note rows open on it. A
step that grabs can hold a chord, which is built on the grabbed note, as the user asked on
2026-11-09: until then the Chord row was blocked on such a step.
"""

from llamatron.composition.file_format import Row
from llamatron.composition.limits import MIN_DEGREE
from llamatron.music.note import NoteName
from llamatron.tui.components.toggle_row import ToggleRow
from llamatron.tui import keybindings

# What an empty step gets as its own note when it's marked to grab: the root, or C on a drum pattern.
DRUM_GRAB_NOTE = NoteName.C


class GrabRow(ToggleRow):
    """Space marks or unmarks the step, giving an empty step a note first, and Bksp unmarks it."""

    KEYS = keybindings.GrabRow

    __slots__ = ()

    def on_rests(self):
        return True

    def toggle(self):
        if not self.value() and not self.is_note():
            self.editor.set_value(value=DRUM_GRAB_NOTE if self.editor.is_drum() else MIN_DEGREE, row=Row.DEGREE)
            self.editor.fill_in()
        super().toggle()
