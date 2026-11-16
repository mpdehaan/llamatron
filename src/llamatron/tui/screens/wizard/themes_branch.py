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

"""The wizard's Themes branch: the chord progression the song is built on and the melody style its tunes are sketched by."""

from llamatron.strings.labels import MSG_WIZARD_ANY_PROGRESSION, MSG_WIZARD_MELODY_LABEL, MSG_WIZARD_PROGRESSION_LABEL, MSG_WIZARD_THEMES_BRANCH, MSG_WIZARD_USUAL_MELODY
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.song_ways_branch import A_CHOICE, SongWaysBranch


class ThemesBranch(SongWaysBranch):
    """The song's Progression and Melody; each theme's own settings are to come."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_THEMES_BRANCH

    def traits(self):
        return []

    def set_progression(self, progression):
        choices = self.choices()
        if progression == MSG_WIZARD_ANY_PROGRESSION:
            choices.set_any_progression()
        else:
            choices.set_way(trait=choices.progression_trait(), value=progression)

    def fields(self):
        choices = self.choices()
        if not choices.is_ready():
            return []
        fields = []
        trait = choices.progression_trait()
        if trait is not None and len(choices.song_ways(trait)) >= A_CHOICE:
            # The first choice, the one a song starts with, leaves the progression to chance: each run takes one of the subgenre's.
            fields.append(ChoiceField(page=self.page(), label=MSG_WIZARD_PROGRESSION_LABEL, choices=[MSG_WIZARD_ANY_PROGRESSION, *choices.song_ways(trait)],
                                      current=MSG_WIZARD_ANY_PROGRESSION if choices.has_any_progression() else choices.get_way(trait), set=self.page().choosing(self.set_progression)))
        styles = choices.melody_styles()
        if len(styles) >= A_CHOICE:
            # The first choice leaves each player's tunes to the style the genre gives the player.
            fields.append(ChoiceField(page=self.page(), label=MSG_WIZARD_MELODY_LABEL, choices=[MSG_WIZARD_USUAL_MELODY, *styles], current=choices.get_melody() or MSG_WIZARD_USUAL_MELODY,
                                      set=self.page().choosing(lambda style: choices.set_melody(None if style == MSG_WIZARD_USUAL_MELODY else style))))
        return fields
