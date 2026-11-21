# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Inversion row of the pattern editor: how many of a step's chord's lowest notes move up an octave."""

from llamatron.model.vocabulary.file_format import Row
from llamatron.tui import drawing, keybindings
from llamatron.tui.components.cycle_row import CycleRow


class InversionRow(CycleRow):
    """Blank for root position, then 1, 2 and 3; a step with no chord can't take one, since one note has no inversion."""

    KEYS = keybindings.InversionRow

    __slots__ = ()

    def blocked(self, *, step=None):
        return not self.is_note(step=step) or self.editor.value(row=Row.CHORD, step=step) is None

    def cell_text(self, *, step):
        value = self.value(step=step)
        return drawing.NOTHING if self.blocked(step=step) or value is None else str(value)
