# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The wizard's Section Players panel: what each player plays in each kind of section.

A heading for each kind of section the form has, and under it a field for each player with
something to choose there: the accompaniment the genre writes for the player, the melody, or a
riff the player knows. The player the genre gives the melody to rests where another has it.
"""

import functools

from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.user_strings import labels
from llamatron.wizards.create_song import wizard_limits

# What a player plays where nothing was chosen for the player.
UNCHOSEN_PARTS = (wizard_limits.ACCOMPANIMENT, wizard_limits.RESTS_PART)


class SectionPlayersBranch(Branch):
    """A heading for each kind of section, with what each player plays there."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_SECTION_PLAYERS_BRANCH

    def summary(self):
        """Return how many kinds of section have a player playing a riff or another player's melody, or None where nothing can be chosen."""
        choices = self.get_choices()
        if not choices.is_ready():
            return None
        kinds = [kind for kind in choices.section_player_kinds() if choices.section_players(kind)]
        return str(len([kind for kind in kinds if self.kind_is_set(kind)])) if kinds else None

    def kind_is_set(self, kind):
        """Return whether anybody plays other than the genre says in a kind of section: a riff, another player's melody, or a rest from the melody."""
        choices = self.get_choices()
        own = choices.get_band().tune_player()
        for role in choices.section_players(kind):
            part = choices.section_part(kind=kind, role=role)
            usual = part == wizard_limits.ACCOMPANIMENT if role != own else part != wizard_limits.RESTS_PART or kind not in choices.get_tunes().tune_kinds()
            if not usual:
                return True
        return False

    def fields(self):
        choices = self.get_choices()
        if not choices.is_ready():
            return []
        fields = []
        for kind in choices.section_player_kinds():
            players = choices.section_players(kind)
            if players:
                fields.append(self.get_page().heading(label=kind.capitalize(), is_set=functools.partial(self.kind_is_set, kind)))
                fields += [self.part_field(kind=kind, role=role) for role in players]
        return fields

    def part_field(self, *, kind, role):
        """Return the field of what a player plays in a kind of section."""
        choices = self.get_choices()
        page = self.get_page()

        def chosen(part):
            try:
                page.choosing(lambda value: choices.set_section_part(kind=kind, role=role, part=value))(part)
            except ValueError as problem:
                page.refuse(str(problem))
        return ChoiceField(page=page, label=choices.player(role).title(), choices=choices.section_parts_offered(kind=kind, role=role), current=choices.section_part(kind=kind, role=role), set=chosen)
