# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pattern editor's Inversion row, in Basics under Chord: blocked on a step with no chord, cycling blank, 1, 2 and 3 on one with a chord."""

from llamatron.composition.file_format import Row
from llamatron.tui import keybindings
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.pattern import grid_drawing
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.user_strings import marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

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
        return self.document.step_value(name=ui_testing.TUNE, row=Row.INVERSION, step=FIRST_STEP)

    async def test_a_note_with_no_chord_is_blocked(self):
        self.assertEqual(self.editor.row_for(Row.INVERSION).cell_lines(step=FIRST_STEP), [marks.MSG_BLOCKED_CELL])

    async def test_the_roll_draws_a_note_hollow_while_its_inversion_plays_the_root_an_octave_up(self):
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        roll = self.editor.roll
        self.assertFalse(roll.root_is_lifted(FIRST_STEP))
        self.assertNotIn(marks.MSG_NOTE_HOLLOW, self.text())
        self.assertNotIn(marks.MSG_NOTE_HOLLOW_UNDER_CURSOR, self.text())
        # An inversion with no chord lifts nothing: one note has no inversion.
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_value, row=Row.INVERSION, step=FIRST_STEP, value=1)
        self.assertFalse(roll.root_is_lifted(FIRST_STEP))
        # With a chord, the written note doesn't sound where it is drawn: its bar is hollow, medium under the cursor and light once the cursor has left.
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_value, row=Row.CHORD, step=FIRST_STEP, value=TRIAD)
        self.assertTrue(roll.root_is_lifted(FIRST_STEP))
        self.editor.draw()
        self.assertIn(marks.MSG_NOTE_HOLLOW_UNDER_CURSOR * grid_drawing.CELL_WIDTH, self.text())
        await self.press(Key.RIGHT)
        self.assertIn(marks.MSG_NOTE_HOLLOW * grid_drawing.CELL_WIDTH, self.text())
        # Root position again, and the bar is solid.
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_value, row=Row.INVERSION, step=FIRST_STEP, value=None)
        self.editor.draw()
        self.assertNotIn(marks.MSG_NOTE_HOLLOW, self.text())

    async def test_a_chord_cycles_through_the_inversions_and_back(self):
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_value, row=Row.CHORD, step=FIRST_STEP, value=TRIAD)
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
