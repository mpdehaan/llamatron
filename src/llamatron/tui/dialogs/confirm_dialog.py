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

"""The Confirm dialog: answers True for yes. Anything else that closes it counts as no."""

from rich.text import Text

from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.components.button_row import button_row
from llamatron.tui.drawing import NOTHING
from llamatron.tui.key_table import cursor_moved
from llamatron.strings.labels import MSG_CONFIRM_BUTTONS
from llamatron.tui import keybindings


# The two buttons' places, in the order MSG_CONFIRM_BUTTONS draws them, and the binding whose key each shows.
YES = 0
NO = 1
BUTTON_BINDINGS = (keybindings.ConfirmDialog.YES, keybindings.ConfirmDialog.NO)


class ConfirmDialog(MessageDialog):
    """Answers True for yes. Anything else that closes it counts as no.

    Yes and No are boxed buttons under the message, like a real window's: Left and
    Right move between them and Enter presses the selected one, while Y and N still answer at once.
    """

    KEYS = keybindings.ConfirmDialog

    def __init__(self, *, title, messages):
        super().__init__(title=title, messages=messages)
        self.choice = YES

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.SELECT, action=self.move, wants_key=True),
            self.bind(self.KEYS.ANSWER, action=self.answer),
            self.bind(self.KEYS.YES, action=lambda: self.dismiss(True)),
            self.bind(self.KEYS.NO, action=lambda: self.dismiss(None)),
        ]

    def move(self, name):
        self.choice = cursor_moved(place=self.choice, name=name, count=len(MSG_CONFIRM_BUTTONS))

    def answer(self):
        self.dismiss(True if self.choice == YES else None)

    def lines(self, width):
        """Return the message, a blank line and Yes and No as boxed buttons, the selected one double-lined, the user's design."""
        buttons = [(binding[1], label) for label, binding in zip(MSG_CONFIRM_BUTTONS, BUTTON_BINDINGS)]
        return [*self.message_lines(width), Text(NOTHING), *button_row(buttons=buttons, selected=self.choice)]
