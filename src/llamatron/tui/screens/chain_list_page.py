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

from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import Align
from llamatron.strings.errors import ERR_MAKE_A_CHAIN_FIRST, ERR_NOTHING_TO_ADD_TITLE
from llamatron.strings.help import HELP_CHAIN_LIST_PAGE
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.messages import MSG_ADD_CHAIN_TITLE
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.shared import list_keys, move_key
from llamatron.tui.text import sorted_names
from llamatron.tui import themes
from llamatron.tui import keybindings


class ChainListPage(ListPage):

    THEME = themes.CHAINS
    """A list of chains by name, in the order they run: A adds one, U and D move it, Bksp takes it out of the list.

    It edits whatever list the page that opened it hands over: names() returns the list as it is
    now, and store(names) keeps a new one, so the clip page, the Scene page and the track editor
    share it. A chain may be listed more than once, and then runs more than once.
    """

    KEYS = keybindings.ChainListPage
    HELP = HELP_CHAIN_LIST_PAGE
    columns = ((Column.SELECT_CHAIN, None, Align.LEFT),)

    def __init__(self, *, holder, opener, names, store):
        super().__init__(holder)
        self.opener = opener
        self.names = names
        self.store = store

    def crumb_trail(self):
        return (*self.opener.crumb_trail(), Crumb.CHAINS)

    def rows(self):
        return [(place, [name]) for place, name in enumerate(self.names())]

    def keys(self):
        return list_keys(page=self, extra=[self.bind(self.KEYS.REMOVE, action=self.remove_chain), move_key(self)])

    def add(self):
        chains = sorted_names(self.document().song().get_chain_names())
        if not chains:
            self.tell(ERR_NOTHING_TO_ADD_TITLE, ERR_MAKE_A_CHAIN_FIRST)
            return

        def picked(item):
            self.store([*self.names(), chains[item]])
            self.place = len(self.names()) - 1
        self.ask(dialog=ChoiceDialog(title=MSG_ADD_CHAIN_TITLE, options=chains), then=picked)

    def remove_chain(self):
        names = self.names()
        names.pop(self.place)
        self.store(names)
        self.clamp()

    def shift(self, offset):
        names = self.names()
        moved = self.place + offset
        if 0 <= moved < len(names):
            names[self.place], names[moved] = names[moved], names[self.place]
            self.store(names)
            self.place = moved
