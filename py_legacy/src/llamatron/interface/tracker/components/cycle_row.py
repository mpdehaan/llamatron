# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A row whose values go round a short fixed cycle, like the Dot and accidental rows."""

from llamatron.interface.tracker import key_table, keybindings
from llamatron.interface.tracker.components.pattern_row import PatternRow


class CycleRow(PatternRow):
    """Space or Enter goes to the next of the row's choices, ] does the same and [ goes to the one before, and Bksp clears, which is where the choices start."""

    KEYS = keybindings.CycleRow

    __slots__ = ()
    def keys(self):
        return [
            self.bind(self.KEYS.NEXT, action=lambda: self.cycle(key_table.STEP_FORWARD)),
            *self.adjust_keys(),
            self.bind(self.KEYS.CLEAR, action=lambda: self.set_value(None)),
        ]

    def choices(self):
        """Return the values in the order + steps through them: the row's blank first, then the choices of the row's one description."""
        return [self.described().blank(), *self.described().get_choices()]

    def nudge(self, offset):
        """[ and ] go round the cycle, as they step a number on the other rows."""
        self.cycle(offset)

    def cycle(self, offset):
        choices = self.choices()
        value = self.value()
        # A row with no values yet answers None, which is the row's blank.
        place = choices.index(self.described().blank() if value is None else value)
        self.set_value(choices[(place + offset) % len(choices)])
