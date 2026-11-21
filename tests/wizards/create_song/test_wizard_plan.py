# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The wizard's choices of a planned song: the plan switched on, its contrast, its phrasing and the hook's kind."""

import copy
import itertools
import random
import unittest

from llamatron.model.file import version
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import Row, SceneSetting, Section, VelocitySetting
from llamatron.user_strings import errors, song_wizard as wizard_text
from llamatron.wizards.create_song import hook_writing, joins, notation, phrasing, song_plan, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import shares_a_bar as arranger_shares_a_bar
from llamatron.wizards.create_song.own_values import chords_as_text, chords_from_text
from llamatron.wizards.create_song.wizard_choices import WizardChoices

A_NAME = 'made'
A_DEGREE = 7
A_GENRE_OF_MANY_SOLOS = 'blues'
ANOTHER_DEGREE = 6
A_SEED = 11
A_PLANNED_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_SUBGENRE_IN_SIX = 'six-eight ballad'
AN_UNPLANNED_GENRE = 'experimental'
NOT_A_SWITCH = 'yes'
NOT_A_PART = 'wobble'
A_HIGH_CONTRAST = 9
A_VERSE = 1
A_FEW_FORMS_APART = 7
KIND_OF_SECTION = 'kind'
THE_INTRO = 0
A_KIND_WITH_SHAPES = 'solo'
A_BAR_OF_STEPS = 16
MANY_SEEDS = 40
A_SLOW_TEMPO = 90
A_FAST_TEMPO = 150
ANOTHER_ROOT = 'D'
SOME_CHORDS = '6 4 1 b7'
CHORDS_SHARING_A_BAR = '1 4 1 1-5'
THE_BARS_FIRST_CHORDS = '1 4 1 1'
THREE_IN_A_BAR = '1-4-5'
A_DASH_ALONE = '1 -'
NOT_CHORDS = ('', '9', 'x', '0', 'bb3')


def chosen(*, genre=A_PLANNED_GENRE, subgenre=A_SUBGENRE, plan=True):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre or choices.subgenres()[0])
    choices.set_seed(A_SEED)
    if choices.can_have_song_plan():
        choices.set_song_plan(plan)
    return choices


class TestWizardSongPlan(unittest.TestCase):
    """The plan switched on and off, and what it holds."""

    __slots__ = ()

    def test_a_song_has_no_plan_until_asked_and_only_a_genre_with_one_can_have_it(self):
        choices = chosen(plan=False)
        self.assertFalse(choices.has_song_plan())
        self.assertTrue(choices.can_have_song_plan())
        # A genre with a plan plans every song until the plan is switched off.
        unasked = WizardChoices()
        unasked.set_genre(A_PLANNED_GENRE)
        unasked.set_subgenre(A_SUBGENRE)
        self.assertTrue(unasked.has_song_plan())
        self.assertFalse(WizardChoices.from_data(choices.to_data()).has_song_plan())
        other = chosen(genre=AN_UNPLANNED_GENRE, subgenre=None, plan=False)
        self.assertFalse(other.can_have_song_plan())
        with self.assertRaisesRegex(ValueError, errors.ERR_WIZARD_GENRE_HAS_NO_PLAN):
            other.set_song_plan(True)

    def test_the_plan_s_settings_are_refused_without_a_plan(self):
        choices = chosen(plan=False)
        for asked in (choices.get_contrast, choices.has_phrasing, choices.energies, choices.said_of_sections):
            with self.assertRaisesRegex(ValueError, errors.ERR_WIZARD_NO_SONG_PLAN):
                asked()

    def test_a_plan_gives_every_section_an_energy_and_says_how_each_leaves(self):
        choices = chosen()
        places = len(choices.get_song_form().section_labels())
        self.assertEqual(len(choices.energies()), places)
        self.assertEqual(len(choices.said_of_sections()), places)
        for energy in choices.energies():
            self.assertTrue(wizard_names.LOWEST_ENERGY <= energy <= wizard_names.HIGHEST_ENERGY)
        # The last chorus is the song's most.
        kinds = choices.get_song_form().section_kinds_in_form()
        self.assertEqual(max(choices.energies()), choices.energies()[len(kinds) - 1 - kinds[::-1].index('chorus')])

    def test_contrast_stretches_the_energies_and_is_held_to_its_range(self):
        choices = chosen()
        self.assertEqual(choices.get_contrast(), song_plan.USUAL_CONTRAST)
        usual = choices.energies()
        choices.set_contrast(A_HIGH_CONTRAST)
        self.assertEqual(choices.get_contrast(), A_HIGH_CONTRAST)
        self.assertLess(min(choices.energies()), min(usual))
        for wrong in (wizard_names.LOWEST_ENERGY - 1, wizard_names.HIGHEST_ENERGY + 1, True, NOT_A_SWITCH):
            with self.assertRaises(ValueError):
                choices.set_contrast(wrong)

    def test_the_switches_take_only_true_or_false(self):
        choices = chosen()
        for setter in (choices.set_song_plan, choices.set_phrasing):
            with self.assertRaises(ValueError):
                setter(NOT_A_SWITCH)

    def test_the_plan_is_kept_with_the_choices_and_makes_the_same_song_again(self):
        choices = chosen()
        choices.set_contrast(A_HIGH_CONTRAST)
        choices.set_phrasing(False)
        choices.get_hook().set_hook_behavior(wizard_names.CHANT)
        again = WizardChoices.from_data(choices.to_data())
        self.assertTrue(again.has_song_plan())
        self.assertEqual(again.get_contrast(), A_HIGH_CONTRAST)
        self.assertFalse(again.has_phrasing())
        self.assertEqual(again.get_hook().get_hook_behavior(), wizard_names.CHANT)
        self.assertEqual(again.made_setlist(name=A_NAME, version=version.VERSION).to_data(), choices.made_setlist(name=A_NAME, version=version.VERSION).to_data())

    def test_switching_the_plan_off_or_choosing_another_genre_drops_it(self):
        choices = chosen()
        choices.get_hook().set_hook_behavior(wizard_names.CHANT)
        choices.set_song_plan(False)
        self.assertFalse(choices.has_song_plan())
        choices.set_song_plan(True)
        # How the hook is written is the song's, with a plan or without one, and one genre's.
        self.assertEqual(choices.get_hook().get_hook_behavior(), wizard_names.CHANT)
        choices.set_genre(AN_UNPLANNED_GENRE)
        choices.set_subgenre(choices.subgenres()[0])
        self.assertFalse(choices.has_song_plan())

    def test_a_planned_song_differs_from_the_song_without_a_plan(self):
        self.assertNotEqual(chosen().made_setlist(name=A_NAME, version=version.VERSION).to_data(), chosen(plan=False).made_setlist(name=A_NAME, version=version.VERSION).to_data())


