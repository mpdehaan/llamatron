# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A row that's on or off for each step, like Glide, Grab and the registers' uses."""

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.pattern_row import PatternRow
from llamatron.user_strings import marks


class ToggleRow(PatternRow):
    """Space or Enter switches the step's value, and Bksp switches it off."""

    KEYS = keybindings.ToggleRow

    __slots__ = ()

    def keys(self):
        return [
            self.bind(self.KEYS.TOGGLE, action=self.toggle),
            self.bind(self.KEYS.CLEAR, action=lambda: self.set_value(False)),
        ]

    def toggle(self):
        self.set_value(not self.value())

    def cell_text(self, *, step):
        if not self.is_note(step=step) and not self.on_rests():
            return drawing.NOTHING
        return marks.MSG_TOGGLE_ON if self.value(step=step) else marks.MSG_TOGGLE_OFF
