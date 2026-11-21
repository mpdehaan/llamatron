# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Message dialog dialog."""

from rich.text import Text

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.drawing import wrapped
from llamatron.user_strings import labels


class MessageDialog(Dialog):

    """A dialog that says one thing and waits for OK."""

    KEYS = keybindings.MessageDialog

    def __init__(self, *, title, messages):
        super().__init__()
        self.title = title
        self.messages = messages

    def keys(self):
        return [self.bind(self.KEYS.CLOSE, action=lambda: self.dismiss(None))]

    def lines(self, width):
        """Return the messages, a blank line and the one OK button, boxed as a real window's."""
        return [*self.message_lines(width), Text(drawing.NOTHING), *button_row(buttons=[(self.KEYS.CLOSE.name, labels.MSG_OK_BUTTON)], selected=0)]

    def message_lines(self, width):
        """Return the messages as lines, each wrapped to the dialog's width. A dialog that says more than its messages draws them here."""
        result = []
        for message in self.messages:
            result += wrapped(text=message, width=width)
        return result