class TestWizardPhrasing(unittest.TestCase):
    """How a planned song's lines breathe."""

    __slots__ = ()

    def test_each_respect_starts_as_usual_takes_what_is_offered_and_is_kept(self):
        choices = chosen()
        for name, offered in wizard_limits.PHRASING_OFFERED.items():
            self.assertEqual(choices.phrasing_way(name), phrasing.USUAL_WAYS[name])
            for value in offered:
                choices.set_phrasing_way(name=name, value=value)
                self.assertEqual(choices.phrasing_way(name), value)
                self.assertEqual(WizardChoices.from_data(choices.to_data()).phrasing_way(name), value)
            with self.assertRaises(ValueError):
                choices.set_phrasing_way(name=name, value=NOT_A_PART)
        with self.assertRaises(ValueError):
            choices.set_phrasing_way(name=NOT_A_PART, value=phrasing.LONG)

    def test_longer_breaths_leave_more_silence_and_no_early_notes_moves_none(self):
        line = [{notation.STEPS: A_BAR_OF_STEPS}, {notation.STEPS: A_BAR_OF_STEPS}]
        silences = []
        for breath in phrasing.BREATHS:
            made = phrasing.breathed(line=line, grid=A_BAR_OF_STEPS, count=0, dice=random.Random(A_SEED), ways={phrasing.BREATH: breath, phrasing.EARLY_NOTES: phrasing.FEWEST_EARLY})
            silences.append(sum(note.get(notation.REST, 0) for note in made))
        self.assertEqual(silences, sorted(set(silences)))

    def test_which_lines_are_the_shorter_follows_the_line_lengths(self):
        self.assertEqual([phrasing.is_shorter(count=count, lengths=phrasing.LONG_THEN_SHORT) for count in range(4)], [False, True, False, True])
        self.assertEqual([phrasing.is_shorter(count=count, lengths=phrasing.SHORT_THEN_LONG) for count in range(4)], [True, False, True, False])
        self.assertFalse(any(phrasing.is_shorter(count=count, lengths=phrasing.EVEN) for count in range(4)))


