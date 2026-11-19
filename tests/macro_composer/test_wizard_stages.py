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

"""Tests of how a song of the wizard's starts and ends: each way's stages as sections of their own, the first player, the setup's bars, and a section that fades."""

import unittest

from llamatron.composition.file_format import Section, VelocitySetting
from llamatron.macro_composer.arranger import style_names
from llamatron.macro_composer.song_plan import FADE_LEVEL, FADE_OVER, FADED, FADES, TEMPO_END_OF_PLACE, UNFADED
from llamatron.macro_composer.wizard_choices import (
    DRUM_FILL_IN, DRUMS_FIRST, ENDS, FADE_IN, FADE_OUT, FULL_BAND, HARD_STOP, HELD_CHORD, LAYERS, ONE_PLAYER_ALONE, ONE_PLAYER_FIRST, OUTRO_KIND, REPEAT_AND_FADE, SLOWS_DOWN, STARTS, STRAIGHT_IN, STRIPS_DOWN, WizardChoices,
)
from llamatron.support import version

A_NAME = 'made'
A_SEED = 11
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
AN_ELECTRONIC_GENRE = 'electronic'
A_DANCE_SUBGENRE = 'house'
THE_INTRO = 'intro'
THE_ENDING = 'ending'
THE_DRUMS = 'drums'
THE_BASS = 'bass'
NOT_A_WAY = 'sideways'
NOT_BARS = 3
FIRST = 0
A_VERSE = 1
# A fade's level, a percentage of each note's written velocity.
HALF_VELOCITY = 50
TWO_BARS = 2


def chosen(*, genre=A_GENRE, subgenre=A_SUBGENRE):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    return choices


def subgenres_of(genre):
    choices = WizardChoices()
    choices.set_genre(genre)
    return choices.subgenres()


def made(choices):
    return choices.made_setlist(name=A_NAME, version=version.VERSION)


