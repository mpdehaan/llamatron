# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Grab row: a toggle that works on every step, and makes an empty step a note.

A grab can be marked on an empty step: marking it gives the
step the root in the default octave as a note of its own, which the grab overrides at render, so
that the step has a velocity, a gate and the rest like any note and the note rows open on it. A
step that grabs can hold a chord, which is built on the grabbed note.
"""

from llamatron.model.values.note import NoteName
from llamatron.model.vocabulary import limits
from llamatron.model.vocabulary.file_format import Row
from llamatron.tui import keybindings
from llamatron.tui.components.toggle_row import ToggleRow

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
            self.editor.set_value(value=DRUM_GRAB_NOTE if self.editor.is_drum() else limits.MIN_DEGREE, row=Row.DEGREE)
            self.editor.fill_in()
        super().toggle()
