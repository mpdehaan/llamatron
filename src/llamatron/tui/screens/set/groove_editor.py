# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The groove editor: one groove's cells in a row, like the arp offsets editor, each a percentage of its cell late or early.

A row wider than the screen scrolls sideways, as the offsets editor and the pattern editor do,
where the cells used to wrap onto more blocks: the groove editor scrolls so
that the one-row editors could share OneRowEditor (one_row_editor.py).
"""

from rich.text import Text

from llamatron.model.objects import groove as groove_values
from llamatron.model.objects.groove import is_factory_groove
from llamatron.model.vocabulary import limits
from llamatron.model.vocabulary.file_format import Section
from llamatron.tui import drawing, keybindings
from llamatron.tui.drawing import Box, Style
from llamatron.tui.screens.shared.one_row_editor import OneRowEditor
from llamatron.tui.screens.shared.shared import stepped
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.user_strings import help as help_text, labels, marks, messages


class GrooveEditor(ShowsNamedItem, OneRowEditor):
    """A groove's cells, which can be edited unless the groove is a factory one, which can only be looked at."""

    KEYS = keybindings.GrooveEditor

    HELP = help_text.HELP_GROOVE_EDITOR
    SECTION = Section.GROOVES
    CRUMBS_BEFORE = (labels.Crumb.GROOVES,)
    RENAME_PROMPT = messages.MSG_RENAME_GROOVE_PROMPT
    CELL_WIDTH = 5
    MOST = limits.MAX_GROOVE_AMOUNT
    MOST_STEPS = limits.MAX_GROOVE_CELLS
    FEWEST_STEPS = limits.MIN_GROOVE_CELLS
    INSERT = KEYS.INSERT_CELL
    REMOVE = KEYS.REMOVE_CELL
    STEPS_SHOWN = marks.MSG_CELLS_SHOWN

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
        self.document().change(self.document().get_setlist().get_groove(self.item).set_cell, step=self.step, value=value)

    def add_step(self):
        self.document().change(self.document().get_setlist().get_groove(self.item).insert_cell, self.step)

    def remove_step_here(self):
        self.document().change(self.document().get_setlist().get_groove(self.item).remove_cell, self.step)

    def next_cell_length(self):
        """Step the cell length through the choices, going round at the end."""
        choices = groove_values.GROOVE_CELL_LENGTH_CHOICES
        current = self.groove().get_cell_length_text()
        following = stepped(values=choices, current=current, offset=1) if current in choices[:-1] else choices[0]
        self.document().change(self.document().get_setlist().get_groove(self.item).set_cell_length, following)

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        cells = self.cells()
        lines = [
            self.with_steps_shown(text=marks.MSG_GROOVE_NAME_SHOWN.format(label=labels.MSG_NAME_LABEL, name=self.item), style=Style.BOLD, width=width, first=first, last=last),
            Text(messages.MSG_GROOVE_NOTE.format(length=self.groove().get_cell_length_text()), style=Style.DIM),
            Text(messages.MSG_GROOVE_REPEATS_NOTE, style=Style.DIM),
        ]
        if self.is_factory():
            lines.append(Text(messages.MSG_FACTORY_GROOVE_NOTE, style=Style.DIM))
        lines += [
            Text(drawing.NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=labels.MSG_CELL_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], bold=True),
            self.grid_line(label=labels.MSG_AMOUNT_ROW_LABEL, cells=[(place, str(cells[place])) for place in places], selected=self.step),
            self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)),
        ]
        return lines
