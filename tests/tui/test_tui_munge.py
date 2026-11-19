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

"""Tests of the Munge dialog in the pattern editor: its key, its sorted list, and what its newer choices ask and do with the cursor.

The pattern has five steps whose degrees count from 1 to 5. What each choice does to a pattern is
tested on Pattern alone, in tests/composition/test_pattern_munges.py.
"""

from llamatron.composition import limits
from llamatron.composition.checks import listed
from llamatron.composition.file_format import ChordSymbol, Row
from llamatron.strings import errors, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern import pattern_editor
from llamatron.tui.screens.pattern.pattern_editor import Munge, munge_groups, munges_in_order, PatternEditor
from tests.support import ui_testing
from tests.support.pattern_editor_testing import munge
from tests.support.ui_testing import UITest

LONG = 'long'
STEPS = 5
ROWS = {Row.DEGREE: [1, 2, 3, 4, 5], Row.VELOCITY: [10, None, None, None, 50], Row.CC1: [0, None, 20, None, None], Row.CHORD: [7, None, None, None, None]}
THIRD = 2
TWO = '2'
TOO_MANY = '6'
NOT_A_NUMBER = 'many'
FIRST_INVERSION = 1
# The one step of the pattern called other holds degree 5.
OTHER_DEGREE = 5
# What the pattern's parts are called when the pattern is split, and when split again.
PARTS = ['long-split-1', 'long-split-2', 'long-split-3']
LATER_PART_1 = 'long-split-3'
LATER_PART_2 = 'long-split-4'


