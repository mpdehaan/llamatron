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

"""Tests of what a song asks of its melodies: a section's plan as asked, and the wizard's choices for every melody and for one kind of section's."""

import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer.melody import ANSWER, HEIGHT, HIGH, HIGHER, HOOK, LINE, LINE_BUSY, LOW, LOWER, MIDDLE, REPEATS, REPEATS_A_LITTLE, REPEATS_A_LOT, REPEATS_SOME, VARIED, plan_as_asked
from llamatron.macro_composer.wizard_choices import ATONAL, MELODY_BUSY, MELODY_RANGE, MELODY_SPARSE, MELODY_WIDE, SMOOTH, USUAL_MELODY_WAYS, WizardChoices
from llamatron.support.version import VERSION

A_NAME = 'made'
A_SEED = 11
A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_KIND = 'verse'
ANOTHER_GENRE = 'blues'
A_KIND_WITH_NO_MELODY = 'intro'
NOT_A_WAY = 'sideways'
A_BUSY_PLACE = 7
FIRST_LETTER = 'a'
SECOND_LETTER = 'b'
A_PLAN = [{LINE: FIRST_LETTER}, {LINE: SECOND_LETTER, HIGHER: True}, {LINE: FIRST_LETTER, VARIED: True}, {LINE: HOOK, HOOK: True, HIGHER: True}]


def chosen():
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(A_SUBGENRE)
    choices.set_seed(A_SEED)
    return choices


def patterns(choices):
    return choices.written_setlist(name=A_NAME, version=VERSION).to_data()[Section.PATTERNS]


class TestPlanAsAsked(unittest.TestCase):

    def test_nothing_asked_leaves_the_plan_as_written_and_what_is_handed_over_is_not_changed(self):
        before = [dict(entry) for entry in A_PLAN]
        self.assertEqual(plan_as_asked(plan=A_PLAN), A_PLAN)
        plan_as_asked(plan=A_PLAN, height=LOW, busy=A_BUSY_PLACE, repeats=REPEATS_A_LOT)
        self.assertEqual(A_PLAN, before)

    def test_a_height_is_asked_of_every_line(self):
        self.assertTrue(all(entry.get(HIGHER) and LOWER not in entry for entry in plan_as_asked(plan=A_PLAN, height=HIGH)))
        self.assertTrue(all(entry.get(LOWER) and HIGHER not in entry for entry in plan_as_asked(plan=A_PLAN, height=LOW)))
        self.assertFalse(any(HIGHER in entry or LOWER in entry for entry in plan_as_asked(plan=A_PLAN, height=MIDDLE)))

    def test_busy_is_asked_of_every_line(self):
        self.assertEqual([entry[LINE_BUSY] for entry in plan_as_asked(plan=A_PLAN, busy=A_BUSY_PLACE)], [A_BUSY_PLACE] * len(A_PLAN))

    def test_a_lot_of_repeats_makes_every_line_but_the_hook_the_first_with_the_last_varied(self):
        asked = plan_as_asked(plan=A_PLAN, repeats=REPEATS_A_LOT)
        self.assertEqual([entry[LINE] for entry in asked], [FIRST_LETTER, FIRST_LETTER, FIRST_LETTER, HOOK])
        self.assertEqual([bool(entry.get(VARIED)) for entry in asked], [False, False, True, False])

    def test_a_little_gives_each_line_but_the_hook_a_line_of_its_own_and_some_leaves_the_plan(self):
        asked = plan_as_asked(plan=A_PLAN, repeats=REPEATS_A_LITTLE)
        own = [entry[LINE] for entry in asked[:-1]]
        self.assertEqual(len(set(own)), len(own))
        self.assertFalse(any(entry.get(VARIED) for entry in asked))
        self.assertEqual(asked[-1][LINE], HOOK)
        self.assertEqual(plan_as_asked(plan=A_PLAN, repeats=REPEATS_SOME), A_PLAN)

    def test_lines_that_answer_repeat_among_themselves(self):
        plan = [{LINE: FIRST_LETTER}, {LINE: SECOND_LETTER, ANSWER: True}, {LINE: FIRST_LETTER}, {LINE: FIRST_LETTER, ANSWER: True}]
        asked = plan_as_asked(plan=plan, repeats=REPEATS_A_LOT)
        self.assertEqual([entry[LINE] for entry in asked], [FIRST_LETTER, SECOND_LETTER, FIRST_LETTER, SECOND_LETTER])


