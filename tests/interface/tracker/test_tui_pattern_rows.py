# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Kinds of row in the pattern editor: the limits a file holds a row to, the statement rows, the Tie row, and a drum pattern's rows."""

from llamatron.interface.forms import grouped_choices
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.pattern.pattern_editor import Reconfigure
from llamatron.model.objects import conditions
from llamatron.model.schema import file_format, limits, row_descriptions
from llamatron.model.schema.file_format import Operator, Row, StatementPart, StepStatement
from llamatron.model.schema.row_descriptions import RowOfNumbers
from llamatron.model.values.note import NoteName
from llamatron.user_strings import errors, labels as labels_text, legends, marks, messages
from tests.support import ui_testing
from tests.support.pattern_editor_testing import PatternEditorTest
from tests.support.rendering import render_song
from tests.support.ui_testing import UITest

BEAT = 'beat'
TUNE = 'tune'
# Where a test saves the set to read the file back.
SAVED_SET = 'saved.yml'
# The step of tune that holds nothing.
EMPTY_STEP = 2
# A number typed into a statement.
TYPED_NUMBER = 12


class TestTheRowsLimitsAreTheFiles(PatternEditorTest):
    """A row of numbers stops where the row's one description says, which is what a file's values are checked against (model/schema/row_descriptions.py)."""

    async def test_every_row_of_numbers_stops_at_the_limits_a_file_is_checked_against(self):
        for name, described in row_descriptions.ROW_DESCRIPTIONS.items():
            if type(described) is not RowOfNumbers:
                continue
            with self.subTest(row=name):
                await self.go_to_row(name)
                self.assertEqual(self.editor.row_for(name).range(), (described.get_lowest(), described.get_highest()))
                self.editor.set_value(value=described.get_highest())
                await self.press(keybindings.NumberRow.MORE)
                self.assertEqual(self.value(row=name), described.get_highest())
                self.editor.set_value(value=described.get_lowest())
                await self.press(keybindings.NumberRow.LESS)
                self.assertEqual(self.value(row=name), described.get_lowest())

    async def test_what_the_editor_can_set_on_every_row_is_what_a_file_may_hold(self):
        for name, described in row_descriptions.ROW_DESCRIPTIONS.items():
            if type(described) is RowOfNumbers:
                await self.go_to_row(name)
                self.editor.set_value(value=described.get_highest())
        self.document.save(path=SAVED_SET)
        self.assertEqual(Document.load_or_correct(SAVED_SET)[1], [])

    async def test_a_blank_step_shows_a_dot_only_where_a_blank_changes_nothing(self):
        for name, described in row_descriptions.ROW_DESCRIPTIONS.items():
            if type(described) is not RowOfNumbers:
                continue
            with self.subTest(row=name):
                row = self.editor.row_for(name)
                self.editor.set_value(value=None, row=name)
                shown = row.cell_text(step=self.editor.step)
                self.assertEqual(shown, marks.MSG_UNSET_MARK if described.is_quiet() else str(described.get_default()))


