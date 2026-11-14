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

"""A chord in the pattern editor (the user's design): the Scale and Tension rows beside the Chord row, each stepped and
cleared, the Chord dialog all three open with its three lists, what the dialog says of the chord as the choice moves, the
status line naming the chord under the cursor, and the whole choice as one step of undo."""

import unittest

from ui_testing import TUNE, UITest, key_name
from llamatron.composition.file_format import ChordSymbol, Row, ScaleKind, Tension
from llamatron.composition.naming import words
from llamatron.strings.labels import MSG_SCALE_CATEGORY_COMMON, Column
from llamatron.composition.named_scale import scale_type_name, scale_type_names
from llamatron.music.scale import ScaleType
from llamatron.strings.marks import MSG_BLOCKED_CELL, MSG_FLYOUT_CHOSEN, MSG_FLYOUT_CLOSED, MSG_FLYOUT_TITLE, MSG_TENSIONS_COUNTED
from llamatron.strings.messages import MSG_CHORD_DIALOG_TITLE, MSG_CHORD_OF_STEP, MSG_NOTE_SENTENCE, MSG_RESTING_STEP
from llamatron.tui import keybindings
from llamatron.tui.dialogs.chord_dialog import LISTS, NOT_BORROWED_ROW, QUALITY_LIST, SCALE_LIST, TENSION_LIST, ChordDialog
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN, DIALOG_SELECTOR, FLYOUT_SHIFT
from llamatron.tui.drawing import Box
from llamatron.tui.scale_categories import COMMON_SCALE_TYPES, SCALE_CATEGORIES, SCALE_TYPES_IN_ORDER, SORTED_SCALE_CATEGORIES
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.pattern_editor import PatternEditor

MINOR = scale_type_name(ScaleType.MINOR)
FIRST_STEP = 0
ALTERED = (Tension.FLAT_NINTH, Tension.THIRTEENTH)
THREE_TENSIONS = (Tension.FLAT_NINTH, Tension.SHARP_ELEVENTH, Tension.THIRTEENTH)
SCALE_CELL = 'Minor'
# The mark between a category and the scale type picked in it.
FLYOUT_MARK = '▸'
# The smallest console everything must fit.
CONSOLE_WIDTH = 80
CONSOLE_LINES = 24
C_MAJOR = 'C Major'
C_MINOR = 'C Minor'


