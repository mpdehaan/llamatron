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

"""Tests of the Lines dialog, a section's lines one by one, opened from a section's panel of the song wizard."""

from llamatron.macro_composer import line_edits
from llamatron.macro_composer.melody import LINE_NOTES
from llamatron.macro_composer.phrasing import LINE_BREATH, LINE_EARLY, SHORT_BREATH
from llamatron.macro_composer.wizard_choices import LINE_BREATHES, LINE_OWN
from llamatron.strings.labels import MSG_WIZARD_HOOK_NOTES_OWN, MSG_WIZARD_LINES_LABEL, MSG_WIZARD_LINES_TITLE
from llamatron.strings.marks import MSG_LINES_COUNT_OWN, MSG_LINES_FROM_MELODY, MSG_LINES_SAME_IDEA
from llamatron.tui import keybindings
from llamatron.tui.dialogs.lines_dialog import LinesDialog
from llamatron.tui.dialogs.tune_dialog import TuneDialog
from llamatron.tui.keys import Key
from tests.support.ui_testing import forward_key
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_SEED = 11
A_VERSE = 'verse-1'
A_VERSE_PLACE = 1
FIRST = 0
AN_ENDING = 'ending'


class TestLinesDialog(WizardTest):
    """The Lines dialog on a verse."""

    async def open_lines(self):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(A_VERSE)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_LINES_LABEL)
        await self.press(Key.ENTER)
        return choices

    def lines(self, choices):
        return choices.section_lines(A_VERSE_PLACE)

    async def test_the_field_opens_the_section_s_lines_a_row_a_line(self):
        choices = await self.open_lines()
        self.assertIsInstance(self.app.screen, LinesDialog)
        shown = self.text()
        self.assertIn(MSG_WIZARD_LINES_TITLE.format(section=A_VERSE), shown)
        self.assertIn(MSG_LINES_FROM_MELODY, shown)
        self.assertEqual(self.lines(choices)[FIRST][LINE_OWN], {})
        await self.press(keybindings.LinesDialog.CLOSE)
        self.assertNotIsInstance(self.app.screen, LinesDialog)

    async def test_the_breath_is_made_longer_and_shorter_and_bksp_gives_the_line_back(self):
        choices = await self.open_lines()
        before = self.lines(choices)[FIRST][LINE_NOTES]
        await self.press(keybindings.LinesDialog.LONGER, keybindings.LinesDialog.LONGER)
        self.assertEqual(self.lines(choices)[FIRST][LINE_OWN], {LINE_BREATH: SHORT_BREATH + 2})
        await self.press(keybindings.LinesDialog.SHORTER)
        self.assertEqual(self.lines(choices)[FIRST][LINE_OWN], {LINE_BREATH: SHORT_BREATH + 1})
        self.assertNotEqual(self.lines(choices)[FIRST][LINE_NOTES], before)
        await self.press(keybindings.LinesDialog.USUAL)
        self.assertEqual(self.lines(choices)[FIRST][LINE_NOTES], before)
        self.assertEqual(self.lines(choices)[FIRST][LINE_OWN], {})
        await self.press(keybindings.LinesDialog.CLOSE)
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_space_has_a_note_come_early_or_not(self):
        choices = await self.open_lines()
        await self.press(keybindings.LinesDialog.EARLY)
        self.assertEqual(self.lines(choices)[FIRST][LINE_OWN], {LINE_EARLY: True})
        await self.press(keybindings.LinesDialog.EARLY)
        self.assertEqual(self.lines(choices)[FIRST][LINE_OWN], {LINE_EARLY: False})

    async def test_a_line_that_says_an_idea_again_takes_no_breath_of_its_own(self):
        choices = await self.open_lines()
        again = next(count for count, line in enumerate(self.lines(choices)) if not line[LINE_BREATHES])
        await self.press(*[Key.DOWN] * again)
        self.assertIn(MSG_LINES_SAME_IDEA, self.text())
        await self.press(keybindings.LinesDialog.LONGER, keybindings.LinesDialog.EARLY)
        self.assertEqual(self.lines(choices)[again][LINE_OWN], {})

    async def test_enter_opens_the_line_s_notes_and_the_notes_kept_are_the_line_s_own(self):
        choices = await self.open_lines()
        before = self.lines(choices)[FIRST][LINE_NOTES]
        await self.press(keybindings.LinesDialog.EDIT)
        self.assertIsInstance(self.app.screen, TuneDialog)
        await self.press(forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.DONE)
        self.assertIsInstance(self.app.screen, LinesDialog)
        after = self.lines(choices)[FIRST]
        self.assertEqual(line_edits.place_of(after[LINE_NOTES][FIRST]), line_edits.place_of(before[FIRST]) + 1)
        self.assertIn(LINE_NOTES, after[LINE_OWN])
        self.assertIn(MSG_WIZARD_HOOK_NOTES_OWN, self.text())
        await self.press(keybindings.LinesDialog.CLOSE)
        self.assertIn(MSG_LINES_COUNT_OWN.format(count=len(self.lines(choices)), own=1), self.text())

    async def test_a_section_with_no_tune_has_no_lines_field(self):
        await self.open_lines()
        await self.press(keybindings.LinesDialog.CLOSE, keybindings.WizardPage.TO_TREE)
        await self.go_to_named_branch(AN_ENDING)
        self.assertNotIn(MSG_WIZARD_LINES_LABEL, self.text())
