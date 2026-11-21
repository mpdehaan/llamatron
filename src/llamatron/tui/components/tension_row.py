# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Tension row of the pattern editor: the notes added on top of a step's chord, like a flat ninth."""

from llamatron.model.vocabulary.file_format import Row
from llamatron.tui import drawing, keybindings
from llamatron.tui.components.chord_row import ChordRow
from llamatron.user_strings import marks

# The widest a step's tensions are written out in a cell; more are counted.
CELL_ROOM = 5


class TensionRow(ChordRow):
    """Enter opens the Chord dialog on its tensions, Space or ] and [ step through each tension alone, and Bksp clears; a step with no chord can't take one, since a single note has no tensions."""

    KEYS = keybindings.TensionRow

    __slots__ = ()

    def blocked(self, *, step=None):
        return not self.is_note(step=step) or self.editor.value(row=Row.CHORD, step=step) is None

    def options(self):
        return [None, *[(tension,) for tension in self.described().get_choices()]]

    def cell_text(self, *, step):
        if self.blocked(step=step):
            return drawing.NOTHING
        value = self.value(step=step)
        if value is None:
            return marks.MSG_UNSET_MARK
        for separator in (marks.MSG_TENSIONS_IN_CELL_SEPARATOR, drawing.NOTHING):
            if len(separator.join(value)) <= CELL_ROOM:
                return separator.join(value)
        return marks.MSG_TENSIONS_COUNTED.format(count=len(value))
