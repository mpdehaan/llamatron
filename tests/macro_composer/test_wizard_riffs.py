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

"""Tests of the riffs of the song wizard's choices: the riffs a song has, who knows each, and what each player plays in each kind of section."""

import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import riffs
from llamatron.macro_composer import wizard_choices
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.strings import macro_composer as composer_text, names
from llamatron.support import version

A_NAME = 'made'
A_SEED = 11
A_GENRE = 'rock'
A_RIFF_SUBGENRE = 'hard rock'
A_PLAIN_SUBGENRE = 'folk rock'
THE_GUITAR = 'guitar'
THE_BASS = 'bass'
THE_DRUMS = 'drums'
A_VERSE = 'verse'
ONE_BAR = 1
A_NEW_NAME = 'main riff'
NOT_A_RIFF = 'no such riff'
NOT_A_PART = 'sideways'
FIRST_RIFF = names.MSG_NEW_RIFF_WORD + '-1'
SECOND_RIFF = names.MSG_NEW_RIFF_WORD + '-2'


def chosen(*, subgenre=A_PLAIN_SUBGENRE):
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    return choices


def patterns(choices):
    return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]


def pattern_of(*, role, riff):
    return composer_text.MSG_PART_OF_SECTION.format(role, riff)


class TestWizardRiffList(unittest.TestCase):
    """The song's riffs: written for a player, renamed, copied, regenerated and deleted, played by anybody or not."""

    def test_a_plain_song_has_no_riff_and_every_player_but_the_drummer_can_have_one_written(self):
        choices = chosen()
        self.assertEqual(choices.riff_names(), [])
        self.assertIn(THE_GUITAR, choices.riff_instruments())
        self.assertIn(THE_BASS, choices.riff_instruments())
        self.assertNotIn(THE_DRUMS, choices.riff_instruments())

    def test_the_genres_riff_arrives_written_known_by_its_players_and_played(self):
        choices = chosen(subgenre=A_RIFF_SUBGENRE)
        self.assertEqual(choices.riff_names(), [FIRST_RIFF])
        self.assertEqual(choices.riff_written_for(FIRST_RIFF), THE_GUITAR)
        self.assertIn(FIRST_RIFF, choices.riffs_known_by(THE_GUITAR))
        self.assertIn(FIRST_RIFF, choices.riffs_known_by(THE_BASS))
        self.assertIn(A_VERSE, choices.riff_kinds_used(FIRST_RIFF))
        self.assertIn(pattern_of(role=THE_GUITAR, riff=FIRST_RIFF), patterns(choices))

    def test_a_new_riff_is_named_in_turn_known_by_its_player_and_changes_no_song_until_played(self):
        choices = chosen()
        before = patterns(choices)
        riff = choices.add_riff(role=THE_GUITAR)
        self.assertEqual(riff, FIRST_RIFF)
        self.assertEqual(choices.add_riff(role=THE_BASS, settings={riffs.RIFF_BAR_COUNT: ONE_BAR}), SECOND_RIFF)
        self.assertEqual(choices.riffs_for(THE_GUITAR), [FIRST_RIFF])
        self.assertEqual(choices.riffs_for(THE_BASS), [SECOND_RIFF])
        self.assertEqual(choices.riffs_known_by(THE_GUITAR), [FIRST_RIFF])
        self.assertEqual(choices.riff_kinds_used(FIRST_RIFF), [])
        self.assertEqual((choices.riff_bar_count(FIRST_RIFF), choices.riff_bar_count(SECOND_RIFF)), (riffs.RIFF_BARS, ONE_BAR))
        self.assertEqual(patterns(choices), before)

    def test_a_riff_is_heard_and_opened_before_anybody_plays_it(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR, settings={riffs.RIFF_NOTES: riffs.ACCENT_CHORDS})
        setlist, name, place, role, pattern = choices.riff_heard(riff)
        self.assertEqual(role, THE_GUITAR)
        self.assertEqual(pattern, pattern_of(role=THE_GUITAR, riff=riff))
        self.assertTrue(setlist.has_pattern(pattern))
        self.assertIsNotNone(setlist.get_song(name).get_scenes()[place].get_clip_slot(THE_GUITAR))

    def test_a_riff_played_takes_the_place_of_the_accompaniment_in_that_kind_of_section_alone(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR)
        before = patterns(choices)
        self.assertEqual(choices.section_part(kind=A_VERSE, role=THE_GUITAR), wizard_choices.ACCOMPANIMENT)
        self.assertIn(riff, choices.section_parts_offered(kind=A_VERSE, role=THE_GUITAR))
        self.assertNotIn(riff, choices.section_parts_offered(kind=A_VERSE, role=THE_BASS))
        choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=riff)
        self.assertEqual(choices.section_part(kind=A_VERSE, role=THE_GUITAR), riff)
        self.assertEqual(choices.riff_kinds_used(riff), [A_VERSE])
        self.assertIn(pattern_of(role=THE_GUITAR, riff=riff), patterns(choices))
        self.assertNotEqual(patterns(choices), before)
        choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=wizard_choices.ACCOMPANIMENT)
        self.assertEqual(patterns(choices), before)

    def test_a_riff_is_renamed_wherever_it_is_known_and_played_and_a_taken_name_is_refused(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR)
        other = choices.add_riff(role=THE_GUITAR)
        choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=riff)
        choices.rename_riff(riff=riff, name=A_NEW_NAME)
        self.assertEqual(choices.riffs_for(THE_GUITAR), [A_NEW_NAME, other])
        self.assertEqual(choices.section_part(kind=A_VERSE, role=THE_GUITAR), A_NEW_NAME)
        self.assertIn(A_NEW_NAME, choices.riffs_known_by(THE_GUITAR))
        with self.assertRaises(ValueError):
            choices.rename_riff(riff=other, name=A_NEW_NAME.upper())
        with self.assertRaises(ValueError):
            choices.rename_riff(riff=NOT_A_RIFF, name=A_NAME)

    def test_a_copy_for_another_player_is_that_players_riff_with_a_name_counted_on(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR)
        copy = choices.copy_riff(riff=riff, role=THE_BASS)
        self.assertEqual(copy, SECOND_RIFF)
        self.assertEqual(choices.riff_written_for(copy), THE_BASS)
        self.assertEqual(choices.riffs_known_by(THE_BASS), [copy])
        self.assertEqual(choices.riff_is_edited(copy), choices.riff_is_edited(riff))
        self.assertEqual(choices.riff_bar_count(copy), choices.riff_bar_count(riff))
        self.assertIsNotNone(choices.riff_heard(copy))

    def test_a_riff_regenerated_has_other_notes_and_notes_by_hand_are_given_up(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR, settings={riffs.RIFF_NOTES: riffs.SINGLE_NOTES})

        def notes():
            setlist, _, _, _, pattern = choices.riff_heard(riff)
            return setlist.get_pattern(pattern).to_data()
        first = notes()
        choices.regenerate_riff(riff)
        second = notes()
        self.assertNotEqual(first, second)
        choices.set_riff_pattern(riff=riff, pattern=first)
        self.assertTrue(choices.riff_is_edited(riff))
        self.assertEqual(notes(), first)
        choices.regenerate_riff(riff)
        self.assertFalse(choices.riff_is_edited(riff))
        self.assertNotIn(notes(), (first,))

    def test_a_deleted_riff_leaves_its_players_the_accompaniment_and_nobody_knows_it(self):
        choices = chosen()
        before = patterns(choices)
        riff = choices.add_riff(role=THE_GUITAR)
        choices.give_riff(role=THE_BASS, riff=riff)
        choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=riff)
        choices.set_section_part(kind=A_VERSE, role=THE_BASS, part=riff)
        self.assertEqual(choices.kinds_playing(role=THE_BASS, riff=riff), [A_VERSE])
        choices.delete_riff(riff)
        self.assertEqual(choices.riff_names(), [])
        self.assertEqual(choices.riffs_known_by(THE_BASS), [])
        self.assertEqual(choices.section_part(kind=A_VERSE, role=THE_BASS), wizard_choices.ACCOMPANIMENT)
        self.assertEqual(patterns(choices), before)
        # A name is never given again while the song is made, so the next riff counts on.
        self.assertEqual(choices.add_riff(role=THE_GUITAR), FIRST_RIFF)


