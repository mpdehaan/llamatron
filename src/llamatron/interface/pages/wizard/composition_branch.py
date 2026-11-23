# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The wizard's Composition branch: what the song is written from, each a branch under it: its chords, its melody and its hooks."""


from llamatron.interface.forms.remarks import dim_remark, remark
from llamatron.interface.pages.wizard.branch import Branch
from llamatron.interface.pages.wizard.chords_branch import ChordsBranch
from llamatron.interface.pages.wizard.melodies_branch import MelodiesBranch
from llamatron.interface.pages.wizard.melody_branch import MelodyBranch
from llamatron.interface.pages.wizard.riff_assign_branch import RiffAssignBranch
from llamatron.interface.pages.wizard.riffs_branch import RiffsBranch
from llamatron.interface.pages.wizard.section_players_branch import SectionPlayersBranch
from llamatron.user_strings import errors, labels, marks, messages


class CompositionBranch(Branch):
    """The branches Chords, Melody, Melodies, which holds the hook and a melody for each kind of section, Riffs, Riff Assign and Section Players, with what each is set to shown at a glance."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_COMPOSITION_BRANCH

    def refusal(self):
        return None if self.get_choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def children(self):
        page = self.get_page()
        return [ChordsBranch(page=page), MelodyBranch(page=page), MelodiesBranch(page=page), RiffsBranch(page=page), RiffAssignBranch(page=page), SectionPlayersBranch(page=page)]

    def remarks(self, width):
        """Return each branch under this one with what it is set to, leaving out a branch the subgenre has nothing to choose in; or what to choose first."""
        if not self.get_choices().is_ready():
            return [dim_remark(messages.MSG_WIZARD_CHOOSE_FIRST)]
        shown = [(child.name(), child.summary()) for child in self.children() if child.summary() is not None]
        longest = max((len(name) for name, _ in shown), default=0)
        return [remark(marks.MSG_WIZARD_COMPOSITION_LINE.format(name=name, width=longest, value=value)) for name, value in shown]
