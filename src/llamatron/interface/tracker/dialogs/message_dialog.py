# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Message dialog: a title, what it says, and one OK button."""

from llamatron.interface.forms.dialogs import answers, said
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.dialog import Dialog
from llamatron.interface.tracker.renderers import dialogs as dialog_renderer
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
        """Return what the dialog says, a blank line and its answers, drawn from its nodes."""
        return dialog_renderer.message_lines(paragraphs=self.paragraphs(), answers=self.answers(), width=width)

    def paragraphs(self):
        """Return what the dialog says, each message a paragraph wrapped to the dialog."""
        return [said(message) for message in self.messages]

    def answers(self):
        """Return the one OK button, boxed as a real window's, its name alone, since ENTER or ESC closes the dialog."""
        return answers(labels=[labels.MSG_OK_BUTTON], selected=0)
