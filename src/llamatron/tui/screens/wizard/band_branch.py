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

from llamatron.macro_composer import wizard_limits
from llamatron.strings import errors, labels
from llamatron.tui.screens.shared.field import ChoiceField, Field, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.player_branch import PlayerBranch


class BandBranch(Branch):
    """A toggle for each player the genre's band may have, and under it the players who are in."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_BAND_BRANCH

    def refusal(self):
        return None if self.get_choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def children(self):
        return [PlayerBranch(page=self.get_page(), role=role) for role in self.get_choices().roles_in() if role in self.get_choices().roles_shown()]

    def fields(self):
        choices = self.get_choices()
        # A player with no way of playing written for the subgenre is not offered.
        # Sounds is the band's, which every player follows unless the player has a Sound of its own.
        sounds = ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_SOUNDS_LABEL, choices=list(wizard_limits.BAND_SOUNDS), current=choices.get_band_sounds(), set=self.get_page().choosing(choices.set_band_sounds))
        fields = [sounds]
        if choices.offers_one_guitarist() or choices.has_one_guitarist():
            # One guitarist plays the chords and takes the solo, and is then one player on the screen.
            fields.append(ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_GUITARISTS_LABEL, choices=list(wizard_limits.GUITARIST_COUNTS), names=[str(count) for count in wizard_limits.GUITARIST_COUNTS], current=choices.get_guitarists(), set=self.get_page().choosing(choices.set_guitarists)))
        if choices.answerers():
            # Who has the tune, which is only shown, and who answers that player: one of the players who can, or nobody.
            answerers = choices.answerers()
            names = [choices.role_title(role) for role in answerers]
            by = choices.answered_by()
            fields += [Field(label=labels.MSG_WIZARD_TUNE_LABEL, value=lambda: choices.role_title(choices.tune_played_by()) if choices.tune_played_by() else labels.MSG_WIZARD_NOBODY),
                       ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_ANSWERED_BY_LABEL, choices=[labels.MSG_WIZARD_NOBODY, *answerers], names=[labels.MSG_WIZARD_NOBODY, *names],
                                   current=by or labels.MSG_WIZARD_NOBODY, shown=choices.role_title(by) if by else labels.MSG_WIZARD_NOBODY,
                                   set=self.get_page().choosing(lambda role: choices.set_answered_by(None if role == labels.MSG_WIZARD_NOBODY else role)))]
        return [*fields, *(Toggle(label=choices.role_title(role), on=choices.role_is_in(role), set=self.setter_of(role)) for role in choices.roles_shown() if choices.role_can_play(role))]

    def setter_of(self, role):
        """Return what puts a player in the band or leaves the player out, refusing to leave out the last."""
        choices = self.get_choices()
        page = self.get_page()

        def set_in(on):
            if not on and choices.roles_in() == [role]:
                page.refuse(errors.ERR_WIZARD_LAST_PLAYER)
                return
            try:
                page.choosing(lambda wanted: choices.set_role_in(role=role, on=wanted))(on)
            except ValueError as problem:
                # A player with no way of playing that fits the subgenre, as a strummed guitar in a waltz that has none written.
                page.refuse(str(problem))
        return set_in
