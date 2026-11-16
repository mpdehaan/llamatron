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

"""What the pattern editor refuses, and says."""

from tests.support.ui_testing import fixed_text, ROW_SHOWN, UITest
from llamatron.composition.file_format import Row, Section
from llamatron.composition.limits import MAX_STEPS, MIN_STEPS
from llamatron.tui.drawing import NOTHING
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import Munge, PatternEditor, Reconfigure
from llamatron.strings.errors import ERR_NOTHING_AFTER, ERR_NOTHING_BEFORE, ERR_NOTHING_TO_PIVOT, ERR_ONE_STEP, ERR_STEPS_OUT_OF_RANGE
from llamatron.strings.labels import MSG_ROW_LABELS
from llamatron.strings.marks import MSG_MORE_AFTER, MSG_STEPS_SHOWN
from llamatron.strings.messages import MSG_CHANGE_TYPE_EMPTY_QUESTION
from llamatron.tui import keybindings
from tests.support.pattern_editor_testing import munge, open_section

BEAT = 'beat'
TUNE = 'tune'
OTHER = 'other'
ALREADY_IN_USE = 'already in use'
# A pattern too wide for the screen, and a step about halfway along it.
LONG = 64
NO_OTHER_PATTERNS_TO_LOAD = 'no other patterns to load'
LETTERS = 'letters'
# What the Patterns page's + calls the first new pattern, and C major's notes from the root, as the gauge labels its rows.
NEW_PATTERN = 'pattern 4'
LOTS = 'lots'
NOT_AN_INTEGER = 'is not an integer'
LOUD = 'loud'


class TestPatternEditorRefusals(UITest):

    async def open(self, name):
        """Open a pattern on its rows, which a drum pattern opens on and a note pattern reaches past its piano roll."""
        await self.open_patterns_on(name)
        await self.press(Key.ENTER)
        if not self.document.song().get_pattern(name).is_drum():
            await self.press(keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen
        self.assertIsInstance(self.editor, PatternEditor)

    async def go_to_row(self, name):
        """Move the cursor to a row, opening the section that has it first if it's closed."""
        if name not in [row.name for row in self.editor.rows_view.reachable()]:
            await open_section(test=self, section=self.editor.rows_view.section_of(name))
        names = [row.name for row in self.editor.rows_view.reachable()]
        while self.editor.rows_view.row != names.index(name):
            await self.press(Key.DOWN if self.editor.rows_view.row < names.index(name) else Key.UP)

    async def test_munging_says_when_there_is_nothing_to_move(self):
        await self.open(OTHER)
        for choice, message in [
            (Munge.REVERSE_AFTER, ERR_NOTHING_AFTER), (Munge.REVERSE_BEFORE, ERR_NOTHING_BEFORE), (Munge.REVERSE, ERR_ONE_STEP),
            (Munge.PIVOT, ERR_NOTHING_TO_PIVOT), (Munge.RANDOMIZE, ERR_ONE_STEP),
        ]:
            await munge(test=self, choice=choice)
            self.assertIn(message, self.text())

    async def test_load_over_needs_another_pattern(self):
        # Only one pattern can stay, so the scenes that play the others go first, as a person would have to delete them.
        for index in reversed(range(len(self.document.song().get_scenes()))):
            self.document.delete_scene(index)
        for name in self.document.song().get_pattern_names():
            if name != TUNE:
                self.document.delete_named(section=Section.PATTERNS, name=name)
        await self.open(TUNE)
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.assertIn(NO_OTHER_PATTERNS_TO_LOAD, self.text())

    async def test_load_over_a_pattern_with_notes_asks_first(self):
        await self.open(TUNE)
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.place = self.app.screen.options.index(OTHER)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_row(Row.DEGREE), [5])

    async def test_the_step_count_must_be_a_sensible_number(self):
        await self.open(TUNE)
        for text, message in [(LOTS, NOT_AN_INTEGER), ('0', ERR_STEPS_OUT_OF_RANGE.format(low=MIN_STEPS, high=MAX_STEPS))]:
            await self.press(keybindings.PatternEditor.RESIZE)
            self.app.screen.value = text
            await self.press(Key.ENTER)
            self.assertIn(message, self.text())
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 4)

    async def test_shortening_past_steps_that_hold_something_asks_first(self):
        await self.open(TUNE)
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = '1'
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 1)

    async def test_a_typed_velocity_must_be_in_range(self):
        await self.open(TUNE)
        await self.go_to_row(Row.VELOCITY)
        for text, message in [(LOUD, NOT_AN_INTEGER), ('200', 'Velocity must be from 1 to 127')]:
            await self.press(Key.ENTER)
            self.app.screen.value = text
            await self.press(Key.ENTER)
            self.assertIn(message, self.text())
        self.assertIsNone(self.document.step_value(name=TUNE, row=Row.VELOCITY, step=0))

    async def test_turning_an_empty_pattern_into_drums_asks_too(self):
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.ADD)
        self.app.screen.value = NEW_PATTERN
        await self.press(Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await self.reconfigure(Reconfigure.DRUM)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(fixed_text(MSG_CHANGE_TYPE_EMPTY_QUESTION), self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertTrue(self.document.song().get_pattern(NEW_PATTERN).is_drum())

    async def test_turning_a_pattern_with_notes_into_drums_asks_first(self):
        await self.open(TUNE)
        await self.reconfigure(Reconfigure.DRUM)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(LETTERS, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertTrue(self.document.song().get_pattern(TUNE).is_drum())
        self.assertIsNone(self.document.song().get_pattern(TUNE).get_row(Row.DEGREE))

    async def test_renaming_to_a_name_in_use_is_refused(self):
        await self.open(TUNE)
        await self.reconfigure(Reconfigure.RENAME)
        self.app.screen.value = BEAT
        await self.press(Key.ENTER)
        self.assertIn(ALREADY_IN_USE, self.text())
        self.assertTrue(self.document.song().has_pattern(TUNE))

    async def test_backspace_on_a_gate_makes_it_one_step(self):
        await self.open(TUNE)
        await self.go_to_row(Row.GATE)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.step_value(name=TUNE, row=Row.GATE, step=0))

    async def test_an_octave_without_a_value_starts_from_the_default(self):
        await self.open(OTHER)
        await self.go_to_row(Row.OCTAVE)
        await self.press(keybindings.OctaveRow.MORE)
        self.assertEqual(self.document.step_value(name=OTHER, row=Row.OCTAVE, step=0), self.document.song().get_default_octave() + 1)

    async def test_a_long_pattern_draws_one_grid_and_says_which_steps_show(self):
        self.document.set_steps(name=TUNE, steps=LONG)
        await self.open(TUNE)
        self.assertEqual(self.text().count(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.DEGREE])), 1)
        shown = self.app.screen.drawing.steps_shown(self.SIZE[0])
        self.assertIn(MSG_STEPS_SHOWN.format(before=NOTHING, first=1, last=shown, after=MSG_MORE_AFTER), self.text())

    async def test_a_pattern_that_fits_says_nothing_about_which_steps_show(self):
        await self.open(TUNE)
        self.assertNotIn(fixed_text(MSG_STEPS_SHOWN), self.text())
