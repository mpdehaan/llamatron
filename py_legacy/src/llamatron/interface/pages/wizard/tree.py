# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The song wizard's tabs as a presenter: its top panels, one a tab, in the order a song is thought through, and the rows each
tab lists, every panel under its tab's panel shown, each with how deep it is. The wizard's page keeps the cursor and draws the
tabs and their rows."""

from llamatron.interface.pages.wizard.band_branch import BandBranch
from llamatron.interface.pages.wizard.composition_branch import CompositionBranch
from llamatron.interface.pages.wizard.create_branch import CreateBranch
from llamatron.interface.pages.wizard.form_branch import FormBranch
from llamatron.interface.pages.wizard.genre_branch import GenreBranch

# How deep a tab's own panel is, at the head of its rows.
TOP = 0


class WizardTree:
    """The wizard's tabs and their panels, for the wizard's page, which every panel asks for its dialogs and the choices."""

    __slots__ = ('_page',)

    def __init__(self, *, page):
        self._page = page

    def roots(self):
        """Return the tabs' panels, in the order a song is thought through, the genre and the subgenre unlocking the rest."""
        page = self._page
        return [
            GenreBranch(page=page),
            BandBranch(page=page),
            CompositionBranch(page=page),
            FormBranch(page=page),
            CreateBranch(page=page),
        ]

    def rows(self):
        """Return every tab's rows, one tab after another, each with how deep it is: the tab's panel, and every panel under it,
        however deep, unless the tab's panel is locked."""
        rows = []
        for root in self.roots():
            self._list(rows=rows, branch=root, depth=TOP)
        return rows

    def shows_children(self, branch):
        """Return whether a panel shows the panels under it, which every panel does but a locked one."""
        return not branch.refusal()

    def _list(self, *, rows, branch, depth):
        rows.append((depth, branch))
        if self.shows_children(branch):
            for child in branch.children():
                self._list(rows=rows, branch=child, depth=depth + 1)
