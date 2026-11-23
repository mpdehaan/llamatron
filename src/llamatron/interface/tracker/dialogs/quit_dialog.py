# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Quit dialog, asked when quitting with unsaved changes: Quit without saving, Save, then Quit, and Cancel as boxed buttons.
Left and Right choose, Enter presses, Q and S answer at once and Esc cancels. It answers QUIT_WITHOUT_SAVING,
SAVE_THEN_QUIT, or None for Cancel."""

from rich.text import Text

from llamatron.interface.forms import moves
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.components.button_row import button_row
from llamatron.interface.tracker.dialogs import dialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.drawing import legend
from llamatron.user_strings import labels

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
            self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.PRESS, action=self.press_selected),
            self.bind(self.KEYS.QUIT, action=lambda: self.dismiss(QUIT_WITHOUT_SAVING)),
            self.bind(self.KEYS.SAVE, action=lambda: self.dismiss(SAVE_THEN_QUIT)),
        ]

    def wanted_width(self):
        """Return a width that holds the dialog's keys on one line, where the console has the room, since they are too many for the usual width."""
        shown = [item for item in self.keys() if item.shown]
        keys_on_one_line = max(line.cell_len for line in legend(keys=shown, width=UNLIMITED_WIDTH))
        return max(super().wanted_width(), keys_on_one_line + dialog.DIALOG_MARGIN)

    def move_cursor(self, name):
        self.choice = moves.moved(place=self.choice, name=name, count=len(labels.MSG_QUIT_BUTTONS))

    def press_selected(self):
        self.dismiss(None if self.choice == CANCEL else self.choice)

    def lines(self, width):
        keys = (self.KEYS.QUIT.name, self.KEYS.SAVE.name, self.KEYS.CANCEL.name)
        buttons = list(zip(keys, labels.MSG_QUIT_BUTTONS))
        return [*self.message_lines(width), Text(drawing.NOTHING), *button_row(buttons=buttons, selected=self.choice)]
