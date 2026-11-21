# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The group of the song's melodies in the wizard's tree: its hook, then a melody for each kind of section that has one.

The hook comes first, since the chorus is written around it and every other melody stays under it.
"""

from llamatron.interface.tracker.screens.wizard import solo_melody_branch
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.interface.tracker.screens.wizard.hooks_branch import HooksBranch
from llamatron.interface.tracker.screens.wizard.intro_melody_branch import IntroMelodyBranch
from llamatron.interface.tracker.screens.wizard.section_melody_branch import SectionMelodyBranch
from llamatron.interface.tracker.screens.wizard.solo_melody_branch import SoloMelodyBranch
from llamatron.user_strings import labels


class MelodiesBranch(Branch):
    """The branches Hook, one for each kind of section that has a melody, one for each solo, and Intro where the song can have a hook."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_MELODIES_BRANCH

    def summary(self):
        """Return how many melodies the song has, the hook among them, for the overview of Composition."""
        return str(len(self.children())) if self.get_choices().is_ready() else None

    def children(self):
        page = self.get_page()
        choices = self.get_choices()
        if not choices.is_ready():
            return []
        hook = [HooksBranch(page=page)] if choices.get_hook().can_have_hook() else []
        # The intro comes last: its melody is the hook, said before anybody sings, so it is made from the melodies above it. The
        # panel is there whenever the Hook panel is, whoever can say the hook in the intro just now, so that a change to the form,
        # which is under this group in the tree, never moves the rows above the cursor.
        intro = [IntroMelodyBranch(page=page)] if choices.get_hook().can_have_hook() else []
        # A solo is its player's, never the tune's player's, so each solo has a panel of its own after the sections' melodies.
        solos = [SoloMelodyBranch(page=page, number=number) for number, _ in enumerate(choices.get_solos().solo_places(), start=solo_melody_branch.FIRST_SOLO)]
        return [*hook, *(SectionMelodyBranch(page=page, kind=kind) for kind in choices.get_tunes().tune_kinds()), *solos, *intro]
