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

"""The Message dialog dialog."""

from llamatron.tui.dialogs.dialog import Dialog
from rich.text import Text

from llamatron.strings.labels import MSG_OK_BUTTON
from llamatron.tui.components.button_row import button_row
from llamatron.tui.drawing import NOTHING, wrapped
from llamatron.tui import keybindings


class MessageDialog(Dialog):

    KEYS = keybindings.MessageDialog

    def __init__(self, *, title, messages):
        super().__init__()
        self.title = title
        self.messages = messages

    def keys(self):
        return [self.bind(self.KEYS.CLOSE, action=lambda: self.dismiss(None))]

    def lines(self, width):
        """Return the messages, a blank line and the one OK button, boxed as a real window's, the user's design."""
        _, key_name, _ = self.KEYS.CLOSE
        return [*self.message_lines(width), Text(NOTHING), *button_row(buttons=[(key_name, MSG_OK_BUTTON)], selected=0)]

    def message_lines(self, width):
        """Return the messages as lines, each wrapped to the dialog's width. A dialog that says more than its messages draws them here."""
        result = []
        for message in self.messages:
            result += wrapped(text=message, width=width)
        return result
