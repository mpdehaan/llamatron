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
"""The Gate row: how long a note sounds, one step when blank, as a whole number or fraction of whole notes."""

from llamatron.composition.file_format import GATE_LENGTH_CHOICES
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.drawing import NOTHING
from llamatron.composition.checks import fraction_text
from llamatron.tui.text import fraction
from llamatron.strings.messages import MSG_GATE_PROMPT
from llamatron.tui import keybindings

class GateRow(PatternRow):
    """[ and ] step through the plain lengths, Enter types any length and Bksp makes it one step."""

    KEYS = keybindings.GateRow

    __slots__ = ()

    def keys(self):
        return [
            *self.adjust_keys(),
            self.bind(self.KEYS.TYPE, action=self.ask),
            self.bind(self.KEYS.ONE_STEP, action=lambda: self.set_value(None)),
        ]

    def gate_now(self, *, step=None):
        """Return a step's gate before its Dot row, which is one step if it has none."""
        current = self.value(step=step)
        return self.editor.document().lengths().step_size(self.editor.item) if current is None else fraction(current)

    def set_gate(self, length):
        self.set_value(fraction_text(length))

    def nudge(self, offset):
        """Set the gate to the next plain length longer or shorter than it is now."""
        now = self.gate_now()
        lengths = [fraction(length) for length in GATE_LENGTH_CHOICES]
        if offset > 0:
            choices = [length for length in lengths if length > now] or [lengths[-1]]
            self.set_gate(choices[0])
        else:
            choices = [length for length in lengths if length < now] or [lengths[0]]
            self.set_gate(choices[-1])

    def ask(self):
        self.editor.ask_length(title=MSG_GATE_PROMPT, current=self.value() or NOTHING, most=self.described().get_most(), then=self.set_value, blank_allowed=False)

    def cell_text(self, *, step):
        """A rest has no gate, and a blank gate is one step."""
        value = self.value(step=step)
        return NOTHING if not self.is_note(step=step) or value is None else str(value)
