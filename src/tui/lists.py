# noose6: a Python language and framework for producing MIDI clips.
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

"""The two kinds of screen that most pages are: a list of things, and a list of settings."""

from dataclasses import dataclass
from typing import Callable

from rich.text import Text

from src.tui.base import ARROWS_UP_DOWN, ConfirmDialog, Page, PromptDialog, fit, key


PLUS = '+'


class ListPage(Page):
    """A table with a cursor, where each page adds its own keys.

    A page with an add method gets a row at the bottom showing a +, where Enter does the same as
    pressing +.
    """

    columns = ()

    def __init__(self, holder):
        super().__init__(holder)
        self.place = 0

    def rows(self):
        """Return (what the row is, its column text) for each row."""
        return []

    def can_add(self):
        return hasattr(self, 'add')

    def rows_with_plus(self):
        rows = self.rows()
        if self.can_add():
            return [*rows, (None, [PLUS, *[''] * (len(self.columns) - 1)])]
        return rows

    def key_table(self):
        table = super().key_table()
        if self.can_add() and self.current() is None:
            table.insert(1, key('enter', 'add', self.add))
        return table

    def current(self):
        rows = self.rows()
        return rows[self.place][0] if rows and 0 <= self.place < len(rows) else None

    def move_cursor(self, name):
        count = len(self.rows_with_plus())
        if count:
            self.place = (self.place + (-1 if name == 'up' else 1)) % count

    def clamp(self):
        self.place = max(min(self.place, len(self.rows_with_plus()) - 1), 0)

    def move_keys(self):
        return [key(ARROWS_UP_DOWN, 'select', self.move_cursor, wants_key=True)]

    def body(self, width, height):
        self.clamp()
        fixed = sum(size + 1 for _, size, _ in self.columns if size)
        flexible = max(width - fixed - 3, 8)
        sizes = [size or flexible for _, size, _ in self.columns]

        def cells(values, style=''):
            line = Text(no_wrap=True, style=style)
            line.append('  ')
            for value, size, (_, _, align) in zip(values, sizes, self.columns):
                line.append(fit(value, size, align) + ' ')
            return line

        lines = [cells([name for name, _, _ in self.columns], 'bold'), Text('')]
        rows = self.rows_with_plus()
        if not rows:
            return lines
        room = max(height - 2, 1)
        start = max(min(self.place - room // 2, len(rows) - room), 0)
        for place in range(start, min(start + room, len(rows))):
            selected = place == self.place
            line = cells(rows[place][1], 'reverse' if selected else '')
            lines.append(line)
        return lines

    # What many lists share.

    def ask_name(self, title, value, taken, then):
        """Ask for a name that isn't empty or already in use."""
        def named(text):
            text = text.strip()
            if not text:
                self.status = 'A name cannot be empty.'
            elif text != value and text in taken:
                self.status = f'{text!r} is already in use.'
            elif text != value:
                then(text)
        self.ask(PromptDialog(title, value), named)

    def delete_after_checks(self, what, uses, delete, extra=None):
        """Refuse if anything still uses an item, and otherwise confirm and delete it."""
        if uses:
            lines = [f'{what} is still used, so change these first:', *uses[:5]]
            if len(uses) > 5:
                lines.append(f'... and {len(uses) - 5} more')
            self.tell("Can't delete", *lines)
            return
        message = [f'Delete {what}?']
        if extra:
            message.append(extra)

        def confirmed(_):
            delete()
            self.clamp()
        self.ask(ConfirmDialog('Delete', message), confirmed)


@dataclass
class Field:
    """One setting on a page. A missing function means that key does nothing there."""

    label: str
    value: Callable
    adjust: Callable = None
    enter: Callable = None
    enter_what: str = 'edit'
    clear: Callable = None
    clear_what: str = 'clear'


class FieldPage(Page):
    """Settings in a column, where the keys depend on the setting under the cursor."""

    def __init__(self, holder):
        super().__init__(holder)
        self.place = 0

    def fields(self):
        return []

    def page_keys(self):
        return []

    def notes(self, width):
        """Return lines to show under the settings."""
        return []

    def field(self):
        fields = self.fields()
        self.place = max(min(self.place, len(fields) - 1), 0)
        return fields[self.place] if fields else None

    def move_cursor(self, name):
        count = len(self.fields())
        if count:
            self.place = (self.place + (-1 if name == 'up' else 1)) % count

    def keys(self):
        result = [key(ARROWS_UP_DOWN, 'select', self.move_cursor, wants_key=True)]
        field = self.field()
        if field is not None:
            if field.adjust:
                result.append(key(('+', '=', 'right'), 'more', lambda: field.adjust(1), label='+ →'))
                result.append(key(('-', 'left'), 'less', lambda: field.adjust(-1), label='- ←'))
            if field.enter:
                result.append(key('enter', field.enter_what, field.enter))
            if field.clear:
                result.append(key('backspace', field.clear_what, field.clear))
        result += self.page_keys()
        result.append(key('tab', 'back', self.go_back))
        return result

    def body(self, width, height):
        fields = self.fields()
        self.field()
        label_width = max((len(field.label) for field in fields), default=0) + 2
        lines = []
        for place, field in enumerate(fields):
            line = Text(no_wrap=True)
            line.append('  ' + field.label.ljust(label_width), style='bold' if place == self.place else '')
            line.append(f' {field.value()} ', style='reverse' if place == self.place else '')
            lines.append(line)
        notes = self.notes(width)
        if notes:
            lines += [Text(''), *notes]
        return lines

    # Common kinds of setting.

    def ask_number(self, title, value, then, low=None, high=None):
        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.status = f'{text!r} is not a whole number.'
                return
            if (low is not None and number < low) or (high is not None and number > high):
                self.status = f'{number} must be from {low} to {high}.'
                return
            then(number)
        self.ask(PromptDialog(title, value), answered)
