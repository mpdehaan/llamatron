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

"""The wizard's choices of a planned song: the plan switched on, its contrast, its phrasing and the hook's kind."""

import itertools
import random
import unittest

from llamatron.composition.file_format import SceneSetting, Section
from llamatron.macro_composer import hook_kinds, phrasing
from llamatron.macro_composer.notation import REST, STEPS
from llamatron.macro_composer.arranger import CHORDS
from llamatron.macro_composer.joins import BUILD, DROP_OUT, LEAVES, STOPS
from llamatron.macro_composer.song_plan import ENERGY, HIGHEST_ENERGY, LOWEST_ENERGY, NOT_AT_ALL, RISES, ROOT_OF_PLACE, SETUP, TEMPO_END_OF_PLACE, TEMPO_OF_PLACE, TYPE_OF_PLACE, USUAL_CONTRAST
from llamatron.macro_composer.wizard_choices import BRIDGE, DRUM_SOLO_KIND, LAST_CHORUSES, NO, PRE_CHORUS, PRE_CHORUSES, SOLO, SOLO_COUNTS, SOLOS, VERSES_FIRST, YES, HOOK_PARTS, LEAVES_AS_JOIN, OWN_WITHOUT_PLAN, PHRASING_OFFERED, SHAPE_OF_SECTION, MINOR, WizardChoices, chords_as_text, chords_from_text
from llamatron.composition import limits
from llamatron.strings import errors, macro_composer as composer_text
from llamatron.macro_composer.arranger import shares_a_bar as arranger_shares_a_bar
from llamatron.support.version import VERSION

A_NAME = 'made'
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
        for asked in (choices.get_contrast, choices.has_phrasing, choices.hook_kind, choices.energies, choices.said_of_sections):
            with self.assertRaisesRegex(ValueError, errors.ERR_WIZARD_NO_SONG_PLAN):
                asked()

    def test_a_plan_gives_every_section_an_energy_and_says_how_each_leaves(self):
        choices = chosen()
        places = len(choices.section_labels())
        self.assertEqual(len(choices.energies()), places)
        self.assertEqual(len(choices.said_of_sections()), places)
        for energy in choices.energies():
            self.assertTrue(LOWEST_ENERGY <= energy <= HIGHEST_ENERGY)
        # The last chorus is the song's most.
        kinds = choices.section_kinds_in_form()
        self.assertEqual(max(choices.energies()), choices.energies()[len(kinds) - 1 - kinds[::-1].index('chorus')])

    def test_contrast_stretches_the_energies_and_is_held_to_its_range(self):
        choices = chosen()
        self.assertEqual(choices.get_contrast(), USUAL_CONTRAST)
        usual = choices.energies()
        choices.set_contrast(A_HIGH_CONTRAST)
        self.assertEqual(choices.get_contrast(), A_HIGH_CONTRAST)
        self.assertLess(min(choices.energies()), min(usual))
        for wrong in (LOWEST_ENERGY - 1, HIGHEST_ENERGY + 1, True, NOT_A_SWITCH):
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
        choices.set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        again = WizardChoices.from_data(choices.to_data())
        self.assertTrue(again.has_song_plan())
        self.assertEqual(again.get_contrast(), A_HIGH_CONTRAST)
        self.assertFalse(again.has_phrasing())
        self.assertEqual(again.hook_kind(), choices.hook_kind())
        self.assertEqual(again.made_setlist(name=A_NAME, version=VERSION).to_data(), choices.made_setlist(name=A_NAME, version=VERSION).to_data())

    def test_switching_the_plan_off_or_choosing_another_genre_drops_it(self):
        choices = chosen()
        choices.set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        choices.set_song_plan(False)
        self.assertFalse(choices.has_song_plan())
        choices.set_song_plan(True)
        self.assertFalse(choices.hook_part_is_chosen(hook_kinds.CONTOUR))
        choices.set_genre(AN_UNPLANNED_GENRE)
        choices.set_subgenre(choices.subgenres()[0])
        self.assertFalse(choices.has_song_plan())

    def test_a_planned_song_differs_from_the_song_without_a_plan(self):
        self.assertNotEqual(chosen().made_setlist(name=A_NAME, version=VERSION).to_data(), chosen(plan=False).made_setlist(name=A_NAME, version=VERSION).to_data())


