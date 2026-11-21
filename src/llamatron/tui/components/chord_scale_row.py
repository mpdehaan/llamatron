# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Scale row of the pattern editor: the scale type a step's degree and chord are drawn from, on the clip's root, which is how a chord is borrowed."""

from llamatron.composition.naming import words
from llamatron.tui import drawing, keybindings, scale_categories
from llamatron.tui.components.chord_row import ChordRow
from llamatron.user_strings import marks

# How much of a scale type's name a cell shows; the status line and the Chord dialog say it whole.
CELL_ROOM = 5


class ChordScaleRow(ChordRow):
    """Enter opens the Chord dialog on its scales, Space or ] and [ step through the scale types, and Bksp clears, which is the clip's own scale."""

    KEYS = keybindings.ChordScaleRow

    __slots__ = ()

    def options(self):
        return [None, *scale_categories.SCALE_TYPES_IN_ORDER]

    def cell_text(self, *, step):
        if self.blocked(step=step):
            return drawing.NOTHING
        value = self.value(step=step)
        return marks.MSG_UNSET_MARK if value is None else words(value).title()[:CELL_ROOM]
