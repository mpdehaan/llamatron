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
"""The Chains list page: the chains a clip, a scene or a track runs, in the order they run, which the page that opened it reads and stores."""

from llamatron.strings import errors, help as help_text, labels, messages
from llamatron.tui import keybindings, themes
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import Align
from llamatron.tui.screens.shared.generator_names import generators_to_add, listed_generator
from llamatron.tui.screens.shared.list_page import ListPage
from llamatron.tui.screens.shared.shared import list_keys, move_key


class GeneratorListPage(ListPage):

    """A list of the generators of one kind, with the keys every list of named things has."""

    THEME = themes.GENERATORS
    """A list of generators by name, a chain among them, in the order they run: A adds one, M moves it, Bksp takes it out of the list.

    It edits whatever list the page that opened it hands over: names() returns the list as it is
    now, and store(names) keeps a new one, so the clip page, the Scene page and the track editor
    share it. A generator may be listed more than once, and then runs more than once.
    """

    KEYS = keybindings.GeneratorListPage
    HELP = help_text.HELP_GENERATOR_LIST_PAGE
    columns = ((labels.Column.SELECT_ANY_GENERATOR, None, Align.LEFT),)

    def __init__(self, *, holder, opener, names, store):
        super().__init__(holder)
        self.opener = opener
        self.names = names
        self.store = store

    def crumb_trail(self):
        return (*self.opener.crumb_trail(), labels.Crumb.GENERATORS)

    def rows(self):
        setlist = self.document().get_setlist()
        return [(place, [listed_generator(setlist=setlist, name=name)]) for place, name in enumerate(self.names())]

    def keys(self):
        return list_keys(page=self, extra=[self.bind(self.KEYS.REMOVE, action=self.remove_chain), move_key(self)])

    def add(self):
        setlist = self.document().get_setlist()
        offered = [name for _, name in generators_to_add(setlist)]
        if not offered:
            self.tell(errors.ERR_NOTHING_TO_ADD_TITLE, errors.ERR_MAKE_A_GENERATOR_FIRST)
            return

        def picked(item):
            self.store([*self.names(), offered[item]])
            self.cursor.set_place(len(self.names()) - 1)
        self.ask(dialog=ChoiceDialog(title=messages.MSG_ADD_GENERATOR_TITLE, options=[listed_generator(setlist=setlist, name=name) for name in offered]), then=picked)

    def remove_chain(self):
        names = self.names()
        names.pop(self.cursor.get_place())
        self.store(names)
        self.clamp()

    def shift(self, offset):
        names = self.names()
        moved = self.cursor.get_place() + offset
        if 0 <= moved < len(names):
            names[self.cursor.get_place()], names[moved] = names[moved], names[self.cursor.get_place()]
            self.store(names)
            self.cursor.set_place(moved)
