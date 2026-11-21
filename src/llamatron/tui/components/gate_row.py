# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Gate row: how long a note sounds, one step when blank, as a whole number or fraction of whole notes."""

from llamatron.model.file.checks import fraction_text
from llamatron.model.schema import file_format
from llamatron.tui import drawing, keybindings
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.text import fraction
from llamatron.user_strings import messages

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
        lengths = [fraction(length) for length in file_format.GATE_LENGTH_CHOICES]
        if offset > 0:
            choices = [length for length in lengths if length > now] or [lengths[-1]]
            self.set_gate(choices[0])
        else:
            choices = [length for length in lengths if length < now] or [lengths[0]]
            self.set_gate(choices[-1])

    def ask(self):
        self.editor.ask_length(title=messages.MSG_GATE_PROMPT, current=self.value() or drawing.NOTHING, most=self.described().get_most(), then=self.set_value, blank_allowed=False)

    def cell_text(self, *, step):
        """A rest has no gate, and a blank gate is one step."""
        value = self.value(step=step)
        return drawing.NOTHING if not self.is_note(step=step) or value is None else str(value)
