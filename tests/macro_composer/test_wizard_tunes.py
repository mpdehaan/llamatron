# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's tunes: one for each kind of section, the wizard's until a person writes its pattern by hand, and the person's own from then on."""

import unittest

from llamatron.composition import generator_settings
from llamatron.composition.file_format import GeneratorKind, PatternSetting, Row
from llamatron.composition.generator_settings import PhrasingSetting
from llamatron.generators import phrasing
from llamatron.macro_composer import arranger, wizard_limits
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.user_strings import errors, macro_composer as composer_text
from tests.support.ui_testing import fixed_text

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
ANOTHER_GENRE = 'blues'
A_KIND = 'verse'
ANOTHER_KIND = 'chorus'
A_KIND_WITH_NO_TUNE = 'intro'
NOT_A_KIND = 'middle bit'
A_SEED = 7
ANOTHER_SEED = 8
A_DEGREE = 7
NOT_A_STEP_COUNT = 'many'


def chosen():
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(A_SUBGENRE)
    choices.set_seed(A_SEED)
    return choices


def rewritten(pattern):
    """Return a tune's pattern with every note on one degree, which no tune the wizard writes is."""
    return {**pattern, Row.DEGREE: [None if degree is None else A_DEGREE for degree in pattern[Row.DEGREE]]}


def tunes_played(*, choices, kind):
    """Return the name of the pattern the tune's player plays in each section of a kind, in the set the choices make."""
    setlist, name = choices.made_for_listening()
    player = choices.get_band().tune_player()
    scenes = setlist.get_song(name).get_scenes()
    return [scene.get_clip_slot(player).get_pattern_name() for place, scene in enumerate(scenes) if choices.section(place).kind() == kind and scene.has_clip_slot(player)]


class TestWizardTunes(unittest.TestCase):

    def test_a_kind_of_section_the_tunes_player_plays_in_has_a_tune_and_each_is_listed_once_in_the_forms_order(self):
        choices = chosen()
        kinds = choices.get_tunes().tune_kinds()
        self.assertIn(A_KIND, kinds)
        self.assertNotIn(A_KIND_WITH_NO_TUNE, kinds)
        self.assertEqual(len(kinds), len(set(kinds)))
        in_form = choices.get_song_form().section_kinds_in_form()
        self.assertEqual(kinds, sorted(kinds, key=in_form.index))

    def test_until_edited_a_tune_is_the_one_the_choices_write_and_follows_them(self):
        choices = chosen()
        self.assertFalse(choices.get_tunes().tune_is_own(A_KIND))
        first = choices.get_tunes().tune_pattern(A_KIND)
        self.assertIn(choices.get_tunes().tune_pattern_name(A_KIND), tunes_played(choices=choices, kind=A_KIND))
        choices.set_seed(ANOTHER_SEED)
        self.assertNotEqual(choices.get_tunes().tune_pattern(A_KIND), first)

    def test_a_tune_written_by_hand_is_played_by_every_section_of_its_kind_and_by_no_other(self):
        choices = chosen()
        other = next(kind for kind in choices.get_tunes().tune_kinds() if kind != A_KIND)
        before = tunes_played(choices=choices, kind=other)
        own = rewritten(choices.get_tunes().tune_pattern(A_KIND))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        self.assertTrue(choices.get_tunes().tune_is_own(A_KIND))
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), own)
        played = tunes_played(choices=choices, kind=A_KIND)
        self.assertGreater(len(played), 1)
        self.assertEqual(set(played), {choices.get_tunes().tune_pattern_name(A_KIND)})
        setlist, _ = choices.made_for_listening()
        self.assertEqual(setlist.get_pattern(played[0]).to_data()[Row.DEGREE], own[Row.DEGREE])
        self.assertEqual(tunes_played(choices=choices, kind=other), before)

    def test_what_is_handed_over_and_what_is_handed_back_are_copies(self):
        choices = chosen()
        own = rewritten(choices.get_tunes().tune_pattern(A_KIND))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        note = own[Row.DEGREE].index(A_DEGREE)
        own[Row.DEGREE][note] = None
        choices.get_tunes().tune_pattern(A_KIND)[Row.DEGREE][note] = None
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND)[Row.DEGREE][note], A_DEGREE)

    def test_no_other_choice_writes_over_a_tune_written_by_hand(self):
        choices = chosen()
        own = rewritten(choices.get_tunes().tune_pattern(A_KIND))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        choices.set_seed(ANOTHER_SEED)
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), own)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), own)

    def test_none_gives_the_tune_back_to_the_choices(self):
        choices = chosen()
        first = choices.get_tunes().tune_pattern(A_KIND)
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=rewritten(first))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=None)
        self.assertFalse(choices.get_tunes().tune_is_own(A_KIND))
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), first)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_a_tune_written_by_hand_is_kept_with_the_choices_and_read_back(self):
        choices = chosen()
        own = rewritten(choices.get_tunes().tune_pattern(A_KIND))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        read = WizardChoices.from_data(choices.to_data())
        self.assertTrue(read.get_tunes().tune_is_own(A_KIND))
        self.assertEqual(read.get_tunes().tune_pattern(A_KIND), own)

    def test_a_kind_with_no_tune_and_a_pattern_no_song_can_be_made_with_are_refused_and_nothing_changes(self):
        choices = chosen()
        before = choices.to_data()
        for kind in (A_KIND_WITH_NO_TUNE, NOT_A_KIND):
            with self.assertRaises(ValueError) as refused:
                choices.get_tunes().set_tune_pattern(kind=kind, pattern=choices.get_tunes().tune_pattern(A_KIND))
            self.assertIn(fixed_text(errors.ERR_WIZARD_NO_TUNE_IN), str(refused.exception))
        with self.assertRaises(ValueError) as refused:
            choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern={**choices.get_tunes().tune_pattern(A_KIND), PatternSetting.STEPS: NOT_A_STEP_COUNT})
        self.assertIn(fixed_text(errors.ERR_WIZARD_TUNE_PATTERN), str(refused.exception))
        self.assertEqual(choices.to_data(), before)
        own = rewritten(choices.get_tunes().tune_pattern(A_KIND))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        with self.assertRaises(ValueError):
            choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern={**own, PatternSetting.STEPS: NOT_A_STEP_COUNT})
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), own)


