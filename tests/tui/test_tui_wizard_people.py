# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a player as a person on the song wizard's player panels, and in the choices underneath: where the player comes in, where the player lays out, and how strongly the player answers to Energy."""

from llamatron.engine.generators.musician import generator as musician
from llamatron.engine.generators.musician.model import MusicianSetting
from llamatron.model.file import version
from llamatron.model.schema.file_format import Section
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.musician_editor import MusicianEditor
from llamatron.tui.screens.wizard.wizard_page import WizardPage
from llamatron.user_strings import labels, messages
from llamatron.wizards.create_song import song_plan, wizard_limits
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_NAME = 'made'
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
        return [role in choices.section(place).plays() for place in range(len(choices.get_song_form().section_labels()))]

    def patterns(self, choices):
        return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]

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
        self.assertEqual(choices.player(THE_BASS).get_comes_in(), wizard_limits.FROM_THE_START)
        self.assertEqual(choices.player(THE_BASS).comes_in_offered()[0], wizard_limits.FROM_THE_START)
        usual = self.patterns(choices)
        choices.player(THE_BASS).set_comes_in(wizard_limits.AFTER_FIRST_VERSE)
        self.assertEqual(choices.player(THE_BASS).get_comes_in(), wizard_limits.AFTER_FIRST_VERSE)
        played = self.plays(choices=choices, role=THE_BASS)
        self.assertEqual(played[:THE_VERSE + 2], [False] * (THE_VERSE + 1) + [True])
        self.assertNotEqual(self.patterns(choices), usual)
        choices.player(THE_BASS).set_comes_in(wizard_limits.AFTER_THE_INTRO)
        self.assertEqual(self.plays(choices=choices, role=THE_BASS)[:2], [False, True])
        again = type(choices).from_data(choices.to_data())
        self.assertEqual(again.player(THE_BASS).get_comes_in(), wizard_limits.AFTER_THE_INTRO)

    async def test_a_player_lays_out_never_in_the_breakdowns_or_whenever_it_is_quiet(self):
        choices = self.chosen()
        self.assertEqual(choices.player(THE_BASS).lays_out_offered(), [wizard_limits.NEVER_LAYS_OUT, wizard_limits.IN_BREAKDOWNS, wizard_limits.WHEN_QUIET])
        bridge = choices.get_song_form().section_kinds_in_form().index(THE_BRIDGE)
        choices.player(THE_BASS).set_lays_out(wizard_limits.IN_BREAKDOWNS)
        self.assertEqual(choices.player(THE_BASS).get_lays_out(), wizard_limits.IN_BREAKDOWNS)
        self.assertFalse(self.plays(choices=choices, role=THE_BASS)[bridge])
        choices.player(THE_BASS).set_lays_out(wizard_limits.WHEN_QUIET)
        quiet = [place for place, energy in enumerate(choices.energies()) if energy <= 4 and place]
        self.assertTrue(quiet)
        self.assertFalse(any(self.plays(choices=choices, role=THE_BASS)[place] for place in quiet))
        choices.player(THE_BASS).set_lays_out(wizard_limits.NEVER_LAYS_OUT)
        self.assertTrue(self.plays(choices=choices, role=THE_BASS)[bridge])
        # A song with no plan has no quiet sections to name.
        choices.set_song_plan(False)
        self.assertNotIn(wizard_limits.WHEN_QUIET, choices.player(THE_BASS).lays_out_offered())

    async def test_sections_changed_one_by_one_read_as_the_person_s_own_and_what_is_no_way_is_refused(self):
        choices = self.chosen()
        choices.section(THE_VERSE + 1).set_plays(role=THE_BASS, on=False)
        self.assertIsNone(choices.player(THE_BASS).get_lays_out())
        player = choices.player(THE_BASS)
        for setter in (player.set_comes_in, player.set_lays_out):
            with self.assertRaises(ValueError):
                setter(NOT_A_WAY)
        for reacts in (song_plan.LOWEST_ENERGY - 1, song_plan.HIGHEST_ENERGY + 1, True):
            with self.assertRaises(ValueError):
                choices.player(THE_BASS).set_reacts(reacts)

    async def test_a_dramatic_player_and_an_even_one_play_a_planned_song_differently(self):
        choices = self.chosen()
        self.assertEqual(choices.player(THE_DRUMS).get_reacts(), song_plan.USUAL_CONTRAST)
        made = {}
        for reacts in (song_plan.LOWEST_ENERGY, song_plan.USUAL_CONTRAST, song_plan.HIGHEST_ENERGY):
            choices.player(THE_DRUMS).set_reacts(reacts)
            self.assertEqual(choices.player(THE_DRUMS).get_reacts(), reacts)
            made[reacts] = self.patterns(choices)
        self.assertNotEqual(made[song_plan.LOWEST_ENERGY], made[song_plan.HIGHEST_ENERGY])
        self.assertNotEqual(made[song_plan.USUAL_CONTRAST], made[song_plan.HIGHEST_ENERGY])
        # With no song plan there is no Energy to answer to, and so nothing for Reacts to change.
        unplanned = self.chosen()
        unplanned.set_song_plan(False)
        self.assertFalse(unplanned.player(THE_DRUMS).reacts())

    async def test_the_player_s_panel_shows_the_three_and_steps_them(self):
        choices = await self.to_player(THE_BASS)
        shown = self.text()
        for said in (labels.MSG_WIZARD_COMES_IN_LABEL, labels.MSG_WIZARD_LAYS_OUT_LABEL, labels.MSG_WIZARD_REACTS_LABEL, wizard_limits.FROM_THE_START, wizard_limits.NEVER_LAYS_OUT, labels.MSG_WIZARD_REACTS_SAID[song_plan.USUAL_CONTRAST]):
            self.assertIn(said, shown)
        await self.select_field(labels.MSG_WIZARD_COMES_IN_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.player(THE_BASS).get_comes_in(), choices.player(THE_BASS).comes_in_offered()[1])
        await self.select_field(labels.MSG_WIZARD_LAYS_OUT_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.player(THE_BASS).get_lays_out(), wizard_limits.IN_BREAKDOWNS)
        await self.select_field(labels.MSG_WIZARD_REACTS_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.player(THE_BASS).get_reacts(), song_plan.USUAL_CONTRAST + 1)
        self.assertTrue(self.wizard().has_choices_to_lose())
        choices.section(len(choices.get_song_form().section_labels()) - 2).set_plays(role=THE_BASS, on=False)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(labels.MSG_WIZARD_OWN_START, self.text())