class TestWizardHookKind(unittest.TestCase):
    """How the hook is written: a behavior and gauges, the genre's until the song moves one."""

    __slots__ = ()

    def test_the_behavior_and_each_gauge_are_the_genre_s_until_chosen_and_go_back_to_it(self):
        choices = chosen()
        usual = choices.get_hook().genre_hook_behavior()
        other = next(behavior for behavior in wizard_names.BEHAVIORS if behavior != usual)
        choices.get_hook().set_hook_behavior(other)
        self.assertEqual(choices.get_hook().get_hook_behavior(), other)
        choices.get_hook().set_hook_behavior(usual)
        self.assertEqual(choices.to_data().get(wizard_limits.WRITING_SAVED), None)
        for name in choices.get_hook().hook_gauges():
            position = choices.get_hook().genre_hook_gauge(name)
            moved = wizard_names.HOOK_WRITING_LOWEST if position != wizard_names.HOOK_WRITING_LOWEST else wizard_names.HOOK_WRITING_HIGHEST
            self.assertFalse(choices.get_hook().writing_gauge_is_moved(part=wizard_names.HOOK_WRITING, name=name))
            choices.get_hook().set_hook_gauge(name=name, position=moved)
            self.assertTrue(choices.get_hook().writing_gauge_is_moved(part=wizard_names.HOOK_WRITING, name=name))
            self.assertEqual(choices.get_hook().get_hook_gauge(name), moved)
            choices.get_hook().set_hook_gauge(name=name, position=None)
            self.assertEqual(choices.get_hook().get_hook_gauge(name), position)
        self.assertEqual(choices.to_data().get(wizard_limits.WRITING_SAVED), None)

    def test_a_behavior_and_a_gauge_chosen_stay_through_a_new_hook_and_are_kept_with_the_song(self):
        choices = chosen()
        choices.get_hook().set_hook_behavior(wizard_names.CHANT)
        choices.get_hook().set_hook_gauge(name=hook_writing.HOLD, position=wizard_names.HOOK_WRITING_LOWEST)
        choices.get_hook().set_body_gauge(name=hook_writing.SPACE, position=wizard_names.HOOK_WRITING_HIGHEST)
        choices.get_hook().new_hook()
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_hook().get_hook_behavior(), wizard_names.CHANT)
        self.assertEqual(again.get_hook().get_hook_gauge(hook_writing.HOLD), wizard_names.HOOK_WRITING_LOWEST)
        self.assertEqual(again.get_hook().get_body_gauge(hook_writing.SPACE), wizard_names.HOOK_WRITING_HIGHEST)
        self.assertEqual(again.get_hook().hook_notes(), choices.get_hook().hook_notes())

    def test_each_behavior_is_another_hook_and_each_take_of_one_another(self):
        choices = chosen()
        hooks = set()
        for behavior in wizard_names.BEHAVIORS:
            choices.get_hook().set_hook_behavior(behavior)
            hooks.add(repr(choices.get_hook().hook_notes()))
        self.assertEqual(len(hooks), len(wizard_names.BEHAVIORS))
        before = choices.get_hook().hook_notes()
        choices.get_hook().new_hook()
        self.assertNotEqual(choices.get_hook().hook_notes(), before)

    def test_a_behavior_shows_only_the_gauges_that_change_its_hook(self):
        choices = chosen()
        for behavior in wizard_names.BEHAVIORS:
            choices.get_hook().set_hook_behavior(behavior)
            self.assertEqual(choices.get_hook().hook_gauges(), list(hook_writing.HOOK_GAUGES_OF[behavior]))
        choices.get_hook().set_hook_behavior(wizard_names.CHANT)
        self.assertNotIn(hook_writing.LEAP, choices.get_hook().hook_gauges())
        choices.get_hook().set_hook_behavior(wizard_names.LADDER)
        self.assertIn(hook_writing.LEAP, choices.get_hook().hook_gauges())

    def test_what_is_no_behavior_no_gauge_or_off_the_scale_is_refused(self):
        choices = chosen()
        with self.assertRaises(ValueError):
            choices.get_hook().set_hook_behavior(NOT_A_PART)
        with self.assertRaises(ValueError):
            choices.get_hook().set_hook_gauge(name=NOT_A_PART, position=wizard_names.HOOK_WRITING_LOWEST)
        for position in (wizard_names.HOOK_WRITING_LOWEST - 1, wizard_names.HOOK_WRITING_HIGHEST + 1, True):
            with self.assertRaises(ValueError):
                choices.get_hook().set_hook_gauge(name=hook_writing.HOLD, position=position)
            with self.assertRaises(ValueError):
                choices.get_hook().set_body_gauge(name=hook_writing.SPACE, position=position)

    def test_a_song_not_in_four_has_no_gauges_and_no_phrasing(self):
        choices = chosen(subgenre=A_SUBGENRE_IN_SIX)
        self.assertFalse(choices.counts_in_four())
        self.assertFalse(choices.get_hook().writes_hook())
        self.assertEqual(choices.get_hook().hook_gauges(), [])
        self.assertEqual(choices.get_hook().body_gauges(), [])
        self.assertTrue(chosen().counts_in_four())


