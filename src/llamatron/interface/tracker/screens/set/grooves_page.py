# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Grooves page: the factory grooves every set has, then the set's own, which songs, scenes and tracks choose by name."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.drawing import Align
from llamatron.interface.tracker.screens.shared.named_list_page import NamedListPage
from llamatron.interface.tracker.screens.shared.shared import numbers_text
from llamatron.model.objects import groove
from llamatron.model.objects.groove import is_factory_groove
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, legends, marks, messages, names


class GroovesPage(NamedListPage):
    """Every groove a song can choose, the factory ones first, each with its cells, cell length and uses."""

    KEYS = keybindings.GroovesPage
    LISTED_SECTION = Section.GROOVES
    RENAME_PROMPT = messages.MSG_RENAME_GROOVE_PROMPT
    WHAT = legends.MSG_GROOVE_WHAT
    crumbs = (labels.Crumb.GROOVES,)
    HELP = help_text.HELP_GROOVES_PAGE
    columns = ((labels.Column.SELECT_GROOVE, None, Align.LEFT), (labels.Column.FROM, 9, Align.LEFT), (labels.Column.CELLS, 40, Align.LEFT), (labels.Column.CELL, 5, Align.RIGHT), (labels.Column.USED, 4, Align.RIGHT))

    def rows(self):
        document = self.document()
        song = document.song()
        return [
            (name, [
                name, marks.MSG_FACTORY_GROOVE_SHOWN if is_factory_groove(name) else marks.MSG_OWN_GROOVE_SHOWN, numbers_text(song.get_setlist().get_groove(name).get_cells()),
                song.get_setlist().get_groove(name).get_cell_length_text(), len(self.uses(name)),
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
        return self.cursor.get_place() - len(groove.FACTORY_GROOVE_NAMES)

    def open_item(self):
        self.open_editor(section=Section.GROOVES, name=self.current())

    def add(self):
        """Add a straight groove, numbered like new tracks and scenes, and open it."""
        name = self.new_name(names.MSG_NEW_GROOVE_WORD)
        self.document().add_groove(name)
        self.put_cursor_on(name)
        self.open_editor(section=Section.GROOVES, name=name)
