# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The List page: a table with a cursor, where each page adds its own keys."""

from rich.text import Text

from llamatron.interface.forms import moves
from llamatron.interface.forms.cursor import Cursor, place_of
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.cursor import Search, shown_around
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.drawing import cursor_mark, fit, Style
from llamatron.interface.tracker.screens.shared.page import Page
from llamatron.model.schema import limits
from llamatron.user_strings import errors, marks, messages


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
    # The most room the column with no width of its own takes, the names: a name is at most this long, so the columns after it
    # stay close to it however wide the console. None on a page whose first column isn't names, as files.
    NAME_COLUMN_WIDTH = limits.MAX_NAME_LENGTH

    def __init__(self, holder):
        super().__init__(holder)
        self.cursor = Cursor(place=0)
        self.search = Search()
        self.searching = False
        self.place_before_search = 0
        # Move mode: whether M has picked up the cursor's row, and whether it has been carried yet, so that one move is one undo step.
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
            return [*rows, (None, [marks.MSG_NEW_ROW, *[drawing.NOTHING] * (len(self.columns) - 1)])]
        return rows

    def page_key_table(self):
        if self.moving:
            return self.in_order([self.bind(self.KEYS.DROP, action=self.drop), self.bind(self.KEYS.CARRY, action=self.carry)])
        if self.searching:
            return self.in_order(self.search_keys())
        table = super().page_key_table()
        if self.can_add() and self.current() is None:
            table.insert(1, self.bind(self.KEYS.ADD_HERE, action=self.add))
        # The search key works everywhere on a list but stays off the legend, where F1 lists it.
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
        return self.search.places_matching(self.row_texts())

    def start_search(self):
        self.searching = True
        self.search.clear()
        self.place_before_search = self.cursor.get_place()
        self.show_search()

    def type_character(self, name):
        self.search.type_key(name)
        self.settle()

    def erase(self):
        self.search.erase()
        self.settle()

    def complete(self):
        self.search.complete(self.row_texts())
        self.settle()

    def settle(self):
        self.cursor.keep_among(self.matches())
        self.show_search()

    def show_search(self):
        self.say(messages.MSG_SEARCH_STATUS.format(text=self.search.get_typed()))

    def keep(self):
        self.searching = False

    def stop_search(self):
        self.searching = False
        self.cursor.set_place(self.place_before_search)
        self.clamp()

    def row_names(self):
        """Return what each row is keyed by, in the rows' order."""
        return [row[0] for row in self.remembered_rows()]

    def current(self):
        rows = self.remembered_rows()
        return rows[self.cursor.get_place()][0] if rows and 0 <= self.cursor.get_place() < len(rows) else None

    def under_cursor(self):
        """Return what the cursor's row is, as current() does: None on the + row."""
        return self.current()

    def key_toward(self, target):
        """Return the key that brings the cursor nearer the row that is the target, or None when the cursor is on it."""
        return moves.toward(here=self.cursor.get_place(), there=place_of(screen=self, names=self.row_names(), target=target))

    def move_cursor(self, name):
        self.cursor.move_among(name=name, places=self.matches())
        if self.searching:
            self.show_search()

    def clamp(self):
        self.cursor.keep_within(len(self.rows_with_plus()))

    def remember_place(self):
        return self.current()

    def restore_place(self, place):
        """Put the cursor back on the row that was under it, by what the row is, if the row is still there."""
        rows = [what for what, _ in self.remembered_rows()]
        if place in rows:
            self.cursor.set_place(rows.index(place))
        self.clamp()

    # Move mode: M picks up the cursor's row, Up and Down carry it, and Enter, Esc or M drops it where it is.

    def start_moving(self):
        self.moving = True
        self.carried = False
        self.say_moving()

    def say_moving(self):
        self.say(messages.MSG_MOVING.format(what=messages.MSG_MOVING_ROW.format(name=self.row_texts()[self.cursor.get_place()])))

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

    def row_style(self, what):
        """Return the style a row is drawn in, by what the row is: plain, unless the page says otherwise."""
        return Style.PLAIN

    def row_selected(self, place):
        """Return whether the row at a place is the cursor's."""
        return place == self.cursor.get_place()

    def body(self, *, width, height):
        """Return the list: its column headings in bold, a blank line, then as many rows as fit, around the cursor's."""
        self.clamp()
        sizes = self.column_sizes(width)
        lines = [self.row_line(values=[name for name, _, _ in self.columns], sizes=sizes, style=Style.BOLD), Text(drawing.NOTHING)]
        rows = self.rows_with_plus()
        matches = self.matches()
        if not matches:
            return lines
        room = max(height - 2, 1)
        at = matches.index(self.cursor.get_place()) if self.cursor.is_on_one_of(matches) else 0
        for place in shown_around(places=matches, at=at, room=room):
            lines.append(self.row_line(values=rows[place][1], sizes=sizes, style=self.row_style(rows[place][0]), selected=self.row_selected(place)))
        return lines

    def column_sizes(self, width):
        """Return each column's width: its own where it has one, and what is left for the names', held to a name's room."""
        fixed = sum(size + 1 for _, size, _ in self.columns if size)
        flexible = max(width - fixed - 3, 8)
        if self.NAME_COLUMN_WIDTH is not None and len(self.columns) > 1:
            flexible = min(flexible, self.NAME_COLUMN_WIDTH)
        return [size or flexible for _, size, _ in self.columns]

    def row_line(self, *, values, sizes, style=Style.PLAIN, selected=False):
        """Return one row's line: the cursor's mark, then each column's value fitted to its width."""
        line = Text(no_wrap=True, style=style)
        carried = selected and self.moving
        # A row Move mode carries has its name between < and >, put where the spaces beside it were, so that nothing shifts.
        mark = cursor_mark(selected)
        line.append(mark[:-1] + marks.MSG_MOVING_OPEN if carried else mark)
        for column, (value, size, (_, _, align)) in enumerate(zip(values, sizes, self.columns)):
            shown = fit(text=value, width=size, align=align)
            if carried and column == 0:
                end = len(shown.rstrip())
                shown = shown[:end] + marks.MSG_MOVING_CLOSE + shown[end + 1:] if end < size else shown + marks.MSG_MOVING_CLOSE
                line.append(shown if end >= size else shown + drawing.SPACE, style=Style.BOLD)
                continue
            line.append(shown + drawing.SPACE)
        return line

    # What many lists share.

    def delete_taking_out(self, *, what, uses, delete):
        """Confirm and delete an item that lists may name, as a generator is named by chains and clips, listing up to a few of
        the uses it is taken out of."""
        message = [messages.MSG_DELETE_QUESTION.format(what=what)]
        if uses:
            message += [messages.MSG_TAKEN_OUT_OF, *uses[:MOST_USES_SHOWN]]
            if len(uses) > MOST_USES_SHOWN:
                message.append(errors.ERR_AND_MORE.format(count=len(uses) - MOST_USES_SHOWN))

        def confirmed(_):
            delete()
            self.clamp()
        self.ask(dialog=ConfirmDialog(title=messages.MSG_DELETE_TITLE, messages=message), then=confirmed)

    def delete_after_checks(self, *, what, uses, delete, extra=None):
        """Refuse if anything still uses an item, and otherwise confirm and delete it."""
        if uses:
            lines = [errors.ERR_STILL_USED.format(what=what), *uses[:MOST_USES_SHOWN]]
            if len(uses) > MOST_USES_SHOWN:
                lines.append(errors.ERR_AND_MORE.format(count=len(uses) - MOST_USES_SHOWN))
            self.tell(errors.ERR_CANT_DELETE_TITLE, *lines)
            return
        message = [messages.MSG_DELETE_QUESTION.format(what=what)]
        if extra:
            message.append(extra)

        def confirmed(_):
            delete()
            self.clamp()
        self.ask(dialog=ConfirmDialog(title=messages.MSG_DELETE_TITLE, messages=message), then=confirmed)
