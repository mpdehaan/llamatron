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

"""Kinds of row in the pattern editor: the limits a file holds a row to, the register rows, the Tie row, and a drum pattern's rows."""

from tests.support.ui_testing import ROW_SHOWN, UITest
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS, RowOfNumbers
from llamatron.composition.file_format import CONDITION_ROWS, REGISTER_ADD_ROWS, REGISTER_SET_ROWS, RegisterSetting, Comparison, RegisterName, Row
from llamatron.music.note import NoteName
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.document import Document
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import Reconfigure
from llamatron.strings.errors import ERR_AT_ALLOWED_INC_MAX
from llamatron.strings.labels import MSG_ROW_LABELS
from llamatron.strings.legends import KeyName
from llamatron.strings.marks import MSG_UNSET_MARK, MSG_BLOCKED_CELL, MSG_TOGGLE_ON
from llamatron.strings.messages import MSG_DESCRIBE_TIED
from llamatron.tui import keybindings
from tests.support.rendering import render_song
from tests.support.pattern_editor_testing import PatternEditorTest

BEAT = 'beat'
TUNE = 'tune'
# Where a test saves the set to read the file back.
SAVED_SET = 'saved.yml'
# The step of tune that holds nothing.
EMPTY_STEP = 2
# The register rows whose line is narrower than a file allows, and an Allowed Inc Max narrower than the default.
NARROWER_ROWS = {*REGISTER_ADD_ROWS.values(), *REGISTER_SET_ROWS.values()}
NARROW_INC_MAX = 4
# What Space or Enter goes through on a condition row, from blank, and back to blank.
COMPARISON_CYCLE = [Comparison.LESS, Comparison.MORE, Comparison.SAME, None]


class TestTheRowsLimitsAreTheFiles(PatternEditorTest):
    """A row of numbers stops where the row's one description says, which is what a file's values are checked against (composition/row_descriptions.py)."""

    async def test_every_row_of_numbers_stops_at_the_limits_a_file_is_checked_against(self):
        for name, described in ROW_DESCRIPTIONS.items():
            # The register rows that change a register step through a shorter line than a file allows, by design: TestRegisterChangeRows holds them to it.
            if type(described) is not RowOfNumbers or name in NARROWER_ROWS:
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
        for name, described in ROW_DESCRIPTIONS.items():
            if type(described) is RowOfNumbers:
                await self.go_to_row(name)
                # A += row reaches only its register's Allowed Inc Max, which is what the file is held to for the songs that play the pattern.
                self.editor.set_value(value=self.editor.row_for(name).range()[1] if name in REGISTER_ADD_ROWS.values() else described.get_highest())
        self.document.save(path=SAVED_SET)
        self.assertEqual(Document.load_or_correct(SAVED_SET)[1], [])

    async def test_a_blank_step_shows_a_dot_only_where_a_blank_changes_nothing(self):
        for name, described in ROW_DESCRIPTIONS.items():
            if type(described) is not RowOfNumbers:
                continue
            with self.subTest(row=name):
                row = self.editor.row_for(name)
                self.editor.set_value(value=None, row=name)
                shown = row.cell_text(step=self.editor.step)
                self.assertEqual(shown, MSG_UNSET_MARK if described.is_quiet() else str(described.get_default()))


