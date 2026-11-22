# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a player as a person on the song wizard's player panels, and in the choices underneath: where the player comes in, where the player lays out, and how strongly the player answers to Energy."""

from llamatron.engine.generators.musician import schema
from llamatron.engine.generators.musician.model import MusicianSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.interface.tracker.screens.wizard.wizard_page import WizardPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels, messages
from llamatron.wizards.create_song import song_plan, wizard_limits, wizard_names
from tests.interface.tracker.test_tui_wizard import WizardTest
from tests.support.ui_testing import key_of
from tests.support.wizard_testing import made_data

A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_GENRE_OF_MACHINES = 'electronic'
A_SEED = 11
THE_BASS = 'bass'
THE_DRUMS = 'drums'
THE_VERSE = 1
THE_BRIDGE = 'bridge'
NOT_A_WAY = 'sideways'


class TestWizardPeople(WizardTest):
    """Comes in, Lays out and Reacts."""

    def chosen(self, *, genre=A_GENRE):
        choices = self.choices()
        choices.set_genre(genre)
        choices.set_subgenre(A_SUBGENRE if genre == A_GENRE else choices.subgenres()[0])
        choices.set_seed(A_SEED)
        return choices

    def plays(self, *, choices, role):
        form_choices = choices.get_song_form()
        song_form = form_choices
        return [role in choices.section(place).plays() for place in range(len(song_form.section_labels()))]

    def patterns(self, choices):
        return made_data(choices)[Section.PATTERNS]

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    async def to_player(self, role):
        choices = self.chosen()
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(choices.player(role).title())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    async def test_a_player_comes_in_where_asked_and_sits_out_every_section_before(self):
        choices = self.chosen()
        bass = choices.player(THE_BASS)
        bass_sections = bass.sections()
        self.assertEqual(bass_sections.get_comes_in(), wizard_limits.FROM_THE_START)
        self.assertEqual(bass_sections.comes_in_offered()[0], wizard_limits.FROM_THE_START)
        usual = self.patterns(choices)
        bass_sections.set_comes_in(wizard_limits.AFTER_FIRST_VERSE)
        self.assertEqual(bass_sections.get_comes_in(), wizard_limits.AFTER_FIRST_VERSE)
        played = self.plays(choices=choices, role=THE_BASS)
        self.assertEqual(played[:THE_VERSE + 2], [False] * (THE_VERSE + 1) + [True])
        self.assertNotEqual(self.patterns(choices), usual)
        bass_sections.set_comes_in(wizard_limits.AFTER_THE_INTRO)
        self.assertEqual(self.plays(choices=choices, role=THE_BASS)[:2], [False, True])
        again = type(choices).from_data(choices.to_data())
        self.assertEqual(again.player(THE_BASS).sections().get_comes_in(), wizard_limits.AFTER_THE_INTRO)

    async def test_a_player_lays_out_never_in_the_breakdowns_or_whenever_it_is_quiet(self):
        choices = self.chosen()
        form_choices = choices.get_song_form()
        song_form = form_choices
        bass = choices.player(THE_BASS)
        bass_sections = bass.sections()
        self.assertEqual(bass_sections.lays_out_offered(), [wizard_limits.NEVER_LAYS_OUT, wizard_limits.IN_BREAKDOWNS, wizard_limits.WHEN_QUIET])
        bridge = song_form.section_kinds_in_form().index(THE_BRIDGE)
        bass_sections.set_lays_out(wizard_limits.IN_BREAKDOWNS)
        self.assertEqual(bass_sections.get_lays_out(), wizard_limits.IN_BREAKDOWNS)
        self.assertFalse(self.plays(choices=choices, role=THE_BASS)[bridge])
        bass_sections.set_lays_out(wizard_limits.WHEN_QUIET)
        quiet = [place for place, energy in enumerate(choices.energies()) if energy <= 4 and place]
        self.assertTrue(quiet)
        self.assertFalse(any(self.plays(choices=choices, role=THE_BASS)[place] for place in quiet))
        bass_sections.set_lays_out(wizard_limits.NEVER_LAYS_OUT)
        self.assertTrue(self.plays(choices=choices, role=THE_BASS)[bridge])
        # A song with no plan has no quiet sections to name.
        choices.set_song_plan(False)
        self.assertNotIn(wizard_limits.WHEN_QUIET, bass_sections.lays_out_offered())

    async def test_sections_changed_one_by_one_read_as_the_person_s_own_and_what_is_no_way_is_refused(self):
        choices = self.chosen()
        bass = choices.player(THE_BASS)
        bass_sections = bass.sections()
        choices.section(THE_VERSE + 1).set_plays(role=THE_BASS, on=False)
        self.assertIsNone(bass_sections.get_lays_out())
        player = bass
        player_sections = player.sections()
        sections = player_sections
        for setter in (sections.set_comes_in, sections.set_lays_out):
            with self.assertRaises(ValueError):
                setter(NOT_A_WAY)
        for reacts in (wizard_names.LOWEST_ENERGY - 1, wizard_names.HIGHEST_ENERGY + 1, True):
            with self.assertRaises(ValueError):
                bass.set_reacts(reacts)

    async def test_a_dramatic_player_and_an_even_one_play_a_planned_song_differently(self):
        choices = self.chosen()
        drums = choices.player(THE_DRUMS)
        self.assertEqual(drums.get_reacts(), song_plan.USUAL_CONTRAST)
        made = {}
        for reacts in (wizard_names.LOWEST_ENERGY, song_plan.USUAL_CONTRAST, wizard_names.HIGHEST_ENERGY):
            drums.set_reacts(reacts)
            self.assertEqual(drums.get_reacts(), reacts)
            made[reacts] = self.patterns(choices)
        self.assertNotEqual(made[wizard_names.LOWEST_ENERGY], made[wizard_names.HIGHEST_ENERGY])
        self.assertNotEqual(made[song_plan.USUAL_CONTRAST], made[wizard_names.HIGHEST_ENERGY])
        # With no song plan there is no Energy to answer to, and so nothing for Reacts to change.
        unplanned = self.chosen()
        unplanned.set_song_plan(False)
        self.assertFalse(unplanned.player(THE_DRUMS).reacts())

    async def test_the_player_s_panel_shows_the_three_and_steps_them(self):
        choices = await self.to_player(THE_BASS)
        form_choices = choices.get_song_form()
        bass = choices.player(THE_BASS)
        bass_sections = bass.sections()
        song_form = form_choices
        shown = self.text()
        for said in (labels.MSG_WIZARD_COMES_IN_LABEL, labels.MSG_WIZARD_LAYS_OUT_LABEL, labels.MSG_WIZARD_REACTS_LABEL, wizard_limits.FROM_THE_START, wizard_limits.NEVER_LAYS_OUT, labels.MSG_WIZARD_REACTS_SAID[song_plan.USUAL_CONTRAST]):
            self.assertIn(said, shown)
        await self.select_field(labels.MSG_WIZARD_COMES_IN_LABEL)
        await self.press(self.more())
        self.assertEqual(bass_sections.get_comes_in(), bass_sections.comes_in_offered()[1])
        await self.select_field(labels.MSG_WIZARD_LAYS_OUT_LABEL)
        await self.press(self.more())
        self.assertEqual(bass_sections.get_lays_out(), wizard_limits.IN_BREAKDOWNS)
        await self.select_field(labels.MSG_WIZARD_REACTS_LABEL)
        await self.press(self.more())
        self.assertEqual(bass.get_reacts(), song_plan.USUAL_CONTRAST + 1)
        self.assertTrue(self.wizard().has_choices_to_lose())
        choices.section(len(song_form.section_labels()) - 2).set_plays(role=THE_BASS, on=False)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(labels.MSG_WIZARD_OWN_START, self.text())