class TestWizardPhrasing(unittest.TestCase):
    """How a planned song's lines breathe."""

    __slots__ = ()

    def test_each_respect_starts_as_usual_takes_what_is_offered_and_is_kept(self):
        choices = chosen()
        for name, offered in PHRASING_OFFERED.items():
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
        line = [{STEPS: A_BAR_OF_STEPS}, {STEPS: A_BAR_OF_STEPS}]
        silences = []
        for breath in phrasing.BREATHS:
            made = phrasing.breathed(line=line, grid=A_BAR_OF_STEPS, count=0, dice=random.Random(A_SEED), ways={phrasing.BREATH: breath, phrasing.EARLY_NOTES: phrasing.FEWEST_EARLY})
            silences.append(sum(note.get(REST, 0) for note in made))
        self.assertEqual(silences, sorted(set(silences)))

    def test_which_lines_are_the_shorter_follows_the_line_lengths(self):
        self.assertEqual([phrasing.is_shorter(count=count, lengths=phrasing.LONG_THEN_SHORT) for count in range(4)], [False, True, False, True])
        self.assertEqual([phrasing.is_shorter(count=count, lengths=phrasing.SHORT_THEN_LONG) for count in range(4)], [True, False, True, False])
        self.assertFalse(any(phrasing.is_shorter(count=count, lengths=phrasing.EVEN) for count in range(4)))


class TestWizardHookKind(unittest.TestCase):
    """The hook's kind: the wizard's pick, and each part chosen over it."""

    __slots__ = ()

    def test_the_kind_is_the_take_s_until_a_part_is_chosen_and_goes_back_to_it(self):
        choices = chosen()
        picked = choices.hook_kind()
        self.assertEqual(picked, hook_kinds.kind_of(seed=A_SEED, take=choices.get_hook_take()))
        for part, offered in HOOK_PARTS.items():
            other = next(value for value in offered if value != picked[part])
            self.assertFalse(choices.hook_part_is_chosen(part))
            choices.set_hook_part(part=part, value=other)
            self.assertTrue(choices.hook_part_is_chosen(part))
            self.assertEqual(choices.hook_kind()[part], other)
            choices.set_hook_part(part=part, value=None)
            self.assertEqual(choices.hook_kind(), picked)

    def test_a_part_chosen_stays_through_a_new_hook(self):
        choices = chosen()
        choices.set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        choices.new_hook()
        self.assertEqual(choices.hook_kind()[hook_kinds.CONTOUR], hook_kinds.CHANT)

    def test_a_chosen_contour_is_the_hook_the_song_plays(self):
        choices = chosen()
        hooks = set()
        for contour in hook_kinds.CONTOURS:
            choices.set_hook_part(part=hook_kinds.CONTOUR, value=contour)
            hooks.add(repr(choices.hook_notes()))
        self.assertEqual(len(hooks), len(hook_kinds.CONTOURS))

    def test_what_is_not_a_part_or_not_offered_is_refused(self):
        choices = chosen()
        with self.assertRaises(ValueError):
            choices.set_hook_part(part=NOT_A_PART, value=hook_kinds.CHANT)
        with self.assertRaises(ValueError):
            choices.set_hook_part(part=hook_kinds.CONTOUR, value=NOT_A_PART)

    def test_a_long_note_has_neither_a_rhythm_nor_a_detail(self):
        choices = chosen()
        choices.set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.LONG_NOTE)
        self.assertEqual(choices.hook_parts(), [hook_kinds.CONTOUR])
        choices.set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        self.assertEqual(choices.hook_parts(), list(HOOK_PARTS))

    def test_a_song_not_in_four_has_no_kinds_and_no_phrasing(self):
        choices = chosen(subgenre=A_SUBGENRE_IN_SIX)
        self.assertFalse(choices.counts_in_four())
        self.assertEqual(choices.hook_parts(), [])
        self.assertTrue(chosen().counts_in_four())