class TestWizardRiffAssign(unittest.TestCase):
    """Who knows each riff: a player given a riff written for another plays it, and a riff taken away is played no more."""

    def test_a_player_is_given_a_riff_written_for_another_and_plays_it_in_a_pattern_of_the_players_own(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR)
        self.assertEqual(choices.riffs_to_give(THE_BASS), [riff])
        self.assertEqual(choices.riffs_to_give(THE_GUITAR), [])
        choices.give_riff(role=THE_BASS, riff=riff)
        self.assertEqual(choices.riffs_known_by(THE_BASS), [riff])
        self.assertEqual(choices.riffs_to_give(THE_BASS), [])
        choices.set_section_part(kind=A_VERSE, role=THE_BASS, part=riff)
        self.assertIn(pattern_of(role=THE_BASS, riff=riff), patterns(choices))
        self.assertEqual(choices.riff_kinds_used(riff), [A_VERSE])

    def test_a_riff_taken_from_a_player_is_played_by_that_player_no_more(self):
        choices = chosen()
        before = patterns(choices)
        riff = choices.add_riff(role=THE_GUITAR)
        choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=riff)
        choices.take_riff_from(role=THE_GUITAR, riff=riff)
        self.assertEqual(choices.riffs_known_by(THE_GUITAR), [])
        self.assertEqual(choices.riff_names(), [riff])
        self.assertEqual(choices.section_part(kind=A_VERSE, role=THE_GUITAR), wizard_choices.ACCOMPANIMENT)
        self.assertEqual(patterns(choices), before)

    def test_what_is_no_riff_or_no_part_is_refused(self):
        choices = chosen()
        riff = choices.add_riff(role=THE_GUITAR)
        for refused in (lambda: choices.give_riff(role=THE_BASS, riff=NOT_A_RIFF), lambda: choices.give_riff(role=THE_DRUMS, riff=riff),
                        lambda: choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=NOT_A_PART), lambda: choices.set_section_part(kind=A_VERSE, role=THE_BASS, part=riff),
                        lambda: choices.add_riff(role=THE_DRUMS), lambda: choices.delete_riff(NOT_A_RIFF)):
            with self.assertRaises(ValueError):
                refused()


