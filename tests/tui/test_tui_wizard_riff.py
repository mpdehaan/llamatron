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

from llamatron.macro_composer.riffs import ACCENT_CHORDS, MUTED_ROOTS, RESTS_BETWEEN, RIFF_BETWEEN, RIFF_NOTES, RIFF_UNDER_TUNE, SINGLE_NOTES
from llamatron.strings import labels as labels_text, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs.tune_dialog import TuneDialog
from llamatron.tui.keys import Key
from tests.support.ui_testing import forward_key, key_of
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
A_SEED = 11
NEW_LINE = '\n'


class TestWizardRiffPanel(WizardTest):
    """The Hooks panel's groups and its Riff."""

    async def to_hooks(self, *, riff=False):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        if not riff:
            # A song with no riff until one is given: the riff the kind is built on is taken away.
            choices.set_riff(players=[])
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(labels_text.MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    def is_kick_row(self, line):
        """Whether a line of the screen is the kick's row of the riff's picture: the kick's name, then cells that end at a bar line."""
        return marks.MSG_WIZARD_HOOK_ROW.format(name=labels_text.MSG_WIZARD_RIFF_KICK_ROW, width=0, cells='') in line and line.strip().endswith(marks.MSG_WIZARD_HOOK_BAR_LINE)

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    async def test_the_panel_keeps_the_hook_s_notes_on_top_and_groups_the_rest(self):
        await self.to_hooks()
        shown = self.text()
        for said in (labels_text.MSG_WIZARD_HOOK_NOTES_LABEL, labels_text.MSG_WIZARD_GROUP_HOOK_KIND, labels_text.MSG_WIZARD_GROUP_HOOK_SAID, labels_text.MSG_WIZARD_GROUP_RIFF):
            self.assertIn(said, shown)
        self.assertNotIn(labels_text.MSG_WIZARD_RIFF_PLAYED_BY_LABEL, shown)

    async def test_a_riff_is_given_to_a_player_and_then_shows_where_it_is_played_its_notes_and_its_picture(self):
        choices = await self.to_hooks()
        await self.select_field(labels_text.MSG_WIZARD_RIFF_PLAYED_BY_LABEL)
        self.assertIn(labels_text.MSG_WIZARD_NOBODY, self.text())
        self.assertNotIn(labels_text.MSG_WIZARD_RIFF_SAID_LABEL, self.text())
        await self.press(self.more())
        self.assertEqual(choices.get_riff_players(), choices.riff_players_offered()[0])
        shown = self.text()
        for said in (labels_text.MSG_WIZARD_RIFF_SAID_LABEL, labels_text.MSG_WIZARD_RIFF_NOTES_LABEL, labels_text.MSG_WIZARD_NEW_RIFF_BUTTON, messages.MSG_WIZARD_RIFF_SAID.format(players=choices.role_title(choices.get_riff_players()[0]))):
            self.assertIn(said, shown)
        self.assertTrue(self.wizard().has_choices_to_lose())
        await self.select_field(labels_text.MSG_WIZARD_RIFF_SAID_LABEL)
        before = choices.get_riff_said()
        await self.press(self.more())
        self.assertNotEqual(choices.get_riff_said(), before)

    async def test_the_riff_s_notes_are_written_by_hand_given_back_and_made_again(self):
        choices = await self.to_hooks()
        choices.set_riff(players=choices.riff_players_offered()[-1])
        await self.press(Key.DOWN, Key.UP)
        usual = choices.riff_line()
        await self.select_field(labels_text.MSG_WIZARD_RIFF_NOTES_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, TuneDialog)
        await self.press(forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.DONE)
        self.assertTrue(choices.riff_is_own())
        await self.select_field(labels_text.MSG_WIZARD_RIFF_NOTES_LABEL)
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertFalse(choices.riff_is_own())
        self.assertEqual(choices.riff_line(), usual)
        await self.select_field(labels_text.MSG_WIZARD_NEW_RIFF_BUTTON)
        await self.press(Key.ENTER)
        self.assertNotEqual(choices.riff_line(), usual)

    async def test_hard_rock_s_riff_shows_its_settings_and_one_steps(self):
        choices = await self.to_hooks(riff=True)
        self.assertTrue(choices.has_riff())
        await self.select_field(labels_text.MSG_WIZARD_RIFF_SETTING_LABELS[RIFF_BETWEEN])
        labels = [field.label for field in self.wizard().shown_fields()]
        for field in choices.riff_settings_offered():
            self.assertIn(labels_text.MSG_WIZARD_RIFF_SETTING_LABELS[field], labels)
        self.assertIn(ACCENT_CHORDS, self.text())
        self.assertEqual(choices.get_riff_setting(RIFF_BETWEEN), MUTED_ROOTS)
        await self.press(self.more())
        self.assertEqual(choices.get_riff_setting(RIFF_BETWEEN), RESTS_BETWEEN)
        self.assertIn(RESTS_BETWEEN, self.text())
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_the_riff_s_picture_comes_first_on_the_riff_s_fields_with_the_kick_s_strokes_over_it(self):
        choices = await self.to_hooks(riff=True)
        said = messages.MSG_WIZARD_RIFF_SAID.format(players=labels_text.MSG_WIZARD_RIFF_PLAYERS_JOINED.join(choices.role_title(role) for role in choices.get_riff_players()))
        await self.select_field(labels_text.MSG_WIZARD_HOOK_NOTES_LABEL)
        shown = self.text()
        self.assertTrue(labels_text.MSG_WIZARD_RIFF_KICK_ROW not in shown or shown.index(labels_text.MSG_WIZARD_GROUP_RIFF) < shown.index(labels_text.MSG_WIZARD_RIFF_KICK_ROW))
        await self.select_field(labels_text.MSG_WIZARD_RIFF_PLAYED_BY_LABEL)
        shown = self.text()
        kick_row = next(line for line in shown.split(NEW_LINE) if self.is_kick_row(line))
        self.assertIn(said, shown)
        self.assertLess(shown.index(kick_row), shown.index(said))
        self.assertEqual(sum(cell == marks.MSG_WIZARD_HOOK_CELL for cell in kick_row), len(choices.riff_kick()))
        # A riff of single notes leaves the kick alone, and its picture has no row for the kick.
        await self.select_field(labels_text.MSG_WIZARD_RIFF_SETTING_LABELS[RIFF_NOTES])
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(choices.get_riff_setting(RIFF_NOTES), SINGLE_NOTES)
        self.assertFalse(any(self.is_kick_row(line) for line in self.text().split(NEW_LINE)))
        self.assertNotIn(labels_text.MSG_WIZARD_RIFF_SETTING_LABELS[RIFF_UNDER_TUNE], [field.label for field in self.wizard().shown_fields()])