class TestStatementRows(PatternEditorTest):
    """The five rows of Stop When, Restart When and Mute When write one statement on a step, part by part."""

    async def test_a_draw_starts_a_statement_and_the_other_rows_then_take_their_parts(self):
        for kind, rows in file_format.STATEMENT_ROWS.items():
            with self.subTest(kind=kind):
                drawn_row, operator_row, value_row, comparison_row, against_row = rows
                await self.go_to_row(drawn_row)
                await self.press(Key.RIGHT)
                for row in rows[1:]:
                    self.assertTrue(self.editor.row_for(row).blocked())
                await self.press(keybindings.StatementRow.NEXT)
                # The first name in the order the picker lists them.
                started = conditions.new_statement(grouped_choices.VALUE_NAMES_IN_ORDER[0])
                self.assertEqual(self.statement(kind), started)
                self.assertFalse(self.editor.row_for(value_row).blocked())
                self.assertTrue(self.editor.row_for(comparison_row).blocked())
                await self.go_to_row(value_row)
                await self.press(keybindings.StatementRow.MORE, keybindings.StatementRow.MORE, keybindings.StatementRow.LESS)
                self.assertEqual(self.statement(kind)[StatementPart.VALUE], started[StatementPart.VALUE] + 1)
                await self.go_to_row(operator_row)
                for _ in range(file_format.OPERATORS.index(Operator.PLUS) - file_format.OPERATORS.index(started[StatementPart.OPERATOR])):
                    await self.press(keybindings.StatementRow.MORE)
                self.assertEqual(self.statement(kind)[StatementPart.OPERATOR], Operator.PLUS)
                self.assertFalse(self.editor.row_for(comparison_row).blocked())
                self.assertFalse(self.editor.row_for(against_row).blocked())
                await self.go_to_row(comparison_row)
                await self.press(keybindings.StatementRow.NEXT)
                self.assertIn(self.statement(kind)[StatementPart.COMPARISON], file_format.RESULT_COMPARISONS)
                await self.press(keybindings.StatementRow.CLEAR)
                self.assertIsNone(self.statement(kind))
                await self.press(Key.LEFT)

    async def test_a_choice_stops_at_each_end_of_its_list(self):
        drawn_row, operator_row = file_format.STATEMENT_ROWS[StepStatement.MUTE][:2]
        await self.go_to_row(drawn_row)
        await self.press(keybindings.StatementRow.LESS)
        self.assertIsNone(self.statement(StepStatement.MUTE))
        for _ in range(len(grouped_choices.VALUE_NAMES_IN_ORDER) + 1):
            await self.press(keybindings.StatementRow.MORE)
        self.assertEqual(self.statement(StepStatement.MUTE)[StatementPart.REGISTER], grouped_choices.VALUE_NAMES_IN_ORDER[-1])
        await self.go_to_row(operator_row)
        for _ in range(len(file_format.OPERATORS)):
            await self.press(keybindings.StatementRow.LESS)
        self.assertEqual(self.statement(StepStatement.MUTE)[StatementPart.OPERATOR], file_format.OPERATORS[0])

    async def test_the_value_picker_heads_the_constant_and_the_draws_and_the_cursor_passes_over_the_headings(self):
        drawn_row, _, value_row = file_format.STATEMENT_ROWS[StepStatement.MUTE][:3]
        await self.go_to_row(drawn_row)
        await self.press(keybindings.StatementRow.NEXT)
        await self.go_to_row(value_row)
        await self.press(keybindings.StatementRow.CHOOSE)
        for heading in (labels_text.MSG_PICKER_CONSTANT_HEADING, labels_text.MSG_PICKER_DRAWS_HEADING):
            self.assertIn(heading, self.text())
        # From the number to type, Down passes the blank line and the draws' heading, and as many more reach the last draw.
        await self.press(*[Key.DOWN] * len(file_format.DRAW_NAMES), Key.ENTER)
        self.assertEqual(self.statement(StepStatement.MUTE)[StatementPart.VALUE], file_format.DRAW_NAMES[-1])

    async def test_the_picker_chooses_a_draw_and_a_number_or_a_draw_to_compare_with(self):
        drawn_row, _, value_row = file_format.STATEMENT_ROWS[StepStatement.STOP][:3]
        await self.go_to_row(drawn_row)
        # The picker lists the draws under their heading, which the cursor passes over.
        await self.press(keybindings.StatementRow.CHOOSE, Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.statement(StepStatement.STOP)[StatementPart.REGISTER], grouped_choices.VALUE_NAMES_IN_ORDER[1])
        await self.go_to_row(value_row)
        await self.press(keybindings.StatementRow.CHOOSE, Key.DOWN, Key.ENTER)
        self.assertEqual(self.statement(StepStatement.STOP)[StatementPart.VALUE], grouped_choices.VALUE_NAMES_IN_ORDER[0])
        await self.press(keybindings.StatementRow.CHOOSE, Key.UP, Key.ENTER)
        await self.type(str(TYPED_NUMBER))
        await self.press(Key.ENTER)
        self.assertEqual(self.statement(StepStatement.STOP)[StatementPart.VALUE], TYPED_NUMBER)
        await self.press(keybindings.StatementRow.CHOOSE, Key.ENTER)
        await self.type(str(limits.MAX_STATEMENT_NUMBER + 1))
        await self.press(Key.ENTER)
        self.assertEqual(self.statement(StepStatement.STOP)[StatementPart.VALUE], TYPED_NUMBER)

    async def test_a_statement_cannot_divide_by_zero(self):
        drawn_row, _, value_row = file_format.STATEMENT_ROWS[StepStatement.MUTE][:3]
        await self.go_to_row(drawn_row)
        await self.press(keybindings.StatementRow.NEXT)
        self.document.change_pattern(self.document.pattern(self.editor.item).set_statement, kind=StepStatement.MUTE, step=self.editor.step, statement=conditions.with_operator(statement=self.statement(StepStatement.MUTE), operator=Operator.REMAINDER))
        await self.go_to_row(value_row)
        await self.press(keybindings.StatementRow.LESS)
        self.assertNotEqual(self.statement(StepStatement.MUTE)[StatementPart.VALUE], 0)
        self.assertIn(errors.ERR_CANNOT_DIVIDE_BY_ZERO, self.text())

    async def test_the_first_step_cannot_start_the_pattern_over(self):
        for row in file_format.STATEMENT_ROWS[StepStatement.RESTART]:
            self.assertTrue(self.editor.row_for(row).blocked(step=0))
        self.assertFalse(self.editor.row_for(file_format.STATEMENT_ROWS[StepStatement.RESTART][0]).blocked(step=EMPTY_STEP))

    async def test_an_empty_step_holds_a_statement_and_clearing_a_note_keeps_one(self):
        drawn_row = file_format.STATEMENT_ROWS[StepStatement.MUTE][0]
        self.assertFalse(self.editor.row_for(drawn_row).blocked(step=EMPTY_STEP))
        await self.go_to_row(drawn_row)
        await self.press(keybindings.StatementRow.NEXT)
        self.document.change_pattern(self.document.pattern(self.editor.item).clear_sound, self.editor.step)
        self.assertIsNotNone(self.statement(StepStatement.MUTE))

    def statement(self, kind):
        return self.editor.pattern().get_statement(kind=kind, step=self.editor.step)


