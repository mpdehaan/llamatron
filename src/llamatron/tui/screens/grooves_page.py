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
"""The Grooves page: the factory grooves every set has, then the set's own, which songs, scenes and tracks choose by name."""

from llamatron.composition.defaults import FIRST_NUMBER
from llamatron.composition.file_format import Section
from llamatron.composition.groove import FACTORY_GROOVE_NAMES, is_factory_groove
from llamatron.tui.drawing import Align
from llamatron.strings.help import HELP_GROOVES_PAGE
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.named_list_page import NamedListPage
from llamatron.tui.screens.shared import numbers_text
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.legends import MSG_GROOVE_WHAT
from llamatron.strings.marks import MSG_FACTORY_GROOVE_SHOWN, MSG_OWN_GROOVE_SHOWN
from llamatron.strings.messages import MSG_RENAME_GROOVE_PROMPT
from llamatron.strings.names import MSG_NEW_GROOVE_NAME
from llamatron.tui import keybindings


class GroovesPage(NamedListPage):
    """Every groove a song can choose, the factory ones first, each with its cells, cell length and uses."""

    KEYS = keybindings.GroovesPage
    LISTED_SECTION = Section.GROOVES
    RENAME_PROMPT = MSG_RENAME_GROOVE_PROMPT
    WHAT = MSG_GROOVE_WHAT
    crumbs = (Crumb.GROOVES,)
    HELP = HELP_GROOVES_PAGE
    columns = ((Column.SELECT_GROOVE, None, Align.LEFT), (Column.FROM, 7, Align.LEFT), (Column.CELLS, 40, Align.LEFT), (Column.CELL, 5, Align.RIGHT), (Column.USED, 4, Align.RIGHT))

    def rows(self):
        document = self.document()
        song = document.song()
        return [
            (name, [
                name, MSG_FACTORY_GROOVE_SHOWN if is_factory_groove(name) else MSG_OWN_GROOVE_SHOWN, numbers_text(song.get_groove(name).get_cells()),
                song.get_groove(name).get_cell_length_text(), len(self.uses(name)),
            ])
            for name in self.names()
        ]

    def item_keys(self):
        """Return the selected groove's keys: a factory groove can only be looked at and copied, and the set's own have the usual list keys."""
        if self.current() is not None and is_factory_groove(self.current()):
            return [self.bind(self.KEYS.VIEW, action=self.open_item), self.bind(self.KEYS.COPY, action=self.copy)]
        return super().item_keys()

    def own_place(self):
        """Return the selected groove's place among the set's own grooves, which come after the factory ones."""
        return self.place - len(FACTORY_GROOVE_NAMES)

    def open_item(self):
        self.show_page(GrooveEditor(holder=self.holder, name=self.current()))

    def add(self):
        """Add a straight groove, numbered like new tracks and scenes, and open it."""
        taken = self.names()
        number = FIRST_NUMBER
        while MSG_NEW_GROOVE_NAME.format(number=number) in taken:
            number += 1
        name = MSG_NEW_GROOVE_NAME.format(number=number)
        self.document().add_groove(name)
        self.put_cursor_on(name)
        self.show_page(GrooveEditor(holder=self.holder, name=name))
