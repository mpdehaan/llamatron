# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Confirm dialog: answers True for yes. Anything else that closes it counts as no."""

from rich.text import Text

from llamatron.interface.forms import moves
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.user_strings import labels


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

    def __init__(self, *, title, messages, starts_on_no=False, deletes=False):
        super().__init__(title=title, messages=messages)
        self.deletes = deletes
        # A question whose yes is easy to give by accident starts on No, so that ENTER alone changes nothing.
        self.choice = NO if starts_on_no else YES

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.ANSWER, action=self.answer),
            self.bind(self.KEYS.YES, action=lambda: self.dismiss(True)),
            self.bind(self.KEYS.NO, action=lambda: self.dismiss(None)),
        ]

    def move_cursor(self, name):
        self.choice = moves.moved(place=self.choice, name=name, count=len(labels.MSG_CONFIRM_BUTTONS))

    def answer(self):
        self.dismiss(True if self.choice == YES else None)

    def lines(self, width):
        """Return the message, a blank line and Yes and No as boxed buttons, the selected one double-lined."""
        buttons = [(binding.name, label) for label, binding in zip(labels.MSG_CONFIRM_BUTTONS, BUTTON_BINDINGS)]
        return [*self.message_lines(width), Text(drawing.NOTHING), *button_row(buttons=buttons, selected=self.choice)]