class TestWizardSectionOwn(unittest.TestCase):
    """What a section of a planned song is given of its own: Energy, how it leaves, its setup, chords, tempo, key and scale."""

    __slots__ = ()

    def scene(self, *, choices, place=A_VERSE):
        return choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME).get_scenes()[place]

    def test_a_section_has_fields_of_its_own_only_under_a_plan_and_a_join_only_where_it_leaves(self):
        # Without a plan a section still takes chords, a tempo, a key and a scale of its own, in every genre.
        self.assertEqual(chosen(plan=False).section(A_VERSE).own_fields(), list(wizard_limits.OWN_WITHOUT_PLAN))
        self.assertEqual(chosen(genre=AN_UNPLANNED_GENRE, subgenre=None, plan=False).section(A_VERSE).own_fields(), list(wizard_limits.OWN_WITHOUT_PLAN))
        choices = chosen()
        last = len(choices.get_song_form().section_labels()) - 1
        self.assertIn(wizard_names.JOINS_LEAVES, choices.section(A_VERSE).own_fields())
        # The ending, one held chord, takes nothing of its own.
        self.assertEqual(choices.section(last).own_fields(), [])
        self.assertIn(wizard_names.SONG_PLAN_ENERGY, choices.section(A_VERSE).own_fields())

    def test_each_field_is_none_until_given_and_shows_what_the_plan_or_the_song_gives(self):
        choices = chosen()
        for field in choices.section(A_VERSE).own_fields():
            self.assertIsNone(choices.section(A_VERSE).own(field=field))
        self.assertEqual(choices.section(A_VERSE).from_plan(field=wizard_names.SONG_PLAN_ENERGY), choices.energies()[A_VERSE])
        self.assertEqual(choices.section(A_VERSE).from_plan(field=wizard_names.TEMPO_OF_PLACE), choices.get_tempo())
        self.assertEqual(choices.section(A_VERSE).from_plan(field=wizard_names.ROOT_OF_PLACE), choices.get_root())
        self.assertEqual(choices.section(A_VERSE).from_plan(field=wizard_names.TYPE_OF_PLACE), choices.get_scale_type())

    def test_an_energy_of_its_own_is_the_section_s_energy_and_none_gives_it_back(self):
        choices = chosen()
        usual = choices.energies()
        choices.section(A_VERSE).set_own(field=wizard_names.SONG_PLAN_ENERGY, value=wizard_names.HIGHEST_ENERGY)
        self.assertEqual(choices.energies()[A_VERSE], wizard_names.HIGHEST_ENERGY)
        self.assertTrue(choices.get_song_form().has_own_form())
        choices.section(A_VERSE).set_own(field=wizard_names.SONG_PLAN_ENERGY, value=None)
        self.assertEqual(choices.energies(), usual)

    def test_a_tempo_a_tempo_at_the_end_a_key_and_a_scale_are_the_scene_s(self):
        choices = chosen()
        choices.section(A_VERSE).set_own(field=wizard_names.TEMPO_OF_PLACE, value=A_SLOW_TEMPO)
        self.assertEqual(self.scene(choices=choices).get_tempo_setting(), A_SLOW_TEMPO)
        choices.section(A_VERSE).set_own(field=wizard_names.TEMPO_END_OF_PLACE, value=A_FAST_TEMPO)
        data = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.SONGS][A_NAME][Section.SCENES][A_VERSE]
        # The scene keeps its tempo and ramps in to the tempo at its end, over every bar of the section.
        self.assertEqual((data[SceneSetting.TEMPO], data[SceneSetting.TEMPO_IN_END]), (A_SLOW_TEMPO, A_FAST_TEMPO))
        self.assertEqual(data[SceneSetting.TEMPO_IN_OVER], choices.section(A_VERSE).bars())
        choices.section(A_VERSE).set_own(field=wizard_names.ROOT_OF_PLACE, value=ANOTHER_ROOT)
        choices.section(A_VERSE).set_own(field=wizard_names.TYPE_OF_PLACE, value=wizard_limits.MINOR)
        made = choices.made_setlist(name=A_NAME, version=version.VERSION)
        name = made.get_song(A_NAME).get_scenes()[A_VERSE].get_scale_name()
        scale = made.to_data()[Section.SCALES][name]
        self.assertEqual((scale[wizard_names.ROOT_OF_PLACE], scale[wizard_names.TYPE_OF_PLACE]), (ANOTHER_ROOT, wizard_limits.MINOR))
        # The section before keeps the song's.
        self.assertIsNone(made.get_song(A_NAME).get_scenes()[A_VERSE - 1].get_scale_name())

    def test_a_tempo_at_the_end_alone_starts_from_the_song_s_tempo(self):
        choices = chosen()
        choices.section(A_VERSE).set_own(field=wizard_names.TEMPO_END_OF_PLACE, value=A_SLOW_TEMPO)
        data = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.SONGS][A_NAME][Section.SCENES][A_VERSE]
        self.assertEqual(data[SceneSetting.TEMPO_IN_END], A_SLOW_TEMPO)
        self.assertNotIn(SceneSetting.TEMPO, data)

    def test_each_way_of_leaving_is_what_the_plan_says_of_the_section(self):
        choices = chosen()
        said = set()
        for way in wizard_limits.LEAVES_AS_JOIN:
            choices.section(A_VERSE).set_own(field=wizard_names.JOINS_LEAVES, value=way)
            said.add(choices.said_of_sections()[A_VERSE])
            if way in (joins.STOPS, joins.DROP_OUT, joins.BUILD):
                self.assertIn(wizard_text.MSG_PLAN_LEAVES_TAIL.format(way), choices.said_of_sections()[A_VERSE])
        self.assertEqual(len(said), len(wizard_limits.LEAVES_AS_JOIN))

    def test_chords_are_typed_as_degrees_and_change_the_song(self):
        choices = chosen()
        before = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
        choices.section(A_VERSE).set_own(field=wizard_names.ARRANGER_CHORDS, value=SOME_CHORDS)
        self.assertEqual(chords_as_text(choices.section(A_VERSE).own(field=wizard_names.ARRANGER_CHORDS)), SOME_CHORDS)
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=version.VERSION).to_data(), before)
        for wrong in NOT_CHORDS:
            with self.assertRaises(ValueError):
                chords_from_text(wrong)

    def test_two_chords_joined_by_a_dash_share_a_bar_and_are_played_by_the_half_bar(self):
        choices = chosen()
        usual = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
        choices.section(A_VERSE).set_own(field=wizard_names.ARRANGER_CHORDS, value=CHORDS_SHARING_A_BAR)
        own = choices.section(A_VERSE).own(field=wizard_names.ARRANGER_CHORDS)
        self.assertEqual(chords_as_text(own), CHORDS_SHARING_A_BAR)
        self.assertTrue(arranger_shares_a_bar(own[-1]))
        shared = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
        self.assertNotEqual(shared, usual)
        # The same bars with their first chords alone are another song.
        choices.section(A_VERSE).set_own(field=wizard_names.ARRANGER_CHORDS, value=THE_BARS_FIRST_CHORDS)
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=version.VERSION).to_data(), shared)

    def test_shared_bars_are_refused_past_what_a_progression_holds_and_three_never_share(self):
        too_many = ' '.join([CHORDS_SHARING_A_BAR] * limits.MAX_PROGRESSION_CHORDS)
        for wrong in (too_many, THREE_IN_A_BAR, A_DASH_ALONE):
            with self.assertRaises(ValueError):
                chords_from_text(wrong)

    def test_what_a_field_cannot_take_is_refused_and_nothing_changes(self):
        choices = chosen()
        before = choices.to_data()
        for field, wrong in ((wizard_names.SONG_PLAN_ENERGY, wizard_names.HIGHEST_ENERGY + 1), (wizard_names.JOINS_LEAVES, NOT_A_PART), (wizard_names.SONG_PLAN_SETUP, NOT_A_PART), (wizard_names.TEMPO_OF_PLACE, 0), (wizard_names.ROOT_OF_PLACE, NOT_A_PART), (wizard_names.TYPE_OF_PLACE, NOT_A_PART), (NOT_A_PART, 1)):
            with self.assertRaises(ValueError):
                choices.section(A_VERSE).set_own(field=field, value=wrong)
        self.assertEqual(choices.to_data(), before)
        with self.assertRaises(ValueError):
            chosen(plan=False).section(A_VERSE).set_own(field=wizard_names.SONG_PLAN_ENERGY, value=wizard_names.HIGHEST_ENERGY)

    def test_a_section_of_a_song_with_no_plan_takes_chords_a_tempo_a_key_and_a_scale(self):
        for genre in (A_PLANNED_GENRE, AN_UNPLANNED_GENRE):
            choices = chosen(genre=genre, subgenre=None, plan=False)
            choices.section(A_VERSE).set_own(field=wizard_names.ARRANGER_CHORDS, value=SOME_CHORDS)
            choices.section(A_VERSE).set_own(field=wizard_names.TEMPO_OF_PLACE, value=A_SLOW_TEMPO)
            choices.section(A_VERSE).set_own(field=wizard_names.ROOT_OF_PLACE, value=ANOTHER_ROOT)
            choices.section(A_VERSE).set_own(field=wizard_names.TYPE_OF_PLACE, value=wizard_limits.MINOR)
            made = choices.made_setlist(name=A_NAME, version=version.VERSION)
            scene = made.get_song(A_NAME).get_scenes()[A_VERSE]
            self.assertEqual(scene.get_tempo_setting(), A_SLOW_TEMPO)
            scale = made.to_data()[Section.SCALES][scene.get_scale_name()]
            self.assertEqual((scale[wizard_names.ROOT_OF_PLACE], scale[wizard_names.TYPE_OF_PLACE]), (ANOTHER_ROOT, wizard_limits.MINOR))
            # The sections beside it keep the song's.
            self.assertIsNone(made.get_song(A_NAME).get_scenes()[A_VERSE + 1].get_tempo_setting())
            again = WizardChoices.from_data(choices.to_data())
            self.assertEqual(again.made_setlist(name=A_NAME, version=version.VERSION).to_data(), made.to_data())

    def test_what_a_section_was_given_goes_with_it_when_moved_and_copied_and_is_kept(self):
        choices = chosen()
        choices.section(A_VERSE).set_own(field=wizard_names.SONG_PLAN_ENERGY, value=wizard_names.HIGHEST_ENERGY)
        choices.section(A_VERSE).set_own(field=wizard_names.ARRANGER_CHORDS, value=SOME_CHORDS)
        choices.section(A_VERSE).copy()
        choices.section(A_VERSE).move(offset=1)
        for place in (A_VERSE, A_VERSE + 1):
            self.assertEqual(choices.section(place).own(field=wizard_names.SONG_PLAN_ENERGY), wizard_names.HIGHEST_ENERGY)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.to_data(), choices.to_data())
        self.assertEqual(again.made_setlist(name=A_NAME, version=version.VERSION).to_data(), choices.made_setlist(name=A_NAME, version=version.VERSION).to_data())
        choices.section(A_VERSE).remove()
        choices.section(A_VERSE).remove()
        self.assertIsNone(choices.section(A_VERSE).own(field=wizard_names.SONG_PLAN_ENERGY))

    def test_no_setup_leaves_the_section_s_last_chord_alone(self):
        # A progression that starts at home is the one a section is set up for, so the seeds are tried until a song has one.
        for seed in range(MANY_SEEDS):
            choices = chosen()
            choices.set_seed(seed)
            set_up = [place for place, said in enumerate(choices.said_of_sections()) if wizard_text.MSG_PLAN_SET_UP.split('{')[0] in said]
            if set_up:
                break
        self.assertTrue(set_up)
        choices.section(set_up[0]).set_own(field=wizard_names.SONG_PLAN_SETUP, value=wizard_names.NOT_AT_ALL)
        self.assertNotIn(wizard_text.MSG_PLAN_SET_UP.split('{')[0], choices.said_of_sections()[set_up[0]])