class TestWizardTuneTakes(unittest.TestCase):

    def test_a_new_take_writes_another_tune_for_its_kind_and_leaves_every_other_pattern_of_the_song(self):
        choices = chosen()
        before, name = choices.made_for_listening()
        first = choices.get_tunes().tune_pattern(A_KIND)
        usual_name = choices.get_tunes().tune_pattern_name(A_KIND)
        choices.get_tunes().new_tune_take(A_KIND)
        self.assertEqual(choices.get_tunes().tune_take(A_KIND), wizard_limits.FIRST_TUNE_TAKE + 1)
        taken = choices.get_tunes().tune_pattern(A_KIND)
        self.assertNotEqual(taken[Row.DEGREE], first[Row.DEGREE])
        self.assertEqual(len(taken[Row.DEGREE]), len(first[Row.DEGREE]))
        after, _ = choices.made_for_listening()
        took = choices.get_tunes().tune_pattern_name(A_KIND)
        for pattern in before.get_pattern_names():
            if pattern != usual_name:
                self.assertEqual(after.get_pattern(pattern).to_data(), before.get_pattern(pattern).to_data(), pattern)
        self.assertEqual(set(after.get_pattern_names()) - set(before.get_pattern_names()), {took})
        self.assertEqual(set(tunes_played(choices=choices, kind=A_KIND)), {took})

    def test_each_take_is_another_tune_the_same_take_is_the_same_tune_and_takes_are_kept_with_the_choices(self):
        choices = chosen()
        choices.get_tunes().new_tune_take(A_KIND)
        second = choices.get_tunes().tune_pattern(A_KIND)
        self.assertEqual(WizardChoices.from_data(choices.to_data()).get_tunes().tune_pattern(A_KIND), second)
        choices.get_tunes().new_tune_take(A_KIND)
        self.assertNotEqual(choices.get_tunes().tune_pattern(A_KIND)[Row.DEGREE], second[Row.DEGREE])
        read = WizardChoices.from_data(choices.to_data())
        self.assertEqual(read.get_tunes().tune_take(A_KIND), wizard_limits.FIRST_TUNE_TAKE + 2)
        self.assertEqual(read.get_tunes().tune_pattern(A_KIND), choices.get_tunes().tune_pattern(A_KIND))

    def test_a_new_take_gives_up_notes_written_by_hand_and_notes_written_by_hand_win_over_a_take(self):
        choices = chosen()
        own = rewritten(choices.get_tunes().tune_pattern(A_KIND))
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        choices.get_tunes().new_tune_take(A_KIND)
        self.assertFalse(choices.get_tunes().tune_is_own(A_KIND))
        self.assertNotEqual(choices.get_tunes().tune_pattern(A_KIND), own)
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=own)
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), own)
        self.assertEqual(choices.get_tunes().tune_take(A_KIND), wizard_limits.FIRST_TUNE_TAKE + 1)

    def test_a_kind_with_no_tune_has_no_take_and_another_genre_starts_from_the_first_take(self):
        choices = chosen()
        with self.assertRaises(ValueError):
            choices.get_tunes().new_tune_take(A_KIND_WITH_NO_TUNE)
        choices.get_tunes().new_tune_take(A_KIND)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertEqual(choices.get_tunes().tune_take(A_KIND), wizard_limits.FIRST_TUNE_TAKE)


