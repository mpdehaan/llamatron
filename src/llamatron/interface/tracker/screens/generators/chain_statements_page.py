# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The page of a chain's statements about the draws, which say when a clip's pass goes by the whole chain."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared import statements
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.interface.tracker.screens.shared.statements import statement_lines
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels


class ChainStatementsPage(ShowsNamedItem, FieldPage):
    """One chain's table of statements, opened from the chain's editor, whose list of steps has no room for it."""

    KEYS = keybindings.ChainStatementsPage
    HELP = help_text.HELP_CHAIN_STATEMENTS_PAGE
    SECTION = Section.CHAINS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.STATEMENTS,)

    def fields(self):
        """Return the table's lines with no heading, since the table is all the page holds."""
        document = self.document()
        return statement_lines(
            page=self, table=statements.FIRST_TABLE, statements=lambda: document.song().get_setlist().get_chain(self.item).get_bypass_when(),
            store=lambda place, statement: document.change_set(document.get_setlist().get_chain(self.item).set_bypass_statement, place=place, statement=statement),
        )
