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
"""The dialog after an import: what the song was imported as, what it holds, and every warning, or that there were none, with one OK button, the user's design of 2026-11-10.

There is nothing to choose, since the song is in the set already; the dialog makes sure what the
import had to change, like CCs left out or notes moved to a step, is seen before going on. Enter
or Esc closes it.
"""

from rich.text import Text

from llamatron.strings.importing import (
    MSG_IMPORTED_BUTTON, MSG_IMPORTED_COUNTS, MSG_IMPORTED_NO_WARNINGS, MSG_IMPORTED_SONG, MSG_IMPORTED_TITLE, MSG_IMPORTED_WARNINGS,
)
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.drawing import NOTHING, wrapped
from llamatron.tui import keybindings


class ImportedDialog(MessageDialog):
    """Says what an import made and what it had to change, with one OK button."""

    KEYS = keybindings.ImportedDialog
    shows_legend = False

    def __init__(self, imported):
        made = [
            MSG_IMPORTED_SONG.format(name=imported.song.name),
            MSG_IMPORTED_COUNTS.format(tracks=imported.tracks, patterns=imported.patterns, scenes=imported.scenes),
            MSG_IMPORTED_WARNINGS if imported.warnings else MSG_IMPORTED_NO_WARNINGS,
        ]
        super().__init__(title=MSG_IMPORTED_TITLE, messages=made)
        self.warnings = imported.warnings

    def lines(self, width):
        lines = self.message_lines(width)
        for warning in self.warnings:
            lines += [Text(NOTHING), *wrapped(text=warning, width=width)]
        _, key_name, _ = self.KEYS.CLOSE
        return [*lines, Text(NOTHING), *button_row(buttons=[(key_name, MSG_IMPORTED_BUTTON)], selected=0)]