class TestWizardStarts(unittest.TestCase):
    """How a song starts."""

    __slots__ = ()

    def test_a_song_starts_with_the_full_band_until_asked_and_every_way_offered_is_a_way(self):
        choices = chosen()
        self.assertEqual(choices.get_start(), FULL_BAND)
        self.assertEqual(choices.starts(), list(STARTS))
        self.assertEqual(WizardChoices().starts(), [])

    def test_each_way_puts_its_stages_before_the_first_verse_and_leaves_the_rest_alone(self):
        choices = chosen()
        body = choices.section_kinds_in_form()[1:]
        players = choices.first_players()
        expected = {STRAIGHT_IN: [], FULL_BAND: [players], DRUMS_FIRST: [[THE_DRUMS], players], DRUM_FILL_IN: [[THE_DRUMS]]}
        for way, stages in expected.items():
            choices.set_start(way)
            self.assertEqual(choices.get_start(), way)
            self.assertEqual(choices.section_kinds_in_form(), [THE_INTRO] * len(stages) + body)
            self.assertEqual([sorted(choices.section_plays(place)) for place in range(len(stages))], [sorted(stage) for stage in stages])
            made(choices)

    def test_layers_bring_the_players_in_one_at_a_time_the_first_player_first(self):
        choices = chosen()
        choices.set_start(LAYERS)
        count = len(choices.first_players())
        first = choices.get_first_player()
        self.assertNotEqual(first, THE_DRUMS)
        self.assertEqual([len(choices.section_plays(place)) for place in range(count)], list(range(1, count + 1)))
        self.assertEqual(choices.section_plays(FIRST), [first])
        choices.set_first_player(THE_BASS)
        self.assertEqual(choices.section_plays(FIRST), [THE_BASS])
        self.assertEqual(choices.get_start(), LAYERS)
        choices.set_start(ONE_PLAYER_FIRST)
        self.assertEqual(choices.section_plays(FIRST), [THE_BASS])
        self.assertEqual(sorted(choices.section_plays(FIRST + 1)), sorted(choices.first_players()))

    def test_the_setup_s_bars_are_the_length_of_every_stage(self):
        choices = chosen()
        choices.set_start(DRUMS_FIRST)
        usual = choices.get_setup_bars()
        for bars in choices.setup_bars_offered():
            choices.set_setup_bars(bars)
            self.assertEqual(choices.section_bars(FIRST), bars)
            self.assertEqual(choices.get_start(), DRUMS_FIRST)
        self.assertIn(usual, choices.setup_bars_offered())
        with self.assertRaises(ValueError):
            choices.set_setup_bars(NOT_BARS)

    def test_a_drum_fill_in_is_the_drums_alone_leaving_with_a_big_fill_and_needs_a_plan(self):
        choices = chosen()
        choices.set_song_plan(False)
        self.assertNotIn(DRUM_FILL_IN, choices.starts())
        with self.assertRaises(ValueError):
            choices.set_start(DRUM_FILL_IN)

    def test_opening_sections_a_person_changed_read_as_nobody_s_way_and_a_new_way_replaces_them(self):
        choices = chosen()
        choices.set_start(DRUMS_FIRST)
        choices.set_section_plays(place=FIRST, role=THE_BASS, on=True)
        self.assertIsNone(choices.get_start())
        choices.set_start(FULL_BAND)
        self.assertEqual(choices.section_kinds_in_form().count(THE_INTRO), 1)

    def test_what_is_not_a_way_or_a_player_is_refused_and_the_ways_are_kept_with_the_choices(self):
        choices = chosen()
        for setter in (choices.set_start, choices.set_end, choices.set_first_player):
            with self.assertRaises(ValueError):
                setter(NOT_A_WAY)
        choices.set_start(LAYERS)
        choices.set_end(STRIPS_DOWN)
        choices.set_first_player(THE_BASS)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual((again.get_start(), again.get_end(), again.get_first_player()), (LAYERS, STRIPS_DOWN, THE_BASS))
        self.assertEqual(made(again).to_data()[Section.PATTERNS], made(choices).to_data()[Section.PATTERNS])
        # Another form keeps how the song was chosen to start and to end, and who starts alone.
        choices.set_form(choices.forms()[-1])
        self.assertEqual((choices.get_start(), choices.get_end(), choices.get_first_player()), (LAYERS, STRIPS_DOWN, THE_BASS))

    def test_another_form_keeps_how_the_song_starts_and_ends_and_a_form_chosen_with_neither_is_the_forms_own(self):
        choices = chosen()
        another = next(form for form in choices.forms() if form != choices.get_form())
        choices.set_start(LAYERS)
        choices.set_end(STRIPS_DOWN)
        choices.set_setup_bars(choices.setup_bars_offered()[-1])
        bars = choices.get_setup_bars()
        choices.set_form(another)
        self.assertEqual(choices.get_form(), another)
        self.assertEqual((choices.get_start(), choices.get_end(), choices.get_setup_bars()), (LAYERS, STRIPS_DOWN, bars))
        made(choices)
        plain = chosen()
        plain.set_form(another)
        self.assertFalse(plain.has_own_form())
        self.assertEqual((plain.get_start(), plain.get_end()), (FULL_BAND, chosen().get_end()))
        body = plain.section_kinds_in_form()[1:-1]
        kinds = choices.section_kinds_in_form()
        self.assertEqual([kind for kind in kinds if kind in body], body)

    def test_every_way_of_every_subgenre_makes_a_song(self):
        for genre in style_names():
            for subgenre in subgenres_of(genre):
                choices = chosen(genre=genre, subgenre=subgenre)
                for way in choices.starts():
                    with self.subTest(subgenre=subgenre, start=way):
                        choices.set_start(way)
                        self.assertEqual(choices.get_start(), way)
                for way in choices.ends():
                    with self.subTest(subgenre=subgenre, end=way):
                        choices.set_end(way)
                        self.assertEqual(choices.get_end(), way)
                made(choices)


