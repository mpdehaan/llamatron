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

"""The Chains page."""

from llamatron.composition.file_format import Section
from llamatron.tui.drawing import Align, NOTHING
from llamatron.strings.help import HELP_CHAINS_PAGE
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.named_list_page import NamedListPage
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.legends import MSG_CHAIN_WHAT
from llamatron.strings.messages import MSG_NEW_CHAIN_PROMPT, MSG_RENAME_CHAIN_PROMPT
from llamatron.tui import keybindings


class ChainsPage(NamedListPage):

    KEYS = keybindings.ChainsPage
    LISTED_SECTION = Section.CHAINS
    RENAME_PROMPT = MSG_RENAME_CHAIN_PROMPT
    WHAT = MSG_CHAIN_WHAT
    crumbs = (Crumb.CHAINS,)
    HELP = HELP_CHAINS_PAGE
    columns = ((Column.SELECT_CHAIN, None, Align.LEFT), (Column.STEPS, 5, Align.RIGHT), (Column.USED, 4, Align.RIGHT))

    def rows(self):
        song = self.document().song()
        return [
            (name, [name, len(song.get_chain(name).get_steps()), len(self.uses(name))])
            for name in self.names()
        ]

    def open_item(self):
        self.show_page(ChainEditor(holder=self.holder, name=self.current()))

    def add(self):
        def named(text):
            self.document().add_chain(text)
            self.put_cursor_on(text)
        self.ask_name(title=MSG_NEW_CHAIN_PROMPT, value=NOTHING, taken=self.names(), then=named)