class TestDrumPatterns(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_patterns_on(BEAT)
        await self.press(Key.ENTER)
        self.editor = self.app.screen

    def value(self, row):
        return self.document.step_value(name=BEAT, row=row, step=self.editor.step)

    async def test_takes_letters_in_upper_or_lower_case(self):
        await self.press(Key.RIGHT, NoteName.F.lower())
        self.assertEqual(self.value(Row.DEGREE), NoteName.F)
        await self.press(NoteName.G)
        self.assertEqual(self.value(Row.DEGREE), NoteName.G)

    async def test_a_new_hit_gets_the_drum_octave(self):
        self.document.change_set(self.document.get_setlist().set_default_drum_octave, 2)
        await self.press(keybindings.PatternRows.INSERT_STEP, NoteName.C.lower())
        self.assertEqual(self.value(Row.OCTAVE), 2)

    async def test_has_no_chord_row(self):
        self.assertNotIn(Row.CHORD, [row.name for row in self.editor.rows_view.reachable()])
        self.assertIn('│ Note', self.text())

    async def test_numbers_do_nothing(self):
        await self.press('5')
        self.assertEqual(self.value(Row.DEGREE), NoteName.C)

    async def test_the_toggle_asks_before_clearing_notes(self):
        await self.reconfigure(Reconfigure.DRUM)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(ui_testing.ANSWER_NO)
        self.assertTrue(self.document.get_setlist().get_pattern(BEAT).is_drum())
        await self.reconfigure(Reconfigure.DRUM)
        await self.press(*ui_testing.ANSWER_YES)
        self.assertFalse(self.document.get_setlist().get_pattern(BEAT).is_drum())
        self.assertFalse(self.document.has_notes(BEAT))

    async def test_it_builds(self):
        await self.press(Key.RIGHT, NoteName.F.lower())
        render_song(self.document.song())


class TestTieRow(UITest):
    """Tie is on the normal rows, works only on empty steps, and holds the note before it."""

    EMPTY_STEP = 2

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen
        while self.editor.row_name() != Row.TIE:
            await self.press(Key.DOWN)

    def tie(self, step):
        return self.document.step_value(name=TUNE, row=Row.TIE, step=step)

    async def test_it_is_a_normal_row_and_toggles_on_an_empty_step(self):
        self.assertIn(ui_testing.ROW_SHOWN.format(label=labels_text.MSG_ROW_LABELS[Row.TIE]), self.text())
        await self.press(*[Key.RIGHT] * self.EMPTY_STEP)
        await self.press(Key.SPACE)
        self.assertIs(self.tie(self.EMPTY_STEP), True)
        # The tied step shows the toggle mark, the dividers stay, and a note's own step draws no tie: it can't take one.
        tie = self.editor.row_for(Row.TIE)
        self.assertEqual(tie.cell_text(step=self.EMPTY_STEP), marks.MSG_TOGGLE_ON)
        self.assertEqual(tie.cell_lines(step=self.EMPTY_STEP - 1), [marks.MSG_BLOCKED_CELL])
        self.assertEqual(tie.cell_lines(step=0), [marks.MSG_BLOCKED_CELL])
        self.assertIn(messages.MSG_DESCRIBE_TIED.format(step=self.EMPTY_STEP + 1), self.text())
        render_song(self.document.song())
        await self.press(Key.BACKSPACE)
        self.assertIs(self.tie(self.EMPTY_STEP), False)

    async def test_a_step_with_a_note_has_no_tie_keys(self):
        labels = [item.shown_label() for item in self.editor.key_table()]
        self.assertNotIn(legends.KeyName.SPACE, labels)
        await self.press(Key.SPACE)
        self.assertFalse(self.tie(0))

    async def test_typing_a_degree_on_a_tied_step_removes_the_tie(self):
        await self.press(*[Key.RIGHT] * self.EMPTY_STEP, Key.SPACE)
        while self.editor.row_name() != Row.DEGREE:
            await self.press(Key.UP)
        await self.press('5')
        self.assertIs(self.tie(self.EMPTY_STEP), False)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=self.EMPTY_STEP), 5)
        render_song(self.document.song())

    async def test_shortening_past_a_tie_asks_first(self):
        last = self.editor.step_count() - 1
        await self.press(*[Key.RIGHT] * last, Key.SPACE)
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = str(last)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
