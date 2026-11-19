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

"""The wizard's Section Players panel: what each player plays in each kind of section.

A heading for each kind of section the form has, and under it a field for each player with
something to choose there: the accompaniment the genre writes for the player, the melody, or a
riff the player knows. The player the genre gives the melody to rests where another has it.
"""

from llamatron.macro_composer import wizard_limits
from llamatron.strings import labels
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.branch import Branch

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
        own = choices.tune_player()
        for role in choices.section_players(kind):
            part = choices.section_part(kind=kind, role=role)
            usual = part == wizard_limits.ACCOMPANIMENT if role != own else part != wizard_limits.RESTS_PART or kind not in choices.tune_kinds()
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
                fields.append(self.get_page().heading(label=kind.capitalize(), is_set=lambda kind=kind: self.kind_is_set(kind)))
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
        return ChoiceField(page=page, label=choices.role_title(role), choices=choices.section_parts_offered(kind=kind, role=role), current=choices.section_part(kind=kind, role=role), set=chosen)