class TestMunge(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.add_pattern_with_rows(name=LONG, steps=STEPS, rows=ROWS)
        await self.open_patterns_on(LONG)
        await self.press(Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def row(self, *, row=None):
        """Return a row of the pattern, its degrees unless another is named."""
        row = Row.DEGREE if row is None else row
        return self.document.song().get_pattern(LONG).get_row(row)

    async def test_the_key_opens_the_choices_sorted_by_name_and_esc_changes_nothing(self):
        await self.press(keybindings.PatternEditor.MUNGE)
        dialog = self.app.screen
        self.assertIsInstance(dialog, GroupedChoiceDialog)
        # The headings are sorted, closed until opened, and each heading's choices are sorted; every munge is under one heading.
        self.assertEqual(dialog.headings, sorted(pattern_editor.MUNGE_GROUPS))
        self.assertEqual(len(dialog.rows()), len(pattern_editor.MUNGE_GROUPS))
        for heading, choices in munge_groups():
            names = [labels.MSG_MUNGE_CHOICES[choice] for choice in choices]
            self.assertEqual(names, sorted(names, key=str.lower))
        self.assertEqual(sorted(munges_in_order()), list(range(len(labels.MSG_MUNGE_CHOICES))))
        self.assertEqual(len(labels.MSG_MUNGE_CHOICES), len([name for name in vars(Munge) if name.isupper()]))
        # A heading opens to its choices, and stays open the next time.
        await self.press(Key.ENTER)
        self.assertEqual(len(dialog.rows()), len(pattern_editor.MUNGE_GROUPS) + len(pattern_editor.MUNGE_GROUPS[dialog.headings[0]]))
        self.assertIn(labels.MSG_MUNGE_CHOICES[Munge.CLEAR_CHORDS], self.text())
        await self.press(Key.ESCAPE, keybindings.PatternEditor.MUNGE)
        self.assertIn(labels.MSG_MUNGE_CHOICES[Munge.CLEAR_CHORDS], self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.row(), ROWS[Row.DEGREE])

    async def test_a_copy_to_the_end_leaves_the_cursor_and_a_copy_before_the_start_keeps_it_on_its_note(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.COPY_BEFORE_TO_END)
        self.assertEqual(self.row(), [1, 2, 3, 4, 5, 1, 2, 3])
        self.assertEqual(self.editor.step, THIRD)
        await munge(test=self, choice=Munge.COPY_BEFORE_TO_START)
        self.assertEqual(self.row(), [1, 2, 3, 1, 2, 3, 4, 5, 1, 2, 3])
        self.assertEqual(self.editor.step, THIRD + THIRD + 1)

    async def test_the_copies_from_the_cursor(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.COPY_AFTER_TO_END)
        self.assertEqual(self.row(), [1, 2, 3, 4, 5, 3, 4, 5])
        await self.press(keybindings.Page.UNDO)
        await munge(test=self, choice=Munge.COPY_AFTER_TO_START)
        self.assertEqual(self.row(), [3, 4, 5, 1, 2, 3, 4, 5])

    async def test_a_copy_that_would_pass_the_most_steps_is_refused(self):
        self.document.change(self.document.setlist().get_pattern(LONG).set_steps, limits.MAX_STEPS)
        await self.press(Key.RIGHT)
        for choice in (Munge.COPY_BEFORE_TO_END, Munge.MIRROR):
            with self.subTest(choice=choice):
                await munge(test=self, choice=choice)
                self.assertEqual(self.document.song().get_pattern(LONG).get_steps(), limits.MAX_STEPS)
                self.assertIn(errors.ERR_MUNGE_TOO_MANY_STEPS.format(steps=limits.MAX_STEPS * 2 if choice == Munge.MIRROR else limits.MAX_STEPS + 2, most=limits.MAX_STEPS), self.text())

    async def test_a_roll_asks_how_many_steps_and_the_cursor_stays(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.ROLL_LEFT)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertIn(messages.MSG_ROLL_LEFT_PROMPT, self.text())
        await self.type(TWO)
        await self.press(Key.ENTER)
        self.assertEqual(self.row(), [3, 4, 5, 1, 2])
        self.assertEqual(self.editor.step, 1)
        await munge(test=self, choice=Munge.ROLL_RIGHT)
        self.assertIn(messages.MSG_ROLL_RIGHT_PROMPT, self.text())
        await self.type(TWO)
        await self.press(Key.ENTER)
        self.assertEqual(self.row(), ROWS[Row.DEGREE])

    async def test_a_roll_of_too_many_steps_or_of_no_number_is_refused(self):
        for typed, problem in ((TOO_MANY, errors.ERR_ROLL_OUT_OF_RANGE.format(low=1, high=STEPS)), (NOT_A_NUMBER, errors.ERR_TYPED_NOT_AN_INTEGER.format(text=NOT_A_NUMBER))):
            with self.subTest(typed=typed):
                await munge(test=self, choice=Munge.ROLL_LEFT)
                await self.type(typed)
                await self.press(Key.ENTER)
                self.assertEqual(self.row(), ROWS[Row.DEGREE])
                self.assertIn(problem, self.text())

    async def test_the_shuffles_of_a_part(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.RANDOMIZE_AFTER)
        self.assertEqual(self.row()[:THIRD], [1, 2])
        await munge(test=self, choice=Munge.RANDOMIZE_BEFORE)
        self.assertEqual(sorted(self.row()), ROWS[Row.DEGREE])

    async def test_the_rolls_at_the_cursor_ask_nothing_and_are_refused_with_nothing_to_roll(self):
        await munge(test=self, choice=Munge.ROLL_LEFT_AT_CURSOR)
        self.assertIn(errors.ERR_NOTHING_BEFORE, self.text())
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.ROLL_LEFT_AT_CURSOR)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.row(), [2, 3, 1, 4, 5])
        await munge(test=self, choice=Munge.ROLL_RIGHT_AT_CURSOR)
        self.assertEqual(self.row(), [2, 3, 5, 1, 4])
        self.assertEqual(self.editor.step, THIRD)
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.ROLL_RIGHT_AT_CURSOR)
        self.assertIn(errors.ERR_NOTHING_AFTER, self.text())

    async def test_the_munges_of_notes(self):
        await munge(test=self, choice=Munge.REVERSE_PITCHES)
        self.assertEqual(self.row(), [5, 4, 3, 2, 1])
        await munge(test=self, choice=Munge.CLEAR_EVERY)
        self.assertIn(messages.MSG_CLEAR_EVERY_PROMPT, self.text())
        await self.type(TWO)
        await self.press(Key.ENTER)
        self.assertEqual(self.row(), [5, None, 3, None, 1])
        await munge(test=self, choice=Munge.RANDOMIZE_RHYTHM)
        self.assertEqual([degree for degree in self.row() if degree is not None], [5, 3, 1])
        await munge(test=self, choice=Munge.RANDOMIZE_PITCHES)
        self.assertEqual(sorted(degree for degree in self.row() if degree is not None), [1, 3, 5])
        await munge(test=self, choice=Munge.HUMANIZE_VELOCITY)
        self.assertIn(messages.MSG_HUMANIZE_PROMPT, self.text())
        await self.type(TOO_MANY)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_the_legato_munges_and_the_crop(self):
        await munge(test=self, choice=Munge.CROP)
        self.assertEqual(self.row(), ROWS[Row.DEGREE][:1])
        await munge(test=self, choice=Munge.CROP)
        self.assertIn(errors.ERR_NOTHING_TO_CROP, self.text())
        await munge(test=self, choice=Munge.MIRROR)
        await munge(test=self, choice=Munge.JOIN_NOTES)
        self.assertEqual(self.row(), [1, None])
        self.assertEqual(self.row(row=Row.TIE), [False, True])
        await munge(test=self, choice=Munge.DIVIDE_NOTES)
        self.assertEqual(self.row(), [1, 1])

    async def test_invert_melody_mirrors_around_the_cursors_note_and_voice_leading_needs_chords(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.INVERT_MELODY)
        self.assertEqual(self.row(), [5, 4, 3, 2, 1])
        for choice in (Munge.VOICE_LEADING, Munge.VOICE_LEADING_OCTAVES):
            await munge(test=self, choice=choice)
            self.assertIn(errors.ERR_VOICE_LEADING_NEEDS_CHORDS, self.text())
        self.document.change(self.document.setlist().get_pattern(LONG).set_value, row=Row.CHORD, step=THIRD, value=ChordSymbol.SCALE_TRIAD)
        self.document.change(self.document.setlist().get_pattern(LONG).set_value, row=Row.INVERSION, step=THIRD, value=FIRST_INVERSION)
        await munge(test=self, choice=Munge.VOICE_LEADING)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertNotIn(errors.ERR_VOICE_LEADING_NEEDS_CHORDS, self.text())

    async def test_the_mirror_doubles_the_pattern(self):
        await munge(test=self, choice=Munge.MIRROR)
        self.assertEqual(self.row(), [1, 2, 3, 4, 5, 5, 4, 3, 2, 1])

    async def test_the_choices_that_clear_and_smooth(self):
        await munge(test=self, choice=Munge.SMOOTH_VELOCITY)
        self.assertEqual(self.row(row=Row.VELOCITY), [10, 20, 30, 40, 50])
        await munge(test=self, choice=Munge.SMOOTH_CCS)
        self.assertEqual(self.row(row=Row.CC1), [0, 10, 20, None, None])
        await munge(test=self, choice=Munge.CLEAR_CHORDS)
        self.assertFalse(any(self.row(row=Row.CHORD) or []))
        self.assertEqual(self.row(row=Row.VELOCITY), [10, 20, 30, 40, 50])
        await munge(test=self, choice=Munge.CLEAR_ALL_BUT_PITCH)
        self.assertFalse(any(self.row(row=Row.VELOCITY) or []))
        self.assertFalse(any(self.row(row=Row.CC1) or []))
        self.assertEqual(self.row(), ROWS[Row.DEGREE])

    async def test_interleave_asks_for_another_pattern_and_puts_its_steps_between(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.INTERLEAVE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertIn(messages.MSG_INTERLEAVE_CHOICE_TITLE, self.text())
        self.assertNotIn(LONG, self.app.screen.options)
        await self.press(*[Key.DOWN] * self.app.screen.options.index(ui_testing.OTHER), Key.ENTER)
        self.assertEqual(self.row(), [1, OTHER_DEGREE, 2, OTHER_DEGREE, 3, OTHER_DEGREE, 4, OTHER_DEGREE, 5, OTHER_DEGREE])
        # The cursor stays on its note.
        self.assertEqual(self.editor.step, 2)
        self.assertEqual(self.document.song().get_pattern(ui_testing.OTHER).get_steps(), 1)

    async def test_splice_asks_for_another_pattern_and_adds_it_at_the_end(self):
        await munge(test=self, choice=Munge.SPLICE)
        self.assertIn(messages.MSG_SPLICE_CHOICE_TITLE, self.text())
        await self.press(*[Key.DOWN] * self.app.screen.options.index(ui_testing.OTHER), Key.ENTER)
        self.assertEqual(self.row(), [*ROWS[Row.DEGREE], OTHER_DEGREE])
        self.assertEqual(self.editor.step, 0)
        await munge(test=self, choice=Munge.SPLICE_BEFORE)
        self.assertIn(messages.MSG_SPLICE_BEFORE_CHOICE_TITLE, self.text())
        await self.press(*[Key.DOWN] * self.app.screen.options.index(ui_testing.OTHER), Key.ENTER)
        self.assertEqual(self.row(), [OTHER_DEGREE, *ROWS[Row.DEGREE], OTHER_DEGREE])
        self.assertEqual(self.editor.step, 1)
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.SPLICE_AT_CURSOR)
        self.assertIn(messages.MSG_SPLICE_AT_CURSOR_CHOICE_TITLE, self.text())
        await self.press(*[Key.DOWN] * self.app.screen.options.index(ui_testing.OTHER), Key.ENTER)
        self.assertEqual(self.row(), [OTHER_DEGREE, 1, OTHER_DEGREE, 2, 3, 4, 5, OTHER_DEGREE])
        self.assertEqual(self.editor.step, 3)

    async def test_split_asks_for_the_steps_makes_new_patterns_and_names_them(self):
        await munge(test=self, choice=Munge.SPLIT)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertIn(messages.MSG_SPLIT_PROMPT, self.text())
        # The prompt opens on 16 steps, or on the most a split of this pattern can take.
        self.assertEqual(self.app.screen.value, str(STEPS - 1))
        self.app.screen.value = TWO
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(messages.MSG_SPLIT_CREATED.format(count=len(PARTS), names=listed(PARTS)), self.text())
        await self.press(Key.ENTER)
        song = self.document.song()
        self.assertEqual([song.get_pattern(part).get_row(Row.DEGREE) for part in PARTS], [[1, 2], [3, 4], [5]])
        self.assertEqual(self.row(), ROWS[Row.DEGREE])
        # One undo takes every new pattern away.
        await self.press(keybindings.Page.UNDO)
        self.assertFalse(any(self.document.setlist().has_pattern(part) for part in PARTS))

    async def test_a_second_split_takes_no_name_of_the_first(self):
        for _ in range(2):
            await munge(test=self, choice=Munge.SPLIT)
            self.app.screen.value = str(THIRD + 1)
            await self.press(Key.ENTER, Key.ENTER)
        names = self.document.setlist().get_pattern_names()
        for part in (*PARTS[:2], LATER_PART_1, LATER_PART_2):
            self.assertIn(part, names)

    async def test_a_split_into_parts_as_long_as_the_pattern_is_refused(self):
        await munge(test=self, choice=Munge.SPLIT)
        self.app.screen.value = str(STEPS)
        await self.press(Key.ENTER)
        self.assertIn(errors.ERR_SPLIT_OUT_OF_RANGE.format(low=1, high=STEPS - 1), self.text())
        self.assertNotIn(PARTS[0], self.document.setlist().get_pattern_names())

    async def test_a_drum_pattern_is_not_interleaved_with_a_pattern_of_notes(self):
        await munge(test=self, choice=Munge.INTERLEAVE)
        await self.press(*[Key.DOWN] * self.app.screen.options.index(ui_testing.BEAT), Key.ENTER)
        self.assertEqual(self.row(), ROWS[Row.DEGREE])
        self.assertIn(errors.ERR_INTERLEAVE_DRUM_MISMATCH, self.text())