class TestWizardSectionOwn(unittest.TestCase):
    """What a section of a planned song is given of its own: Energy, how it leaves, its setup, chords, tempo, key and scale."""

    __slots__ = ()

    def scene(self, *, choices, place=A_VERSE):
        return choices.made_setlist(name=A_NAME, version=VERSION).get_song(A_NAME).get_scenes()[place]

    def test_a_section_has_fields_of_its_own_only_under_a_plan_and_a_join_only_where_it_leaves(self):
        # Without a plan a section still takes chords, a tempo, a key and a scale of its own, in every genre.
        self.assertEqual(chosen(plan=False).section_own_fields(A_VERSE), list(OWN_WITHOUT_PLAN))
        self.assertEqual(chosen(genre=AN_UNPLANNED_GENRE, subgenre=None, plan=False).section_own_fields(A_VERSE), list(OWN_WITHOUT_PLAN))
        choices = chosen()
        last = len(choices.section_labels()) - 1
        self.assertIn(LEAVES, choices.section_own_fields(A_VERSE))
        # The ending, one held chord, takes nothing of its own.
        self.assertEqual(choices.section_own_fields(last), [])
        self.assertIn(ENERGY, choices.section_own_fields(A_VERSE))

    def test_each_field_is_none_until_given_and_shows_what_the_plan_or_the_song_gives(self):
        choices = chosen()
        for field in choices.section_own_fields(A_VERSE):
            self.assertIsNone(choices.section_own(place=A_VERSE, field=field))
        self.assertEqual(choices.section_from_plan(place=A_VERSE, field=ENERGY), choices.energies()[A_VERSE])
        self.assertEqual(choices.section_from_plan(place=A_VERSE, field=TEMPO_OF_PLACE), choices.get_tempo())
        self.assertEqual(choices.section_from_plan(place=A_VERSE, field=ROOT_OF_PLACE), choices.get_root())
        self.assertEqual(choices.section_from_plan(place=A_VERSE, field=TYPE_OF_PLACE), choices.get_scale_type())

    def test_an_energy_of_its_own_is_the_section_s_energy_and_none_gives_it_back(self):
        choices = chosen()
        usual = choices.energies()
        choices.set_section_own(place=A_VERSE, field=ENERGY, value=HIGHEST_ENERGY)
        self.assertEqual(choices.energies()[A_VERSE], HIGHEST_ENERGY)
        self.assertTrue(choices.has_own_form())
        choices.set_section_own(place=A_VERSE, field=ENERGY, value=None)
        self.assertEqual(choices.energies(), usual)

    def test_a_tempo_a_tempo_at_the_end_a_key_and_a_scale_are_the_scene_s(self):
        choices = chosen()
        choices.set_section_own(place=A_VERSE, field=TEMPO_OF_PLACE, value=A_SLOW_TEMPO)
        self.assertEqual(self.scene(choices=choices).get_tempo_setting(), A_SLOW_TEMPO)
        choices.set_section_own(place=A_VERSE, field=TEMPO_END_OF_PLACE, value=A_FAST_TEMPO)
        data = choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.SONGS][A_NAME][Section.SCENES][A_VERSE]
        self.assertEqual((data[SceneSetting.TEMPO_START], data[SceneSetting.TEMPO_END]), (A_SLOW_TEMPO, A_FAST_TEMPO))
        choices.set_section_own(place=A_VERSE, field=ROOT_OF_PLACE, value=ANOTHER_ROOT)
        choices.set_section_own(place=A_VERSE, field=TYPE_OF_PLACE, value=MINOR)
        made = choices.made_setlist(name=A_NAME, version=VERSION)
        name = made.get_song(A_NAME).get_scenes()[A_VERSE].get_scale_name()
        scale = made.to_data()[Section.SCALES][name]
        self.assertEqual((scale[ROOT_OF_PLACE], scale[TYPE_OF_PLACE]), (ANOTHER_ROOT, MINOR))
        # The section before keeps the song's.
        self.assertIsNone(made.get_song(A_NAME).get_scenes()[A_VERSE - 1].get_scale_name())

    def test_a_tempo_at_the_end_alone_starts_from_the_song_s_tempo(self):
        choices = chosen()
        choices.set_section_own(place=A_VERSE, field=TEMPO_END_OF_PLACE, value=A_SLOW_TEMPO)
        data = choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.SONGS][A_NAME][Section.SCENES][A_VERSE]
        self.assertEqual((data[SceneSetting.TEMPO_START], data[SceneSetting.TEMPO_END]), (choices.get_tempo(), A_SLOW_TEMPO))

    def test_each_way_of_leaving_is_what_the_plan_says_of_the_section(self):
        choices = chosen()
        said = set()
        for way in LEAVES_AS_JOIN:
            choices.set_section_own(place=A_VERSE, field=LEAVES, value=way)
            said.add(choices.said_of_sections()[A_VERSE])
            if way in (STOPS, DROP_OUT, BUILD):
                self.assertIn(composer_text.MSG_PLAN_LEAVES_TAIL.format(way), choices.said_of_sections()[A_VERSE])
        self.assertEqual(len(said), len(LEAVES_AS_JOIN))

    def test_chords_are_typed_as_degrees_and_change_the_song(self):
        choices = chosen()
        before = choices.made_setlist(name=A_NAME, version=VERSION).to_data()
        choices.set_section_own(place=A_VERSE, field=CHORDS, value=SOME_CHORDS)
        self.assertEqual(chords_as_text(choices.section_own(place=A_VERSE, field=CHORDS)), SOME_CHORDS)
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=VERSION).to_data(), before)
        for wrong in NOT_CHORDS:
            with self.assertRaises(ValueError):
                chords_from_text(wrong)

    def test_two_chords_joined_by_a_dash_share_a_bar_and_are_played_by_the_half_bar(self):
        choices = chosen()
        usual = choices.made_setlist(name=A_NAME, version=VERSION).to_data()
        choices.set_section_own(place=A_VERSE, field=CHORDS, value=CHORDS_SHARING_A_BAR)
        own = choices.section_own(place=A_VERSE, field=CHORDS)
        self.assertEqual(chords_as_text(own), CHORDS_SHARING_A_BAR)
        self.assertTrue(arranger_shares_a_bar(own[-1]))
        shared = choices.made_setlist(name=A_NAME, version=VERSION).to_data()
        self.assertNotEqual(shared, usual)
        # The same bars with their first chords alone are another song.
        choices.set_section_own(place=A_VERSE, field=CHORDS, value=THE_BARS_FIRST_CHORDS)
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=VERSION).to_data(), shared)

    def test_shared_bars_are_refused_past_what_a_progression_holds_and_three_never_share(self):
        too_many = ' '.join([CHORDS_SHARING_A_BAR] * limits.MAX_PROGRESSION_CHORDS)
        for wrong in (too_many, THREE_IN_A_BAR, A_DASH_ALONE):
            with self.assertRaises(ValueError):
                chords_from_text(wrong)

    def test_what_a_field_cannot_take_is_refused_and_nothing_changes(self):
        choices = chosen()
        before = choices.to_data()
        for field, wrong in ((ENERGY, HIGHEST_ENERGY + 1), (LEAVES, NOT_A_PART), (SETUP, NOT_A_PART), (TEMPO_OF_PLACE, 0), (ROOT_OF_PLACE, NOT_A_PART), (TYPE_OF_PLACE, NOT_A_PART), (NOT_A_PART, 1)):
            with self.assertRaises(ValueError):
                choices.set_section_own(place=A_VERSE, field=field, value=wrong)
        self.assertEqual(choices.to_data(), before)
        with self.assertRaises(ValueError):
            chosen(plan=False).set_section_own(place=A_VERSE, field=ENERGY, value=HIGHEST_ENERGY)

    def test_a_section_of_a_song_with_no_plan_takes_chords_a_tempo_a_key_and_a_scale(self):
        for genre in (A_PLANNED_GENRE, AN_UNPLANNED_GENRE):
            choices = chosen(genre=genre, subgenre=None, plan=False)
            choices.set_section_own(place=A_VERSE, field=CHORDS, value=SOME_CHORDS)
            choices.set_section_own(place=A_VERSE, field=TEMPO_OF_PLACE, value=A_SLOW_TEMPO)
            choices.set_section_own(place=A_VERSE, field=ROOT_OF_PLACE, value=ANOTHER_ROOT)
            choices.set_section_own(place=A_VERSE, field=TYPE_OF_PLACE, value=MINOR)
            made = choices.made_setlist(name=A_NAME, version=VERSION)
            scene = made.get_song(A_NAME).get_scenes()[A_VERSE]
            self.assertEqual(scene.get_tempo_setting(), A_SLOW_TEMPO)
            scale = made.to_data()[Section.SCALES][scene.get_scale_name()]
            self.assertEqual((scale[ROOT_OF_PLACE], scale[TYPE_OF_PLACE]), (ANOTHER_ROOT, MINOR))
            # The sections beside it keep the song's.
            self.assertIsNone(made.get_song(A_NAME).get_scenes()[A_VERSE + 1].get_tempo_setting())
            again = WizardChoices.from_data(choices.to_data())
            self.assertEqual(again.made_setlist(name=A_NAME, version=VERSION).to_data(), made.to_data())

    def test_what_a_section_was_given_goes_with_it_when_moved_and_copied_and_is_kept(self):
        choices = chosen()
        choices.set_section_own(place=A_VERSE, field=ENERGY, value=HIGHEST_ENERGY)
        choices.set_section_own(place=A_VERSE, field=CHORDS, value=SOME_CHORDS)
        choices.copy_section(A_VERSE)
        choices.move_section(place=A_VERSE, offset=1)
        for place in (A_VERSE, A_VERSE + 1):
            self.assertEqual(choices.section_own(place=place, field=ENERGY), HIGHEST_ENERGY)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.to_data(), choices.to_data())
        self.assertEqual(again.made_setlist(name=A_NAME, version=VERSION).to_data(), choices.made_setlist(name=A_NAME, version=VERSION).to_data())
        choices.remove_section(A_VERSE)
        choices.remove_section(A_VERSE)
        self.assertIsNone(choices.section_own(place=A_VERSE, field=ENERGY))

    def test_no_setup_leaves_the_section_s_last_chord_alone(self):
        # A progression that starts at home is the one a section is set up for, so the seeds are tried until a song has one.
        for seed in range(MANY_SEEDS):
            choices = chosen()
            choices.set_seed(seed)
            set_up = [place for place, said in enumerate(choices.said_of_sections()) if composer_text.MSG_PLAN_SET_UP.split('{')[0] in said]
            if set_up:
                break
        self.assertTrue(set_up)
        choices.set_section_own(place=set_up[0], field=SETUP, value=NOT_AT_ALL)
        self.assertNotIn(composer_text.MSG_PLAN_SET_UP.split('{')[0], choices.said_of_sections()[set_up[0]])