class TestWizardEnds(unittest.TestCase):
    """How a song ends."""

    __slots__ = ()

    def test_a_song_ends_on_its_form_s_ending_until_asked(self):
        self.assertEqual(chosen().get_end(), HELD_CHORD)
        self.assertEqual(chosen().ends(), list(ENDS))
        dance = chosen(genre=AN_ELECTRONIC_GENRE, subgenre=A_DANCE_SUBGENRE)
        self.assertIn(dance.get_end(), dance.ends())
        self.assertNotEqual(dance.get_end(), HELD_CHORD)

    def test_each_way_puts_its_stages_after_the_last_chorus(self):
        choices = chosen()
        body = choices.section_kinds_in_form()[:-1]
        count = len(choices.first_players())
        expected = {HARD_STOP: [], HELD_CHORD: [THE_ENDING], SLOWS_DOWN: [OUTRO_KIND, THE_ENDING], ONE_PLAYER_ALONE: [OUTRO_KIND, THE_ENDING], REPEAT_AND_FADE: [OUTRO_KIND],
                    STRIPS_DOWN: [OUTRO_KIND] * (count - 1) + [THE_ENDING]}
        for way, stages in expected.items():
            choices.set_end(way)
            self.assertEqual(choices.get_end(), way)
            self.assertEqual(choices.section_kinds_in_form(), body + stages)
            made(choices)

    def test_slowing_down_ends_slower_stripping_down_loses_a_player_a_stage_and_a_fade_grows_softer(self):
        choices = chosen()
        last = len(choices.section_kinds_in_form())
        choices.set_end(SLOWS_DOWN)
        self.assertLess(choices.section_own(place=last - 1, field=TEMPO_END_OF_PLACE), choices.get_tempo())
        choices.set_end(STRIPS_DOWN)
        stages = range(last - 1, len(choices.section_kinds_in_form()) - 1)
        counts = [len(choices.section_plays(place)) for place in stages]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(choices.section_plays(stages[-1]), [choices.get_first_player()])
        choices.set_end(REPEAT_AND_FADE)
        self.assertTrue(choices.section_own(place=last - 1, field=FADES))
        scene = made(choices).get_song(A_NAME).get_scenes()[last - 1]
        self.assertEqual(scene.to_data()[VelocitySetting.OUT_END], FADED)

    def test_an_opening_section_fades_in_and_a_closing_one_fades_out_with_or_without_a_plan_and_no_other_fades(self):
        for plan in (True, False):
            choices = chosen()
            choices.set_song_plan(plan)
            choices.set_end(REPEAT_AND_FADE)
            last = len(choices.section_kinds_in_form()) - 1
            self.assertEqual((choices.fade_way(FIRST), choices.fade_way(A_VERSE), choices.fade_way(last)), (FADE_IN, None, FADE_OUT))
            self.assertNotIn(FADES, choices.section_own_fields(A_VERSE))
            with self.assertRaises(ValueError):
                choices.set_section_own(place=A_VERSE, field=FADES, value=True)
            # A fade in rises from silence over the whole section until it is given a velocity and its bars.
            self.assertEqual(choices.fade_fields(FIRST), [FADES])
            choices.set_section_own(place=FIRST, field=FADES, value=True)
            self.assertEqual(choices.fade_fields(FIRST), [FADES, FADE_LEVEL, FADE_OVER])
            self.assertEqual(choices.section_from_plan(place=FIRST, field=FADE_LEVEL), FADED)
            self.assertEqual(choices.section_from_plan(place=FIRST, field=FADE_OVER), choices.section_bars(FIRST))
            scene = made(choices).get_song(A_NAME).get_scenes()[FIRST].to_data()
            self.assertEqual(scene[VelocitySetting.IN_START], FADED)
            self.assertGreater(scene[VelocitySetting.LEVEL], FADED)
            self.assertEqual(scene[VelocitySetting.IN_OVER], choices.section_bars(FIRST))
            choices.set_section_own(place=FIRST, field=FADE_LEVEL, value=HALF_VELOCITY)
            choices.set_section_own(place=FIRST, field=FADE_OVER, value=TWO_BARS)
            scene = made(choices).get_song(A_NAME).get_scenes()[FIRST].to_data()
            self.assertEqual(scene[VelocitySetting.IN_START], HALF_VELOCITY)
            self.assertEqual(scene[VelocitySetting.IN_OVER], TWO_BARS)
            with self.assertRaises(ValueError):
                choices.set_section_own(place=FIRST, field=FADE_OVER, value=choices.section_bars(FIRST) + 1)
            with self.assertRaises(ValueError):
                choices.set_section_own(place=FIRST, field=FADE_LEVEL, value=UNFADED + 1)
            again = WizardChoices.from_data(choices.to_data())
            self.assertEqual(again.section_own(place=FIRST, field=FADE_OVER), TWO_BARS)
            # A fade out falls to its velocity over the whole section until it is given its bars, the last of the section.
            self.assertEqual(choices.fade_fields(last), [FADES, FADE_LEVEL, FADE_OVER])
            choices.set_section_own(place=last, field=FADE_LEVEL, value=HALF_VELOCITY)
            scene = made(choices).get_song(A_NAME).get_scenes()[last].to_data()
            self.assertEqual(scene[VelocitySetting.OUT_END], HALF_VELOCITY)
            self.assertEqual(scene[VelocitySetting.OUT_OVER], choices.section_bars(last))
            choices.set_section_own(place=last, field=FADE_OVER, value=1)
            self.assertEqual(made(choices).get_song(A_NAME).get_scenes()[last].to_data()[VelocitySetting.OUT_OVER], 1)
            choices.set_section_own(place=last, field=FADE_OVER, value=None)
            # A fade switched off keeps nothing of how it faded.
            choices.set_section_own(place=FIRST, field=FADES, value=False)
            self.assertIsNone(choices.section_own(place=FIRST, field=FADE_LEVEL))
            self.assertEqual(choices.fade_fields(FIRST), [FADES])