class TestWhoPlaysTheTune(unittest.TestCase):

    def test_the_genres_player_has_the_tune_until_another_is_chosen_and_the_bass_and_the_drums_are_not_offered(self):
        choices = chosen()
        self.assertEqual(choices.get_tunes().tune_played_by(), choices.get_band().tune_player())
        offered = choices.get_tunes().tune_players_offered()
        self.assertIn(choices.get_band().tune_player(), offered)
        self.assertTrue(set(offered) < set(choices.get_band().roles_in()))
        for kind in choices.get_tunes().tune_kinds():
            self.assertIsNone(choices.get_tunes().tune_played_by_in(kind))
            self.assertEqual(choices.get_tunes().tune_player_in(kind), choices.get_band().tune_player())

    def test_the_songs_player_plays_every_tune_in_place_of_the_usual_part_and_the_genres_player_rests(self):
        choices = chosen()
        usual = choices.get_band().tune_player()
        other = next(role for role in choices.get_tunes().tune_players_offered() if role != usual)
        tune = choices.get_tunes().tune_pattern(A_KIND)
        choices.get_tunes().set_tune_played_by(other)
        setlist, name = choices.made_for_listening()
        for place, scene in enumerate(setlist.get_song(name).get_scenes()):
            if choices.section(place).kind() == A_KIND:
                self.assertFalse(scene.has_clip_slot(usual))
                self.assertEqual(setlist.get_pattern(scene.get_clip_slot(other).get_pattern_name()).to_data()[Row.DEGREE], tune[Row.DEGREE])
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND)[Row.DEGREE], tune[Row.DEGREE])
        choices.get_tunes().set_tune_played_by(None)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_a_kind_of_section_takes_a_player_of_its_own_or_nobody_and_the_other_kinds_go_by_the_song(self):
        choices = chosen()
        usual = choices.get_band().tune_player()
        other = next(role for role in choices.get_tunes().tune_players_offered() if role != usual)
        another_kind = next(kind for kind in choices.get_tunes().tune_kinds() if kind != A_KIND)
        choices.get_tunes().set_tune_played_by_in(kind=A_KIND, role=other)
        self.assertEqual(choices.get_tunes().tune_player_in(A_KIND), other)
        self.assertEqual(choices.get_tunes().tune_player_in(another_kind), usual)
        # A last chorus may be written anew, so the kind's tune is one of the tunes its sections play.
        self.assertIn(choices.get_tunes().tune_pattern_name(another_kind), tunes_played(choices=choices, kind=another_kind))
        choices.get_tunes().set_tune_played_by_in(kind=A_KIND, role=arranger.NOBODY)
        self.assertIsNone(choices.get_tunes().tune_player_in(A_KIND))
        self.assertIsNone(choices.get_tunes().tune_pattern(A_KIND))
        setlist, name = choices.made_for_listening()
        for place, scene in enumerate(setlist.get_song(name).get_scenes()):
            if choices.section(place).kind() == A_KIND:
                self.assertFalse(scene.has_clip_slot(usual))
        self.assertIn(A_KIND, choices.get_tunes().tune_kinds())
        choices.get_tunes().set_tune_played_by_in(kind=A_KIND, role=None)
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_what_is_chosen_is_kept_refused_when_no_such_player_and_given_up_with_the_genre_or_the_player(self):
        choices = chosen()
        usual = choices.get_band().tune_player()
        other = next(role for role in choices.get_tunes().tune_players_offered() if role != usual)
        for refused in (NOT_A_KIND, next(role for role in choices.get_band().roles_in() if role not in choices.get_tunes().tune_players_offered())):
            with self.assertRaises(ValueError):
                choices.get_tunes().set_tune_played_by(refused)
            with self.assertRaises(ValueError):
                choices.get_tunes().set_tune_played_by_in(kind=A_KIND, role=refused)
        with self.assertRaises(ValueError):
            choices.get_tunes().set_tune_played_by_in(kind=A_KIND_WITH_NO_TUNE, role=other)
        choices.get_tunes().set_tune_played_by(other)
        choices.get_tunes().set_tune_played_by_in(kind=A_KIND, role=arranger.NOBODY)
        read = WizardChoices.from_data(choices.to_data())
        self.assertEqual(read.get_tunes().tune_played_by(), other)
        self.assertEqual(read.get_tunes().tune_played_by_in(A_KIND), arranger.NOBODY)
        choices.player(other).set_in(on=False)
        self.assertEqual(choices.get_tunes().tune_played_by(), usual)
        choices.set_genre(ANOTHER_GENRE)
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        self.assertIsNone(choices.get_tunes().tune_played_by_in(A_KIND))