class TestWizardShapesAndIntroHook(unittest.TestCase):
    """A section's shape, a section that rises, and the hook said in the intro."""

    __slots__ = ()

    def test_a_kind_with_shapes_offers_them_and_each_makes_another_song(self):
        choices = chosen()
        solo = choices.get_song_form().section_kinds_in_form().index(A_KIND_WITH_SHAPES)
        self.assertTrue(choices.section(solo).shapes())
        self.assertEqual(choices.section(A_VERSE).shapes(), [])
        self.assertNotIn(wizard_limits.SHAPE_OF_SECTION, choices.section(A_VERSE).own_fields())
        for shape in choices.section(solo).shapes():
            choices.section(solo).set_own(field=wizard_limits.SHAPE_OF_SECTION, value=shape)
            self.assertEqual(choices.section(solo).own(field=wizard_limits.SHAPE_OF_SECTION), shape)
        with self.assertRaises(ValueError):
            choices.section(solo).set_own(field=wizard_limits.SHAPE_OF_SECTION, value=NOT_A_PART)
        with self.assertRaises(ValueError):
            choices.section(A_VERSE).set_own(field=wizard_limits.SHAPE_OF_SECTION, value=choices.section(solo).shapes()[0])

    def test_a_section_made_to_rise_leaves_with_a_build_and_grows_louder(self):
        choices = chosen()
        self.assertFalse(choices.section(A_VERSE).from_plan(field=wizard_names.SONG_PLAN_RISES))
        choices.section(A_VERSE).set_own(field=wizard_names.SONG_PLAN_RISES, value=True)
        self.assertIn(wizard_text.MSG_PLAN_LEAVES_TAIL.format(joins.BUILD), choices.said_of_sections()[A_VERSE])
        scene = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.SONGS][A_NAME][Section.SCENES][A_VERSE]
        self.assertLess(scene[VelocitySetting.IN_START], scene[VelocitySetting.LEVEL])
        # The climb takes every bar of the section.
        self.assertEqual(scene[VelocitySetting.IN_OVER], choices.section(A_VERSE).bars())

    def test_the_hook_is_said_in_the_intro_by_whoever_is_chosen_and_by_nobody_until_then(self):
        choices = chosen()
        players = choices.intro_hook_players()
        self.assertEqual(players, [choices.interplay().answered_by(), choices.get_band().tune_player()])
        self.assertIsNone(choices.get_intro_hook())
        for role in players:
            choices.set_intro_hook(role)
            self.assertEqual(choices.get_intro_hook(), role)
            self.assertEqual(WizardChoices.from_data(choices.to_data()).get_intro_hook(), role)
            song = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)
            self.assertIsNotNone(song.get_scenes()[THE_INTRO].get_clip_slot(role))
        choices.set_intro_hook(None)
        self.assertIsNone(choices.get_intro_hook())
        with self.assertRaises(ValueError):
            choices.set_intro_hook(NOT_A_PART)

    def test_the_intros_notes_written_by_hand_are_played_by_its_player_kept_with_the_song_and_given_back(self):
        for role in chosen().intro_hook_players():
            with self.subTest(role=role):
                choices = chosen()
                self.assertIsNone(choices.intro_melody_place())
                self.assertIsNone(choices.intro_pattern())
                with self.assertRaises(ValueError):
                    choices.set_intro_pattern(pattern={})
                choices.set_intro_hook(role)
                self.assertEqual(choices.intro_melody_place(), THE_INTRO)
                written = choices.intro_pattern()
                own = copy.deepcopy(written)
                own[Row.DEGREE][0] = A_DEGREE if written[Row.DEGREE][0] != A_DEGREE else ANOTHER_DEGREE
                self.assertFalse(choices.intro_is_own())
                choices.set_intro_pattern(pattern=own)
                self.assertTrue(choices.intro_is_own())
                self.assertEqual(choices.intro_pattern()[Row.DEGREE], own[Row.DEGREE])
                setlist = choices.made_setlist(name=A_NAME, version=version.VERSION)
                slot = setlist.get_song(A_NAME).get_scenes()[THE_INTRO].get_clip_slot(role)
                self.assertEqual(setlist.get_pattern(slot.get_pattern_name()).to_data()[Row.DEGREE], own[Row.DEGREE])
                again = WizardChoices.from_data(choices.to_data())
                self.assertTrue(again.intro_is_own())
                self.assertEqual(again.intro_pattern()[Row.DEGREE], own[Row.DEGREE])
                choices.set_intro_pattern(pattern=None)
                self.assertFalse(choices.intro_is_own())
                self.assertEqual(choices.intro_pattern(), written)

    def test_the_intros_own_notes_are_one_players_and_another_player_says_the_hook(self):
        choices = chosen()
        first, second = choices.intro_hook_players()
        choices.set_intro_hook(first)
        own = choices.intro_pattern()
        own[Row.DEGREE][0] = A_DEGREE if own[Row.DEGREE][0] != A_DEGREE else ANOTHER_DEGREE
        choices.set_intro_pattern(pattern=own)
        choices.set_intro_hook(second)
        self.assertFalse(choices.intro_is_own())
        choices.set_intro_hook(first)
        self.assertTrue(choices.intro_is_own())

    def test_a_solos_notes_written_by_hand_are_that_solos_alone_played_kept_with_the_song_and_given_back(self):
        choices = chosen(genre=A_GENRE_OF_MANY_SOLOS, subgenre=None)
        places = choices.get_solos().solo_places()
        self.assertGreater(len(places), 1)
        last = places[-1]
        written = choices.get_solos().solo_pattern(last)
        own = copy.deepcopy(written)
        step = next(place for place, degree in enumerate(own[Row.DEGREE]) if degree is not None)
        own[Row.DEGREE][step] = A_DEGREE if own[Row.DEGREE][step] != A_DEGREE else ANOTHER_DEGREE
        choices.get_solos().set_solo_pattern(place=last, pattern=own)
        self.assertEqual([choices.get_solos().solo_is_own(place) for place in places], [place == last for place in places])
        setlist = choices.made_setlist(name=A_NAME, version=version.VERSION)
        scenes = setlist.get_song(A_NAME).get_scenes()
        played = [setlist.get_pattern(scenes[place].get_clip_slot(choices.get_solos().solo_player()).get_pattern_name()).to_data()[Row.DEGREE] for place in places]
        self.assertEqual(played[-1], own[Row.DEGREE])
        self.assertNotIn(own[Row.DEGREE], played[:-1])
        again = WizardChoices.from_data(choices.to_data())
        self.assertTrue(again.get_solos().solo_is_own(last))
        self.assertEqual(again.get_solos().solo_pattern(last)[Row.DEGREE], own[Row.DEGREE])
        choices.get_solos().set_solo_pattern(place=last, pattern=None)
        self.assertFalse(choices.get_solos().solo_is_own(last))
        self.assertEqual(choices.get_solos().solo_pattern(last), written)
        with self.assertRaises(ValueError):
            choices.get_solos().set_solo_pattern(place=THE_INTRO, pattern=own)

    def test_another_take_of_a_solo_changes_that_solo_alone_is_kept_with_the_song_and_gives_up_notes_by_hand(self):
        choices = chosen(genre=A_GENRE_OF_MANY_SOLOS, subgenre=None)
        places = choices.get_solos().solo_places()
        before = [choices.get_solos().solo_pattern(place) for place in places]
        choices.get_solos().new_solo_take(places[0])
        after = [choices.get_solos().solo_pattern(place) for place in places]
        self.assertNotEqual(after[0], before[0])
        self.assertEqual(after[1:], before[1:])
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual([again.get_solos().solo_pattern(place) for place in places], after)
        own = copy.deepcopy(after[0])
        step = next(place for place, degree in enumerate(own[Row.DEGREE]) if degree is not None)
        own[Row.DEGREE][step] = A_DEGREE if own[Row.DEGREE][step] != A_DEGREE else ANOTHER_DEGREE
        choices.get_solos().set_solo_pattern(place=places[0], pattern=own)
        choices.get_solos().new_solo_take(places[0])
        self.assertFalse(choices.get_solos().solo_is_own(places[0]))
        self.assertNotIn(choices.get_solos().solo_pattern(places[0])[Row.DEGREE], (own[Row.DEGREE], after[0][Row.DEGREE]))
        with self.assertRaises(ValueError):
            choices.get_solos().new_solo_take(THE_INTRO)

    def test_a_band_with_one_guitarist_still_has_its_solo_to_edit(self):
        choices = chosen()
        places = choices.get_solos().solo_places()
        self.assertTrue(places)
        choices.get_band().set_guitarists(wizard_limits.ONE_GUITARIST_COUNT)
        self.assertEqual(choices.get_solos().solo_places(), places)
        self.assertIsNotNone(choices.get_solos().solo_pattern(places[0]))

    def test_nobody_can_say_the_hook_in_an_intro_without_a_plan_or_a_hook(self):
        self.assertEqual(chosen(plan=False).intro_hook_players(), [])
        choices = chosen()
        choices.get_hook().set_hook(False)
        self.assertEqual(choices.intro_hook_players(), [])