class TestPatternEditorChords(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen
        self.assertIsInstance(self.editor, PatternEditor)
        # The Chord section starts closed: PgDn reaches its heading and Space opens it.
        while self.editor.row_name() != RowSection.CHORD:
            await self.press(Key.PAGE_DOWN)
        await self.press(Key.SPACE)

    async def go_to_row(self, name):
        names = [row.name for row in self.editor.rows_view.reachable()]
        self.assertIn(name, names)
        distance = names.index(name) - names.index(self.editor.row_name())
        await self.press(*[Key.DOWN if distance > 0 else Key.UP] * abs(distance))
        self.assertEqual(self.editor.row_name(), name)

    def value(self, row):
        return self.document.step_value(name=TUNE, row=row, step=FIRST_STEP)

    def set(self, *, row, value):
        self.document.set_step_value(name=TUNE, row=row, step=FIRST_STEP, value=value)

    def dialog_text(self):
        self.app.screen.draw()
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_the_scale_row_steps_through_the_scale_types_and_clears(self):
        await self.go_to_row(Row.CHORD_SCALE)
        await self.press(keybindings.ChordScaleRow.NEXT)
        self.assertEqual(self.value(Row.CHORD_SCALE), SCALE_TYPES_IN_ORDER[0])
        await self.press(keybindings.ChordScaleRow.MORE, keybindings.ChordScaleRow.LESS, keybindings.ChordScaleRow.LESS)
        self.assertIsNone(self.value(Row.CHORD_SCALE))
        # The scale types stop at the last and never go round to none (the user's rule), and [ goes back from the last.
        self.set(row=Row.CHORD_SCALE, value=SCALE_TYPES_IN_ORDER[-1])
        await self.press(keybindings.ChordScaleRow.MORE, keybindings.ChordScaleRow.NEXT)
        self.assertEqual(self.value(Row.CHORD_SCALE), SCALE_TYPES_IN_ORDER[-1])
        await self.press(keybindings.ChordScaleRow.LESS)
        self.assertEqual(self.value(Row.CHORD_SCALE), SCALE_TYPES_IN_ORDER[-2])
        self.set(row=Row.CHORD_SCALE, value=MINOR)
        self.assertEqual(self.editor.row_for(Row.CHORD_SCALE).cell_text(step=FIRST_STEP), SCALE_CELL)
        await self.press(keybindings.ChordScaleRow.CLEAR)
        self.assertIsNone(self.value(Row.CHORD_SCALE))

    async def test_the_tension_row_needs_a_chord_and_steps_through_each_tension_alone(self):
        self.assertEqual(self.editor.row_for(Row.TENSION).cell_lines(step=FIRST_STEP), [MSG_BLOCKED_CELL])
        self.set(row=Row.CHORD, value=ChordSymbol.DOMINANT7)
        await self.go_to_row(Row.TENSION)
        await self.press(keybindings.TensionRow.NEXT)
        self.assertEqual(self.value(Row.TENSION), (Tension.FLAT_NINTH,))
        await self.press(keybindings.TensionRow.MORE)
        self.assertEqual(self.value(Row.TENSION), (Tension.NINTH,))
        self.set(row=Row.TENSION, value=ALTERED)
        self.assertEqual(self.editor.row_for(Row.TENSION).cell_text(step=FIRST_STEP), ' '.join(ALTERED))
        self.set(row=Row.TENSION, value=THREE_TENSIONS)
        self.assertEqual(self.editor.row_for(Row.TENSION).cell_text(step=FIRST_STEP), MSG_TENSIONS_COUNTED.format(count=len(THREE_TENSIONS)))
        # Several tensions are no step of the cycle, so stepping starts again from none.
        await self.press(keybindings.TensionRow.MORE)
        self.assertEqual(self.value(Row.TENSION), (Tension.FLAT_NINTH,))

    async def test_each_row_opens_the_dialog_on_its_own_list(self):
        self.set(row=Row.CHORD, value=ChordSymbol.DOMINANT7)
        for row, part in ((Row.CHORD_SCALE, SCALE_LIST), (Row.CHORD, QUALITY_LIST), (Row.TENSION, TENSION_LIST)):
            await self.go_to_row(row)
            await self.press(keybindings.ChordRow.CHOOSE)
            self.assertIsInstance(self.app.screen, ChordDialog, row)
            self.assertEqual(self.app.screen.part, part, row)
            self.assertIn(MSG_CHORD_DIALOG_TITLE.format(where=MSG_CHORD_OF_STEP.format(step=FIRST_STEP + 1, pattern=TUNE)), self.dialog_text())
            await self.press(keybindings.ChordDialog.CANCEL)

    async def test_the_dialog_sets_all_three_rows_and_says_the_chord_as_the_choice_moves(self):
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        # A single note is said as a note, in the scale the pattern is known to play under.
        degree = self.value(Row.DEGREE)
        self.assertIn(MSG_NOTE_SENTENCE.format(scale=C_MAJOR, degree=degree, name='')[:-1].rstrip(), self.dialog_text())
        dialog.places[QUALITY_LIST] = dialog.qualities.index(ChordSymbol.DOMINANT7)
        dialog.picked = set(ALTERED)
        dialog.set_kind(MINOR)
        self.assertIn(C_MINOR, self.dialog_text())
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.TENSION), self.value(Row.CHORD_SCALE)), (ChordSymbol.DOMINANT7, ALTERED, MINOR))
        resting = self.editor.resting_status()
        self.assertTrue(resting.startswith(MSG_RESTING_STEP.format(step=FIRST_STEP + 1)))
        for part in (C_MINOR, C_MAJOR, 'Dominant Seventh', 'b9'):
            self.assertIn(part, resting)
        self.assertIn(resting[:30], self.text())

    async def open_on_scales(self):
        self.set(row=Row.CHORD, value=ChordSymbol.SCALE_TRIAD)
        await self.go_to_row(Row.CHORD_SCALE)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        self.assertEqual((dialog.part, dialog.places[SCALE_LIST]), (SCALE_LIST, NOT_BORROWED_ROW))
        return dialog

    async def test_a_category_opens_a_flyout_where_enter_picks_and_the_next_enter_takes_the_chord(self):
        dialog = await self.open_on_scales()
        # Down reaches Common, the first category, whose flyout opens on its first scale type, Minor.
        await self.press(Key.DOWN, keybindings.ChordDialog.OPEN)
        self.assertEqual(dialog.flyout, 1)
        self.assertIn(MSG_FLYOUT_TITLE.format(name=MSG_SCALE_CATEGORY_COMMON), self.dialog_text())
        # The sentences speak of the scale type under the flyout's cursor before it is picked.
        self.assertIn(C_MINOR, self.dialog_text())
        self.assertIsNone(dialog.kind)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertIsNone(dialog.flyout)
        self.assertEqual((dialog.kind, dialog.part), (COMMON_SCALE_TYPES[0], QUALITY_LIST))
        self.assertIn(MSG_FLYOUT_CHOSEN.format(name=MSG_SCALE_CATEGORY_COMMON, chosen=SCALE_CELL), self.dialog_text())
        # Every category is drawn as a button, and only the one whose scale type was picked carries the mark (the user's design).
        for name, _ in dialog.categories:
            if name != MSG_SCALE_CATEGORY_COMMON:
                self.assertIn(MSG_FLYOUT_CLOSED.format(name=name), self.dialog_text(), name)
        self.assertEqual(self.dialog_text().count(FLYOUT_MARK), 1)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.value(Row.CHORD_SCALE), MINOR)

    async def test_escape_and_left_close_the_flyout_and_change_nothing_and_its_cursor_stops_at_its_edges(self):
        dialog = await self.open_on_scales()
        await self.press(Key.DOWN, keybindings.ChordDialog.OPEN, Key.UP)
        self.assertEqual(dialog.flyout_place, 0)
        await self.press(*[Key.DOWN] * (len(COMMON_SCALE_TYPES) + 1), Key.RIGHT)
        self.assertEqual(dialog.flyout_place, len(COMMON_SCALE_TYPES) - 1)
        await self.press(keybindings.ChordDialog.CLOSE_FLYOUT)
        self.assertIsInstance(self.app.screen, ChordDialog)
        self.assertEqual((dialog.flyout, dialog.kind), (None, None))
        await self.press(keybindings.ChordDialog.OPEN, Key.LEFT)
        self.assertEqual((dialog.flyout, dialog.part), (None, SCALE_LIST))
        self.assertNotIn(C_MINOR, self.dialog_text())

    async def test_the_dialog_opens_on_the_category_of_the_scale_borrowed_and_its_flyout_on_that_scale(self):
        self.set(row=Row.CHORD_SCALE, value=ScaleKind.LYDIAN_DOMINANT)
        self.set(row=Row.CHORD, value=ChordSymbol.SCALE_TRIAD)
        await self.go_to_row(Row.CHORD_SCALE)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        name, kinds = dialog.categories[dialog.places[SCALE_LIST] - 1]
        self.assertIn(ScaleKind.LYDIAN_DOMINANT, kinds)
        await self.press(keybindings.ChordDialog.OPEN)
        self.assertEqual(kinds[dialog.flyout_place], ScaleKind.LYDIAN_DOMINANT)
        # The row that borrows none takes the scale away and goes on to the qualities.
        await self.press(keybindings.ChordDialog.CLOSE_FLYOUT, *[Key.UP] * len(dialog.categories), keybindings.ChordDialog.OPEN)
        self.assertEqual((dialog.kind, dialog.part), (None, QUALITY_LIST))

    async def test_a_flyout_is_a_box_of_the_dialogs_size_stacked_over_it_and_the_dialog_stays_where_it_was(self):
        dialog = await self.open_on_scales()
        closed = self.dialog_text().splitlines()
        view = dialog.query_one(DIALOG_SELECTOR)
        await self.settle()
        corner = (view.region.x, view.region.y)
        await self.press(Key.DOWN, keybindings.ChordDialog.OPEN)
        stacked = self.dialog_text().splitlines()
        await self.settle()
        # The stack is the dialog and a box as large, FLYOUT_SHIFT down and to the right, and the dialog's corner has not moved.
        self.assertEqual(len(stacked), len(closed) + FLYOUT_SHIFT)
        self.assertEqual(max(len(line) for line in stacked), len(closed[0]) + FLYOUT_SHIFT)
        self.assertEqual(stacked[0].rstrip(), closed[0])
        self.assertEqual(stacked[FLYOUT_SHIFT][FLYOUT_SHIFT:], closed[0])
        self.assertEqual(stacked[-1].strip(), closed[-1])
        self.assertEqual((view.region.x, view.region.y), corner)
        # The dialog's lists are covered, and the flyout says what the chord comes to and lists its own keys.
        self.assertNotIn(Column.BORROW_SCALE, self.dialog_text())
        self.assertIn(C_MINOR, self.dialog_text())
        self.assertIn(key_name(keybindings.ChordDialog.CLOSE_FLYOUT), self.dialog_text())

    async def test_the_dialog_is_one_size_on_every_list_wide_enough_for_the_most_keys_on_one_line(self):
        dialog = await self.open_on_scales()
        sizes = set()
        for _ in range(LISTS):
            lines = self.dialog_text().splitlines()
            sizes.add((len(lines), len(lines[0])))
            await self.press(keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(len(sizes), 1)
        # With the room this console has, the tension list's keys, the most, are on one line.
        dialog.part = TENSION_LIST
        self.assertEqual(len(dialog.legend_lines(dialog.wanted_width() - DIALOG_MARGIN)), 1)
        self.assertEqual(len(self.dialog_text().splitlines()[0]), dialog.wanted_width())

    async def test_the_pattern_shows_the_chord_as_the_choice_moves_and_escape_puts_it_back_with_no_undo_step(self):
        self.set(row=Row.CHORD, value=ChordSymbol.MAJOR)
        self.document.forget_history()
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        await self.press(Key.DOWN)
        moved_to = dialog.choice().quality
        self.assertNotEqual(moved_to, ChordSymbol.MAJOR)
        self.assertEqual(self.value(Row.CHORD), moved_to)
        # The flyout's cursor is shown too, before anything is picked.
        await self.press(Key.RIGHT, Key.RIGHT, *[Key.UP] * len(dialog.categories), Key.DOWN, keybindings.ChordDialog.OPEN)
        self.assertEqual(self.value(Row.CHORD_SCALE), COMMON_SCALE_TYPES[0])
        await self.press(keybindings.ChordDialog.CLOSE_FLYOUT)
        self.assertIsNone(self.value(Row.CHORD_SCALE))
        await self.press(keybindings.ChordDialog.CANCEL)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.CHORD_SCALE)), (ChordSymbol.MAJOR, None))
        self.assertFalse(self.document.can_undo())

    async def test_the_roll_draws_a_chords_tensions_and_a_borrowed_scales_notes_as_thin_lines(self):
        roll = self.editor.roll
        self.set(row=Row.CHORD, value=ChordSymbol.MAJOR)
        plain = roll.ghost_pitches(FIRST_STEP)
        self.set(row=Row.TENSION, value=(Tension.NINTH,))
        with_ninth = roll.ghost_pitches(FIRST_STEP)
        self.assertEqual(len(with_ninth - plain), 1)
        # The first step is degree 1, whose major chord has an E; drawn from C minor with the scale's own triad, it has an E flat, a half step lower.
        self.set(row=Row.TENSION, value=None)
        self.set(row=Row.CHORD, value=ChordSymbol.SCALE_TRIAD)
        own = roll.ghost_pitches(FIRST_STEP)
        self.set(row=Row.CHORD_SCALE, value=MINOR)
        self.assertEqual(sorted(roll.ghost_pitches(FIRST_STEP)), [min(own) - 1, max(own)])

    async def test_a_single_note_takes_no_tensions_from_the_dialog_and_says_nothing_on_the_status_line(self):
        self.assertEqual(self.editor.resting_status(), '')
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        self.app.screen.picked = set(ALTERED)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertIsNone(self.value(Row.TENSION))

    async def test_the_whole_choice_is_one_step_of_undo(self):
        before = self.document.song().get_pattern(TUNE).to_data()
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        dialog.places[QUALITY_LIST] = dialog.qualities.index(ChordSymbol.DOMINANT7)
        dialog.picked = set(ALTERED)
        dialog.set_kind(MINOR)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertNotEqual(self.document.song().get_pattern(TUNE).to_data(), before)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.song().get_pattern(TUNE).to_data(), before)


