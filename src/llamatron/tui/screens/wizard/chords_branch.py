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
"""The wizard's Chords branch, under Composition: the chord progression the song is built on."""

from llamatron.strings.labels import MSG_WIZARD_ANY_PROGRESSION, MSG_WIZARD_CHORDS_BRANCH, MSG_WIZARD_PROGRESSION_LABEL
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.song_ways_branch import A_CHOICE, SongWaysBranch


class ChordsBranch(SongWaysBranch):
    """The song's Progression; a section's own chords are to come."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_CHORDS_BRANCH

    def traits(self):
        return []

    def offers_progressions(self):
        """Return whether the subgenre has more than one progression, since one is nothing to choose."""
        choices = self.choices()
        trait = choices.progression_trait() if choices.is_ready() else None
        return trait is not None and len(choices.song_ways(trait)) >= A_CHOICE

    def progression(self):
        """Return the progression as the field shows it: the one chosen, or the word for one left to chance."""
        choices = self.choices()
        return MSG_WIZARD_ANY_PROGRESSION if choices.has_any_progression() else choices.get_way(choices.progression_trait())

    def set_progression(self, progression):
        choices = self.choices()
        if progression == MSG_WIZARD_ANY_PROGRESSION:
            choices.set_any_progression()
        else:
            choices.set_way(trait=choices.progression_trait(), value=progression)

    def summary(self):
        return self.progression() if self.offers_progressions() else None

    def fields(self):
        if not self.offers_progressions():
            return []
        choices = self.choices()
        # The first choice, the one a song starts with, leaves the progression to chance: each run takes one of the subgenre's.
        return [ChoiceField(page=self.page(), label=MSG_WIZARD_PROGRESSION_LABEL, choices=[MSG_WIZARD_ANY_PROGRESSION, *choices.song_ways(choices.progression_trait())],
                            current=self.progression(), set=self.page().choosing(self.set_progression))]