class TestWizardFormQuestions(unittest.TestCase):
    """A form made from a few answers."""

    __slots__ = ()

    def test_only_the_kinds_the_subgenre_plays_are_asked_about_and_a_genre_with_no_chorus_is_asked_nothing(self):
        asked = [name for name, _, _ in chosen(plan=False).get_song_form().form_questions()]
        self.assertEqual(asked, [wizard_limits.VERSES_FIRST, wizard_limits.PRE_CHORUSES, wizard_limits.BRIDGE, wizard_limits.SOLOS, wizard_limits.DRUM_SOLO_KIND, wizard_limits.LAST_CHORUSES])
        other = chosen(genre=AN_UNPLANNED_GENRE, subgenre=None, plan=False)
        self.assertEqual(other.get_song_form().form_questions(), [])
        with self.assertRaises(ValueError):
            other.get_song_form().form_of_answers({})

    def test_every_run_of_answers_makes_a_form_the_song_can_be_made_with(self):
        choices = chosen(plan=False)
        questions = choices.get_song_form().form_questions()
        forms = set()
        for answers in itertools.product(*(offered for _, offered, _ in questions)):
            given = {name: answer for (name, _, _), answer in zip(questions, answers)}
            form = choices.get_song_form().form_of_answers(given)
            forms.add(tuple(form))
            self.assertEqual(form.count(wizard_limits.SOLO), wizard_limits.SOLO_COUNTS.index(given[wizard_limits.SOLOS]))
            self.assertEqual(wizard_limits.BRIDGE in form, given[wizard_limits.BRIDGE] == wizard_limits.YES)
            self.assertEqual(wizard_limits.DRUM_SOLO_KIND in form, given[wizard_limits.DRUM_SOLO_KIND] == wizard_limits.YES)
            self.assertEqual(wizard_limits.PRE_CHORUS in form, given[wizard_limits.PRE_CHORUSES] != wizard_limits.NO)
        self.assertEqual(len(forms), len(list(itertools.product(*(offered for _, offered, _ in questions)))))
        for form in sorted(forms)[::A_FEW_FORMS_APART]:
            made = chosen()
            made.get_song_form().set_own_sections(sections=[{KIND_OF_SECTION: kind} for kind in form])
            made.made_setlist(name=A_NAME, version=version.VERSION)

    def test_the_answers_become_the_song_s_own_form_and_a_wrong_answer_changes_nothing(self):
        choices = chosen(plan=False)
        choices.get_song_form().set_form_from_answers({wizard_limits.SOLOS: wizard_limits.SOLO_COUNTS[2], wizard_limits.DRUM_SOLO_KIND: wizard_limits.YES})
        self.assertTrue(choices.get_song_form().has_own_form())
        kinds = choices.get_song_form().section_kinds_in_form()
        self.assertEqual((kinds.count(wizard_limits.SOLO), kinds.count(wizard_limits.DRUM_SOLO_KIND)), (2, 1))
        for wrong in ({wizard_limits.SOLOS: NOT_A_PART}, {NOT_A_PART: wizard_limits.YES}):
            with self.assertRaises(ValueError):
                choices.get_song_form().set_form_from_answers(wrong)
        self.assertEqual(choices.get_song_form().section_kinds_in_form(), kinds)


class TestWizardListeningPlaces(unittest.TestCase):
    """Where in the made song the hook and the tune are, for a panel to listen to."""

    __slots__ = ()

    def test_the_hook_s_section_says_the_hook_and_the_tune_s_has_the_tune_s_player(self):
        choices = chosen(plan=False)
        kinds = choices.get_song_form().section_kinds_in_form()
        self.assertEqual(kinds[choices.get_hook().hook_scene()], 'chorus')
        self.assertIn(choices.get_band().tune_player(), choices.section(choices.tune_scene()).plays())
        setlist, name = choices.made_for_listening()
        self.assertEqual(len(setlist.get_song(name).get_scenes()), len(kinds))
