# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The dialog after an import: what the song was imported as, what it holds, and every warning, or that there were none, with one OK button.

There is nothing to choose, since the song is in the set already; the dialog makes sure what the
import had to change, like CCs left out or notes moved to a step, is seen before going on. Enter
or Esc closes it.
"""

from rich.text import Text

from llamatron.tui import drawing, keybindings
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.drawing import wrapped
from llamatron.user_strings import importing


class ImportedDialog(MessageDialog):
    """Says what an import made and what it had to change, with one OK button."""

    KEYS = keybindings.ImportedDialog
    shows_legend = False

    def __init__(self, imported):
        made = [
            importing.MSG_IMPORTED_SONG.format(name=imported.song.name),
            importing.MSG_IMPORTED_COUNTS.format(tracks=imported.tracks, patterns=imported.patterns, scenes=imported.scenes),
            importing.MSG_IMPORTED_WARNINGS if imported.warnings else importing.MSG_IMPORTED_NO_WARNINGS,
        ]
        super().__init__(title=importing.MSG_IMPORTED_TITLE, messages=made)
        self.warnings = imported.warnings

    def lines(self, width):
        lines = self.message_lines(width)
        for warning in self.warnings:
            lines += [Text(drawing.NOTHING), *wrapped(text=warning, width=width)]
        return [*lines, Text(drawing.NOTHING), *button_row(buttons=[(self.KEYS.CLOSE.name, importing.MSG_IMPORTED_BUTTON)], selected=0)]
