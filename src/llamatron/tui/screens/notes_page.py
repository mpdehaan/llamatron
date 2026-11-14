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

"""The Notes page: the set's notes, text of any length, for people reading or sharing the file."""

import textwrap

from rich.text import Text

from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import cursor_mark, INDENT, LINE_BREAK, NOTHING, padded, SPACE, Style
from llamatron.strings.help import HELP_NOTES_PAGE
from llamatron.tui.key_table import cursor_moved, pressed_key, quits_at_once
from llamatron.tui.keys import ARROWS_UP_DOWN, Key
from llamatron.tui.screens.page import Page
from llamatron.strings.labels import Crumb, MSG_NOTES_BUTTONS
from llamatron.strings.marks import MSG_CONFIRM_BUTTON_GAP
from llamatron.strings.messages import (
    MSG_CLEAR_NOTES_QUESTION, MSG_CLEAR_NOTES_TITLE, MSG_NOTES_PROTECTED, MSG_NO_NOTES_PROTECTED, MSG_EDITING,
    MSG_NO_NOTES_NOTE,
)
from llamatron.tui import themes
from llamatron.tui import keybindings


# While editing, these keys still work as keys rather than typing text.
TEXT_EDITING_KEYS = (Key.ENTER, Key.TAB, Key.BACKSPACE)
# The two buttons' places, in the order MSG_NOTES_BUTTONS draws them.
SAVE = 0
CANCEL = 1
# The blank line and the button row under the text while editing.
BUTTON_LINES = 2


