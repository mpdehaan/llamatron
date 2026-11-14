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
"""The Prompt dialog: asks for a line of text, and answers with it."""

from rich.text import Text

from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import NOTHING, SPACE, Style
from llamatron.tui.key_table import pressed_key, quits_at_once
from llamatron.tui.keys import Key
from llamatron.strings.marks import MSG_PROMPT_MARK
from llamatron.tui import keybindings

# How far the cursor moves for one arrow press.
ONE_CHARACTER = 1


class PromptDialog(Dialog):
    """Asks for a line of text, and answers with it.

    The cursor starts after the text, so that typing adds to it, and left and right move it so
    that a name like foo.yml can be changed to foo2.yml without erasing the end first.
    """

    KEYS = keybindings.PromptDialog

    def __init__(self, *, title, value=NOTHING):
        super().__init__()
        self.title = title
        self.value = str(value)
        self._cursor = len(self.value)

    def keys(self):
        return [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.DONE, action=lambda: self.dismiss(self.value)),
            self.bind(self.KEYS.ERASE, action=self.erase),
        ]

    def cursor(self):
        """Return where the cursor is, from 0 to the text's length, since the text can be replaced from outside."""
        return max(min(self._cursor, len(self.value)), 0)

    def move(self, name):
        step = -ONE_CHARACTER if name == Key.LEFT else ONE_CHARACTER
        self._cursor = max(min(self.cursor() + step, len(self.value)), 0)

    def erase(self):
        """Erase the character before the cursor, and move the cursor back over it."""
        cursor = self.cursor()
        if cursor:
            self.value = self.value[:cursor - ONE_CHARACTER] + self.value[cursor:]
            self._cursor = cursor - ONE_CHARACTER

    def insert(self, character):
        """Put a character where the cursor is, and move the cursor past it."""
        cursor = self.cursor()
        self.value = self.value[:cursor] + character + self.value[cursor:]
        self._cursor = cursor + len(character)

    def lines(self, width):
        # The text scrolls so that the cursor always shows, with the cursor drawn in reverse video
        # over the character it's before, or over a space when it's at the end.
        shown = width - len(MSG_PROMPT_MARK) - 1
        cursor = self.cursor()
        start = max(cursor - shown + 1, 0)
        text = self.value[start:start + shown]
        at = cursor - start
        line = Text(MSG_PROMPT_MARK + text[:at])
        line.append(text[at:at + 1] or SPACE, style=Style.REVERSE)
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
