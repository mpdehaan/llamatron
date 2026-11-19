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

"""The Notes page."""

from tests.support.ui_testing import KEY_SHOWN, UITest
from llamatron.tui import drawing
from llamatron.tui.dialogs.help_dialog import HelpDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.notes_page import NotesPage
from llamatron.tui.screens.set.file_page import FilePage
from llamatron.strings import labels, marks
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key

NO_NOTES_YET = 'No notes yet'
HI_THERE = 'Hi there\n'
HIX_THERE = 'HiX there\n'
HIX_THERE_2 = 'HiX there'
H_2 = 'h\n'
TYPED_LETTER = 'h'
ONETWO = 'onetwo\n'
ONE = 'one\n'
LINE_0 = 'line 0\n'
LINE_2 = 'line 2'


class TestNotesPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(labels.MSG_NOTES_LABEL)
        await self.press(Key.ENTER)

    async def save(self):
        """Press Save under the text: Tab reaches the buttons, Save is the first, and ENTER presses it."""
        await self.press(Key.TAB)
        self.assertTrue(self.app.screen.on_buttons)
        await self.press(Key.ENTER)
        self.assertFalse(self.app.screen.editing)

    async def test_enter_on_the_notes_field_opens_it_editing_and_esc_twice_comes_back(self):
        self.assertIsInstance(self.app.screen, NotesPage)
        self.assertTrue(self.app.screen.editing)
        await self.press(Key.ESCAPE)
        self.assertFalse(self.app.screen.editing)
        self.assertIn(NO_NOTES_YET, self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertIn(marks.MSG_NOT_SET, self.text())

    async def test_esc_and_the_cancel_button_throw_the_typing_away_and_save_keeps_it(self):
        await self.type(ONE)
        await self.press(Key.ESCAPE)
        self.assertFalse(self.app.screen.editing)
        self.assertFalse(self.document.setlist().has_notes())
        await self.press(keybindings.NotesPage.EDIT)
        await self.type(ONE)
        # Tab reaches the buttons, Right moves to Cancel, and Tab again goes back to the text, where letters type again.
        await self.press(Key.TAB)
        self.assertIn(drawing.SELECTED_MARK + KEY_SHOWN.format(label=labels.MSG_NOTES_BUTTONS[0]), self.text())
        await self.press(Key.RIGHT)
        self.assertIn(drawing.SELECTED_MARK + KEY_SHOWN.format(label=labels.MSG_NOTES_BUTTONS[1]), self.text())
        await self.press(Key.TAB)
        self.assertFalse(self.app.screen.on_buttons)
        await self.type(ONE)
        # The buttons remember that Cancel was chosen, so Tab and ENTER press it.
        await self.press(Key.TAB)
        self.assertIn(drawing.SELECTED_MARK + KEY_SHOWN.format(label=labels.MSG_NOTES_BUTTONS[1]), self.text())
        await self.press(Key.ENTER)
        self.assertFalse(self.app.screen.editing)
        self.assertFalse(self.document.setlist().has_notes())
        await self.press(keybindings.NotesPage.EDIT)
        await self.type(ONE)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), ONE)

    async def test_a_protected_sets_notes_can_only_be_read(self):
        await self.press(Key.ESCAPE, Key.ESCAPE)
        self.document.set_protected(True)
        self.document.set_notes(ONE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, NotesPage)
        self.assertFalse(self.app.screen.editing)
        self.assertNotIn(first_key(keybindings.NotesPage.EDIT), [name for item in self.app.screen.keys() for name in item.keys])
        await self.press(keybindings.NotesPage.EDIT, Key.BACKSPACE)
        self.assertFalse(self.app.screen.editing)
        self.assertEqual(self.document.setlist().get_notes(), ONE)
        self.assertIsInstance(self.app.screen, NotesPage)

    async def test_typing_new_lines_and_erasing(self):
        # What's typed reaches the set when Save is pressed, not letter by letter, so that undo takes it back as one edit.
        await self.type('Hi there')
        await self.press(Key.ENTER)
        await self.type('ok')
        self.assertFalse(self.document.setlist().has_notes())
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), 'Hi there\nok\n')
        await self.press(keybindings.NotesPage.EDIT, Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), HI_THERE)
        # Six steps left from the end of 'Hi there' is just after 'Hi'.
        await self.press(keybindings.NotesPage.EDIT, *[Key.LEFT] * 6)
        await self.type('X')
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), HIX_THERE)
        self.assertFalse(self.app.screen.editing)
        self.assertIn(HIX_THERE_2, self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertIn(HIX_THERE_2, self.text())

    async def test_letters_are_text_while_editing_and_f1_helps_while_reading(self):
        await self.press(TYPED_LETTER)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), H_2)
        await self.press(Key.F1)
        self.assertIsInstance(self.app.screen, HelpDialog)

    async def test_erasing_at_the_start_of_a_line_joins_it_to_the_one_before(self):
        await self.press(Key.ESCAPE)
        self.document.set_notes('one\ntwo\n')
        await self.press(keybindings.NotesPage.EDIT, Key.UP, Key.DOWN)
        self.app.screen.column = 0
        await self.press(Key.BACKSPACE)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), ONETWO)

    async def test_clearing_asks_first_while_reading(self):
        await self.press(Key.ESCAPE)
        self.document.set_notes(ONE)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(self.document.setlist().has_notes())

    async def test_long_notes_scroll(self):
        await self.press(Key.ESCAPE)
        self.document.set_notes(''.join(f'line {n}\n' for n in range(100)))
        await self.press(Key.DOWN, Key.DOWN)
        self.assertNotIn(LINE_0, self.text().replace(' ', ''))
        self.assertIn(LINE_2, self.text())
