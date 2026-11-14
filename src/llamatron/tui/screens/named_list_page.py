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
"""A page that lists the named things of one section of the set: its patterns, scales, chains, grooves, songs, arps or AutoRatchets.

Renaming, copying, deleting, moving and sorting the selected thing are the same on every such
page, since the document edits every section the same way (tui/document_parts/named_edits.py),
so they are written here once. A page says which section it lists, how a prompt and a question
word one of its things, and what Enter opens. Adding stays with each page, since each new thing
starts with something else: a name that is asked for, a numbered name, or a C major scale.
"""

from llamatron.strings.messages import MSG_COPIED_TO
from llamatron.tui.themes import theme_of
from llamatron.tui import keybindings
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.shared import list_keys, move_key


class NamedListPage(ListPage):
    """A list of the named things of one section, with the keys that rename, copy, delete, move and sort the selected one."""

    KEYS = keybindings.NamedListPage

    # The section whose items the page lists. Not SECTION, which is the section of the one thing a page shows.
    LISTED_SECTION = None

    def theme(self):
        """Return the theme colour of the section the page lists."""
        return theme_of(self.LISTED_SECTION)
    # The title of the prompt that renames one of them, and the words for one of them in a question, a template that takes the name.
    RENAME_PROMPT = None
    WHAT = None

    def names(self):
        """Return the names the page lists, in the page's order, which are the names a new one can't take."""
        return self.document().names_of(self.LISTED_SECTION)

    def own_place(self):
        """Return the selected thing's place in its section, which is its row unless the page lists other rows first."""
        return self.place

    def uses(self, name):
        return self.document().uses(section=self.LISTED_SECTION, name=name)

    def rename_title(self):
        return self.RENAME_PROMPT

    def what_is(self, name):
        """Return the words for one of the page's things in a question, like pattern (bass)."""
        return self.WHAT.format(name=name)

    def enter_binding(self):
        """Return the binding of Enter on a row, which edits the thing unless the page says otherwise."""
        return self.KEYS.EDIT

    def open_item(self):
        """Open the selected thing's own page, which each page does its own way."""
        raise NotImplementedError

    def keys(self):
        return list_keys(page=self, extra=self.item_keys())

    def item_keys(self):
        """Return the keys for the selected thing: Enter opens it, N, C, Bksp, U and D rename, copy, delete and move it, and S sorts the list."""
        return [
            self.bind(self.enter_binding(), action=self.open_item),
            self.bind(self.KEYS.RENAME, action=self.rename),
            self.bind(self.KEYS.COPY, action=self.copy),
            self.bind(self.KEYS.DELETE, action=self.delete),
            move_key(self),
            self.bind(self.KEYS.SORT, action=self.sort),
        ]

    def put_cursor_on(self, name):
        """Put the cursor on the row of a name."""
        self.place = self.names().index(name)

    def rename(self):
        name = self.current()
        self.ask_name(
            title=self.rename_title(), value=name, taken=self.names(),
            then=lambda new: self.document().rename_named(section=self.LISTED_SECTION, old=name, new=new),
        )

    def copy(self):
        """Copy the selected thing, say what the copy is called and put the cursor on it."""
        new = self.document().copy_named(section=self.LISTED_SECTION, name=self.current())
        self.say(MSG_COPIED_TO.format(name=new))
        self.put_cursor_on(new)

    def delete(self):
        """Delete the selected thing after asking, or say what still uses it."""
        name = self.current()
        self.delete_after_checks(what=self.what_is(name), uses=self.uses(name), delete=lambda: self.document().delete_named(section=self.LISTED_SECTION, name=name))

    def shift(self, offset):
        if self.document().move_named(section=self.LISTED_SECTION, place=self.own_place(), offset=offset):
            self.place += offset

    def sort(self):
        """Sort the section by name for good, keeping the cursor on the thing it was on."""
        current = self.current()
        self.document().sort_named(self.LISTED_SECTION)
        self.put_cursor_on(current)