class TestWizardMelodyChoices(unittest.TestCase):

    def test_each_field_starts_at_the_genres_own_which_is_not_kept_and_another_value_changes_the_melody(self):
        choices = chosen()
        usual = choices.to_data()
        for field, value in ((MELODY_BUSY, MELODY_SPARSE), (MELODY_RANGE, MELODY_WIDE), (REPEATS, REPEATS_A_LOT)):
            self.assertEqual(choices.get_melody_way(field), USUAL_MELODY_WAYS[field])
            before = patterns(choices)
            choices.set_melody_way(field=field, value=value)
            self.assertEqual(choices.get_melody_way(field), value)
            self.assertNotEqual(patterns(choices), before)
            self.assertEqual(WizardChoices.from_data(choices.to_data()).get_melody_way(field), value)
            choices.set_melody_way(field=field, value=USUAL_MELODY_WAYS[field])
            self.assertEqual(patterns(choices), before)
        self.assertEqual(choices.to_data(), usual)

    def test_only_values_that_make_another_song_are_offered_with_the_genres_own_and_the_one_chosen(self):
        choices = chosen()
        for field in choices.melody_fields():
            for value in choices.melody_ways_offered(field):
                if value != USUAL_MELODY_WAYS[field]:
                    other = WizardChoices.from_data(choices.to_data())
                    other.set_melody_way(field=field, value=value)
                    self.assertNotEqual(patterns(other), patterns(choices), (field, value))

    def test_a_character_is_the_genres_until_chosen_changes_the_melody_and_is_given_back(self):
        choices = chosen()
        before = patterns(choices)
        self.assertIsNone(choices.get_melody_character())
        self.assertIn(SMOOTH, choices.melody_characters_offered())
        choices.set_melody_character(SMOOTH)
        self.assertNotEqual(patterns(choices), before)
        self.assertEqual(WizardChoices.from_data(choices.to_data()).get_melody_character(), SMOOTH)
        choices.set_melody_character(None)
        self.assertEqual(patterns(choices), before)

    def test_a_character_that_writes_in_rows_shows_the_players_rows(self):
        choices = chosen()
        if ATONAL not in choices.melody_characters_offered():
            self.skipTest(ATONAL)
        self.assertFalse(any(choices.player_rows(role) for role in choices.roles_in()))
        choices.set_melody_character(ATONAL)
        self.assertTrue(any(choices.player_rows(role) for role in choices.roles_in()))

    def test_a_kind_of_section_takes_a_height_and_a_busy_of_its_own_and_gives_each_back(self):
        choices = chosen()
        before = patterns(choices)
        for field in choices.section_melody_fields(A_KIND):
            self.assertIsNone(choices.get_section_melody(kind=A_KIND, field=field))
            value = choices.section_melody_ways_offered(kind=A_KIND, field=field)[0]
            choices.set_section_melody(kind=A_KIND, field=field, value=value)
            self.assertEqual(choices.get_section_melody(kind=A_KIND, field=field), value)
            self.assertNotEqual(patterns(choices), before)
            self.assertEqual(WizardChoices.from_data(choices.to_data()).get_section_melody(kind=A_KIND, field=field), value)
            choices.set_section_melody(kind=A_KIND, field=field, value=None)
            self.assertEqual(patterns(choices), before)
        self.assertIn(HEIGHT, choices.section_melody_fields(A_KIND))

    def test_what_is_no_field_no_value_or_no_kind_with_a_melody_is_refused_and_a_genre_change_forgets_the_choices(self):
        choices = chosen()
        for refused in (lambda: choices.set_melody_way(field=NOT_A_WAY, value=MELODY_SPARSE), lambda: choices.set_melody_way(field=MELODY_BUSY, value=NOT_A_WAY),
                        lambda: choices.set_melody_character(NOT_A_WAY), lambda: choices.set_section_melody(kind=A_KIND_WITH_NO_MELODY, field=HEIGHT, value=HIGH),
                        lambda: choices.set_section_melody(kind=A_KIND, field=HEIGHT, value=NOT_A_WAY)):
            with self.assertRaises(ValueError):
                refused()
        choices.set_melody_way(field=MELODY_BUSY, value=MELODY_SPARSE)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_subgenre(choices.subgenres()[0])
        self.assertEqual(choices.get_melody_way(MELODY_BUSY), USUAL_MELODY_WAYS[MELODY_BUSY])
