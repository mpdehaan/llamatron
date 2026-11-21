# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A chord in the pattern editor: the Scale and Tension rows beside the Chord row, each stepped and
cleared, the Chord dialog all three open with its three lists, what the dialog says of the chord as the choice moves, the
status line naming the chord under the cursor, and the whole choice as one step of undo."""

import unittest
from unittest import mock

from llamatron.composition import limits, setlist
from llamatron.composition.file_format import ChordSymbol, Row, ScaleKind, Tension
from llamatron.composition.named_scale import scale_type_name, scale_type_names
from llamatron.composition.naming import words
from llamatron.music.scale import ScaleType
from llamatron.strings import labels, marks, messages
from llamatron.tui import drawing, keybindings, scale_categories
from llamatron.tui.dialogs import chord_dialog, dialog as dialog_values
from llamatron.tui.dialogs.chord_dialog import ChordDialog
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from tests.support import ui_testing
from tests.support.ui_testing import key_name, UITest

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
# The keyboard's lines that hold keys, the black and the white, and the notes of a major chord.
KEYBOARD_ROWS_OF_KEYS = 2
MAJOR_TRIAD_NOTES = 3
SCALES_OF_PATTERN = 'scales_of_pattern'


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
        return self.document.step_value(name=ui_testing.TUNE, row=row, step=FIRST_STEP)

    def set(self, *, row, value):
        self.document.change(self.document.get_setlist().get_pattern(ui_testing.TUNE).set_value, row=row, step=FIRST_STEP, value=value)

    def dialog_text(self):
        self.app.screen.draw()
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_the_scale_row_steps_through_the_scale_types_and_clears(self):
        await self.go_to_row(Row.CHORD_SCALE)
        await self.press(keybindings.ChordScaleRow.NEXT)
        self.assertEqual(self.value(Row.CHORD_SCALE), scale_categories.SCALE_TYPES_IN_ORDER[0])
        await self.press(keybindings.ChordScaleRow.MORE, keybindings.ChordScaleRow.LESS, keybindings.ChordScaleRow.LESS)
        self.assertIsNone(self.value(Row.CHORD_SCALE))
        # The scale types stop at the last and never go round to none, and [ goes back from the last.
        self.set(row=Row.CHORD_SCALE, value=scale_categories.SCALE_TYPES_IN_ORDER[-1])
        await self.press(keybindings.ChordScaleRow.MORE, keybindings.ChordScaleRow.NEXT)
        self.assertEqual(self.value(Row.CHORD_SCALE), scale_categories.SCALE_TYPES_IN_ORDER[-1])
        await self.press(keybindings.ChordScaleRow.LESS)
        self.assertEqual(self.value(Row.CHORD_SCALE), scale_categories.SCALE_TYPES_IN_ORDER[-2])
        self.set(row=Row.CHORD_SCALE, value=MINOR)
        self.assertEqual(self.editor.row_for(Row.CHORD_SCALE).cell_text(step=FIRST_STEP), SCALE_CELL)
        await self.press(keybindings.ChordScaleRow.CLEAR)
        self.assertIsNone(self.value(Row.CHORD_SCALE))

    async def test_the_tension_row_needs_a_chord_and_steps_through_each_tension_alone(self):
        self.assertEqual(self.editor.row_for(Row.TENSION).cell_lines(step=FIRST_STEP), [marks.MSG_BLOCKED_CELL])
        self.set(row=Row.CHORD, value=ChordSymbol.DOMINANT7)
        await self.go_to_row(Row.TENSION)
        await self.press(keybindings.TensionRow.NEXT)
        self.assertEqual(self.value(Row.TENSION), (Tension.FLAT_NINTH,))
        await self.press(keybindings.TensionRow.MORE)
        self.assertEqual(self.value(Row.TENSION), (Tension.NINTH,))
        self.set(row=Row.TENSION, value=ALTERED)
        self.assertEqual(self.editor.row_for(Row.TENSION).cell_text(step=FIRST_STEP), ' '.join(ALTERED))
        self.set(row=Row.TENSION, value=THREE_TENSIONS)
        self.assertEqual(self.editor.row_for(Row.TENSION).cell_text(step=FIRST_STEP), marks.MSG_TENSIONS_COUNTED.format(count=len(THREE_TENSIONS)))
        # Several tensions are no step of the cycle, so stepping starts again from none.
        await self.press(keybindings.TensionRow.MORE)
        self.assertEqual(self.value(Row.TENSION), (Tension.FLAT_NINTH,))

    async def test_each_row_opens_the_dialog_on_its_own_list(self):
        self.set(row=Row.CHORD, value=ChordSymbol.DOMINANT7)
        for row, part in ((Row.CHORD_SCALE, chord_dialog.SCALE_LIST), (Row.CHORD, chord_dialog.QUALITY_LIST), (Row.TENSION, chord_dialog.TENSION_LIST)):
            await self.go_to_row(row)
            await self.press(keybindings.ChordRow.CHOOSE)
            self.assertIsInstance(self.app.screen, ChordDialog, row)
            self.assertEqual(self.app.screen.part, part, row)
            self.assertIn(messages.MSG_CHORD_DIALOG_TITLE.format(where=messages.MSG_CHORD_OF_STEP.format(step=FIRST_STEP + 1, pattern=ui_testing.TUNE)), self.dialog_text())
            await self.press(keybindings.ChordDialog.CANCEL)

    async def test_the_dialog_sets_all_three_rows_and_says_the_chord_as_the_choice_moves(self):
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        # A single note is said as a note, in the scale the pattern is known to play under.
        degree = self.value(Row.DEGREE)
        self.assertIn(messages.MSG_NOTE_SENTENCE.format(scale=C_MAJOR, degree=degree, name='')[:-1].rstrip(), self.dialog_text())
        dialog.places[chord_dialog.QUALITY_LIST] = dialog.qualities.index(ChordSymbol.DOMINANT7)
        dialog.picked = set(ALTERED)
        dialog.set_kind(MINOR)
        self.assertIn(C_MINOR, self.dialog_text())
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.TENSION), self.value(Row.CHORD_SCALE)), (ChordSymbol.DOMINANT7, ALTERED, MINOR))
        resting = self.editor.resting_status()
        self.assertTrue(resting.startswith(messages.MSG_RESTING_STEP.format(step=FIRST_STEP + 1)))
        for part in (C_MINOR, C_MAJOR, 'Dominant Seventh', 'b9'):
            self.assertIn(part, resting)
        self.assertIn(resting[:30], self.text())

    async def open_on_scales(self):
        self.set(row=Row.CHORD, value=ChordSymbol.SCALE_TRIAD)
        await self.go_to_row(Row.CHORD_SCALE)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        self.assertEqual((dialog.part, dialog.places[chord_dialog.SCALE_LIST]), (chord_dialog.SCALE_LIST, chord_dialog.NOT_BORROWED_ROW))
        return dialog

    async def test_a_category_opens_a_flyout_where_enter_picks_and_the_next_enter_takes_the_chord(self):
        dialog = await self.open_on_scales()
        # Down reaches Common, the first category, whose flyout opens on its first scale type, Minor.
        await self.press(Key.DOWN, keybindings.ChordDialog.OPEN)
        self.assertEqual(dialog.flyout, 1)
        self.assertIn(marks.MSG_FLYOUT_TITLE.format(name=labels.MSG_SCALE_CATEGORY_COMMON), self.dialog_text())
        # The sentences speak of the scale type under the flyout's cursor before it is picked.
        self.assertIn(C_MINOR, self.dialog_text())
        self.assertIsNone(dialog.kind)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertIsNone(dialog.flyout)
        self.assertEqual((dialog.kind, dialog.part), (scale_categories.COMMON_SCALE_TYPES[0], chord_dialog.QUALITY_LIST))
        self.assertIn(marks.MSG_FLYOUT_CHOSEN.format(name=labels.MSG_SCALE_CATEGORY_COMMON, chosen=SCALE_CELL), self.dialog_text())
        # Every category is drawn as a button, and only the one whose scale type was picked carries the mark.
        for name, _ in dialog.categories:
            if name != labels.MSG_SCALE_CATEGORY_COMMON:
                self.assertIn(marks.MSG_FLYOUT_CLOSED.format(name=name), self.dialog_text(), name)
        self.assertEqual(self.dialog_text().count(FLYOUT_MARK), 1)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.value(Row.CHORD_SCALE), MINOR)

    async def test_escape_and_left_close_the_flyout_and_change_nothing_and_its_cursor_stops_at_its_edges(self):
        dialog = await self.open_on_scales()
        await self.press(Key.DOWN, keybindings.ChordDialog.OPEN, Key.UP)
        self.assertEqual(dialog.flyout_place, 0)
        await self.press(*[Key.DOWN] * (len(scale_categories.COMMON_SCALE_TYPES) + 1), Key.RIGHT)
        self.assertEqual(dialog.flyout_place, len(scale_categories.COMMON_SCALE_TYPES) - 1)
        await self.press(keybindings.ChordDialog.CLOSE_FLYOUT)
        self.assertIsInstance(self.app.screen, ChordDialog)
        self.assertEqual((dialog.flyout, dialog.kind), (None, None))
        await self.press(keybindings.ChordDialog.OPEN, Key.LEFT)
        self.assertEqual((dialog.flyout, dialog.part), (None, chord_dialog.SCALE_LIST))
        self.assertNotIn(C_MINOR, self.dialog_text())

    async def test_the_dialog_opens_on_the_category_of_the_scale_borrowed_and_its_flyout_on_that_scale(self):
        self.set(row=Row.CHORD_SCALE, value=ScaleKind.LYDIAN_DOMINANT)
        self.set(row=Row.CHORD, value=ChordSymbol.SCALE_TRIAD)
        await self.go_to_row(Row.CHORD_SCALE)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        name, kinds = dialog.categories[dialog.places[chord_dialog.SCALE_LIST] - 1]
        self.assertIn(ScaleKind.LYDIAN_DOMINANT, kinds)
        await self.press(keybindings.ChordDialog.OPEN)
        self.assertEqual(kinds[dialog.flyout_place], ScaleKind.LYDIAN_DOMINANT)
        # The row that borrows none takes the scale away and goes on to the qualities.
        await self.press(keybindings.ChordDialog.CLOSE_FLYOUT, *[Key.UP] * len(dialog.categories), keybindings.ChordDialog.OPEN)
        self.assertEqual((dialog.kind, dialog.part), (None, chord_dialog.QUALITY_LIST))

    async def test_a_flyout_is_a_box_of_the_dialogs_size_stacked_over_it_and_the_dialog_stays_where_it_was(self):
        dialog = await self.open_on_scales()
        closed = self.dialog_text().splitlines()
        view = dialog.query_one(dialog_values.DIALOG_SELECTOR)
        await self.settle()
        corner = (view.region.x, view.region.y)
        await self.press(Key.DOWN, keybindings.ChordDialog.OPEN)
        stacked = self.dialog_text().splitlines()
        await self.settle()
        # The stack is the dialog and a box as large, FLYOUT_SHIFT down and to the right, and the dialog's corner has not moved.
        self.assertEqual(len(stacked), len(closed) + dialog_values.FLYOUT_SHIFT)
        self.assertEqual(max(len(line) for line in stacked), len(closed[0]) + dialog_values.FLYOUT_SHIFT)
        self.assertEqual(stacked[0].rstrip(), closed[0])
        self.assertEqual(stacked[dialog_values.FLYOUT_SHIFT][dialog_values.FLYOUT_SHIFT:], closed[0])
        self.assertEqual(stacked[-1].strip(), closed[-1])
        self.assertEqual((view.region.x, view.region.y), corner)
        # The dialog's lists are covered, and the flyout says what the chord comes to and lists its own keys.
        self.assertNotIn(labels.Column.BORROW_SCALE, self.dialog_text())
        self.assertIn(C_MINOR, self.dialog_text())
        self.assertIn(key_name(keybindings.ChordDialog.CLOSE_FLYOUT), self.dialog_text())

    async def test_the_dialog_is_one_size_on_every_list_wide_enough_for_the_most_keys_on_one_line(self):
        dialog = await self.open_on_scales()
        sizes = set()
        for _ in range(chord_dialog.LISTS):
            lines = self.dialog_text().splitlines()
            sizes.add((len(lines), len(lines[0])))
            await self.press(keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(len(sizes), 1)
        # With the room this console has, the tension list's keys, the most, are on one line.
        dialog.part = chord_dialog.TENSION_LIST
        self.assertEqual(len(dialog.legend_lines(dialog.wanted_width() - dialog_values.DIALOG_MARGIN)), 1)
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
        await self.press(*[Key.RIGHT] * chord_dialog.LISTS, *[Key.UP] * len(dialog.categories), Key.DOWN, keybindings.ChordDialog.OPEN)
        self.assertEqual(self.value(Row.CHORD_SCALE), scale_categories.COMMON_SCALE_TYPES[0])
        await self.press(keybindings.ChordDialog.CLOSE_FLYOUT)
        self.assertIsNone(self.value(Row.CHORD_SCALE))
        await self.press(keybindings.ChordDialog.CANCEL)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.CHORD_SCALE)), (ChordSymbol.MAJOR, None))
        self.assertFalse(self.document.can_undo())

    async def test_an_inversion_is_chosen_in_the_dialog_with_the_chord_and_a_single_note_takes_none(self):
        self.set(row=Row.CHORD, value=ChordSymbol.MAJOR)
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        self.assertEqual(dialog.inversions, [None, *limits.INVERSIONS])
        # Right reaches the inversions, where the cursor's row is the choice, shown in the pattern underneath as it moves.
        await self.press(Key.RIGHT, Key.DOWN, Key.DOWN)
        self.assertEqual((dialog.part, dialog.choice().inversion), (chord_dialog.INVERSION_LIST, limits.INVERSIONS[1]))
        self.assertEqual(self.value(Row.INVERSION), limits.INVERSIONS[1])
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.INVERSION)), (ChordSymbol.MAJOR, limits.INVERSIONS[1]))
        # The dialog opens on the step's inversion, and a single note keeps none.
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        self.assertEqual(dialog.places[chord_dialog.INVERSION_LIST], dialog.inversions.index(limits.INVERSIONS[1]))
        await self.press(*[Key.UP] * len(dialog.qualities), keybindings.ChordDialog.CHOOSE)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.INVERSION)), (None, None))

    async def test_a_note_placed_on_a_chords_step_on_the_roll_moves_the_root_and_erasing_removes_the_chord(self):
        self.set(row=Row.CHORD, value=ChordSymbol.MAJOR)
        self.set(row=Row.INVERSION, value=limits.INVERSIONS[0])
        degree = self.value(Row.DEGREE)
        await self.press(keybindings.PatternEditor.TO_ROLL)
        # Two rows above the chord's note, on the chord's step, the pencil moves the root there and keeps the chord.
        await self.press(Key.UP, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.value(Row.DEGREE), degree + 2)
        self.assertEqual((self.value(Row.CHORD), self.value(Row.INVERSION)), (ChordSymbol.MAJOR, limits.INVERSIONS[0]))
        # On the note, the pencil erases it, the chord with it, and the next note drawn is a single note.
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual((self.value(Row.DEGREE), self.value(Row.CHORD)), (None, None))
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual((self.value(Row.DEGREE), self.value(Row.CHORD)), (degree + 2, None))

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
        before = self.document.song().get_pattern(ui_testing.TUNE).to_data()
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        dialog = self.app.screen
        dialog.places[chord_dialog.QUALITY_LIST] = dialog.qualities.index(ChordSymbol.DOMINANT7)
        dialog.picked = set(ALTERED)
        dialog.set_kind(MINOR)
        await self.press(keybindings.ChordDialog.CHOOSE)
        self.assertNotEqual(self.document.song().get_pattern(ui_testing.TUNE).to_data(), before)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.song().get_pattern(ui_testing.TUNE).to_data(), before)


    async def open_on_the_chord(self):
        await self.go_to_row(Row.CHORD)
        await self.press(keybindings.ChordRow.CHOOSE)
        self.assertIsInstance(self.app.screen, ChordDialog)
        return self.app.screen

    def keyboard_lines(self):
        """Return the dialog's lines that hold the keyboard's keys, and the number of the first."""
        lines = self.dialog_text().splitlines()
        numbers = [number for number, line in enumerate(lines) if marks.MSG_KEY_OF_SCALE_OUTLINED in line or marks.MSG_KEY_OUT_OF_SCALE in line]
        return [lines[number] for number in numbers], (numbers[0] if numbers else None)

    async def test_the_keyboard_under_the_sentences_outlines_the_scale_and_fills_the_chord_one_blank_line_down(self):
        # Where the pattern's scale is known for certain and the console has room, a keyboard under the
        # sentences, one blank line down, the scale's keys outlined and the chord's filled. It takes no key.
        dialog = await self.open_on_the_chord()
        keys_before = [item.keys for item in dialog.keys()]
        height = len(self.dialog_text().splitlines())
        keyboard, first = self.keyboard_lines()
        self.assertEqual(len(keyboard), KEYBOARD_ROWS_OF_KEYS)
        # A single note: one key filled.
        self.assertEqual(drawing.NOTHING.join(keyboard).count(marks.MSG_KEY_IN_CHORD), 1)
        lines = self.dialog_text().splitlines()
        self.assertEqual(lines[first - 1].strip(Box.HEAVY_BAR + drawing.SPACE), drawing.NOTHING)
        self.assertNotEqual(lines[first - 2].strip(Box.HEAVY_BAR + drawing.SPACE), drawing.NOTHING)
        # Major: three keys filled, and the dialog is as tall as it was, the keyboard still one blank line under the last sentence.
        await self.press(Key.DOWN)
        keyboard, first = self.keyboard_lines()
        self.assertEqual(drawing.NOTHING.join(keyboard).count(marks.MSG_KEY_IN_CHORD), MAJOR_TRIAD_NOTES)
        lines = self.dialog_text().splitlines()
        self.assertEqual(len(lines), height)
        self.assertEqual(lines[first - 1].strip(Box.HEAVY_BAR + drawing.SPACE), drawing.NOTHING)
        self.assertNotEqual(lines[first - 2].strip(Box.HEAVY_BAR + drawing.SPACE), drawing.NOTHING)
        self.assertEqual([item.keys for item in dialog.keys()], keys_before)

    async def test_no_keyboard_where_the_patterns_uses_play_it_under_more_than_one_scale(self):
        with mock.patch.object(type(self.document), SCALES_OF_PATTERN, return_value=[setlist.DEFAULT_SCALE, C_MINOR]):
            await self.open_on_the_chord()
            self.assertEqual(self.keyboard_lines(), ([], None))


class TestChordDialogOnASmallConsole(TestPatternEditorChords):
    """The Chord dialog and every flyout on the smallest console, 80 by 24, where the keys take two lines."""

    SIZE = (CONSOLE_WIDTH, CONSOLE_LINES)
    # Two tests of the class above are about a console with room to spare, and the test below says the same of this one.
    test_a_flyout_is_a_box_of_the_dialogs_size_stacked_over_it_and_the_dialog_stays_where_it_was = None
    test_the_dialog_is_one_size_on_every_list_wide_enough_for_the_most_keys_on_one_line = None
    test_the_keyboard_under_the_sentences_outlines_the_scale_and_fills_the_chord_one_blank_line_down = None

    async def test_a_console_with_no_room_has_no_keyboard_under_the_sentences(self):
        await self.open_on_the_chord()
        self.assertEqual(self.keyboard_lines(), ([], None))

    async def test_the_dialog_is_one_size_on_every_list_and_every_flyout_is_whole_on_the_console(self):
        dialog = await self.open_on_scales()
        sizes = set()
        for _ in range(chord_dialog.LISTS):
            lines = self.dialog_text().splitlines()
            sizes.add((len(lines), len(lines[0])))
            await self.press(keybindings.ChordDialog.NEXT_LIST)
        self.assertEqual(len(sizes), 1)
        box = dialog.query_one(dialog_values.DIALOG_SELECTOR)
        corner = (box.region.x, box.region.y)
        for row in range(1, len(dialog.categories) + 1):
            dialog.places[chord_dialog.SCALE_LIST] = row
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
        listed = [kind for _, kinds in scale_categories.SORTED_SCALE_CATEGORIES for kind in kinds]
        self.assertEqual(sorted(listed), sorted(set(scale_type_names())))
        self.assertEqual(scale_categories.SCALE_TYPES_IN_ORDER, listed)
        self.assertEqual(len(listed), len(set(listed)))
        self.assertTrue(set(scale_categories.COMMON_SCALE_TYPES) <= set(listed))
        self.assertEqual(scale_categories.SCALE_CATEGORIES[0], (labels.MSG_SCALE_CATEGORY_COMMON, scale_categories.COMMON_SCALE_TYPES))
