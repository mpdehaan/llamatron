# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Draws page: the Draws presenter's form (interface/pages/draws.py), the song's eight draws over their strips, with the
slots lit while a song plays and the digits that type a slot."""
from llamatron.interface.forms.nodes import Strip
from llamatron.interface.pages.draws import DrawsPresenter
from llamatron.interface.tracker import keybindings, themes
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.user_strings import help as help_text, labels


class DrawsPage(FieldPage):
    """Each draw's direction, how many slots it holds, the range its values keep to, whether conditions redraw it, and its strip."""

    THEME = themes.DRAWS

    KEYS = keybindings.DrawsPage
    # A blank line between one draw's section and the next.
    HEADINGS_APART = True

    crumbs = (labels.Crumb.DRAWS,)
    HELP = help_text.HELP_DRAWS_PAGE

    def presenter(self):
        """Return what the page shows, for the set as it is now and the slots lit while a song plays."""
        return DrawsPresenter(page=self, document=self.document(), lit=self.app.transport.draw_places())

    def fields(self):
        return self.presenter().form()

    def fields_depend_on(self):
        """Return what the fields read besides the set: the slot each draw last took a value from while a song plays."""
        return frozendict(self.app.transport.draw_places())

    def page_keys(self):
        """Return the digits that type a slot, while the cursor is on a draw's strip."""
        if isinstance(self.field(), Strip) and self.cell_field() is not None:
            return [self.bind(self.KEYS.TYPE_SLOT, action=self.type_slot, wants_key=True)]
        return []

    def type_slot(self, digit):
        """Put the number of a digit typed in the slot under the cursor, kept within the draw's range."""
        self.cell_field().set_within(int(digit))

