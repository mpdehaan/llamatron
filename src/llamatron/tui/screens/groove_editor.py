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
"""The groove editor: one groove's cells in a row, like the arp offsets editor, each a percentage of its cell late or early.

A row wider than the screen scrolls sideways, as the offsets editor and the pattern editor do,
where the cells used to wrap onto more blocks: the user allowed the groove editor to scroll so
that the one-row editors could share OneRowEditor (one_row_editor.py).
"""

from rich.text import Text

from llamatron.composition.file_format import Section
from llamatron.composition.groove import GROOVE_CELL_LENGTH_CHOICES, is_factory_groove
from llamatron.composition.limits import MAX_GROOVE_AMOUNT, MAX_GROOVE_CELLS, MIN_GROOVE_CELLS
from llamatron.tui.drawing import Box, NOTHING, Style
from llamatron.strings.help import HELP_GROOVE_EDITOR
from llamatron.tui.screens.one_row_editor import OneRowEditor
from llamatron.tui.screens.shared import stepped
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.strings.labels import Crumb, MSG_AMOUNT_ROW_LABEL, MSG_CELL_ROW_LABEL, MSG_NAME_LABEL
from llamatron.strings.marks import MSG_CELLS_SHOWN, MSG_GROOVE_NAME_SHOWN
from llamatron.strings.messages import MSG_FACTORY_GROOVE_NOTE, MSG_GROOVE_NOTE, MSG_GROOVE_REPEATS_NOTE, MSG_RENAME_GROOVE_PROMPT
from llamatron.tui import keybindings


class GrooveEditor(ShowsNamedItem, OneRowEditor):
    """A groove's cells, which can be edited unless the groove is a factory one, which can only be looked at."""

    KEYS = keybindings.GrooveEditor

    HELP = HELP_GROOVE_EDITOR
    SECTION = Section.GROOVES
    CRUMBS_BEFORE = (Crumb.GROOVES,)
    RENAME_PROMPT = MSG_RENAME_GROOVE_PROMPT
    CELL_WIDTH = 5
    MOST = MAX_GROOVE_AMOUNT
    MOST_STEPS = MAX_GROOVE_CELLS
    FEWEST_STEPS = MIN_GROOVE_CELLS
    INSERT = KEYS.INSERT_CELL
    REMOVE = KEYS.REMOVE_CELL
    STEPS_SHOWN = MSG_CELLS_SHOWN

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def groove(self):
        return self.document().song().get_groove(self.item)

    def cells(self):
        return self.groove().get_cells()

    def values(self):
        return self.cells()

    def is_factory(self):
        return is_factory_groove(self.item)

    def can_edit(self):
        return not self.is_factory()

    def more_keys(self):
        return [self.bind(self.KEYS.CELL_LENGTH, action=self.next_cell_length), self.bind(self.KEYS.RENAME, action=self.rename)]

    def set_value(self, value):
        self.document().set_groove_cell(name=self.item, step=self.step, amount=value)

    def add_step(self):
        self.document().insert_groove_cell(name=self.item, step=self.step)

    def drop_step(self):
        self.document().remove_groove_cell(name=self.item, step=self.step)

    def next_cell_length(self):
        """Step the cell length through the choices, going round at the end."""
        choices = GROOVE_CELL_LENGTH_CHOICES
        current = self.groove().get_cell_length_text()
        following = stepped(values=choices, current=current, offset=1) if current in choices[:-1] else choices[0]
        self.document().set_groove_cell_length(name=self.item, length=following)

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        cells = self.cells()
        lines = [
            self.with_steps_shown(text=MSG_GROOVE_NAME_SHOWN.format(label=MSG_NAME_LABEL, name=self.item), style=Style.BOLD, width=width, first=first, last=last),
            Text(MSG_GROOVE_NOTE.format(length=self.groove().get_cell_length_text()), style=Style.DIM),
            Text(MSG_GROOVE_REPEATS_NOTE, style=Style.DIM),
        ]
        if self.is_factory():
            lines.append(Text(MSG_FACTORY_GROOVE_NOTE, style=Style.DIM))
        lines += [
            Text(NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=MSG_CELL_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], bold=True),
            self.grid_line(label=MSG_AMOUNT_ROW_LABEL, cells=[(place, str(cells[place])) for place in places], selected=self.step),
            self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)),
        ]
        return lines
