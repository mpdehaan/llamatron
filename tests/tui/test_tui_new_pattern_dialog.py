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
"""The New Pattern dialog and a pattern's scale length in the tracker: the dialog's rows and buttons, the Patterns page's new pattern, Arrange's blank pattern, the Reconfigure choice and the header's warning."""

from llamatron.composition import limits
from llamatron.strings import labels, legends, marks, messages, names
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.new_pattern_dialog import NewPatternDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor, Reconfigure, reconfigure_choices
from llamatron.tui.screens.pattern.patterns_page import PatternsPage
from tests.support import ui_testing
from tests.support.ui_testing import fixed_text, UITest

NEW = 'riff'
PENTATONIC = 5
# What the header's warning says after whatever it says of the scale.
WARNING_ALONE = ''


class TestNewPatternDialog(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.ADD)
        self.dialog = self.app.screen
        self.assertIsInstance(self.dialog, NewPatternDialog)

    async def name_it(self):
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = NEW
        await self.press(Key.ENTER)
        return self.document.get_setlist().get_pattern(NEW)

    async def test_it_shows_its_title_and_rows_and_starts_on_a_scale_of_seven_notes(self):
        shown = self.text()
        for text in (messages.MSG_NEW_PATTERN_TITLE, labels.MSG_SCALE_LENGTH_LABEL, labels.MSG_DRUM_PATTERN_LABEL):
            self.assertIn(text, shown)
        self.assertEqual(self.dialog.values()[0], str(limits.NEW_PATTERN_SCALE_LENGTH))

    async def test_enter_at_once_makes_a_pattern_written_for_seven_notes_once_named(self):
        await self.press(keybindings.NewPatternDialog.OK)
        pattern = await self.name_it()
        self.assertEqual(pattern.get_scale_length(), limits.NEW_PATTERN_SCALE_LENGTH)
        self.assertFalse(pattern.is_drum())
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_the_scale_length_steps_and_stops_at_each_end(self):
        await self.press(*[keybindings.NewPatternDialog.LESS] * limits.MAX_SCALE_LENGTH)
        self.assertIsNone(self.dialog.scale_length)
        self.assertEqual(self.dialog.values()[0], marks.MSG_ANY_SCALE_LENGTH)
        await self.press(keybindings.NewPatternDialog.MORE)
        self.assertEqual(self.dialog.scale_length, limits.MIN_SCALE_LENGTH)
        await self.press(*[keybindings.NewPatternDialog.MORE] * limits.MAX_SCALE_LENGTH)
        self.assertEqual(self.dialog.scale_length, limits.MAX_SCALE_LENGTH)
        await self.press(keybindings.NewPatternDialog.OK)
        self.assertEqual((await self.name_it()).get_scale_length(), limits.MAX_SCALE_LENGTH)

    async def test_the_drum_toggle_blocks_the_scale_length_and_makes_a_drum_pattern(self):
        await self.press(Key.DOWN, Key.SPACE)
        self.assertEqual(self.dialog.values()[0], marks.MSG_BLOCKED_CELL)
        await self.press(Key.DOWN, keybindings.NewPatternDialog.PRESS)
        pattern = await self.name_it()
        self.assertTrue(pattern.is_drum())
        self.assertIsNone(pattern.get_scale_length())

    async def test_the_toggle_off_again_brings_the_number_back(self):
        await self.press(Key.DOWN, Key.SPACE, Key.ENTER)
        self.assertEqual(self.dialog.values()[0], str(limits.NEW_PATTERN_SCALE_LENGTH))

    async def test_the_cancel_button_and_escape_make_nothing(self):
        before = self.document.get_setlist().to_data()
        await self.press(Key.DOWN, Key.DOWN, Key.RIGHT, keybindings.NewPatternDialog.PRESS)
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.press(keybindings.PatternsPage.ADD, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternsPage)
        self.assertEqual(self.document.get_setlist().to_data(), before)

    async def test_the_cursor_stops_at_the_buttons_and_at_the_top(self):
        await self.press(Key.UP)
        self.assertEqual(self.dialog.row, 0)
        await self.press(*[Key.DOWN] * 5)
        self.assertEqual(self.dialog.row, 2)


class TestScaleLengthInTheTracker(UITest):

    async def test_a_blank_pattern_on_arrange_takes_the_scale_length_of_its_clips_scale(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.DOWN, keybindings.ArrangePage.BLANK_PATTERN)
        name = names.MSG_NUMBERED_NAME.format(base=ui_testing.LEAD, number=1)
        size = self.document.scale_size(self.document.pattern_scale(name))
        self.assertEqual(self.document.pattern_scale_length(name), size)

    async def test_reconfigure_sets_the_scale_length_and_any_clears_it(self):
        await self.open_patterns_on(ui_testing.TUNE)
        await self.press(Key.ENTER)
        await self.reconfigure(Reconfigure.SCALE_LENGTH)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], marks.MSG_ANY_SCALE_LENGTH)
        await self.pick(str(PENTATONIC))
        self.assertEqual(self.document.pattern_scale_length(ui_testing.TUNE), PENTATONIC)
        await self.reconfigure(Reconfigure.SCALE_LENGTH)
        await self.pick(marks.MSG_ANY_SCALE_LENGTH)
        self.assertIsNone(self.document.pattern_scale_length(ui_testing.TUNE))

    async def test_a_drum_pattern_is_not_offered_a_scale_length_until_it_is_no_drum_pattern(self):
        await self.open_patterns_on(ui_testing.BEAT)
        await self.press(Key.ENTER, keybindings.PatternEditor.RECONFIGURE)
        self.assertNotIn(legends.MSG_SCALE_LENGTH_WHAT, self.app.screen.options)
        self.assertEqual(self.app.screen.options, reconfigure_choices(drum=True))
        await self.press(Key.ESCAPE)
        self.assertIn(legends.MSG_SCALE_LENGTH_WHAT, reconfigure_choices(drum=False))

    async def test_the_header_says_what_a_pattern_was_written_for_only_under_a_scale_of_another_size(self):
        await self.open_patterns_on(ui_testing.TUNE)
        await self.press(Key.ENTER)
        size = self.document.scale_size(self.document.pattern_scale(ui_testing.TUNE))
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_scale_length, size)
        await self.press(Key.RIGHT)
        self.assertNotIn(fixed_text(labels.MSG_WRITTEN_FOR).strip(), self.text())
        other = PENTATONIC if size != PENTATONIC else limits.MAX_SCALE_LENGTH
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_scale_length, other)
        await self.press(Key.RIGHT)
        self.assertIn(labels.MSG_WRITTEN_FOR.format(scale=WARNING_ALONE, length=other).strip(), self.text())
        self.assertEqual(self.document.scales_unsuited_to_pattern(ui_testing.TUNE), self.document.scales_of_pattern(ui_testing.TUNE))
