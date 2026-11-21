# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the song wizard's Form panel fields for how a song starts and ends, and a section's Fades."""

from llamatron.song_wizard import song_plan, wizard_limits
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.wizard.section_branch import SectionBranch
from llamatron.user_strings import labels
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
THE_BASS = 'bass'
FIRST = 0
A_VERSE = 'verse-1'
A_VERSE_PLACE = 1
THE_INTRO = 'intro'
THE_INTRO_PLACE = 0

# The attribute a field keeps its label in.
LABEL = 'label'


class TestWizardStages(WizardTest):
    """Starts with, Ends with, First player and Setup bars on the Form panel."""

    async def to_form(self):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(labels.MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    async def test_a_closing_section_s_fade_out_has_a_velocity_and_bars_of_its_own(self):
        choices = await self.to_form()
        choices.get_song_form().set_end(wizard_limits.REPEAT_AND_FADE)
        await self.press(Key.DOWN, Key.UP)
        last = len(choices.get_song_form().section_kinds_in_form()) - 1
        self.assertEqual(choices.section(last).fade_way(), wizard_limits.FADE_OUT)
        branch = SectionBranch(page=self.wizard(), place=last)
        fade = labels.MSG_WIZARD_FADE_LABELS[wizard_limits.FADE_OUT]
        self.assertEqual([branch.fade_field(field).label for field in choices.section(last).fade_fields()], [fade[song_plan.FADES], fade[song_plan.FADE_LEVEL], fade[song_plan.FADE_OVER]])
        # Until given, the fade takes every bar of the section.
        self.assertEqual(branch.fade_field(song_plan.FADE_OVER).value(), labels.MSG_WIZARD_FADE_BARS.format(value=choices.section(last).bars()))

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    async def test_the_panel_shows_how_the_song_starts_and_ends_and_no_stage_fields_until_a_way_has_stages(self):
        choices = await self.to_form()
        shown = self.text()
        for said in (labels.MSG_WIZARD_STARTS_LABEL, labels.MSG_WIZARD_ENDS_LABEL, wizard_limits.FULL_BAND, wizard_limits.HELD_CHORD):
            self.assertIn(said, shown)
        for label in (labels.MSG_WIZARD_FIRST_PLAYER_LABEL, labels.MSG_WIZARD_SETUP_BARS_LABEL):
            self.assertNotIn(label, shown)
        self.assertEqual(choices.get_song_form().get_start(), wizard_limits.FULL_BAND)

    async def test_how_the_song_starts_and_ends_comes_before_the_form_on_the_panel(self):
        await self.to_form()
        shown = [getattr(field, LABEL, None) for field in self.wizard().shown_fields()]
        self.assertEqual(shown[:2], [labels.MSG_WIZARD_STARTS_LABEL, labels.MSG_WIZARD_ENDS_LABEL])
        self.assertLess(shown.index(labels.MSG_WIZARD_ENDS_LABEL), shown.index(labels.MSG_WIZARD_FORM_LABEL))

    async def test_stepping_starts_with_makes_the_stages_sections_of_the_tree(self):
        choices = await self.to_form()
        before = len(self.wizard().rows())
        await self.select_field(labels.MSG_WIZARD_STARTS_LABEL)
        offered = choices.get_song_form().starts()
        await self.press(*[self.more()] * offered.index(wizard_limits.DRUMS_FIRST))
        self.assertEqual(choices.get_song_form().get_start(), wizard_limits.DRUMS_FIRST)
        self.assertEqual(len(self.wizard().rows()), before + 1)
        self.assertIn(labels.MSG_WIZARD_SETUP_BARS_LABEL, self.text())
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_the_first_player_and_the_setup_s_bars_are_chosen_under_a_way_with_stages(self):
        choices = await self.to_form()
        choices.get_song_form().set_start(wizard_limits.LAYERS)
        choices.get_song_form().set_end(wizard_limits.SLOWS_DOWN)
        await self.press(Key.DOWN, Key.UP)
        await self.select_field(labels.MSG_WIZARD_FIRST_PLAYER_LABEL)
        first = choices.get_song_form().get_first_player()
        await self.press(self.more())
        self.assertNotEqual(choices.get_song_form().get_first_player(), first)
        self.assertEqual(choices.section(FIRST).plays(), [choices.get_song_form().get_first_player()])
        await self.select_field(labels.MSG_WIZARD_SETUP_BARS_LABEL)
        bars = choices.get_song_form().get_setup_bars()
        await self.press(self.more())
        self.assertGreater(choices.get_song_form().get_setup_bars(), bars)
        self.assertEqual(choices.section(FIRST).bars(), choices.get_song_form().get_setup_bars())

    async def test_opening_sections_a_person_changed_read_as_the_person_s_own(self):
        choices = await self.to_form()
        choices.get_song_form().set_start(wizard_limits.DRUMS_FIRST)
        choices.section(FIRST).set_plays(role=THE_BASS, on=True)
        await self.press(Key.DOWN, Key.UP)
        self.assertIsNone(choices.get_song_form().get_start())
        self.assertIn(labels.MSG_WIZARD_OWN_START, self.text())

    async def test_an_intro_s_fade_in_is_switched_on_its_panel_and_shows_its_velocity_and_bars(self):
        choices = await self.to_form()
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(THE_INTRO)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        fade = labels.MSG_WIZARD_FADE_LABELS[wizard_limits.FADE_IN]
        await self.select_field(fade[song_plan.FADES])
        self.assertNotIn(fade[song_plan.FADE_LEVEL], [field.label for field in self.app.screen.shown_fields()])
        await self.press(Key.SPACE)
        self.assertTrue(choices.section(THE_INTRO_PLACE).own(field=song_plan.FADES))
        self.assertIn(labels.MSG_WIZARD_FADE_VELOCITY.format(value=song_plan.FADED), self.text())
        await self.select_field(fade[song_plan.FADE_LEVEL])
        await self.press(keybindings.WizardPage.MORE)
        self.assertEqual(choices.section(THE_INTRO_PLACE).own(field=song_plan.FADE_LEVEL), song_plan.FADED + 1)
        await self.select_field(fade[song_plan.FADE_OVER])
        await self.press(keybindings.WizardPage.LESS)
        self.assertEqual(choices.section(THE_INTRO_PLACE).own(field=song_plan.FADE_OVER), choices.section(THE_INTRO_PLACE).bars() - 1)
        # A verse has no fade.
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(A_VERSE)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        labels_shown = [field.label for field in self.app.screen.fields()]
        self.assertNotIn(fade[song_plan.FADES], labels_shown)
        self.assertNotIn(labels.MSG_WIZARD_FADE_LABELS[wizard_limits.FADE_OUT][song_plan.FADES], labels_shown)
