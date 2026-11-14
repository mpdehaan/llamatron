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
"""The Octave row, typed and shown in the set's octave labels and stored as the file numbers octaves."""

from llamatron.composition.file_format import Row
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.drawing import NOTHING
from llamatron.tui.keys import DIGITS
from llamatron.strings.legends import MSG_DIGITS_RANGE_LABEL
from llamatron.tui import keybindings


class OctaveRow(PatternRow):
    """Digits type an octave, + and - move it, and Bksp goes back to the song's default."""

    KEYS = keybindings.OctaveRow

    __slots__ = ()

    def rule_after(self):
        """A rule closes the pinned rows, so that the sections' rows scroll under a fixed line and a heading right under it needs no rule of its own."""
        return True

    def keys(self):
        return [
            self.bind(self.KEYS.TYPE, action=self.type_octave, wants_key=True, name=self.digits_label()),
            *self.adjust_keys(),
            self.bind(self.KEYS.DEFAULT, action=lambda: self.set_value(None)),
        ]

    def song(self):
        return self.editor.document().song()

    def lowest(self):
        """Return the lowest octave a step can hold, as a file numbers octaves."""
        return self.described().get_lowest()

    def highest(self):
        return self.described().get_highest()

    def digits_label(self):
        """Return the digits label, which runs up to the top octave in the song's octave labels."""
        return MSG_DIGITS_RANGE_LABEL.format(low=DIGITS[0], high=self.song().shown_octave(self.highest()))

    def type_octave(self, digit):
        """Take a typed octave, which is typed in the song's octave labels, and store it as the file numbers it."""
        song = self.song()
        number = self.editor.typed_number(digit=digit, low=song.shown_octave(self.lowest()), high=song.shown_octave(self.highest()))
        if number is not None:
            self.set_value(song.stored_octave(number))

    def octave_now(self, *, step=None):
        current = self.value(step=step)
        return self.editor.default_octave() if current is None else current

    def nudge(self, offset):
        self.set_value(max(min(self.octave_now() + offset, self.highest()), self.lowest()))

    def cell_text(self, *, step):
        """Return the octave the note plays in, which a degree past the scale's top moves up."""
        if not self.is_note(step=step):
            return NOTHING
        shift = self.editor.row_for(Row.DEGREE).octave_shift(step=step)
        return str(self.song().shown_octave(self.octave_now(step=step) + shift))
