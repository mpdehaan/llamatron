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
"""The pattern editor's Inversion row, in Basics under Chord: blocked on a step with no chord, cycling blank, 1, 2 and 3 on one with a chord."""

from ui_testing import TUNE, UITest
from llamatron.composition.file_format import Row
from llamatron.strings.marks import MSG_BLOCKED_CELL
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui import keybindings

TRIAD = '3'
FIRST_STEP = 0
THIRD_INVERSION = 3


class TestInversionRow(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        if self.app.screen.view() is self.app.screen.roll:
            await self.press(keybindings.PatternEditor.TO_EDITOR)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.editor = self.app.screen

    async def go_to_the_row(self):
        # The Chord section, which holds the row, starts closed: PgDn reaches its heading and Space opens it.
        if not self.editor.rows_view.section_is_open(RowSection.CHORD):
            for _ in range(len(self.editor.rows_view.reachable())):
                if self.editor.row_name() == RowSection.CHORD:
                    break
                await self.press(Key.PAGE_DOWN)
            await self.press(Key.SPACE)
        for _ in range(len(self.editor.rows_view.reachable())):
            if self.editor.row_name() == Row.INVERSION:
                return
            await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), Row.INVERSION)

    def inversion(self):
        return self.document.step_value(name=TUNE, row=Row.INVERSION, step=FIRST_STEP)

    async def test_a_note_with_no_chord_is_blocked(self):
        self.assertEqual(self.editor.row_for(Row.INVERSION).cell_lines(step=FIRST_STEP), [MSG_BLOCKED_CELL])

    async def test_a_chord_cycles_through_the_inversions_and_back(self):
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=FIRST_STEP, value=TRIAD)
        await self.go_to_the_row()
        await self.press(keybindings.CycleRow.NEXT)
        self.assertEqual(self.inversion(), 1)
        await self.press(*[keybindings.CycleRow.NEXT] * (THIRD_INVERSION - 1))
        self.assertEqual(self.inversion(), THIRD_INVERSION)
        await self.press(keybindings.CycleRow.NEXT)
        self.assertIsNone(self.inversion())
        await self.press(keybindings.PatternRow.LESS)
        self.assertEqual(self.inversion(), THIRD_INVERSION)
        await self.press(keybindings.CycleRow.CLEAR)
        self.assertIsNone(self.inversion())
