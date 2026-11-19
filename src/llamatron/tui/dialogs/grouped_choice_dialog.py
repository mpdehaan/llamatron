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
"""The Grouped Choice dialog: a picker whose choices lie under headings that open and close, and that still searches every choice as you type."""

from rich.text import Text

from llamatron.strings import marks
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import cursor_mark, fit
from llamatron.tui.key_table import cursor_moved


class GroupedChoiceDialog(ChoiceDialog):
    """Offers choices under headings, each closed until opened, and answers with the chosen item's place in the whole list.

    With nothing typed, the cursor moves over the headings and the choices of the open ones:
    Space or Enter on a heading opens or closes it, PgUp and PgDn jump between headings, and
    Enter on a choice picks it. Typing searches every choice, with no headings, as any picker
    does. The headings open are kept in the set handed in, so that whoever opens the dialog
    again finds them as they were left.
    """

    KEYS = keybindings.GroupedChoiceDialog

    def __init__(self, *, title, groups, opened):
        """Take the groups in the order shown, each a heading and its choices, and the set of headings that are open."""
        super().__init__(title=title, options=[option for _, options in groups for option in options])
        self.headings = [heading for heading, _ in groups]
        self.sizes = [len(options) for _, options in groups]
        self.opened = opened
        self.row = 0

    def rows(self):
        """Return what the cursor moves over with nothing typed: each heading as (its number, None), and under an open one each choice as (the heading's number, the choice's place)."""
        result = []
        first = 0
        for number, heading in enumerate(self.headings):
            result.append((number, None))
            if heading in self.opened:
                result += [(number, place) for place in range(first, first + self.sizes[number])]
            first += self.sizes[number]
        return result

    def on_heading(self):
        return self.rows()[self.row][1] is None

    def keys(self):
        if self.search.get_typed():
            return super().keys()
        heading = self.headings[self.rows()[self.row][0]]
        if self.on_heading():
            enter = self.bind(self.KEYS.CLOSE if heading in self.opened else self.KEYS.OPEN, action=self.toggle)
        else:
            enter = self.bind(self.KEYS.CHOOSE, action=self.choose_row)
        return [
            self.bind(self.KEYS.CANCEL, action=self.cancel),
            self.bind(self.KEYS.MOVE, action=self.move_row, wants_key=True),
            enter,
            self.bind(self.KEYS.HEADING, action=self.jump),
            self.bind(self.KEYS.START_SEARCH, action=self.type_character, wants_key=True),
        ]

    def move_row(self, name):
        self.row = cursor_moved(place=self.row, name=name, count=len(self.rows()))

    def toggle(self):
        """Open the heading under the cursor, or close it."""
        self.opened ^= {self.headings[self.rows()[self.row][0]]}

    def jump(self, direction):
        """Move to the heading before or after the cursor, staying put at either end."""
        rows = self.rows()
        headings = [place for place, (_, choice) in enumerate(rows) if choice is None]
        before = [place for place in headings if place < self.row]
        after = [place for place in headings if place > self.row]
        if direction < 0 and before:
            self.row = before[-1]
        elif direction > 0 and after:
            self.row = after[0]

    def choose_row(self):
        self.dismiss(self.rows()[self.row][1])

    def erase(self):
        super().erase()
        if not self.search.get_typed():
            self.row = self.row_showing(self.cursor.get_place())

    def row_showing(self, place):
        """Return the row of a choice where its heading is open, and its heading's row otherwise."""
        rows = self.rows()
        found = [row for row, (_, choice) in enumerate(rows) if choice == place]
        if found:
            return found[0]
        first = 0
        for number, size in enumerate(self.sizes):
            if place < first + size:
                return rows.index((number, None))
            first += size
        return 0

    def lines(self, width):
        if self.search.get_typed():
            return super().lines(width)
        rows = self.rows()
        start = max(min(self.row - self.SHOWN // 2, len(rows) - self.SHOWN), 0)
        result = []
        for row in range(start, min(start + self.SHOWN, len(rows))):
            number, place = rows[row]
            if place is None:
                mark = marks.MSG_SECTION_OPEN_MARK if self.headings[number] in self.opened else marks.MSG_SECTION_CLOSED_MARK
                shown = marks.MSG_GROUP_OF_CHOICES.format(mark=mark, name=self.headings[number])
            else:
                shown = marks.MSG_GROUPED_CHOICE.format(name=self.options[place])
            result.append(Text(fit(text=cursor_mark(row == self.row) + shown, width=width)))
        return result
