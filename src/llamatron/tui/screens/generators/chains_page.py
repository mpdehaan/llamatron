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
from llamatron.strings import help as help_text, labels, legends, messages
from llamatron.tui import drawing, keybindings
from llamatron.tui.drawing import Align
from llamatron.tui.screens.generators.chain_editor import ChainEditor
from llamatron.tui.screens.shared.named_list_page import NamedListPage


class ChainsPage(NamedListPage):

    KEYS = keybindings.ChainsPage
    LISTED_SECTION = Section.CHAINS
    RENAME_PROMPT = messages.MSG_RENAME_CHAIN_PROMPT
    WHAT = legends.MSG_CHAIN_WHAT
    crumbs = (labels.Crumb.CHAINS,)
    HELP = help_text.HELP_CHAINS_PAGE
    columns = ((labels.Column.SELECT_CHAIN, None, Align.LEFT), (labels.Column.STEPS, 5, Align.RIGHT), (labels.Column.USED, 4, Align.RIGHT))

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
        self.ask_name(title=messages.MSG_NEW_CHAIN_PROMPT, value=drawing.NOTHING, taken=self.names(), then=named)
