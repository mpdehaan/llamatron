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

"""The wizard's Riff Assign panel: the riffs each player knows.

A player knows the riffs written for the player, and may be given a riff written for another,
which the player then plays in the player's own octave. What a player knows is what Section
Players offers the player in each kind of section.
"""

from llamatron.composition.checks import listed
from llamatron.strings import errors, labels, legends, marks, messages
from llamatron.tui import drawing
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.wizard.riffs_branch import RiffsBranch

# What a riff's row is known by: the player and the riff, since two players may know one riff.
KNOWN_KEY = '{player}: {riff}'


class RiffAssignBranch(RiffsBranch):
    """A heading for each player who can play a riff, with the riffs the player knows and a row that adds one of the song's."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_RIFF_ASSIGN_BRANCH

    def summary(self):
        """Return how many riffs the players know between them, or None where the song has no riff."""
        choices = self.get_choices()
        if not choices.is_ready() or not choices.get_riffs().riff_names():
            return None
        return str(sum(len(choices.get_riffs().riffs_known_by(role)) for role in choices.get_riffs().riff_instruments()))

    def fields(self):
        choices = self.get_choices()
        if not choices.is_ready():
            return []
        fields = []
        for role in choices.get_riffs().riff_instruments():
            known = choices.get_riffs().riffs_known_by(role)
            columns = marks.MSG_WIZARD_RIFF_KNOWN_ROW.format(player=labels.MSG_WIZARD_RIFF_FOR_COLUMN, width=self.for_width(), used=labels.MSG_WIZARD_RIFF_PLAYED_IN_COLUMN)
            fields.append(self.player_heading(role=role, count=len(known), columns=columns))
            fields += [self.known_field(role=role, riff=riff) for riff in known]
            fields.append(Field(label=marks.MSG_ADD_ROW_MARK, value=lambda: drawing.NOTHING, enter=lambda role=role: self.give(role), enter_what=legends.What.ADD))
        return fields

    def for_width(self):
        """Return how wide the FOR column is: as wide as its widest value on the panel, the name of a player a riff was written
        for, and no narrower than its heading, so that the column after it starts at one place on every row, as a table's."""
        choices = self.get_choices()
        written_for = [choices.player(choices.get_riffs().riff_written_for(riff)).title() for role in choices.get_riffs().riff_instruments() for riff in choices.get_riffs().riffs_known_by(role)]
        return max(len(name) for name in [labels.MSG_WIZARD_RIFF_FOR_COLUMN, *written_for])

    def known_field(self, *, role, riff):
        """Return the row of a riff a player knows: who the riff was written for and the kinds of section the player plays it in; Bksp takes the riff from the player."""
        choices = self.get_choices()

        def shown():
            return marks.MSG_WIZARD_RIFF_KNOWN_ROW.format(player=choices.player(choices.get_riffs().riff_written_for(riff)).title(), width=self.for_width(), used=listed(choices.get_riffs().kinds_playing(role=role, riff=riff))).rstrip()
        return Field(label=riff, value=shown, clear=lambda: self.take(role=role, riff=riff), clear_what=legends.What.DELETE)

    def field_keys(self):
        """Return the list's key: A gives the player of the heading another of the song's riffs."""
        page = self.get_page()
        return [page.bind(page.KEYS.ADD, action=lambda: self.give(self.role_under_cursor()))] if self.role_under_cursor() is not None else []

    def give(self, role):
        """Offer the song's riffs a player does not know, and have the player know the one picked."""
        choices = self.get_choices()
        page = self.get_page()
        title = choices.player(role).title()
        offered = choices.get_riffs().riffs_to_give(role)
        if not offered:
            page.refuse(errors.ERR_WIZARD_NO_RIFF_TO_GIVE)
            return

        def given(place):
            page.choosing(lambda riff: choices.get_riffs().give_riff(role=role, riff=riff))(offered[place])
            page.app.open_field_sections.add(title)
            page.say(messages.MSG_WIZARD_RIFF_GIVEN.format(player=title, riff=offered[place]))
        page.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_GIVE_RIFF_TITLE.format(player=title), options=offered), then=given)

    def take(self, *, role, riff):
        """Take a riff from a player, asking first where the player plays it."""
        choices = self.get_choices()
        page = self.get_page()
        title = choices.player(role).title()
        used = choices.get_riffs().kinds_playing(role=role, riff=riff)

        def taken(_=None):
            page.choosing(lambda name: choices.get_riffs().take_riff_from(role=role, riff=name))(riff)
            page.say(messages.MSG_WIZARD_RIFF_TAKEN_FROM.format(player=title, riff=riff))
        if not used:
            taken()
            return
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TAKE_RIFF_TITLE.format(riff=riff, player=title), messages=[messages.MSG_WIZARD_RIFF_USED_IN.format(kinds=listed(used))], starts_on_no=True, deletes=True),
                 then=taken)
