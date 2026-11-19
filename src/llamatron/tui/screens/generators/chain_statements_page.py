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

"""The page of a chain's statements about the registers, which say when a clip's pass goes by the whole chain."""

from llamatron.composition.file_format import Section
from llamatron.strings import help as help_text, labels
from llamatron.tui import keybindings
from llamatron.tui.screens.shared import statements
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.shared.statements import statement_section


class ChainStatementsPage(ShowsNamedItem, FieldPage):
    """One chain's table of statements, opened from the chain's editor, whose list of steps has no room for it."""

    KEYS = keybindings.ChainStatementsPage
    HELP = help_text.HELP_CHAIN_STATEMENTS_PAGE
    SECTION = Section.CHAINS
    CRUMBS_BEFORE = (labels.Crumb.CHAINS,)
    CRUMBS_AFTER = (labels.Crumb.STATEMENTS,)

    def __init__(self, *, holder, name):
        super().__init__(holder=holder, name=name)
        # The table is what the page is for, so its heading starts open.
        self.app.open_field_sections |= {labels.MSG_BYPASS_WHEN_LABEL}

    def fields(self):
        document = self.document()
        return statement_section(
            page=self, label=labels.MSG_BYPASS_WHEN_LABEL, table=statements.FIRST_TABLE, statements=lambda: document.song().get_chain(self.item).get_bypass_when(),
            store=lambda place, statement: document.change(document.setlist().get_chain(self.item).set_bypass_statement, place=place, statement=statement),
        )
