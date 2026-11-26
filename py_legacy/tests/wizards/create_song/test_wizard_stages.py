# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of how a song of the wizard's starts and ends: each way's stages as sections of their own, the first player, the setup's bars, and a section that fades."""

import unittest

from llamatron.model.schema.file_format import Section, VelocitySetting
from llamatron.wizards.create_song import wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import style_names
from llamatron.wizards.create_song.wizard_choices import WizardChoices
from tests.support import wizard_testing
from tests.support.wizard_testing import made_set

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
# A ramp's ends are percentages of the scene's velocity.
PERCENT = 100
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
    return made_set(choices)


class TestWizardStarts(unittest.TestCase):
    """How a song starts."""

    __slots__ = ()

    def test_a_song_starts_with_the_full_band_until_asked_and_every_way_offered_is_a_way(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        self.assertEqual(song_form.get_start(), wizard_limits.FULL_BAND)
        self.assertEqual(song_form.starts(), list(wizard_limits.STARTS))
        self.assertEqual(WizardChoices().get_song_form().starts(), [])

    def test_each_way_puts_its_stages_before_the_first_verse_and_leaves_the_rest_alone(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        body = song_form.section_kinds_in_form()[1:]
        players = song_form.first_players()
        expected = {wizard_limits.STRAIGHT_IN: [], wizard_limits.FULL_BAND: [players], wizard_limits.DRUMS_FIRST: [[THE_DRUMS], players], wizard_limits.DRUM_FILL_IN: [[THE_DRUMS]]}
        for way, stages in expected.items():
            song_form.set_start(way)
            self.assertEqual(song_form.get_start(), way)
            self.assertEqual(song_form.section_kinds_in_form(), [THE_INTRO] * len(stages) + body)
            self.assertEqual([sorted(choices.section(place).plays()) for place in range(len(stages))], [sorted(stage) for stage in stages])
            made(choices)

    def test_layers_bring_the_players_in_one_at_a_time_the_first_player_first(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        first_section = choices.section(FIRST)
        song_form = form_choices
        song_form.set_start(wizard_limits.LAYERS)
        count = len(song_form.first_players())
        first = song_form.get_first_player()
        self.assertNotEqual(first, THE_DRUMS)
        self.assertEqual([len(choices.section(place).plays()) for place in range(count)], list(range(1, count + 1)))
        self.assertEqual(first_section.plays(), [first])
        song_form.set_first_player(THE_BASS)
        self.assertEqual(first_section.plays(), [THE_BASS])
        self.assertEqual(song_form.get_start(), wizard_limits.LAYERS)
        song_form.set_start(wizard_limits.ONE_PLAYER_FIRST)
        self.assertEqual(first_section.plays(), [THE_BASS])
        self.assertEqual(sorted(choices.section(FIRST + 1).plays()), sorted(song_form.first_players()))

    def test_the_setup_s_bars_are_the_length_of_every_stage(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        first_section = choices.section(FIRST)
        song_form = form_choices
        song_form.set_start(wizard_limits.DRUMS_FIRST)
        usual = song_form.get_setup_bars()
        for bars in song_form.setup_bars_offered():
            song_form.set_setup_bars(bars)
            self.assertEqual(first_section.bars(), bars)
            self.assertEqual(song_form.get_start(), wizard_limits.DRUMS_FIRST)
        self.assertIn(usual, song_form.setup_bars_offered())
        with self.assertRaises(ValueError):
            song_form.set_setup_bars(NOT_BARS)

    def test_a_drum_fill_in_is_the_drums_alone_leaving_with_a_big_fill_and_needs_a_plan(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        choices.set_song_plan(False)
        self.assertNotIn(wizard_limits.DRUM_FILL_IN, song_form.starts())
        with self.assertRaises(ValueError):
            song_form.set_start(wizard_limits.DRUM_FILL_IN)

    def test_opening_sections_a_person_changed_read_as_nobody_s_way_and_a_new_way_replaces_them(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        first_section = choices.section(FIRST)
        song_form = form_choices
        song_form.set_start(wizard_limits.DRUMS_FIRST)
        first_section.set_plays(role=THE_BASS, on=True)
        self.assertIsNone(song_form.get_start())
        song_form.set_start(wizard_limits.FULL_BAND)
        self.assertEqual(song_form.section_kinds_in_form().count(THE_INTRO), 1)

    def test_what_is_not_a_way_or_a_player_is_refused_and_the_ways_are_kept_with_the_choices(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        for setter in (song_form.set_start, song_form.set_end, song_form.set_first_player):
            with self.assertRaises(ValueError):
                setter(NOT_A_WAY)
        song_form.set_start(wizard_limits.LAYERS)
        song_form.set_end(wizard_limits.STRIPS_DOWN)
        song_form.set_first_player(THE_BASS)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual((again.get_song_form().get_start(), again.get_song_form().get_end(), again.get_song_form().get_first_player()), (wizard_limits.LAYERS, wizard_limits.STRIPS_DOWN, THE_BASS))
        self.assertEqual(made(again).to_data()[Section.PATTERNS], made(choices).to_data()[Section.PATTERNS])
        # Another form keeps how the song was chosen to start and to end, and who starts alone.
        song_form.set_form(song_form.forms()[-1])
        self.assertEqual((song_form.get_start(), song_form.get_end(), song_form.get_first_player()), (wizard_limits.LAYERS, wizard_limits.STRIPS_DOWN, THE_BASS))

    def test_another_form_keeps_how_the_song_starts_and_ends_and_a_form_chosen_with_neither_is_the_forms_own(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        another = next(form for form in song_form.forms() if form != song_form.get_form())
        song_form.set_start(wizard_limits.LAYERS)
        song_form.set_end(wizard_limits.STRIPS_DOWN)
        song_form.set_setup_bars(song_form.setup_bars_offered()[-1])
        bars = song_form.get_setup_bars()
        song_form.set_form(another)
        self.assertEqual(song_form.get_form(), another)
        self.assertEqual((song_form.get_start(), song_form.get_end(), song_form.get_setup_bars()), (wizard_limits.LAYERS, wizard_limits.STRIPS_DOWN, bars))
        made(choices)
        plain = chosen()
        plain.get_song_form().set_form(another)
        self.assertFalse(plain.get_song_form().has_own_form())
        self.assertEqual((plain.get_song_form().get_start(), plain.get_song_form().get_end()), (wizard_limits.FULL_BAND, chosen().get_song_form().get_end()))
        body = plain.get_song_form().section_kinds_in_form()[1:-1]
        kinds = song_form.section_kinds_in_form()
        self.assertEqual([kind for kind in kinds if kind in body], body)

    def test_every_way_of_every_subgenre_makes_a_song(self):
        for genre in style_names():
            for subgenre in subgenres_of(genre):
                choices = chosen(genre=genre, subgenre=subgenre)
                form_choices = choices.get_song_form()
                song_form = form_choices
                for way in song_form.starts():
                    with self.subTest(subgenre=subgenre, start=way):
                        song_form.set_start(way)
                        self.assertEqual(song_form.get_start(), way)
                for way in song_form.ends():
                    with self.subTest(subgenre=subgenre, end=way):
                        song_form.set_end(way)
                        self.assertEqual(song_form.get_end(), way)
                made(choices)


class TestWizardEnds(unittest.TestCase):
    """How a song ends."""

    __slots__ = ()

    def test_a_song_ends_on_its_form_s_ending_until_asked(self):
        self.assertEqual(chosen().get_song_form().get_end(), wizard_limits.HELD_CHORD)
        self.assertEqual(chosen().get_song_form().ends(), list(wizard_limits.ENDS))
        dance = chosen(genre=AN_ELECTRONIC_GENRE, subgenre=A_DANCE_SUBGENRE)
        self.assertIn(dance.get_song_form().get_end(), dance.get_song_form().ends())
        self.assertNotEqual(dance.get_song_form().get_end(), wizard_limits.HELD_CHORD)

    def test_each_way_puts_its_stages_after_the_last_chorus(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        body = song_form.section_kinds_in_form()[:-1]
        count = len(song_form.first_players())
        expected = {wizard_limits.HARD_STOP: [], wizard_limits.HELD_CHORD: [THE_ENDING], wizard_limits.SLOWS_DOWN: [wizard_limits.OUTRO_KIND, THE_ENDING], wizard_limits.ONE_PLAYER_ALONE: [wizard_limits.OUTRO_KIND, THE_ENDING], wizard_limits.REPEAT_AND_FADE: [wizard_limits.OUTRO_KIND],
                    wizard_limits.STRIPS_DOWN: [wizard_limits.OUTRO_KIND] * (count - 1) + [THE_ENDING]}
        for way, stages in expected.items():
            song_form.set_end(way)
            self.assertEqual(song_form.get_end(), way)
            self.assertEqual(song_form.section_kinds_in_form(), body + stages)
            made(choices)

    def test_slowing_down_ends_slower_stripping_down_loses_a_player_a_stage_and_a_fade_grows_softer(self):
        choices = chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        last = len(song_form.section_kinds_in_form())
        song_form.set_end(wizard_limits.SLOWS_DOWN)
        self.assertLess(choices.section(last - 1).own(field=wizard_names.TEMPO_END_OF_PLACE), choices.get_tempo())
        song_form.set_end(wizard_limits.STRIPS_DOWN)
        stages = range(last - 1, len(song_form.section_kinds_in_form()) - 1)
        counts = [len(choices.section(place).plays()) for place in stages]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(choices.section(stages[-1]).plays(), [song_form.get_first_player()])
        song_form.set_end(wizard_limits.REPEAT_AND_FADE)
        self.assertTrue(choices.section(last - 1).own(field=wizard_names.SONG_PLAN_FADES))
        scene = made(choices).get_song(wizard_testing.SONG_NAME).get_scenes()[last - 1]
        self.assertEqual(scene.to_data()[VelocitySetting.OUT_END], wizard_names.FADED)

    def test_an_opening_section_fades_in_and_a_closing_one_fades_out_with_or_without_a_plan_and_no_other_fades(self):
        for plan in (True, False):
            choices = chosen()
            form_choices = choices.get_song_form()
            song_form = form_choices
            verse_section = choices.section(A_VERSE)
            verse_section_fade = verse_section.fade()
            first_section = choices.section(FIRST)
            first_section_fade = first_section.fade()
            choices.set_song_plan(plan)
            song_form.set_end(wizard_limits.REPEAT_AND_FADE)
            last = len(song_form.section_kinds_in_form()) - 1
            section = choices.section(last)
            section_fade = section.fade()
            self.assertEqual((first_section_fade.way(), verse_section_fade.way(), section_fade.way()), (wizard_limits.FADE_IN, None, wizard_limits.FADE_OUT))
            self.assertNotIn(wizard_names.SONG_PLAN_FADES, verse_section.own_fields())
            with self.assertRaises(ValueError):
                verse_section.set_own(field=wizard_names.SONG_PLAN_FADES, value=True)
            # A fade in rises from silence over the whole section until it is given a velocity and its bars.
            self.assertEqual(first_section_fade.fields(), [wizard_names.SONG_PLAN_FADES])
            first_section.set_own(field=wizard_names.SONG_PLAN_FADES, value=True)
            self.assertEqual(first_section_fade.fields(), [wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER])
            self.assertEqual(first_section.from_plan(field=wizard_names.FADE_LEVEL), wizard_names.FADED)
            self.assertEqual(first_section.from_plan(field=wizard_names.FADE_OVER), first_section.bars())
            scene = made(choices).get_song(wizard_testing.SONG_NAME).get_scenes()[FIRST].to_data()
            self.assertEqual(scene[VelocitySetting.IN_START], wizard_names.FADED)
            self.assertGreater(scene[VelocitySetting.LEVEL], wizard_names.FADED)
            self.assertEqual(scene[VelocitySetting.IN_OVER], first_section.bars())
            first_section.set_own(field=wizard_names.FADE_LEVEL, value=HALF_VELOCITY)
            first_section.set_own(field=wizard_names.FADE_OVER, value=TWO_BARS)
            scene = made(choices).get_song(wizard_testing.SONG_NAME).get_scenes()[FIRST].to_data()
            # The fade's level is written as a percentage of the scene's own velocity.
            self.assertEqual(scene[VelocitySetting.IN_START], round(HALF_VELOCITY * PERCENT / scene[VelocitySetting.LEVEL]))
            self.assertEqual(scene[VelocitySetting.IN_OVER], TWO_BARS)
            with self.assertRaises(ValueError):
                first_section.set_own(field=wizard_names.FADE_OVER, value=first_section.bars() + 1)
            with self.assertRaises(ValueError):
                first_section.set_own(field=wizard_names.FADE_LEVEL, value=wizard_names.UNFADED + 1)
            again = WizardChoices.from_data(choices.to_data())
            self.assertEqual(again.section(FIRST).own(field=wizard_names.FADE_OVER), TWO_BARS)
            # A fade out falls to its velocity over the whole section until it is given its bars, the last of the section.
            self.assertEqual(section_fade.fields(), [wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER])
            section.set_own(field=wizard_names.FADE_LEVEL, value=HALF_VELOCITY)
            scene = made(choices).get_song(wizard_testing.SONG_NAME).get_scenes()[last].to_data()
            self.assertEqual(scene[VelocitySetting.OUT_END], round(HALF_VELOCITY * PERCENT / scene[VelocitySetting.LEVEL]))
            self.assertEqual(scene[VelocitySetting.OUT_OVER], section.bars())
            section.set_own(field=wizard_names.FADE_OVER, value=1)
            self.assertEqual(made(choices).get_song(wizard_testing.SONG_NAME).get_scenes()[last].to_data()[VelocitySetting.OUT_OVER], 1)
            section.set_own(field=wizard_names.FADE_OVER, value=None)
            # A fade switched off keeps nothing of how it faded.
            first_section.set_own(field=wizard_names.SONG_PLAN_FADES, value=False)
            self.assertIsNone(first_section.own(field=wizard_names.FADE_LEVEL))
            self.assertEqual(first_section_fade.fields(), [wizard_names.SONG_PLAN_FADES])
