# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Grooves page: the factory grooves every set has, then the set's own, which songs, scenes and tracks choose by name."""

from llamatron.interface.pages.groove_list import GrooveListPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.named_list_page import NamedListPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, legends, messages


class GroovesPage(NamedListPage):
    """Every groove a song can choose, the factory ones first, each with its cells, cell length and uses, from the Groove list
    presenter (interface/pages/groove_list.py)."""

    KEYS = keybindings.GroovesPage
    LISTED_SECTION = Section.GROOVES
    RENAME_PROMPT = messages.MSG_RENAME_GROOVE_PROMPT
    WHAT = legends.MSG_GROOVE_WHAT
    crumbs = (labels.Crumb.GROOVES,)
    HELP = help_text.HELP_GROOVES_PAGE
    columns = GrooveListPresenter.COLUMNS

    def presenter(self):
        return GrooveListPresenter(page=self, document=self.document())

    def rows(self):
        return self.presenter().rows()

    def item_keys(self):
        """Return the selected groove's keys: a factory groove can only be looked at and copied, and the set's own have the usual list keys."""
        if self.current() is not None and GrooveListPresenter.is_factory(self.current()):
            return [self.bind(self.KEYS.VIEW, action=self.open_item), self.bind(self.KEYS.COPY, action=self.copy)]
        return super().item_keys()

    def own_place(self):
        """Return the selected groove's place among the set's own grooves, which come after the factory ones."""
        return GrooveListPresenter.own_place(self.cursor.get_place())

    def open_item(self):
        self.open_place(GrooveListPresenter.place_of(self.current()))

    def add(self):
        self.presenter().add()