class TestTunePhrasing(unittest.TestCase):

    def test_a_tune_is_delivered_by_a_phrasing_as_one_starts_until_its_settings_are_chosen_or_it_is_switched_off(self):
        choices = chosen()
        self.assertEqual(choices.tune_phrasing(), {})
        choices.set_tune_phrasing({PhrasingSetting.BREATH: phrasing.DEEP_BREATH, PhrasingSetting.NOTES: generator_settings.PHRASING_DEFAULTS[PhrasingSetting.NOTES]})
        self.assertEqual(choices.tune_phrasing(), {PhrasingSetting.BREATH: phrasing.DEEP_BREATH})
        self.assertEqual(WizardChoices.from_data(choices.to_data()).tune_phrasing(), {PhrasingSetting.BREATH: phrasing.DEEP_BREATH})
        setlist, name = choices.made_for_listening()
        made = setlist.get_song(name).get_generator_settings(kind=GeneratorKind.PHRASING, name=composer_text.MSG_TUNE_PHRASING_NAME)
        self.assertEqual(made.to_data(), {PhrasingSetting.BREATH: phrasing.DEEP_BREATH})
        choices.set_tune_phrasing(False)
        self.assertIsNone(choices.tune_phrasing())
        self.assertIsNone(WizardChoices.from_data(choices.to_data()).tune_phrasing())
        choices.set_tune_phrasing(None)
        self.assertEqual(choices.tune_phrasing(), {})

    def test_settings_no_phrasing_has_are_refused_and_nothing_changes(self):
        choices = chosen()
        for wrong in ({PhrasingSetting.BREATH: NOT_A_KIND}, {NOT_A_KIND: phrasing.DEEP_BREATH}):
            with self.assertRaises(ValueError):
                choices.set_tune_phrasing(wrong)
        self.assertEqual(choices.tune_phrasing(), {})
