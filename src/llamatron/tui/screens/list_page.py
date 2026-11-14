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

"""The List page: a table with a cursor, where each page adds its own keys."""

from rich.text import Text

from llamatron.tui.dialogs.choice_dialog import completed, places_matching
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.strings.marks import MSG_MOVING_CLOSE, MSG_MOVING_OPEN
from llamatron.strings.messages import MSG_MOVING, MSG_MOVING_ROW
from llamatron.tui.drawing import cursor_mark, fit, NOTHING, SPACE, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key, SPACE_CHARACTER
from llamatron.tui.screens.page import Page
from llamatron.strings.errors import ERR_AND_MORE, ERR_CANT_DELETE_TITLE, ERR_STILL_USED
from llamatron.strings.marks import MSG_ADD_ROW_MARK
from llamatron.strings.messages import MSG_DELETE_QUESTION, MSG_DELETE_TITLE, MSG_SEARCH_STATUS
from llamatron.tui import keybindings


# A list page that can add has a method of this name.
ADD_METHOD = 'add'
# How many of the things still using an item are listed when deleting it is refused.
MOST_USES_SHOWN = 5


class ListPage(Page):
    """A table with a cursor, where each page adds its own keys.

    A page with an add method gets a row at the bottom showing a +, where Enter does the same as
    pressing +. / searches: the rows shrink to the ones containing what's typed, ignoring case,
    Bksp erases, Tab completes, Enter keeps the cursor where the search put it and Esc puts it
    back where it was. The place always counts in the whole list.
    """

    KEYS = keybindings.ListPage

    columns = ()

    def __init__(self, holder):
        super().__init__(holder)
        self.place = 0
        self.searching = False
        self.typed = NOTHING
        self.place_before_search = 0
        # Move mode, the user's design: whether M has picked up the cursor's row, and whether it has been carried yet, so that one move is one undo step.
        self.moving = False
        self.carried = False

    def rows(self):
        """Return (what the row is, its column text) for each row."""
        return []

    def can_add(self):
        return hasattr(self, ADD_METHOD)

    def remembered_rows(self):
        """Return the page's rows, built once per change of the set rather than for each of the several times a key press asks for them, since a row counts what uses its item."""
        document = self.document()
        return document.remembered(key=(type(self).__name__, ListPage.remembered_rows.__name__, *self.rows_depend_on()), on=(document,), compute=self.rows)

    def rows_depend_on(self):
        """Return what the rows depend on besides the set, which the remembered rows are kept by: nothing, for a page that lists the set's own things."""
        return ()

    def rows_with_plus(self):
        rows = self.remembered_rows()
        if self.can_add():
            return [*rows, (None, [MSG_ADD_ROW_MARK, *[NOTHING] * (len(self.columns) - 1)])]
        return rows

    def page_key_table(self):
        if self.moving:
            return self.in_order([self.bind(self.KEYS.DROP, action=self.drop), self.bind(self.KEYS.CARRY, action=self.carry)])
        if self.searching:
            return self.in_order(self.search_keys())
        table = super().page_key_table()
        if self.can_add() and self.current() is None:
            table.insert(1, self.bind(self.KEYS.ADD_HERE, action=self.add))
        # The search key works everywhere on a list but stays off the legend, where F1 lists it, as the user asked on 2026-11-08.
        table.append(self.bind(self.KEYS.SEARCH, action=self.start_search))
        return self.in_order(table)

    # Searching.

    def takes_text(self):
        return self.searching

    def search_keys(self):
        return [
            self.bind(self.KEYS.SEARCH_CANCEL, action=self.stop_search),
            *self.move_keys(),
            self.bind(self.KEYS.SEARCH_TYPE, action=self.type_character, wants_key=True),
            self.bind(self.KEYS.SEARCH_ERASE, action=self.erase),
            self.bind(self.KEYS.SEARCH_COMPLETE, action=self.complete),
            self.bind(self.KEYS.SEARCH_KEEP, action=self.keep),
        ]

    def row_texts(self):
        """Return the text a search looks in for each row: its first column, which is the name it shows."""
        return [str(cells[0]) for _, cells in self.remembered_rows()]

    def matches(self):
        """Return the places of the rows a search keeps, or of every row and the + row when not searching."""
        if not self.searching:
            return list(range(len(self.rows_with_plus())))
        return places_matching(options=self.row_texts(), text=self.typed)

    def start_search(self):
        self.searching = True
        self.typed = NOTHING
        self.place_before_search = self.place
        self.show_search()

    def type_character(self, name):
        self.typed += SPACE_CHARACTER if name == Key.SPACE else name
        self.settle()

    def erase(self):
        self.typed = self.typed[:-1]
        self.settle()

    def complete(self):
        self.typed = completed(options=self.row_texts(), matches=self.matches(), typed=self.typed)
        self.settle()

    def settle(self):
        matches = self.matches()
        if matches and self.place not in matches:
            self.place = matches[0]
        self.show_search()

    def show_search(self):
        self.say(MSG_SEARCH_STATUS.format(text=self.typed))

    def keep(self):
        self.searching = False

    def stop_search(self):
        self.searching = False
        self.place = self.place_before_search
        self.clamp()

    def current(self):
        rows = self.remembered_rows()
        return rows[self.place][0] if rows and 0 <= self.place < len(rows) else None

    def move_cursor(self, name):
        matches = self.matches()
        if not matches:
            return
        if self.place not in matches:
            self.place = matches[0]
            return
        self.place = matches[cursor_moved(place=matches.index(self.place), name=name, count=len(matches))]
        if self.searching:
            self.show_search()

    def clamp(self):
        self.place = max(min(self.place, len(self.rows_with_plus()) - 1), 0)

    def remember_place(self):
        return self.current()

    def restore_place(self, place):
        """Put the cursor back on the row that was under it, by what the row is, if the row is still there."""
        rows = [what for what, _ in self.remembered_rows()]
        if place in rows:
            self.place = rows.index(place)
        self.clamp()

    # Move mode, the user's design: M picks up the cursor's row, Up and Down carry it, and Enter, Esc or M drops it where it is.

    def start_moving(self):
        self.moving = True
        self.carried = False
        self.say_moving()

    def say_moving(self):
        self.say(MSG_MOVING.format(what=MSG_MOVING_ROW.format(name=self.row_texts()[self.place])))

    def carry(self, offset):
        """Carry the picked-up row one place up or down, every carry of one move making one undo step."""
        if self.carried:
            self.document().continue_edit()
        self.carried = True
        self.shift(offset)
        self.say_moving()

    def drop(self):
        self.moving = False

    def move_keys(self):
        return [self.bind(self.KEYS.SELECT, action=self.move_cursor, wants_key=True)]

    def body(self, *, width, height):
        self.clamp()
        fixed = sum(size + 1 for _, size, _ in self.columns if size)
        flexible = max(width - fixed - 3, 8)
        sizes = [size or flexible for _, size, _ in self.columns]

        def cells(*, values, style=Style.PLAIN, selected=False):
            line = Text(no_wrap=True, style=style)
            carried = selected and self.moving
            # A row Move mode carries has its name between < and >, put where the spaces beside it were, so that nothing shifts.
            mark = cursor_mark(selected)
            line.append(mark[:-1] + MSG_MOVING_OPEN if carried else mark)
            for column, (value, size, (_, _, align)) in enumerate(zip(values, sizes, self.columns)):
                shown = fit(text=value, width=size, align=align)
                if carried and column == 0:
                    end = len(shown.rstrip())
                    shown = shown[:end] + MSG_MOVING_CLOSE + shown[end + 1:] if end < size else shown + MSG_MOVING_CLOSE
                    line.append(shown if end >= size else shown + SPACE, style=Style.BOLD)
                    continue
                line.append(shown + SPACE)
            return line

        lines = [cells(values=[name for name, _, _ in self.columns], style=Style.BOLD), Text(NOTHING)]
        rows = self.rows_with_plus()
        matches = self.matches()
        if not matches:
            return lines
        room = max(height - 2, 1)
        at = matches.index(self.place) if self.place in matches else 0
        start = max(min(at - room // 2, len(matches) - room), 0)
        for place in matches[start:start + room]:
            lines.append(cells(values=rows[place][1], selected=place == self.place))
        return lines

    # What many lists share.

    def delete_after_checks(self, *, what, uses, delete, extra=None):
        """Refuse if anything still uses an item, and otherwise confirm and delete it."""
        if uses:
            lines = [ERR_STILL_USED.format(what=what), *uses[:MOST_USES_SHOWN]]
            if len(uses) > MOST_USES_SHOWN:
                lines.append(ERR_AND_MORE.format(count=len(uses) - MOST_USES_SHOWN))
            self.tell(ERR_CANT_DELETE_TITLE, *lines)
            return
        message = [MSG_DELETE_QUESTION.format(what=what)]
        if extra:
            message.append(extra)

        def confirmed(_):
            delete()
            self.clamp()
        self.ask(dialog=ConfirmDialog(title=MSG_DELETE_TITLE, messages=message), then=confirmed)
