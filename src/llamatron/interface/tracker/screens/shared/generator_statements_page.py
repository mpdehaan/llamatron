# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The page of a built-in generator's statements about the draws, which say when a clip's pass goes by the generator,
opened from the Conditions button on the generator's tab of a clip's or a track's page."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared import statements
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.statements import statement_section
from llamatron.user_strings import help as help_text, labels


class GeneratorStatementsPage(GeneratorEditor, FieldPage):
    """One built-in generator's table of statements, which its tab has no room for."""

    KEYS = keybindings.GeneratorStatementsPage
    HELP = help_text.HELP_GENERATOR_STATEMENTS_PAGE
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.STATEMENTS,)

    def __init__(self, *, holder, name, section, built_in=None):
        # The section names the generator before the page opens, since opening asks for the page's crumbs and caption.
        self.SECTION = section
        super().__init__(holder=holder, name=name, built_in=built_in)
        # The table is what the page is for, so its heading starts open.
        self.app.open_field_sections |= {labels.MSG_BYPASS_WHEN_LABEL}

    def fields(self):
        document = self.document()
        return statement_section(
            page=self, label=labels.MSG_BYPASS_WHEN_LABEL, table=statements.FIRST_TABLE, statements=self._statements,
            store=lambda place, statement: document.change_set(self.settings().set_bypass_statement, place=place, statement=statement),
        )

    def shared_sections(self):
        """Return nothing more: the generator's table, which a generator's page adds after its settings, is this page's own."""
        return []

    def _statements(self):
        settings = self.settings()
        return settings.get_bypass_when()
