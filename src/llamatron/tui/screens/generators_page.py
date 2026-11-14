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

"""The Generators page: every generator of the set, of every kind, on one list in an order of the user's own, each with its kind
beside its name, the user's design. Enter edits one, A adds one of a kind asked for, N renames, C copies, Bksp deletes once
nothing uses it, and M moves it, the order kept in the set (Setlist.ordered_generators)."""

from llamatron.composition.file_format import NAMED_GENERATORS
from llamatron.composition.naming import unique_name
from llamatron.strings.help import HELP_GENERATORS_PAGE
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.legends import MSG_GENERATOR_WHAT
from llamatron.strings.marks import MSG_GENERATOR_KIND_SHOWN
from llamatron.strings.messages import MSG_COPIED_TO, MSG_NEW_GENERATOR_KIND_TITLE, MSG_NEW_GENERATOR_NAMED, MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings, themes
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import Align
from llamatron.tui.screens.generator_pages import GENERATOR_PAGES, generator_page_of_kind
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.shared import list_keys, move_key

# How wide the kind's column is: the longest kind's name in parentheses.
KIND_WIDTH = 15
USED_WIDTH = 4


class GeneratorsPage(ListPage):

    THEME = themes.GENERATORS
    KEYS = keybindings.GeneratorsPage
    crumbs = (Crumb.GENERATORS,)
    HELP = HELP_GENERATORS_PAGE
    columns = ((Column.SELECT_ANY_GENERATOR, None, Align.LEFT), (Column.KIND, KIND_WIDTH, Align.LEFT), (Column.USED, USED_WIDTH, Align.RIGHT))

    def generators(self):
        """Return every generator as (kind, name), in the page's order."""
        return self.document().setlist().ordered_generators()

    def rows(self):
        return [((kind, name), [name, MSG_GENERATOR_KIND_SHOWN.format(kind=generator_page_of_kind(kind).label), len(self.uses(kind=kind, name=name))])
                for kind, name in self.generators()]

    def uses(self, *, kind, name):
        return self.document().uses(section=NAMED_GENERATORS[kind], name=name)

    def keys(self):
        return list_keys(page=self, extra=[
            self.bind(self.KEYS.EDIT, action=self.open_item),
            self.bind(self.KEYS.RENAME, action=self.rename),
            self.bind(self.KEYS.COPY, action=self.copy),
            self.bind(self.KEYS.DELETE, action=self.delete),
            move_key(self),
        ])

    def put_cursor_on(self, *, kind, name):
        self.place = self.generators().index((kind, name))

    def open_item(self):
        kind, name = self.current()
        self.show_page(generator_page_of_kind(kind).EDITOR(holder=self.holder, name=name))

    def add(self):
        """Ask which kind of generator to make, make one named after the kind, numbered, put the cursor on it and open it."""
        listings = list(GENERATOR_PAGES.values())

        def chosen(place):
            listing = listings[place]
            name = unique_name(base=MSG_NEW_GENERATOR_NAMED.format(kind=listing.label), taken=self.document().names_of(listing.section))
            self.document().add_generator(section=listing.section, name=name)
            self.put_cursor_on(kind=listing.kind, name=name)
            self.show_page(listing.EDITOR(holder=self.holder, name=name))
        self.ask(dialog=ChoiceDialog(title=MSG_NEW_GENERATOR_KIND_TITLE, options=[listing.label for listing in listings]), then=chosen)

    def rename(self):
        kind, name = self.current()
        section = NAMED_GENERATORS[kind]
        self.ask_name(
            title=MSG_RENAME_GENERATOR_PROMPT.format(label=generator_page_of_kind(kind).label), value=name, taken=self.document().names_of(section),
            then=lambda new: self.document().rename_named(section=section, old=name, new=new),
        )

    def copy(self):
        """Copy the selected generator, say what the copy is called and put the cursor on it."""
        kind, name = self.current()
        new = self.document().copy_named(section=NAMED_GENERATORS[kind], name=name)
        self.say(MSG_COPIED_TO.format(name=new))
        self.put_cursor_on(kind=kind, name=new)

    def delete(self):
        """Delete the selected generator after asking, or say what still uses it."""
        kind, name = self.current()
        what = MSG_GENERATOR_WHAT.format(label=generator_page_of_kind(kind).label, name=name)
        self.delete_after_checks(what=what, uses=self.uses(kind=kind, name=name), delete=lambda: self.document().delete_named(section=NAMED_GENERATORS[kind], name=name))

    def shift(self, offset):
        if self.document().move_generator(place=self.place, offset=offset):
            self.place += offset
