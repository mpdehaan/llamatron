# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The wizard's Band branch: who is in the band, and a branch for each player who is."""

from llamatron.interface.forms.nodes import ChoiceField, Field, Toggle
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.interface.tracker.screens.wizard.player_branch import PlayerBranch
from llamatron.user_strings import errors, labels
from llamatron.wizards.create_song import wizard_limits


class BandBranch(Branch):
    """A toggle for each player the genre's band may have, and under it the players who are in."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_BAND_BRANCH

    def refusal(self):
        return None if self.get_choices().is_ready() else errors.ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE

    def children(self):
        """Return a panel for each player the band shows."""
        choices = self.get_choices()
        band = choices.get_band()
        shown = band.roles_shown()
        return [PlayerBranch(page=self.get_page(), role=role) for role in band.roles_in() if role in shown]

    def fields(self):
        choices = self.get_choices()
        # A player with no way of playing written for the subgenre is not offered.
        # Sounds is the band's, which every player follows unless the player has a Sound of its own.
        sounds = ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_SOUNDS_LABEL, choices=list(wizard_limits.BAND_SOUNDS), current=choices.get_sounds().get_band_sounds(), set=self.get_page().choosing(choices.get_sounds().set_band_sounds))
        fields = [sounds]
        if choices.guitarists().offers_one() or choices.guitarists().has_one():
            # One guitarist plays the chords and takes the solo, and is then one player on the screen.
            fields.append(ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_GUITARISTS_LABEL, choices=list(wizard_limits.GUITARIST_COUNTS), names=[str(count) for count in wizard_limits.GUITARIST_COUNTS], current=choices.guitarists().get_count(), set=self.get_page().choosing(choices.guitarists().set_count)))
        if choices.interplay().answerers():
            # Who has the tune, which is only shown, and who answers that player: one of the players who can, or nobody.
            answerers = choices.interplay().answerers()
            names = [choices.player(role).title() for role in answerers]
            by = choices.interplay().answered_by()
            fields += [Field(label=labels.MSG_WIZARD_TUNE_LABEL, value=lambda: choices.player(choices.get_tunes().tune_played_by()).title() if choices.get_tunes().tune_played_by() else labels.MSG_WIZARD_NOBODY),
                       ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_ANSWERED_BY_LABEL, choices=[labels.MSG_WIZARD_NOBODY, *answerers], names=[labels.MSG_WIZARD_NOBODY, *names],
                                   current=by or labels.MSG_WIZARD_NOBODY, shown=choices.player(by).title() if by else labels.MSG_WIZARD_NOBODY,
                                   set=self.get_page().choosing(lambda role: choices.interplay().set_answered_by(None if role == labels.MSG_WIZARD_NOBODY else role)))]
        return [*fields, *(Toggle(label=choices.player(role).title(), on=choices.player(role).is_in(), set=self.setter_of(role)) for role in choices.get_band().roles_shown() if choices.player(role).can_play())]

    def setter_of(self, role):
        """Return what puts a player in the band or leaves the player out, refusing to leave out the last."""
        choices = self.get_choices()
        page = self.get_page()

        def set_in(on):
            if not on and choices.get_band().roles_in() == [role]:
                page.refuse(errors.ERR_WIZARD_LAST_PLAYER)
                return
            try:
                page.choosing(lambda wanted: choices.player(role).set_in(on=wanted))(on)
            except ValueError as problem:
                # A player with no way of playing that fits the subgenre, as a strummed guitar in a waltz that has none written.
                page.refuse(str(problem))
        return set_in