class TestWizardEditPlayer(WizardTest):
    """The player panel's Edit Player button and the Musician page it opens on the player's Musician."""

    chosen = TestWizardPeople.chosen
    to_player = TestWizardPeople.to_player

    async def test_edit_player_opens_the_musician_page_and_what_is_chosen_there_is_kept(self):
        choices = await self.to_player(THE_BASS)
        bass = choices.player(THE_BASS)
        self.assertIsNone(bass.get_musician())
        await self.select_field(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PluginEditor)
        self.assertTrue(self.app.is_drafting())
        self.assertEqual(self.app.screen.item, bass.musician_name())
        self.app.screen.store(setting=MusicianSetting.LOUDNESS, value=schema.LOUDEST)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertFalse(self.app.is_drafting())
        self.assertEqual(bass.get_musician()[MusicianSetting.LOUDNESS], schema.LOUDEST)
        self.assertNotIn(MusicianSetting.TUNE_FROM, bass.get_musician())
        self.assertIn(messages.MSG_WIZARD_PLAYER_KEPT, self.text())
        self.assertIn(labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON, self.text())

    async def test_a_page_closed_with_nothing_changed_keeps_the_usual_player(self):
        choices = await self.to_player(THE_BASS)
        bass = choices.player(THE_BASS)
        await self.select_field(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON)
        await self.press(Key.ENTER, Key.ESCAPE)
        self.assertIn(messages.MSG_WIZARD_PLAYER_UNCHANGED, self.text())
        self.assertIsNone(bass.get_musician())

    async def test_clearing_gives_the_player_back_the_usual_musician(self):
        choices = await self.to_player(THE_BASS)
        bass = choices.player(THE_BASS)
        bass.set_musician(settings={MusicianSetting.LOUDNESS: schema.LOUDEST})
        await self.press(Key.DOWN, Key.UP)
        await self.select_field(labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsNone(bass.get_musician())
        self.assertIn(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON, self.text())
        self.assertNotIn(labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON, self.text())

    async def test_a_genre_of_machines_has_no_edit_player_button(self):
        choices = self.chosen(genre=A_GENRE_OF_MACHINES)
        band_choices = choices.get_band()
        band = band_choices
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(choices.player(band.roles_in()[0]).title())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertNotIn(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON, self.text())