class TestWizardShapesAndIntroHook(unittest.TestCase):
    """A section's shape, a section that rises, and the hook said in the intro."""

    __slots__ = ()

    def test_a_kind_with_shapes_offers_them_and_each_makes_another_song(self):
        choices = chosen()
        solo = choices.section_kinds_in_form().index(A_KIND_WITH_SHAPES)
        self.assertTrue(choices.section_shapes(solo))
        self.assertEqual(choices.section_shapes(A_VERSE), [])
        self.assertNotIn(SHAPE_OF_SECTION, choices.section_own_fields(A_VERSE))
        for shape in choices.section_shapes(solo):
            choices.set_section_own(place=solo, field=SHAPE_OF_SECTION, value=shape)
            self.assertEqual(choices.section_own(place=solo, field=SHAPE_OF_SECTION), shape)
        with self.assertRaises(ValueError):
            choices.set_section_own(place=solo, field=SHAPE_OF_SECTION, value=NOT_A_PART)
        with self.assertRaises(ValueError):
            choices.set_section_own(place=A_VERSE, field=SHAPE_OF_SECTION, value=choices.section_shapes(solo)[0])

    def test_a_section_made_to_rise_leaves_with_a_build_and_grows_louder(self):
        choices = chosen()
        self.assertFalse(choices.section_from_plan(place=A_VERSE, field=RISES))
        choices.set_section_own(place=A_VERSE, field=RISES, value=True)
        self.assertIn(composer_text.MSG_PLAN_LEAVES_TAIL.format(BUILD), choices.said_of_sections()[A_VERSE])
        scene = choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.SONGS][A_NAME][Section.SCENES][A_VERSE]
        self.assertLess(scene[SceneSetting.SWELL_START], scene[SceneSetting.SWELL_END])

    def test_the_hook_is_said_in_the_intro_by_whoever_is_chosen_and_by_nobody_until_then(self):
        choices = chosen()
        players = choices.intro_hook_players()
        self.assertEqual(players, [choices.answered_by(), choices.tune_player()])
        self.assertIsNone(choices.get_intro_hook())
        for role in players:
            choices.set_intro_hook(role)
            self.assertEqual(choices.get_intro_hook(), role)
            self.assertEqual(WizardChoices.from_data(choices.to_data()).get_intro_hook(), role)
            song = choices.made_setlist(name=A_NAME, version=VERSION).get_song(A_NAME)
            self.assertIsNotNone(song.get_scenes()[THE_INTRO].get_clip_slot(role))
        choices.set_intro_hook(None)
        self.assertIsNone(choices.get_intro_hook())
        with self.assertRaises(ValueError):
            choices.set_intro_hook(NOT_A_PART)

    def test_nobody_can_say_the_hook_in_an_intro_without_a_plan_or_a_hook(self):
        self.assertEqual(chosen(plan=False).intro_hook_players(), [])
        choices = chosen()
        choices.set_hook(False)
        self.assertEqual(choices.intro_hook_players(), [])


