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

"""Tests of the song wizard's Hooks panel in groups, and of the riff on it."""

from llamatron.strings.labels import (
    MSG_WIZARD_GROUP_HOOK_KIND, MSG_WIZARD_GROUP_HOOK_SAID, MSG_WIZARD_GROUP_RIFF, MSG_WIZARD_HOOK_NOTES_LABEL, MSG_WIZARD_HOOKS_BRANCH, MSG_WIZARD_NEW_RIFF_BUTTON, MSG_WIZARD_NOBODY,
    MSG_WIZARD_RIFF_NOTES_LABEL, MSG_WIZARD_RIFF_PLAYED_BY_LABEL, MSG_WIZARD_RIFF_SAID_LABEL,
)
from llamatron.strings.messages import MSG_WIZARD_RIFF_SAID
from llamatron.tui import keybindings
from llamatron.tui.dialogs.tune_dialog import TuneDialog
from llamatron.tui.keys import Key
from tests.support.ui_testing import forward_key, key_of
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
A_SEED = 11


class TestWizardRiffPanel(WizardTest):
    """The Hooks panel's groups and its Riff."""

    async def to_hooks(self):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    async def test_the_panel_keeps_the_hook_s_notes_on_top_and_groups_the_rest(self):
        await self.to_hooks()
        shown = self.text()
        for said in (MSG_WIZARD_HOOK_NOTES_LABEL, MSG_WIZARD_GROUP_HOOK_KIND, MSG_WIZARD_GROUP_HOOK_SAID, MSG_WIZARD_GROUP_RIFF):
            self.assertIn(said, shown)
        self.assertNotIn(MSG_WIZARD_RIFF_PLAYED_BY_LABEL, shown)

    async def test_a_riff_is_given_to_a_player_and_then_shows_where_it_is_played_its_notes_and_its_picture(self):
        choices = await self.to_hooks()
        await self.select_field(MSG_WIZARD_RIFF_PLAYED_BY_LABEL)
        self.assertIn(MSG_WIZARD_NOBODY, self.text())
        self.assertNotIn(MSG_WIZARD_RIFF_SAID_LABEL, self.text())
        await self.press(self.more())
        self.assertEqual(choices.get_riff_players(), choices.riff_players_offered()[0])
        shown = self.text()
        for said in (MSG_WIZARD_RIFF_SAID_LABEL, MSG_WIZARD_RIFF_NOTES_LABEL, MSG_WIZARD_NEW_RIFF_BUTTON, MSG_WIZARD_RIFF_SAID.format(players=choices.role_title(choices.get_riff_players()[0]))):
            self.assertIn(said, shown)
        self.assertTrue(self.wizard().has_choices_to_lose())
        await self.select_field(MSG_WIZARD_RIFF_SAID_LABEL)
        before = choices.get_riff_said()
        await self.press(self.more())
        self.assertNotEqual(choices.get_riff_said(), before)

    async def test_the_riff_s_notes_are_written_by_hand_given_back_and_made_again(self):
        choices = await self.to_hooks()
        choices.set_riff(players=choices.riff_players_offered()[-1])
        await self.press(Key.DOWN, Key.UP)
        usual = choices.riff_line()
        await self.select_field(MSG_WIZARD_RIFF_NOTES_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, TuneDialog)
        await self.press(forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.DONE)
        self.assertTrue(choices.riff_is_own())
        await self.select_field(MSG_WIZARD_RIFF_NOTES_LABEL)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertFalse(choices.riff_is_own())
        self.assertEqual(choices.riff_line(), usual)
        await self.select_field(MSG_WIZARD_NEW_RIFF_BUTTON)
        await self.press(Key.ENTER)
        self.assertNotEqual(choices.riff_line(), usual)
