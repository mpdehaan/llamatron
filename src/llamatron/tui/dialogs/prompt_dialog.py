# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Prompt dialog: asks for a line of text, and answers with it."""

from rich.text import Text

from llamatron.tui import drawing, keybindings
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import Style
from llamatron.tui.key_table import pressed_key, quits_at_once
from llamatron.tui.keys import Key
from llamatron.user_strings import marks

# How far the cursor moves for one arrow press.
ONE_CHARACTER = 1


class PromptDialog(Dialog):
    """Asks for a line of text, and answers with it.

    The cursor starts after the text, so that typing adds to it, and left and right move it so
    that a name like foo.yml can be changed to foo2.yml without erasing the end first.
    """

    KEYS = keybindings.PromptDialog

    def __init__(self, *, title, value=drawing.NOTHING, max_length=None, label=drawing.NOTHING):
        super().__init__()
        self.title = title
        # What the text is, written before it, for a prompt whose title says something else, as a confirmation's does.
        self.label = label
        self.value = str(value)
        # The most characters the text may hold, for a name, or None for any length. A longer text given to start with, an older
        # file's name, stays until it is erased, and takes no more.
        self.max_length = max_length
        self._cursor = len(self.value)

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.DONE, action=lambda: self.dismiss(self.value)),
            self.bind(self.KEYS.ERASE, action=self.erase),
        ]

    def cursor(self):
        """Return where the cursor is, from 0 to the text's length, since the text can be replaced from outside."""
        return max(min(self._cursor, len(self.value)), 0)

    def move_cursor(self, name):
        step = -ONE_CHARACTER if name == Key.LEFT else ONE_CHARACTER
        self._cursor = max(min(self.cursor() + step, len(self.value)), 0)

    def erase(self):
        """Erase the character before the cursor, and move the cursor back over it."""
        cursor = self.cursor()
        if cursor:
            self.value = self.value[:cursor - ONE_CHARACTER] + self.value[cursor:]
            self._cursor = cursor - ONE_CHARACTER

    def insert(self, character):
        """Put a character where the cursor is, and move the cursor past it, unless the text is as long as it may be."""
        if self.max_length is not None and len(self.value) + len(character) > self.max_length:
            return
        cursor = self.cursor()
        self.value = self.value[:cursor] + character + self.value[cursor:]
        self._cursor = cursor + len(character)

    def lines(self, width):
        # The text scrolls so that the cursor always shows, with the cursor drawn in reverse video
        # over the character it's before, or over a space when it's at the end.
        shown = width - len(marks.MSG_PROMPT_MARK) - len(self.label) - 1
        cursor = self.cursor()
        start = max(cursor - shown + 1, 0)
        text = self.value[start:start + shown]
        at = cursor - start
        line = Text(marks.MSG_PROMPT_MARK + self.label + text[:at])
        line.append(text[at:at + 1] or drawing.SPACE, style=Style.REVERSE)
        line.append(text[at + 1:])
        return [line]

    def other_key(self, event):
        if event.character and event.character.isprintable():
            self.insert(event.character)
            self.draw()

    def takes_text(self):
        return True

    def on_key(self, event):
        # Letters are text here, so only the named keys are handled by the table.
        event.stop()
        event.prevent_default()
        name = pressed_key(event)
        if quits_at_once(name):
            self.app.exit()
            return
        for item in self.keys():
            if name in item.keys:
                item.press(name)
                if self.is_attached:
                    self.draw()
                return
        self.other_key(event)
