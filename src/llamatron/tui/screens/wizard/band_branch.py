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

"""The wizard's Band branch: who is in the band, and a branch for each player who is."""

from llamatron.strings.errors import ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE, ERR_WIZARD_LAST_PLAYER
from llamatron.macro_composer.wizard_choices import BAND_SOUNDS, GUITARIST_COUNTS
from llamatron.strings.labels import MSG_WIZARD_BAND_BRANCH, MSG_WIZARD_GUITARISTS_LABEL, MSG_WIZARD_SOUNDS_LABEL
from llamatron.tui.screens.shared.field import ChoiceField, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.player_branch import PlayerBranch


class BandBranch(Branch):
    """A toggle for each player the genre's band may have, and under it the players who are in."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_BAND_BRANCH

    def refusal(self):
        return None if self.choices().is_ready() else ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def children(self):
        return [PlayerBranch(page=self.page(), role=role) for role in self.choices().roles_in() if role in self.choices().roles_shown()]

    def fields(self):
        choices = self.choices()
        # A player with no way of playing written for the subgenre is not offered.
        # Sounds is the band's, which every player follows unless the player has a Sound of its own.
        sounds = ChoiceField(page=self.page(), label=MSG_WIZARD_SOUNDS_LABEL, choices=list(BAND_SOUNDS), current=choices.get_band_sounds(), set=self.page().choosing(choices.set_band_sounds))
        fields = [sounds]
        if choices.offers_one_guitarist() or choices.has_one_guitarist():
            # One guitarist plays the chords and takes the solo, and is then one player on the screen.
            fields.append(ChoiceField(page=self.page(), label=MSG_WIZARD_GUITARISTS_LABEL, choices=list(GUITARIST_COUNTS), names=[str(count) for count in GUITARIST_COUNTS], current=choices.get_guitarists(), set=self.page().choosing(choices.set_guitarists)))
        return [*fields, *(Toggle(label=choices.role_title(role), on=choices.role_is_in(role), set=self.setter_of(role)) for role in choices.roles_shown() if choices.role_can_play(role))]

    def setter_of(self, role):
        """Return what puts a player in the band or leaves the player out, refusing to leave out the last."""
        choices = self.choices()
        page = self.page()

        def set_in(on):
            if not on and choices.roles_in() == [role]:
                page.refuse(ERR_WIZARD_LAST_PLAYER)
                return
            try:
                page.choosing(lambda wanted: choices.set_role_in(role=role, on=wanted))(on)
            except ValueError as problem:
                # A player with no way of playing that fits the subgenre, as a strummed guitar in a waltz that has none written.
                page.refuse(str(problem))
        return set_in