class TestChordDialogOnASmallConsole(TestPatternEditorChords):
    """The Chord dialog and every flyout on the smallest console, 80 by 24, where the keys take two lines."""

    SIZE = (CONSOLE_WIDTH, CONSOLE_LINES)
    # Two tests of the class above are about a console with room to spare, and the test below says the same of this one.
    test_a_flyout_is_a_box_of_the_dialogs_size_stacked_over_it_and_the_dialog_stays_where_it_was = None
    test_the_dialog_is_one_size_on_every_list_wide_enough_for_the_most_keys_on_one_line = None

    async def test_the_dialog_is_one_size_on_every_list_and_every_flyout_is_whole_on_the_console(self):
        dialog = await self.open_on_scales()
        sizes = set()
        for _ in range(LISTS):
            lines = self.dialog_text().splitlines()
            sizes.add((len(lines), len(lines[0])))
            await self.press(keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(len(sizes), 1)
        box = dialog.query_one(DIALOG_SELECTOR)
        corner = (box.region.x, box.region.y)
        for row in range(1, len(dialog.categories) + 1):
            dialog.places[SCALE_LIST] = row
            dialog.open_row()
            text = self.dialog_text()
            await self.settle()
            # The dialog's corner has not moved, and the stack's last column and line are on the console.
            self.assertEqual((box.region.x, box.region.y), corner, row)
            self.assertLessEqual(box.region.x + box.region.width, CONSOLE_WIDTH, row)
            self.assertLessEqual(box.region.y + box.region.height, CONSOLE_LINES, row)
            self.assertEqual((box.region.width, box.region.height), (max(len(line) for line in text.splitlines()), len(text.splitlines())), row)
            self.assertEqual(text.splitlines()[-1].strip()[-1], Box.HEAVY_BOTTOM_RIGHT, row)
            for kind in dialog.kinds_of_row(row):
                self.assertIn(words(kind).title(), text, kind)
            self.assertIn(key_name(keybindings.ChordDialog.CLOSE_FLYOUT), text, row)
            dialog.close_flyout()


class TestScaleCategories(unittest.TestCase):

    def test_every_scale_type_is_in_one_category_after_common_and_common_repeats_some(self):
        listed = [kind for _, kinds in SORTED_SCALE_CATEGORIES for kind in kinds]
        self.assertEqual(sorted(listed), sorted(set(scale_type_names())))
        self.assertEqual(SCALE_TYPES_IN_ORDER, listed)
        self.assertEqual(len(listed), len(set(listed)))
        self.assertTrue(set(COMMON_SCALE_TYPES) <= set(listed))
        self.assertEqual(SCALE_CATEGORIES[0], (MSG_SCALE_CATEGORY_COMMON, COMMON_SCALE_TYPES))
