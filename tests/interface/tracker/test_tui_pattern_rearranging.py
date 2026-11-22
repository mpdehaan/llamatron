# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Rearranging a pattern: Reconfigure and Munge, and the editor's two views."""

from llamatron.interface.tracker import keybindings, keys
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.key_table import first_key
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.pattern.pattern_editor import Munge, Reconfigure
from llamatron.model.schema.file_format import ClipSlotSetting, Row
from llamatron.model.values.note import NoteName
from llamatron.user_strings import errors, legends
from tests.support.pattern_editor_testing import munge
from tests.support.rendering import render_song
from tests.support.ui_testing import UITest

BEAT = 'beat'
OTHER = 'other'
LEAD = 'lead'
EIGHTH = '1/8'
HALF = '1/2'
QUARTER = '1/4'
SIXTEENTH = '1/16'


# A five-step pattern the rearranging tests flip and swap, with a different value on every step.
LONG_PATTERN = 'long'


LONG_PATTERN_STEPS = 5


LONG_PATTERN_ROWS = {
    Row.DEGREE: [1, 2, 3, 4, 5],
    Row.GATE: ['1/4', '1/8', '1/16', '1/2', '1'],
    Row.VELOCITY: [10, 20, 30, 40, 50],
}


class TestRearrangingAPattern(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.add_pattern_with_rows(name=LONG_PATTERN, steps=LONG_PATTERN_STEPS, rows=LONG_PATTERN_ROWS)
        await self.open_patterns_on(LONG_PATTERN)
        await self.press(Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def rows(self, *, row=Row.DEGREE):
        return self.document.get_setlist().get_pattern(LONG_PATTERN).get_row(row)

    async def test_reverse_after_reverses_everything_after_the_cursor(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 5, 4, 3])

    async def test_every_row_moves_with_its_step(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(row=Row.GATE), [QUARTER, EIGHTH, '1', HALF, SIXTEENTH])
        self.assertEqual(self.rows(row=Row.VELOCITY), [10, 20, 50, 40, 30])

    async def test_reversing_after_twice_puts_it_back_and_the_cursor_stays(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_reverse_after_on_the_last_step_says_why_nothing_happens(self):
        await self.press(Key.END)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertIn(errors.ERR_NOTHING_AFTER, self.text())

    async def test_pivot_exchanges_both_sides_of_the_cursor(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.rows(), [3, 4, 5, 2, 1])
        self.assertEqual(self.rows(row=Row.GATE), [SIXTEENTH, HALF, '1', EIGHTH, QUARTER])

    async def test_the_cursor_stays_on_its_step_so_pivoting_twice_puts_it_back(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.editor.step, 3)
        self.assertEqual(self.document.step_value(name=LONG_PATTERN, row=Row.DEGREE, step=self.editor.step), 2)
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_pivot_at_either_end(self):
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.rows(), [2, 3, 4, 5, 1])
        self.assertEqual(self.editor.step, 4)

    async def test_reverse_before_and_after_and_the_whole_pattern(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 3, 5, 4])
        await munge(test=self, choice=Munge.REVERSE_BEFORE)
        self.assertEqual(self.rows(), [2, 1, 3, 5, 4])
        await munge(test=self, choice=Munge.REVERSE)
        self.assertEqual(self.rows(), [4, 5, 3, 1, 2])
        self.assertEqual(self.editor.step, 2)

    async def test_randomize_keeps_every_step_and_is_an_edit(self):
        await munge(test=self, choice=Munge.RANDOMIZE)
        self.assertEqual(sorted(self.rows()), [1, 2, 3, 4, 5])
        self.assertTrue(self.document.is_dirty())

    async def test_the_time_stays_the_same(self):
        before = self.document.lengths().pattern_length(LONG_PATTERN)
        await self.press(Key.RIGHT, NoteName.F.lower())
        self.assertEqual(self.document.lengths().pattern_length(LONG_PATTERN), before)

    async def test_load_replaces_everything_after_asking(self):
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertNotIn(LONG_PATTERN, self.app.screen.options)
        self.app.screen.cursor.set_place(self.app.screen.options.index(BEAT))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.cursor.set_place(self.app.screen.options.index(BEAT))
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        song = self.document.song()
        self.assertEqual(song.get_setlist().get_pattern(LONG_PATTERN).to_data(), song.get_setlist().get_pattern(BEAT).to_data())
        self.assertEqual(self.editor.step_count(), 2)
        self.assertIn('│ Note', self.text())

    async def test_a_loaded_copy_is_separate(self):
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.cursor.set_place(self.app.screen.options.index(BEAT))
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES, Key.RIGHT, NoteName.F.lower())
        self.assertEqual(self.document.step_value(name=LONG_PATTERN, row=Row.DEGREE, step=1), NoteName.F)
        self.assertIsNone(self.document.step_value(name=BEAT, row=Row.DEGREE, step=1))

    async def test_load_keeps_the_name_and_what_uses_it(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.PATTERN, value=LONG_PATTERN)
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.cursor.set_place(self.app.screen.options.index(OTHER))
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song().get_scenes()[0].get_clip_slot(LEAD).get_pattern_name(), LONG_PATTERN)
        render_song(self.document.song())