class TestWizardFormQuestions(unittest.TestCase):
    """A form made from a few answers."""

    __slots__ = ()

    def test_only_the_kinds_the_subgenre_plays_are_asked_about_and_a_genre_with_no_chorus_is_asked_nothing(self):
        asked = [name for name, _, _ in chosen(plan=False).form_questions()]
        self.assertEqual(asked, [VERSES_FIRST, PRE_CHORUSES, BRIDGE, SOLOS, DRUM_SOLO_KIND, LAST_CHORUSES])
        other = chosen(genre=AN_UNPLANNED_GENRE, subgenre=None, plan=False)
        self.assertEqual(other.form_questions(), [])
        with self.assertRaises(ValueError):
            other.form_of_answers({})

    def test_every_run_of_answers_makes_a_form_the_song_can_be_made_with(self):
        choices = chosen(plan=False)
        questions = choices.form_questions()
        forms = set()
        for answers in itertools.product(*(offered for _, offered, _ in questions)):
            given = {name: answer for (name, _, _), answer in zip(questions, answers)}
            form = choices.form_of_answers(given)
            forms.add(tuple(form))
            self.assertEqual(form.count(SOLO), SOLO_COUNTS.index(given[SOLOS]))
            self.assertEqual(BRIDGE in form, given[BRIDGE] == YES)
            self.assertEqual(DRUM_SOLO_KIND in form, given[DRUM_SOLO_KIND] == YES)
            self.assertEqual(PRE_CHORUS in form, given[PRE_CHORUSES] != NO)
        self.assertEqual(len(forms), len(list(itertools.product(*(offered for _, offered, _ in questions)))))
        for form in sorted(forms)[::A_FEW_FORMS_APART]:
            made = chosen()
            made.set_own_sections(sections=[{KIND_OF_SECTION: kind} for kind in form])
            made.made_setlist(name=A_NAME, version=VERSION)

    def test_the_answers_become_the_song_s_own_form_and_a_wrong_answer_changes_nothing(self):
        choices = chosen(plan=False)
        choices.set_form_from_answers({SOLOS: SOLO_COUNTS[2], DRUM_SOLO_KIND: YES})
        self.assertTrue(choices.has_own_form())
        kinds = choices.section_kinds_in_form()
        self.assertEqual((kinds.count(SOLO), kinds.count(DRUM_SOLO_KIND)), (2, 1))
        for wrong in ({SOLOS: NOT_A_PART}, {NOT_A_PART: YES}):
            with self.assertRaises(ValueError):
                choices.set_form_from_answers(wrong)
        self.assertEqual(choices.section_kinds_in_form(), kinds)


class TestWizardListeningPlaces(unittest.TestCase):
    """Where in the made song the hook and the tune are, for a panel to listen to."""

    __slots__ = ()

    def test_the_hook_s_section_says_the_hook_and_the_tune_s_has_the_tune_s_player(self):
        choices = chosen(plan=False)
        kinds = choices.section_kinds_in_form()
        self.assertEqual(kinds[choices.hook_scene()], 'chorus')
        self.assertIn(choices.tune_player(), choices.section_plays(choices.tune_scene()))
        setlist, name = choices.made_for_listening()
        self.assertEqual(len(setlist.get_song(name).get_scenes()), len(kinds))