class NotesPage(Page):

    THEME = themes.SET_FILE
    """The set's notes: text of any length, for people reading or sharing the file.

    Enter on the File page's Notes field opens it editing, and E starts editing again after
    Save or Cancel has stopped it. While editing, letters are text, as in a name prompt, so H types
    an h. A protected set's notes can only be read, so it opens reading and offers no E or
    Bksp.

    While editing, the text is a draft of the page's own, and the Save button under it, which Tab
    reaches, stores it in the set, so that everything typed between E and Save is one undo step:
    undo never works letter by letter, as the user decided. Esc, or the Cancel button, throws the
    draft away, as the user asked on 2026-11-08. Nothing is written to the file; that's Ctrl+S, as
    everywhere.
    """

    KEYS = keybindings.NotesPage

    crumbs = (Crumb.FILE, Crumb.NOTES)
    HELP = HELP_NOTES_PAGE

    def __init__(self, holder, *, editing=False):
        super().__init__(holder)
        self.editing = False
        self.top = 0
        self.row = self.column = 0
        # The lines being typed, until Save stores them, and whether the cursor is on the buttons under them, and which.
        self.draft = None
        self.on_buttons = False
        self.button = SAVE
        if editing and not self.is_protected():
            self.start_editing()

    def is_protected(self):
        return self.document().setlist().is_protected()

    def text_lines(self):
        if self.editing:
            return list(self.draft)
        return self.stored_lines()

    def stored_lines(self):
        text = self.document().setlist().get_notes()
        lines = text.split(LINE_BREAK)
        if text.endswith(LINE_BREAK):
            lines.pop()
        return lines or [NOTHING]

    def store(self, lines):
        """Keep the lines in the draft while editing, and otherwise put them in the set."""
        if self.editing:
            self.draft = lines
            return
        # The notes end with a newline, so that it reads as plain text in the file.
        self.document().set_notes(LINE_BREAK.join(lines) + LINE_BREAK)

    def keys(self):
        if self.editing and self.on_buttons:
            return [
                self.bind(self.KEYS.CANCEL, action=self.cancel_editing),
                self.bind(self.KEYS.SELECT_BUTTON, action=self.move_button, wants_key=True),
                self.bind(self.KEYS.PRESS_BUTTON, action=self.press_button),
                self.bind(self.KEYS.TO_TEXT, action=self.to_text),
            ]
        if self.editing:
            return [
                self.bind(self.KEYS.CANCEL, action=self.cancel_editing),
                self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
                self.bind(self.KEYS.NEW_LINE, action=self.new_line),
                self.bind(self.KEYS.ERASE, action=self.erase),
                self.bind(self.KEYS.TO_BUTTONS, action=self.to_buttons),
            ]
        result = [
            self.bind(self.KEYS.BACK, action=self.go_back),
            self.bind(self.KEYS.SCROLL, action=self.scroll),
        ]
        if not self.is_protected():
            result.append(self.bind(self.KEYS.EDIT, action=self.start_editing))
            result.append(self.bind(self.KEYS.CLEAR, action=self.clear))
        return result

    def takes_text(self):
        return self.editing and not self.on_buttons

    def key_table(self):
        # While editing, every letter is text, so the keys every page has are only there while reading.
        return self.keys() if self.editing else super().key_table()

    def scroll(self, lines):
        """Scroll the text a line up or down, never above its first line."""
        self.top = max(self.top + lines, 0)

    def start_editing(self):
        if self.is_protected():
            self.say(MSG_NOTES_PROTECTED)
            return
        lines = self.stored_lines()
        self.editing = True
        self.on_buttons = False
        self.button = SAVE
        self.draft = lines
        self.row = len(lines) - 1
        self.column = len(lines[-1])
        self.say(MSG_EDITING)

    def to_buttons(self):
        self.on_buttons = True

    def to_text(self):
        self.on_buttons = False

    def move_button(self, name):
        self.button = cursor_moved(place=self.button, name=name, count=len(MSG_NOTES_BUTTONS))

    def press_button(self):
        if self.button == SAVE:
            self.save()
        else:
            self.cancel_editing()

    def save(self):
        """Stop editing and store the draft, as one edit, unless nothing changed."""
        draft = self.draft
        self.stop_editing()
        if draft != self.stored_lines():
            self.store(draft)

    def cancel_editing(self):
        """Stop editing and throw the draft away, so the set keeps the notes it had."""
        self.stop_editing()

    def stop_editing(self):
        self.editing = False
        self.on_buttons = False
        self.draft = None
        self.holder.status_line().clear()

    def clear(self):
        if self.document().setlist().has_notes():
            self.ask(dialog=ConfirmDialog(title=MSG_CLEAR_NOTES_TITLE, messages=[MSG_CLEAR_NOTES_QUESTION]), then=lambda _: self.store([NOTHING]))

    def move(self, name):
        lines = self.text_lines()
        if name in ARROWS_UP_DOWN:
            self.row = max(min(self.row + (-1 if name == Key.UP else 1), len(lines) - 1), 0)
            self.column = min(self.column, len(lines[self.row]))
        elif name == Key.LEFT:
            if self.column:
                self.column -= 1
            elif self.row:
                self.row -= 1
                self.column = len(lines[self.row])
        elif self.column < len(lines[self.row]):
            self.column += 1
        elif self.row < len(lines) - 1:
            self.row += 1
            self.column = 0

    def new_line(self):
        lines = self.text_lines()
        line = lines[self.row]
        lines[self.row:self.row + 1] = [line[:self.column], line[self.column:]]
        self.store(lines)
        self.row += 1
        self.column = 0

    def erase(self):
        lines = self.text_lines()
        if self.column:
            line = lines[self.row]
            lines[self.row] = line[:self.column - 1] + line[self.column:]
            self.column -= 1
        elif self.row:
            self.column = len(lines[self.row - 1])
            lines[self.row - 1:self.row + 1] = [lines[self.row - 1] + lines[self.row]]
            self.row -= 1
        else:
            return
        self.store(lines)

    def type_text(self, character):
        lines = self.text_lines()
        line = lines[self.row]
        lines[self.row] = line[:self.column] + character + line[self.column:]
        self.store(lines)
        self.column += 1

    def on_key(self, event):
        if self.editing and not self.on_buttons and event.character and event.character.isprintable() and pressed_key(event) not in TEXT_EDITING_KEYS \
                and not quits_at_once(pressed_key(event)):
            event.stop()
            event.prevent_default()
            self.type_text(event.character)
            self.draw()
            return
        super().on_key(event)

    def button_line(self):
        """Return the Save and Cancel buttons, the selected one marked and in reverse video while the cursor is on them."""
        line = Text(no_wrap=True)
        for place, label in enumerate(MSG_NOTES_BUTTONS):
            selected = self.on_buttons and place == self.button
            line.append(cursor_mark(selected))
            line.append(padded(label), style=Style.REVERSE if selected else Style.BOLD)
            line.append(MSG_CONFIRM_BUTTON_GAP)
        return line

    def body(self, *, width, height):
        room = max(height, 1)
        if self.editing:
            lines = self.text_lines()
            room = max(room - BUTTON_LINES, 1)
            self.top = max(min(self.top, self.row), self.row - room + 1, 0)
            shown = []
            for number in range(self.top, min(self.top + room, len(lines))):
                line = lines[number]
                if number != self.row:
                    shown.append(Text(INDENT + line, no_wrap=True))
                    continue
                # The cursor's line scrolls sideways to keep the cursor on screen.
                start = max(self.column - (width - 6), 0)
                text = Text(INDENT + line[start:self.column], no_wrap=True)
                text.append(line[self.column:self.column + 1] or SPACE, style=Style.REVERSE)
                text.append(line[self.column + 1:])
                shown.append(text)
            shown += [Text(NOTHING)] * (room - len(shown) + 1)
            shown.append(self.button_line())
            return shown
        if not self.document().setlist().has_notes():
            return [Text(MSG_NO_NOTES_PROTECTED if self.is_protected() else MSG_NO_NOTES_NOTE, style=Style.DIM)]
        wrapped = []
        for line in self.text_lines():
            wrapped += [Text(INDENT + part) for part in (textwrap.wrap(line, width - 4) or [NOTHING])]
        self.top = min(self.top, max(len(wrapped) - room, 0))
        return wrapped[self.top:self.top + room]