class TestWizardEditPlayer(WizardTest):
    """The player panel's Edit Player button and the Musician page it opens on the player's Musician."""

    chosen = TestWizardPeople.chosen
    to_player = TestWizardPeople.to_player

    async def test_edit_player_opens_the_musician_page_and_what_is_chosen_there_is_kept(self):
        choices = await self.to_player(THE_BASS)
        self.assertIsNone(choices.player(THE_BASS).get_musician())
        await self.select_field(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MusicianEditor)
        self.assertTrue(self.app.is_drafting())
        self.assertEqual(self.app.screen.item, choices.player(THE_BASS).musician_name())
        self.app.screen.store(setting=MusicianSetting.LOUDNESS, value=musician.LOUDEST)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, WizardPage)
        self.assertFalse(self.app.is_drafting())
        self.assertEqual(choices.player(THE_BASS).get_musician()[MusicianSetting.LOUDNESS], musician.LOUDEST)
        self.assertNotIn(MusicianSetting.TUNE_FROM, choices.player(THE_BASS).get_musician())
        self.assertIn(messages.MSG_WIZARD_PLAYER_KEPT, self.text())
        self.assertIn(labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON, self.text())

    async def test_a_page_closed_with_nothing_changed_keeps_the_usual_player(self):
        choices = await self.to_player(THE_BASS)
        await self.select_field(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON)
        await self.press(Key.ENTER, Key.ESCAPE)
        self.assertIn(messages.MSG_WIZARD_PLAYER_UNCHANGED, self.text())
        self.assertIsNone(choices.player(THE_BASS).get_musician())

    async def test_clearing_gives_the_player_back_the_usual_musician(self):
        choices = await self.to_player(THE_BASS)
        choices.player(THE_BASS).set_musician(settings={MusicianSetting.LOUDNESS: musician.LOUDEST})
        await self.press(Key.DOWN, Key.UP)
        await self.select_field(labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertIsNone(choices.player(THE_BASS).get_musician())
        self.assertIn(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON, self.text())
        self.assertNotIn(labels.MSG_WIZARD_EDIT_OWN_PLAYER_BUTTON, self.text())

    async def test_a_genre_of_machines_has_no_edit_player_button(self):
        choices = self.chosen(genre=A_GENRE_OF_MACHINES)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(choices.player(choices.get_band().roles_in()[0]).title())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertNotIn(labels.MSG_WIZARD_EDIT_PLAYER_BUTTON, self.text())