class TestTheEditorsTwoViews(UITest):
    """The piano roll and the rows are two views of one shape, each with its cursor, its keys and its drawing, and the editor asks whichever is showing."""

    async def test_tab_switches_between_the_piano_roll_and_the_rows(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assertTrue(self.app.screen.on_roll())
        for binding, on_roll in ((keybindings.PatternEditor.TO_EDITOR, False), (keybindings.PatternEditor.TO_ROLL, True)):
            await self.press(binding)
            self.assertEqual(self.app.screen.on_roll(), on_roll)

    async def test_each_view_says_what_tab_does_and_whether_its_legend_lists_the_step_keys(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        editor = self.app.screen
        self.assertEqual(editor.roll.other_view_what(), legends.MSG_TO_EDITOR_WHAT)
        self.assertEqual(editor.rows_view.other_view_what(), legends.MSG_TO_ROLL_WHAT)
        self.assertFalse(editor.roll.lists_step_keys())
        self.assertTrue(editor.rows_view.lists_step_keys())
        # The roll neither inserts nor removes a step, as Live's piano roll never did; the rows view does both, in its legend.
        self.assertEqual(editor.roll.step_keys(can_remove=True), [])
        on_roll = {name for item in editor.keys() for name in item.keys}
        self.assertNotIn(first_key(keybindings.PatternRows.INSERT_STEP), on_roll)
        self.assertNotIn(first_key(keybindings.PatternRows.REMOVE_STEP), on_roll)
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        on_rows = {name: item.shown for item in editor.keys() for name in item.keys}
        self.assertEqual((on_rows[first_key(keybindings.PatternRows.INSERT_STEP)], on_rows[first_key(keybindings.PatternRows.REMOVE_STEP)]), (True, True))

    async def test_both_views_list_the_keys_that_move_the_cursor_and_then_their_own(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        editor = self.app.screen
        for view in (editor.roll, editor.rows_view):
            moving = [name for item in view.move_keys() for name in item.keys]
            for name in (Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT, *keys.HOME_END):
                self.assertIn(name, moving)
        # Only the rows have section headings to jump between.
        self.assertNotIn(Key.PAGE_DOWN, [name for item in editor.roll.move_keys() for name in item.keys])
        self.assertIn(Key.PAGE_DOWN, [name for item in editor.rows_view.move_keys() for name in item.keys])
        self.assertTrue(editor.roll.keys())

    async def test_a_drum_pattern_shows_only_the_rows_and_its_note_row_takes_letters(self):
        await self.open_patterns_on(BEAT)
        await self.press(Key.ENTER)
        editor = self.app.screen
        self.assertTrue(editor.is_drum())
        self.assertIs(editor.view(), editor.rows_view)
        self.assertNotIn(first_key(keybindings.PatternEditor.TO_ROLL), [name for item in editor.keys() for name in item.keys])
        # On the Note row the letter D is a note, so it can't remove a step there, and it can on the row below.
        self.assertTrue(editor.rows_view.takes_note_letters())
        self.assertFalse(any(item.what == legends.What.REMOVE_STEP for item in editor.keys()))
        await self.press(Key.DOWN)
        self.assertFalse(editor.rows_view.takes_note_letters())
        self.assertTrue(any(item.what == legends.What.REMOVE_STEP for item in editor.keys()))
        self.assertFalse(editor.roll.takes_note_letters())
