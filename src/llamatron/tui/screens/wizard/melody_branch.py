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

"""The wizard's Melody panel: what is decided once for every melody of the song.

Who carries the melody, how busy the melodies are, how wide they range, how much they repeat
and their character, each starting at what the genre does, then how the melody is delivered.
A kind of section's own melody has a panel of its own (section_melody_branch.py).
"""

from llamatron.strings import labels, legends, messages
from llamatron.tui.screens.shared.field import Button, ChoiceField, Toggle
from llamatron.tui.screens.wizard.branch import Branch

# The choice that leaves the character to the genre, which is no character's name.
FROM_GENRE = ''


class MelodyBranch(Branch):
    """Who plays the song's melody, how busy, how wide and how repeated the melodies are, their character, and the Phrasing."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_MELODY_BRANCH

    def has_melody(self):
        return self.get_choices().is_ready() and bool(self.get_choices().get_tunes().tune_kinds())

    def summary(self):
        """Return who plays the song's melody, or None for a song with none."""
        choices = self.get_choices()
        return choices.get_band().role_title(choices.get_tunes().tune_played_by()) if self.has_melody() and choices.get_tunes().tune_played_by() else None

    def fields(self):
        if not self.has_melody():
            return []
        choices = self.get_choices()
        fields = [self.player_field(), *(self.way_field(field) for field in choices.melody_fields())]
        if choices.melody_characters_offered():
            fields.append(self.character_field())
        return fields + self.phrasing_fields()

    def player_field(self):
        choices = self.get_choices()
        offered = choices.get_tunes().tune_players_offered()
        return ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_TUNE_LABEL, choices=offered, names=[choices.get_band().role_title(role) for role in offered],
                           current=choices.get_tunes().tune_played_by(), shown=choices.get_band().role_title(choices.get_tunes().tune_played_by()), set=self.get_page().choosing(choices.get_tunes().set_tune_played_by))

    def way_field(self, field):
        """Return the field of how busy the melodies are, how wide they range or how much they repeat."""
        choices = self.get_choices()
        ways = choices.melody_ways_offered(field)
        # The genre's own value is said to be so, in the field and in its list.
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == choices.genre_melody_way(field) else value for value in ways]
        now = choices.get_melody_way(field)
        return ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_MELODY_WAY_LABELS[field], choices=ways, names=names, current=now, shown=names[ways.index(now)],
                           set=self.get_page().choosing(lambda value: choices.set_melody_way(field=field, value=value)))

    def character_field(self):
        """Return the field of the melodies' character: the genre's own until one is chosen, which the list's first entry gives back."""
        choices = self.get_choices()
        offered = choices.melody_characters_offered()
        return ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_CHARACTER_LABEL, choices=[FROM_GENRE, *offered], names=[labels.MSG_WIZARD_USUAL_MELODY, *offered],
                           current=choices.get_melody_character() or FROM_GENRE, shown=choices.get_melody_character() or labels.MSG_WIZARD_USUAL_MELODY,
                           set=self.get_page().choosing(lambda chosen: choices.set_melody_character(chosen or None)))

    def phrasing_fields(self):
        """Return how the melody is delivered: the Phrasing switch, and under it the button that opens the Phrasing page, where a
        line's length, its breath, its rise and fall and its notes are chosen."""
        choices = self.get_choices()
        page = self.get_page()
        on = choices.tune_phrasing() is not None
        fields = [Toggle(label=labels.MSG_WIZARD_PHRASING_LABEL, on=on, set=page.choosing(lambda wanted: choices.set_tune_phrasing(None if wanted else False)))]
        if on:
            fields.append(Button(label=labels.MSG_WIZARD_EDIT_PHRASING_BUTTON, key_name=legends.KeyName.ENTER, enter=page.edit_tune_phrasing, enter_what=legends.What.EDIT))
        return fields

    def listens(self):
        choices = self.get_choices()
        if not self.has_melody() or choices.get_band().tune_player() is None or choices.tune_scene() is None:
            return None
        return messages.MSG_WIZARD_LISTEN_TUNE, choices.tune_scene(), choices.get_band().tune_player()