class TestWizardSectionPlayers(unittest.TestCase):
    """What each player plays in each kind of section: the accompaniment, the melody or a riff the player knows."""

    def test_the_melodys_player_has_the_melody_and_another_player_takes_it_in_one_kind_of_section(self):
        choices = chosen()
        singer = choices.tune_player()
        self.assertEqual(choices.section_part(kind=A_VERSE, role=singer), wizard_choices.MELODY_PART)
        taker = next(role for role in choices.section_players(A_VERSE) if role != singer and wizard_choices.MELODY_PART in choices.section_parts_offered(kind=A_VERSE, role=role))
        before = patterns(choices)
        choices.set_section_part(kind=A_VERSE, role=taker, part=wizard_choices.MELODY_PART)
        self.assertEqual(choices.tune_player_in(A_VERSE), taker)
        self.assertEqual(choices.section_part(kind=A_VERSE, role=singer), wizard_choices.RESTS_PART)
        self.assertNotEqual(patterns(choices), before)
        choices.set_section_part(kind=A_VERSE, role=singer, part=wizard_choices.MELODY_PART)
        self.assertEqual(choices.tune_player_in(A_VERSE), singer)
        self.assertEqual(patterns(choices), before)

    def test_every_kind_of_section_of_the_form_is_listed_once_and_a_song_kept_keeps_its_riffs(self):
        choices = chosen()
        kinds = choices.section_player_kinds()
        self.assertEqual(len(kinds), len(set(kinds)))
        self.assertIn(A_VERSE, kinds)
        riff = choices.add_riff(role=THE_GUITAR)
        choices.set_section_part(kind=A_VERSE, role=THE_GUITAR, part=riff)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.riff_names(), [riff])
        self.assertEqual(again.section_part(kind=A_VERSE, role=THE_GUITAR), riff)
        self.assertEqual(patterns(again), patterns(choices))

    def test_a_change_of_genre_keeps_edited_riffs_alone(self):
        choices = chosen()
        kept = choices.add_riff(role=THE_GUITAR)
        choices.set_riff_pattern(riff=kept, pattern=choices.riff_heard(kept)[0].get_pattern(pattern_of(role=THE_GUITAR, riff=kept)).to_data())
        choices.add_riff(role=THE_GUITAR)
        choices.set_subgenre(A_RIFF_SUBGENRE)
        self.assertIn(kept, choices.riff_names())
