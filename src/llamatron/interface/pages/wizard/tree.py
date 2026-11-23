# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The song wizard's tree as a presenter: its top panels, in the order a song is thought through, which panels are open, showing
the panels under them, and the rows the tree shows, each panel with how deep it is. The wizard's page keeps the tree's cursor
and draws the rows."""

from llamatron.interface.pages.wizard.band_branch import BandBranch
from llamatron.interface.pages.wizard.composition_branch import CompositionBranch
from llamatron.interface.pages.wizard.create_branch import CreateBranch
from llamatron.interface.pages.wizard.form_branch import FormBranch
from llamatron.interface.pages.wizard.genre_branch import GenreBranch
from llamatron.interface.pages.wizard.subgenre_branch import SubgenreBranch
from llamatron.user_strings import labels

# The panels that start open: the Band and Form panels among them, so that the players and the sections, and the keys that
# add, copy, remove and move a section, show themselves with no key to learn.
OPEN_AT_START = (
    labels.MSG_WIZARD_GENRE_BRANCH,
    labels.MSG_WIZARD_BAND_BRANCH,
    labels.MSG_WIZARD_COMPOSITION_BRANCH,
    labels.MSG_WIZARD_MELODIES_BRANCH,
    labels.MSG_WIZARD_FORM_BRANCH,
)
# How deep the top panels are.
TOP = 0


class WizardTree:
    """The wizard's tree of panels, for the wizard's page, which every panel asks for its dialogs and the choices."""

    __slots__ = ('_page', '_open')

    def __init__(self, *, page):
        self._page = page
        self._open = set(OPEN_AT_START)

    def roots(self):
        """Return the tree's top panels, in the order a song is thought through: each is a page of the wizard, the genre and then the subgenre unlocking the rest."""
        page = self._page
        return [
            GenreBranch(page=page),
            SubgenreBranch(page=page),
            BandBranch(page=page),
            CompositionBranch(page=page),
            FormBranch(page=page),
            CreateBranch(page=page),
        ]

    def rows(self):
        """Return the panels the tree shows, each with how deep it is: every top panel, and the panels under each open one, however deep."""
        rows = []
        for root in self.roots():
            self._list(rows=rows, branch=root, depth=TOP)
        return rows

    def shows_children(self, branch):
        """Return whether a panel of the tree is open, showing the panels under it, which a locked panel never is."""
        return branch.key() in self._open and not branch.refusal()

    def open(self, key):
        """Open a panel by what it is remembered by (Branch.key), showing the panels under it."""
        self._open.add(key)

    def close(self, key):
        self._open.discard(key)

    def open_keys(self):
        """Return what the open panels are remembered by, in order, for what the page keeps its rows by."""
        return tuple(sorted(self._open))

    def _list(self, *, rows, branch, depth):
        rows.append((depth, branch))
        # A locked panel shows nothing under it, whatever was open before the choice that locked it.
        if self.shows_children(branch):
            for child in branch.children():
                self._list(rows=rows, branch=child, depth=depth + 1)
