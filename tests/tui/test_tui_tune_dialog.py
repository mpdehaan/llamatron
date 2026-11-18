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

"""Tests of the Tune dialog, a line of a tune edited by hand, opened from the song wizard's Hooks panel on the hook's notes."""

from llamatron.macro_composer import line_edits
from llamatron.strings import labels, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs.tune_dialog import TuneDialog
from llamatron.tui.keys import Key
from llamatron.tui.note_names import note_shown
from tests.support.ui_testing import back_key, forward_key
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_SEED = 11
FIRST_STEP = 0
UP = 1
MANY_PRESSES = 40


class TestTuneDialog(WizardTest):
    """The hook's notes opened from the Hooks panel, edited and kept."""

    async def open_notes(self):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        await self.press(Key.DOWN, Key.UP)
        names = [branch.name() for _, branch in self.wizard().rows()]
        await self.go_to_branch(names.index(labels.MSG_WIZARD_HOOKS_BRANCH))
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(labels.MSG_WIZARD_HOOK_NOTES_LABEL)
        self.assertIn(labels.MSG_WIZARD_HOOK_NOTES_WIZARD, self.text())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, TuneDialog)
        return choices

    def said_of(self, *, choices, line, step):
        index, _ = line_edits.found(line=line, step=step)
        note = line[index]
        if line_edits.is_rest(note):
            return marks.MSG_TUNE_REST_SAID.format(step=step + 1, steps=line_edits.steps_of(line))
        return marks.MSG_TUNE_NOTE_SAID.format(step=step + 1, steps=line_edits.steps_of(line), note=note_shown(choices.pitch_of_place(line_edits.place_of(note))), length=line_edits.length_of(note))

    async def test_the_dialog_shows_the_hook_and_says_what_the_cursor_is_on_as_it_moves(self):
        choices = await self.open_notes()
        line = choices.hook_line()
        self.assertIn(labels.MSG_WIZARD_HOOK_NOTES_TITLE, self.text())
        self.assertIn(self.said_of(choices=choices, line=line, step=FIRST_STEP), self.text())
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertIn(self.said_of(choices=choices, line=line, step=2), self.text())
        # The cursor stops at both ends of the line.
        await self.press(*[Key.RIGHT] * MANY_PRESSES)
        self.assertEqual(self.app.screen.place, line_edits.steps_of(line) - 1)
        await self.press(*[Key.LEFT] * MANY_PRESSES)
        self.assertEqual(self.app.screen.place, FIRST_STEP)

    async def test_a_note_moved_and_kept_is_the_hook_and_the_panel_says_the_notes_are_the_person_s(self):
        choices = await self.open_notes()
        line = choices.hook_line()
        await self.press(forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.DONE)
        self.assertEqual(choices.hook_line(), line_edits.moved(line=line, step=FIRST_STEP, by=UP))
        self.assertTrue(choices.hook_is_own())
        shown = self.text()
        self.assertIn(labels.MSG_WIZARD_HOOK_NOTES_OWN, shown)
        self.assertIn(messages.MSG_WIZARD_HOOK_OWN.format(player=choices.role_title(choices.tune_player())), shown)
        # The kind's fields and another take are the wizard's, and go while the notes are a person's.
        for label in (*labels.MSG_WIZARD_HOOK_PART_LABELS.values(), labels.MSG_WIZARD_NEW_HOOK_BUTTON):
            self.assertNotIn(label, shown)
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_each_key_edits_the_note_under_the_cursor(self):
        choices = await self.open_notes()
        line = choices.hook_line()
        dialog = self.app.screen
        await self.press(back_key(keybindings.TuneDialog.PITCH))
        self.assertEqual(dialog.line, line_edits.moved(line=line, step=FIRST_STEP, by=-UP))
        await self.press(keybindings.TuneDialog.USUAL)
        self.assertEqual(dialog.line, line_edits.tidied(line))
        await self.press(keybindings.TuneDialog.SHORTER)
        self.assertEqual(dialog.line, line_edits.stretched(line=line, step=FIRST_STEP, by=-UP))
        await self.press(keybindings.TuneDialog.LONGER)
        self.assertEqual(dialog.line, line_edits.tidied(line))
        await self.press(keybindings.TuneDialog.NOTE)
        self.assertEqual(dialog.line, line_edits.toggled(line=line, step=FIRST_STEP))
        self.assertIn(self.said_of(choices=choices, line=dialog.line, step=FIRST_STEP), self.text())
        await self.press(keybindings.TuneDialog.NOTE)
        self.assertFalse(line_edits.is_rest(dialog.line[0]))

    async def test_the_last_note_of_a_line_cannot_be_taken_out(self):
        await self.open_notes()
        dialog = self.app.screen
        for step in range(line_edits.steps_of(dialog.line)):
            dialog.place = step
            if not line_edits.is_rest(dialog.under_cursor()[0]):
                await self.press(keybindings.TuneDialog.NOTE)
        self.assertEqual(len([note for note in dialog.line if not line_edits.is_rest(note)]), 1)

    async def test_cancel_changes_nothing_and_the_wizard_s_notes_come_back_with_the_dialog_s_key_or_the_field_s(self):
        choices = await self.open_notes()
        line = choices.hook_line()
        await self.press(forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.CANCEL)
        self.assertEqual(choices.hook_line(), line)
        self.assertFalse(choices.hook_is_own())
        await self.select_field(labels.MSG_WIZARD_HOOK_NOTES_LABEL)
        await self.press(Key.ENTER, forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.DONE)
        self.assertTrue(choices.hook_is_own())
        await self.select_field(labels.MSG_WIZARD_HOOK_NOTES_LABEL)
        await self.press(Key.ENTER, keybindings.TuneDialog.USUAL, keybindings.TuneDialog.DONE)
        self.assertFalse(choices.hook_is_own())
        self.assertEqual(choices.hook_line(), line)
        # The kind's fields are back above the notes, so the field is found again.
        await self.select_field(labels.MSG_WIZARD_HOOK_NOTES_LABEL)
        await self.press(Key.ENTER, forward_key(keybindings.TuneDialog.PITCH), keybindings.TuneDialog.DONE)
        await self.select_field(labels.MSG_WIZARD_HOOK_NOTES_LABEL)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertFalse(choices.hook_is_own())
