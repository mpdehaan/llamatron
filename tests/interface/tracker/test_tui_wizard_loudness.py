# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests of how loud a player is on the song wizard's player panels: the Dynamics gauge and the levels under the Loudness heading."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.user_strings import labels as labels_text, marks
from llamatron.wizards.create_song import loudness, wizard_names
from tests.interface.tracker.test_tui_wizard import WizardTest
from tests.support.ui_testing import key_of

A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
A_SEED = 11
THE_BASS = 'bass'
THE_LEAD = 'lead'


class TestWizardLoudnessFields(WizardTest):
    """Dynamics and the Loudness heading on a player's panel."""

    def chosen(self):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        return choices

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    def labels(self):
        return [field.label for field in self.wizard().shown_fields()]

    async def to_player(self, role):
        choices = self.chosen()
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(choices.player(role).title())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    async def test_dynamics_is_a_gauge_that_steps(self):
        choices = await self.to_player(THE_LEAD)
        lead = choices.player(THE_LEAD)
        lead_loudness = lead.loudness()
        self.assertIn(labels_text.MSG_WIZARD_DYNAMICS_SAID[loudness.USUAL_DYNAMICS], self.text())
        await self.select_field(labels_text.MSG_WIZARD_DYNAMICS_LABEL)
        await self.press(self.more())
        self.assertEqual(lead_loudness.get_dynamics(), loudness.USUAL_DYNAMICS + 1)
        self.assertIn(labels_text.MSG_WIZARD_DYNAMICS_SAID[loudness.USUAL_DYNAMICS + 1], self.text())
        self.assertEqual(self.wizard().label_under_cursor(), labels_text.MSG_WIZARD_DYNAMICS_LABEL)

    async def test_the_loudness_heading_is_closed_until_opened_and_shows_the_levels_the_player_plays(self):
        choices = await self.to_player(THE_LEAD)
        lead = choices.player(THE_LEAD)
        lead_loudness = lead.loudness()
        self.assertIn(labels_text.MSG_WIZARD_GROUP_LOUDNESS, self.labels())
        self.assertNotIn(labels_text.MSG_WIZARD_LEVEL_LABELS[wizard_names.NORMAL], self.labels())
        await self.select_field(labels_text.MSG_WIZARD_LEVEL_LABELS[wizard_names.NORMAL])
        offered = lead_loudness.levels_offered()
        # The levels are the last settings of the panel, with only the panel's button after them.
        after_heading = self.labels()[self.labels().index(labels_text.MSG_WIZARD_GROUP_LOUDNESS) + 1:]
        self.assertEqual(after_heading, [*(labels_text.MSG_WIZARD_LEVEL_LABELS[level] for level in offered), labels_text.MSG_WIZARD_EDIT_PLAYER_BUTTON])
        self.assertNotIn(labels_text.MSG_WIZARD_LEVEL_LABELS[wizard_names.GHOST], self.labels())
        self.assertIn(marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=lead_loudness.levels()[wizard_names.NORMAL]), self.text())

    async def test_a_level_steps_to_the_songs_own_and_backspace_gives_it_back_to_the_genre(self):
        choices = await self.to_player(THE_LEAD)
        lead = choices.player(THE_LEAD)
        lead_loudness = lead.loudness()
        usual = lead_loudness.levels()
        await self.select_field(labels_text.MSG_WIZARD_LEVEL_LABELS[wizard_names.ACCENT])
        await self.press(self.more())
        self.assertTrue(lead_loudness.level_is_own(level=wizard_names.ACCENT))
        self.assertEqual(lead_loudness.levels()[wizard_names.ACCENT], usual[wizard_names.ACCENT] + 1)
        self.assertNotIn(marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=usual[wizard_names.ACCENT] + 1), self.text())
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertFalse(lead_loudness.level_is_own(level=wizard_names.ACCENT))
        self.assertEqual(lead_loudness.levels(), usual)

    async def test_the_normal_level_carries_the_accent_shown_with_it(self):
        choices = await self.to_player(THE_BASS)
        bass = choices.player(THE_BASS)
        bass_loudness = bass.loudness()
        await self.select_field(labels_text.MSG_WIZARD_LEVEL_LABELS[wizard_names.NORMAL])
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        levels = bass_loudness.levels()
        self.assertEqual(levels[wizard_names.ACCENT] - levels[wizard_names.NORMAL], loudness.ACCENT_ABOVE)
        self.assertTrue(self.wizard().has_choices_to_lose())
