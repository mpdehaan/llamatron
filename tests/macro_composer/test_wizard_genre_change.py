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

"""What another genre gives up of a wizard's choices and what it keeps, counted for the Change Genre question."""

import unittest

from llamatron.macro_composer import arranger, wizard_limits
from llamatron.macro_composer.wizard_choices import WizardChoices

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_KIND = 'verse'
ANOTHER_KIND = 'chorus'
A_SEED = 7
A_TEMPO = 100
# The place of a section whose chords a test writes by hand, and the chords written.
A_PLACE = 1
OWN_CHORDS = [1, 4]
NOTHING_LOST = ({}, {})


def chosen():
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(A_SUBGENRE)
    choices.set_seed(A_SEED)
    return choices


class TestLostWithGenre(unittest.TestCase):

    def test_nothing_is_lost_before_anything_is_chosen_by_hand_whatever_the_genre(self):
        choices = WizardChoices()
        self.assertEqual(choices.lost_with_genre(), NOTHING_LOST)
        choices.set_genre(A_GENRE)
        self.assertEqual(choices.lost_with_genre(), NOTHING_LOST)
        self.assertEqual(chosen().lost_with_genre(), NOTHING_LOST)

    def test_the_tempo_and_the_seed_are_not_counted(self):
        choices = chosen()
        choices.set_tempo(A_TEMPO)
        choices.set_seed(A_SEED + 1)
        self.assertEqual(choices.lost_with_genre(), NOTHING_LOST)

    def test_each_setting_of_the_band_changed_is_counted_once_and_a_setting_put_back_is_not(self):
        choices = chosen()
        player = next(role for role in choices.roles_in() if role != choices.tune_player() and role in choices.get_tunes().tune_players_offered())
        choices.get_tunes().set_tune_played_by(player)
        self.assertEqual(choices.lost_with_genre(), ({wizard_limits.LOST_BAND_SETTINGS: 1}, {}))
        left_out = next(role for role in choices.roles_in() if role != player and role in choices.get_tunes().tune_players_offered())
        choices.set_role_in(role=left_out, on=False)
        self.assertEqual(choices.lost_with_genre()[0][wizard_limits.LOST_BAND_SETTINGS], 2)
        choices.set_role_in(role=left_out, on=True)
        choices.get_tunes().set_tune_played_by(None)
        self.assertEqual(choices.lost_with_genre(), NOTHING_LOST)

    def test_chords_written_by_hand_the_form_and_new_takes_are_lost_and_counted_by_kind(self):
        choices = chosen()
        choices.get_tunes().new_tune_take(A_KIND)
        choices.get_tunes().new_tune_take(A_KIND)
        choices.get_tunes().new_tune_take(ANOTHER_KIND)
        self.assertEqual(choices.lost_with_genre(), ({wizard_limits.LOST_TUNE_TAKES: 2}, {}))
        choices.set_section_own(place=A_PLACE, field=arranger.CHORDS, value=OWN_CHORDS)
        lost, kept = choices.lost_with_genre()
        self.assertEqual(lost[wizard_limits.LOST_OWN_CHORDS], 1)
        self.assertEqual(lost[wizard_limits.LOST_FORM], 1)
        self.assertEqual(kept, {})

    def test_tunes_written_by_hand_are_kept_and_alone_lose_nothing(self):
        choices = chosen()
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=choices.get_tunes().tune_pattern(A_KIND))
        self.assertEqual(choices.lost_with_genre(), ({}, {wizard_limits.KEPT_OWN_TUNES: 1}))
        choices.get_tunes().new_tune_take(ANOTHER_KIND)
        self.assertEqual(choices.lost_with_genre(), ({wizard_limits.LOST_TUNE_TAKES: 1}, {wizard_limits.KEPT_OWN_TUNES: 1}))
