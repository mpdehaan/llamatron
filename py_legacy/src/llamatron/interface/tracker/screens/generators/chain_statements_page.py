# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The page of a chain's statements about the draws, which say when a clip's pass goes by the whole chain."""

from llamatron.interface.pages.statements import BypassWhenPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels


class ChainStatementsPage(ShowsNamedItem, FieldPage):
    """One chain's table of statements, opened from the chain's editor, whose list of steps has no room for it: the Bypass When
    presenter's form (interface/pages/statements.py)."""

    KEYS = keybindings.ChainStatementsPage
    HELP = help_text.HELP_CHAIN_STATEMENTS_PAGE
    SECTION = Section.CHAINS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.STATEMENTS,)

    def fields(self):
        return BypassWhenPresenter(page=self, document=self.document(), holder=self._chain).form()

    def _chain(self):
        setlist = self.document().get_setlist()
        return setlist.get_chain(self.item)