class TestRegisterChangeRows(PatternEditorTest):
    """The = rows step from blank through the current song's register, the += rows within the register's Allowed Inc Max, and the condition rows cycle their comparisons on a note's step alone."""

    async def test_an_add_row_stops_at_the_registers_allowed_inc_max_and_says_so(self):
        for register, name in REGISTER_ADD_ROWS.items():
            with self.subTest(row=name):
                most = self.document.song().get_register(register).get_allowed_inc_max()
                await self.go_to_row(name)
                self.assertEqual(self.editor.row_for(name).range(), (-most, most))
                self.editor.set_value(value=most)
                await self.press(keybindings.AddRow.MORE)
                self.assertEqual(self.value(row=name), most)
                self.assertIn(ERR_AT_ALLOWED_INC_MAX.format(register=register, most=most), self.text())

    async def test_a_narrower_allowed_inc_max_narrows_the_add_rows_line(self):
        self.document.set_register_setting(name=RegisterName.AX, setting=RegisterSetting.ALLOWED_INC_MAX, value=NARROW_INC_MAX)
        await self.go_to_row(Row.AX_ADD)
        self.assertEqual(self.editor.row_for(Row.AX_ADD).range(), (-NARROW_INC_MAX, NARROW_INC_MAX))

    async def test_a_set_row_steps_from_blank_to_the_registers_minimum_and_back(self):
        for register, name in REGISTER_SET_ROWS.items():
            with self.subTest(row=name):
                kept = self.document.song().get_register(register)
                await self.go_to_row(name)
                self.assertIsNone(self.value(row=name))
                await self.press(keybindings.SetRow.LESS)
                self.assertIsNone(self.value(row=name))
                await self.press(keybindings.SetRow.MORE)
                self.assertEqual(self.value(row=name), kept.get_minimum())
                self.editor.set_value(value=kept.get_maximum())
                await self.press(keybindings.SetRow.MORE)
                self.assertEqual(self.value(row=name), kept.get_maximum())
                self.editor.set_value(value=kept.get_minimum())
                await self.press(keybindings.SetRow.LESS)
                self.assertIsNone(self.value(row=name))
                await self.press(keybindings.SetRow.MORE, keybindings.SetRow.MORE, keybindings.SetRow.DEFAULT)
                self.assertIsNone(self.value(row=name))

    async def test_a_condition_cycles_its_comparisons_on_a_note_and_is_blocked_on_an_empty_step(self):
        for name in CONDITION_ROWS.values():
            with self.subTest(row=name):
                await self.go_to_row(name)
                seen = []
                for _ in range(len(COMPARISON_CYCLE)):
                    await self.press(keybindings.ConditionRow.NEXT)
                    seen.append(self.value(row=name))
                self.assertEqual(seen, COMPARISON_CYCLE)
                self.assertTrue(self.editor.row_for(name).blocked(step=EMPTY_STEP))


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
        self.document.set_default_drum_octave(2)
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
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertTrue(self.document.song().get_pattern(BEAT).is_drum())
        await self.reconfigure(Reconfigure.DRUM)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(self.document.song().get_pattern(BEAT).is_drum())
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
        self.assertIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.TIE]), self.text())
        await self.press(*[Key.RIGHT] * self.EMPTY_STEP)
        await self.press(Key.SPACE)
        self.assertIs(self.tie(self.EMPTY_STEP), True)
        # The tied step shows the toggle mark, the dividers stay, and a note's own step draws no tie: it can't take one.
        tie = self.editor.row_for(Row.TIE)
        self.assertEqual(tie.cell_text(step=self.EMPTY_STEP), MSG_TOGGLE_ON)
        self.assertIsNone(tie.edge_text(step=self.EMPTY_STEP))
        self.assertEqual(tie.cell_lines(step=self.EMPTY_STEP - 1), [MSG_BLOCKED_CELL])
        self.assertEqual(tie.cell_lines(step=0), [MSG_BLOCKED_CELL])
        self.assertIsNone(tie.edge_text(step=self.EMPTY_STEP - 1))
        self.assertIn(MSG_DESCRIBE_TIED.format(step=self.EMPTY_STEP + 1), self.text())
        render_song(self.document.song())
        await self.press(Key.BACKSPACE)
        self.assertIs(self.tie(self.EMPTY_STEP), False)

    async def test_a_step_with_a_note_has_no_tie_keys(self):
        labels = [item.shown_label() for item in self.editor.key_table()]
        self.assertNotIn(KeyName.SPACE, labels)
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
        last = self.editor.steps() - 1
        await self.press(*[Key.RIGHT] * last, Key.SPACE)
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = str(last)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
