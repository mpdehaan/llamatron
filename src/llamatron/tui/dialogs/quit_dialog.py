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

"""The Quit dialog, asked when quitting with unsaved changes: Quit without saving, Save, then Quit, and Cancel as boxed buttons, the
user's design and words. Left and Right choose, Enter presses, Q and S answer at once and Esc cancels. It answers QUIT_WITHOUT_SAVING,
SAVE_THEN_QUIT, or None for Cancel."""

from rich.text import Text

from llamatron.strings.labels import MSG_QUIT_BUTTONS
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.drawing import NOTHING, legend
from llamatron.tui.key_table import cursor_moved
from llamatron.tui import keybindings

# A width no legend reaches, to measure the keys on one line.
UNLIMITED_WIDTH = 1000
# The buttons' places, in the order of MSG_QUIT_BUTTONS.
QUIT_WITHOUT_SAVING = 0
SAVE_THEN_QUIT = 1
CANCEL = 2


class QuitDialog(MessageDialog):
    """Asks what to do with unsaved changes on quitting."""

    KEYS = keybindings.QuitDialog

    def __init__(self, *, title, messages):
        super().__init__(title=title, messages=messages)
        self.choice = QUIT_WITHOUT_SAVING

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.SELECT, action=self.move, wants_key=True),
            self.bind(self.KEYS.PRESS, action=self.press_selected),
            self.bind(self.KEYS.QUIT, action=lambda: self.dismiss(QUIT_WITHOUT_SAVING)),
            self.bind(self.KEYS.SAVE, action=lambda: self.dismiss(SAVE_THEN_QUIT)),
        ]

    def wanted_width(self):
        """Return a width that holds the dialog's keys on one line, where the console has the room, since they are too many for the usual width (the user's ask)."""
        keys_on_one_line = max(line.cell_len for line in legend(keys=self.keys(), width=UNLIMITED_WIDTH))
        return max(super().wanted_width(), keys_on_one_line + DIALOG_MARGIN)

    def move(self, name):
        self.choice = cursor_moved(place=self.choice, name=name, count=len(MSG_QUIT_BUTTONS))

    def press_selected(self):
        self.dismiss(None if self.choice == CANCEL else self.choice)

    def lines(self, width):
        keys = (self.KEYS.QUIT[1], self.KEYS.SAVE[1], self.KEYS.CANCEL[1])
        buttons = list(zip(keys, MSG_QUIT_BUTTONS))
        return [*self.message_lines(width), Text(NOTHING), *button_row(buttons=buttons, selected=self.choice)]
