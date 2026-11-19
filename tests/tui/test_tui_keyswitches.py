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
"""Keyswitches in the tracker: an instrument's Keyswitch Map and its note picker, the pattern editor's Keyswitch row, the dialog that picks a step's keyswitches from both views, and the piano roll's lights."""

from tests.support.ui_testing import DRUMS, LEAD, TUNE, UITest, first_key, key_name
from llamatron.composition import file_format
from llamatron.composition.file_format import Row
from llamatron.composition import instrument as instrument_values
from llamatron.composition.instrument import Keyswitch
from llamatron.composition import limits
from llamatron.strings import errors, labels, marks, messages
from llamatron.music import midi
from llamatron.tui.dialogs.keyswitch_dialog import KeyswitchDialog
from llamatron.tui.components.keyswitch_row import slot_row_name
from llamatron.tui.dialogs.keyswitch_map_dialog import BUTTONS_PLACE, NAME_CELL, NOTE_CELL, KeyswitchMapDialog, first_note_offered
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import Style, cursor_mark
from llamatron.tui.keys import RowSection, DIGITS, Key
from llamatron.tui.keyswitch_text import keyswitch_note_text
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.pattern.roll_drawing import TOP_PITCH_LINE
from llamatron.tui.screens.set.instrument_editor import InstrumentEditor
from llamatron.tui import keybindings
from tests.support.pattern_editor_testing import PatternEditorTest, open_section

VIOLIN = 'violin'
CELLO = 'cello'
PORT = 'a port'
SUSTAIN = 'sustain'
STACCATO = 'staccato'
SUSTAIN_SLOT = 0
STACCATO_SLOT = 1
SUSTAIN_NOTE = 24
STACCATO_NOTE = 25
FIRST_STEP = 0
SECOND_STEP = 1
EMPTY_STEP = 2
SECOND_SCENE = 1
A_LEAD = 10
A_WIDTH = 60
MAP = keybindings.KeyswitchMapDialog
PICK = keybindings.KeyswitchDialog


def add_violin(document):
    """Give a document a violin with sustain on slot 0 and staccato on slot 1, which the lead plays through."""
    document.add_instrument(VIOLIN)
    document.set_instrument_device(name=VIOLIN, device=PORT)
    document.set_instrument_keyswitches(name=VIOLIN, keyswitches=[Keyswitch(SUSTAIN, SUSTAIN_NOTE), Keyswitch(STACCATO, STACCATO_NOTE), *[instrument_values.NO_KEYSWITCH] * (file_format.KEYSWITCH_SLOT_COUNT - 2)])
    document.set_track_instrument(name=LEAD, instrument=VIOLIN)


class TestKeyswitchMap(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(VIOLIN)
        await self.press(keybindings.MainPage.INSTRUMENTS, Key.ENTER)
        self.assertIsInstance(self.app.screen, InstrumentEditor)

    def slots(self):
        return self.document.setlist().get_instrument(VIOLIN).get_keyswitches()

    async def open_map(self):
        await self.press(keybindings.InstrumentEditor.KEYSWITCH_MAP)
        self.assertIsInstance(self.app.screen, KeyswitchMapDialog)
        return self.app.screen

    async def name_slot(self, name):
        await self.press(MAP.RENAME)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.type(name)
        await self.press(Key.ENTER)

    async def test_the_key_and_the_button_both_open_the_map_named_after_the_instrument(self):
        dialog = await self.open_map()
        self.assertIn(messages.MSG_KEYSWITCH_MAP_TITLE.format(instrument=VIOLIN), self.text())
        self.assertEqual(dialog.keyswitches, [instrument_values.NO_KEYSWITCH] * file_format.KEYSWITCH_SLOT_COUNT)
        await self.press(Key.ESCAPE)
        await self.press(*[Key.DOWN] * len(self.app.screen.fields()), Key.ENTER)
        self.assertIsInstance(self.app.screen, KeyswitchMapDialog)

    async def test_a_slot_is_named_given_a_note_and_stored_on_ok_as_one_undo_step(self):
        await self.open_map()
        await self.name_slot(SUSTAIN)
        await self.press(Key.RIGHT, MAP.NOTE, Key.RIGHT, MAP.TAKE_NOTE)
        self.assertEqual(self.slots(), [instrument_values.NO_KEYSWITCH] * file_format.KEYSWITCH_SLOT_COUNT)
        await self.press(MAP.OK)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        self.assertEqual(self.slots()[SUSTAIN_SLOT], Keyswitch(SUSTAIN, midi.MIN_MIDI_NUMBER + 1))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.slots(), [instrument_values.NO_KEYSWITCH] * file_format.KEYSWITCH_SLOT_COUNT)
        await self.press(keybindings.Page.REDO)
        self.assertEqual(self.slots()[SUSTAIN_SLOT], Keyswitch(SUSTAIN, midi.MIN_MIDI_NUMBER + 1))

    async def test_the_note_cells_show_themselves_with_headings_a_mark_and_the_arrow_that_reaches_them(self):
        dialog = await self.open_map()
        shown = self.text()
        self.assertIn(labels.Column.NAME, shown)
        self.assertIn(labels.Column.NOTE, shown)
        # An empty slot's note is drawn, with the picker's mark, so that the cell is seen.
        self.assertIn(marks.MSG_KEYSWITCH_NOTE_CELL.format(note=marks.MSG_NONE_SHOWN), shown)
        marked = [line.plain for line in dialog.lines(self.app.size.width) if marks.MSG_KEYSWITCH_NOTE_CELL.format(note=marks.MSG_NONE_SHOWN) in line.plain and marks.MSG_PICKER_MARK in line.plain]
        self.assertEqual(len(marked), file_format.KEYSWITCH_SLOT_COUNT)
        self.assertIn(key_name(MAP.TO_NOTE), shown)
        self.assertNotIn(key_name(MAP.TO_NAME), shown)
        await self.press(MAP.TO_NOTE)
        self.assertEqual(dialog.cell, NOTE_CELL)
        self.assertIn(key_name(MAP.TO_NAME), self.text())

    async def test_the_cursor_is_on_the_name_where_enter_renames_or_on_the_note_where_enter_picks(self):
        dialog = await self.open_map()
        self.assertEqual(dialog.cell, NAME_CELL)
        await self.press(Key.LEFT)
        self.assertEqual(dialog.cell, NAME_CELL)
        self.assertIn(cursor_mark(True) + marks.MSG_NONE_SHOWN, self.text())
        await self.press(MAP.RENAME_HERE)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.type(SUSTAIN)
        await self.press(Key.ENTER)
        self.assertEqual(dialog.keyswitches[SUSTAIN_SLOT], Keyswitch(SUSTAIN, None))
        self.assertIn(cursor_mark(True) + SUSTAIN, self.text())
        # Down keeps the cursor on the names, so that one slot after another is named.
        await self.press(Key.DOWN)
        self.assertEqual((dialog.place, dialog.cell), (STACCATO_SLOT, NAME_CELL))
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(dialog.cell, NOTE_CELL)
        await self.press(MAP.NOTE)
        self.assertIsNotNone(dialog.picking)
        await self.press(MAP.TAKE_NOTE)
        self.assertIn(cursor_mark(True) + keyswitch_note_text(setlist=self.document.setlist(), note=midi.MIN_MIDI_NUMBER), self.text())

    async def test_nothing_on_a_row_moves_when_the_cursor_moves(self):
        self.document.set_instrument_keyswitches(name=VIOLIN, keyswitches=[Keyswitch(SUSTAIN, SUSTAIN_NOTE), *[instrument_values.NO_KEYSWITCH] * (file_format.KEYSWITCH_SLOT_COUNT - 1)])
        dialog = await self.open_map()
        shown = keyswitch_note_text(setlist=self.document.setlist(), note=SUSTAIN_NOTE)
        places = set()
        for presses in ([], [Key.RIGHT], [Key.DOWN], [Key.LEFT]):
            await self.press(*presses)
            line = dialog.slot_line(slot=SUSTAIN_SLOT, width=A_WIDTH).plain
            places.add((line.index(SUSTAIN), line.index(shown), len(line)))
        self.assertEqual(len(places), 1)

    async def test_the_legend_says_what_enter_does_where_the_cursor_is(self):
        dialog = await self.open_map()
        bound = [item.binding for item in dialog.keys()]
        self.assertIn(MAP.RENAME_HERE, bound)
        self.assertNotIn(MAP.NOTE, bound)
        await self.press(Key.RIGHT)
        self.assertIn(MAP.NOTE, [item.binding for item in dialog.keys()])

    async def test_cancel_changes_nothing_by_its_key_or_its_button(self):
        for presses in ([Key.ESCAPE], [*[Key.DOWN] * BUTTONS_PLACE, Key.RIGHT, MAP.PRESS]):
            with self.subTest(presses=presses):
                await self.open_map()
                await self.name_slot(SUSTAIN)
                await self.press(*presses)
                self.assertIsInstance(self.app.screen, InstrumentEditor)
                self.assertEqual(self.slots(), [instrument_values.NO_KEYSWITCH] * file_format.KEYSWITCH_SLOT_COUNT)

    async def test_the_ok_button_is_reached_with_down_and_pressed_with_enter(self):
        dialog = await self.open_map()
        await self.name_slot(SUSTAIN)
        await self.press(*[Key.DOWN] * (BUTTONS_PLACE + 1))
        self.assertTrue(dialog.on_buttons())
        await self.press(MAP.PRESS)
        self.assertEqual(self.slots()[SUSTAIN_SLOT], Keyswitch(SUSTAIN, None))

    async def test_an_empty_name_leaves_the_slot_without_one_and_clear_empties_it(self):
        dialog = await self.open_map()
        await self.name_slot(SUSTAIN)
        await self.press(Key.RIGHT, MAP.NOTE, MAP.TAKE_NOTE)
        self.assertEqual(dialog.keyswitches[SUSTAIN_SLOT], Keyswitch(SUSTAIN, midi.MIN_MIDI_NUMBER))
        await self.press(MAP.RENAME, *[Key.BACKSPACE] * len(SUSTAIN), Key.ENTER)
        self.assertEqual(dialog.keyswitches[SUSTAIN_SLOT], Keyswitch(None, midi.MIN_MIDI_NUMBER))
        await self.press(MAP.CLEAR)
        self.assertEqual(dialog.keyswitches[SUSTAIN_SLOT], instrument_values.NO_KEYSWITCH)

    async def test_the_picker_opens_on_the_lowest_c_then_a_half_step_above_the_highest_note_then_on_the_slots_own(self):
        dialog = await self.open_map()
        await self.press(Key.RIGHT, MAP.NOTE)
        self.assertEqual(dialog.picking, midi.MIN_MIDI_NUMBER)
        await self.press(Key.UP, Key.UP, MAP.TAKE_NOTE, Key.DOWN, MAP.NOTE)
        self.assertEqual(dialog.picking, 2 * midi.HALF_STEPS_PER_OCTAVE + 1)
        await self.press(MAP.CLOSE_PICKER)
        self.assertIsNone(dialog.picking)
        self.assertEqual(dialog.keyswitches[STACCATO_SLOT], instrument_values.NO_KEYSWITCH)
        await self.press(Key.UP, MAP.NOTE)
        self.assertEqual(dialog.picking, 2 * midi.HALF_STEPS_PER_OCTAVE)
        self.assertEqual(first_note_offered([Keyswitch(None, midi.MAX_MIDI_NUMBER)]), midi.MAX_MIDI_NUMBER)

    async def test_the_picker_moves_within_its_octave_and_by_octaves_and_stops_at_every_edge(self):
        dialog = await self.open_map()
        await self.press(Key.RIGHT, MAP.NOTE, Key.LEFT, Key.DOWN)
        self.assertEqual(dialog.picking, midi.MIN_MIDI_NUMBER)
        await self.press(*[Key.RIGHT] * (midi.HALF_STEPS_PER_OCTAVE + 1))
        self.assertEqual(dialog.picking, midi.HALF_STEPS_PER_OCTAVE - 1)
        await self.press(*[Key.UP] * (midi.MAX_MIDI_NUMBER // midi.HALF_STEPS_PER_OCTAVE + 1))
        self.assertLessEqual(dialog.picking, midi.MAX_MIDI_NUMBER)
        self.assertGreater(dialog.picking + midi.HALF_STEPS_PER_OCTAVE, midi.MAX_MIDI_NUMBER)
        self.assertIn(keyswitch_note_text(setlist=self.document.setlist(), note=dialog.picking), self.text())

    async def test_the_map_shows_each_slots_note_in_the_sets_octave_labels_with_its_number(self):
        self.document.set_instrument_keyswitches(name=VIOLIN, keyswitches=[Keyswitch(SUSTAIN, SUSTAIN_NOTE), *[instrument_values.NO_KEYSWITCH] * (file_format.KEYSWITCH_SLOT_COUNT - 1)])
        await self.open_map()
        shown = keyswitch_note_text(setlist=self.document.setlist(), note=SUSTAIN_NOTE)
        self.assertIn(str(SUSTAIN_NOTE), shown)
        self.assertIn(shown, self.text())
        self.assertIn(SUSTAIN, self.text())
        self.assertIn(marks.MSG_NONE_SHOWN, self.text())

    async def test_the_lead_steps_from_nothing_and_stops_at_its_limit(self):
        instrument = self.document.setlist().get_instrument(VIOLIN)
        await self.select_field(labels.MSG_KEYSWITCH_LEAD_LABEL)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(instrument.get_keyswitch_lead(), 1)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(instrument.get_keyswitch_lead(), 0)
        self.assertIsNone(instrument.get_written_keyswitch_lead())
        self.document.set_instrument_keyswitch_lead(name=VIOLIN, milliseconds=limits.MAX_KEYSWITCH_LEAD)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(instrument.get_keyswitch_lead(), limits.MAX_KEYSWITCH_LEAD)


class TestKeyswitchRow(PatternEditorTest):
    """The Keyswitch section of the rows view, a row for each slot, and the dialog the piano roll opens on the same steps."""

    def slot_row(self, slot):
        return self.editor.rows_view.row_for(slot_row_name(slot))

    def section_rows(self):
        return self.editor.rows_view.section_rows(RowSection.KEYSWITCH)

    async def open_dialog(self):
        # The dialog is the piano roll's: Tab goes to the roll the first time, and the editor stays there.
        if self.editor.view() is not self.editor.roll:
            await self.press(keybindings.PatternEditor.TO_ROLL)
        await self.press(keybindings.PianoRoll.KEYSWITCH)
        self.assertIsInstance(self.app.screen, KeyswitchDialog)
        return self.app.screen

    async def test_the_section_has_a_row_for_each_slot_the_instrument_maps_named_by_the_slot(self):
        add_violin(self.document)
        self.document.record_edit()
        self.assertEqual(self.section_rows(), [slot_row_name(SUSTAIN_SLOT), slot_row_name(STACCATO_SLOT)])
        self.assertEqual([self.slot_row(slot).label() for slot in (SUSTAIN_SLOT, STACCATO_SLOT)], [SUSTAIN, STACCATO])
        await open_section(test=self, section=RowSection.KEYSWITCH)
        await self.press(Key.DOWN, Key.DOWN)
        self.assertIn(STACCATO, self.text())
        self.assertIn(messages.MSG_KEYSWITCH_SECTION_HINT.format(instrument=VIOLIN), self.text())

    async def test_a_slots_row_is_a_toggle_on_each_step_and_a_step_with_no_note_takes_none(self):
        add_violin(self.document)
        self.document.record_edit()
        await open_section(test=self, section=RowSection.KEYSWITCH)
        await self.press(Key.DOWN, Key.DOWN)
        row = self.editor.rows_view.current_row()
        self.assertEqual(row.slot, STACCATO_SLOT)
        self.assertEqual(row.cell_lines(step=EMPTY_STEP), [marks.MSG_BLOCKED_CELL])
        self.assertEqual(row.cell_lines(step=FIRST_STEP), [marks.MSG_TOGGLE_OFF])
        await self.press(keybindings.KeyswitchSlotRow.TOGGLE)
        self.assertEqual(self.value(row=Row.KEYSWITCH), (STACCATO_SLOT,))
        self.assertEqual(row.cell_lines(step=FIRST_STEP), [marks.MSG_TOGGLE_ON])
        # The other slot's row adds to the same step, and each row switches only its own slot off.
        await self.press(Key.UP, keybindings.KeyswitchSlotRow.TOGGLE)
        self.assertEqual(self.value(row=Row.KEYSWITCH), (SUSTAIN_SLOT, STACCATO_SLOT))
        await self.press(keybindings.KeyswitchSlotRow.CLEAR)
        self.assertEqual(self.value(row=Row.KEYSWITCH), (STACCATO_SLOT,))
        await self.press(keybindings.Page.UNDO, keybindings.Page.UNDO, keybindings.Page.UNDO)
        self.assertIsNone(self.value(row=Row.KEYSWITCH))

    async def test_with_no_one_instrument_the_rows_are_the_slots_the_steps_use_by_number_and_the_hint_says_why(self):
        self.assertEqual(self.section_rows(), [])
        self.document.set_step_value(name=TUNE, row=Row.KEYSWITCH, step=FIRST_STEP, value=[STACCATO_SLOT])
        self.document.record_edit()
        self.assertEqual(self.section_rows(), [slot_row_name(STACCATO_SLOT)])
        self.assertEqual(self.slot_row(STACCATO_SLOT).label(), marks.MSG_KEYSWITCH_SLOT_NAMED.format(slot=STACCATO_SLOT))
        await open_section(test=self, section=RowSection.KEYSWITCH)
        self.assertIn(messages.MSG_KEYSWITCH_NO_INSTRUMENT, self.text())

    async def test_space_and_the_digits_turn_slots_on_and_enter_stores_them_as_one_undo_step(self):
        dialog = await self.open_dialog()
        self.assertIn(messages.MSG_KEYSWITCH_DIALOG_TITLE.format(step=FIRST_STEP + 1), self.text())
        await self.press(PICK.FLIP)
        await self.press(DIGITS[3])
        self.assertEqual(dialog.place, 3)
        await self.press(DIGITS[9], DIGITS[9])
        self.assertIsNone(self.value(row=Row.KEYSWITCH))
        await self.press(PICK.DONE)
        self.assertEqual(self.value(row=Row.KEYSWITCH), (0, 3))
        await self.press(keybindings.Page.UNDO)
        self.assertIsNone(self.value(row=Row.KEYSWITCH))

    async def test_the_legend_names_the_digits_once_and_the_buttons_name_ok_and_cancel(self):
        dialog = await self.open_dialog()
        shown = [item.binding for item in dialog.keys() if item.shown]
        self.assertEqual(shown, [PICK.MOVE, PICK.FLIP, PICK.TOGGLE_SLOT])
        self.assertEqual(PICK.TOGGLE_SLOT[0], DIGITS)
        self.assertEqual(first_key(PICK.TOGGLE_SLOT), DIGITS[0])

    async def test_cancel_changes_nothing_and_turning_every_slot_off_clears_the_step(self):
        await self.open_dialog()
        await self.press(PICK.FLIP, PICK.CANCEL)
        self.assertIsNone(self.value(row=Row.KEYSWITCH))
        await self.open_dialog()
        await self.press(PICK.FLIP, PICK.DONE)
        self.assertEqual(self.value(row=Row.KEYSWITCH), (0,))
        await self.open_dialog()
        await self.press(PICK.FLIP, PICK.DONE)
        self.assertIsNone(self.value(row=Row.KEYSWITCH))

    async def test_with_no_instrument_the_slots_go_by_number_and_the_dialog_says_why(self):
        await self.open_dialog()
        self.assertIn(messages.MSG_KEYSWITCH_NO_INSTRUMENT, self.text())
        await self.press(PICK.FLIP, PICK.DONE)
        self.assertIn(messages.MSG_DESCRIBE_KEYSWITCHES.format(names=marks.MSG_KEYSWITCH_SLOT_NAMED.format(slot=SUSTAIN_SLOT)), self.text())

    async def test_one_instrument_for_every_use_names_the_slots_and_their_notes(self):
        add_violin(self.document)
        await self.open_dialog()
        text = self.text()
        self.assertIn(VIOLIN, text)
        self.assertIn(STACCATO, text)
        self.assertIn(keyswitch_note_text(setlist=self.document.setlist(), note=STACCATO_NOTE), text)
        await self.press(DIGITS[STACCATO_SLOT], PICK.DONE)
        self.assertIn(messages.MSG_DESCRIBE_KEYSWITCHES.format(names=STACCATO), self.text())

    async def test_a_slot_with_no_note_can_still_be_turned_on(self):
        add_violin(self.document)
        await self.open_dialog()
        await self.press(DIGITS[file_format.KEYSWITCH_SLOT_COUNT - 1], PICK.DONE)
        self.assertEqual(self.value(row=Row.KEYSWITCH), (file_format.KEYSWITCH_SLOT_COUNT - 1,))

    async def test_two_instruments_playing_the_pattern_leave_the_slots_numbered(self):
        add_violin(self.document)
        self.document.add_instrument(CELLO)
        self.document.set_track_instrument(name=DRUMS, instrument=CELLO)
        self.document.add_clip_slot(index=SECOND_SCENE, track=DRUMS, pattern=TUNE)
        await self.open_dialog()
        self.assertIn(messages.MSG_KEYSWITCH_SEVERAL_INSTRUMENTS, self.text())
        self.assertNotIn(STACCATO, self.text())


class TestKeyswitchesFromAClip(UITest):

    async def test_a_clips_track_names_the_slots_even_when_two_instruments_play_the_pattern(self):
        add_violin(self.document)
        self.document.add_instrument(CELLO)
        self.document.set_track_instrument(name=DRUMS, instrument=CELLO)
        self.document.add_clip_slot(index=SECOND_SCENE, track=DRUMS, pattern=TUNE)
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, keybindings.ArrangePage.OPEN_PATTERN)
        editor = self.app.screen
        self.assertIsInstance(editor, PatternEditor)
        self.assertEqual(editor.opened_track, LEAD)
        instrument, said = editor.keyswitch_instrument()
        self.assertEqual(said, VIOLIN)
        self.assertEqual(instrument.get_keyswitch(STACCATO_SLOT), Keyswitch(STACCATO, STACCATO_NOTE))


class TestKeyswitchesOnTheRoll(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.editor = self.app.screen
        if self.editor.view() is not self.editor.roll:
            await self.press(keybindings.PatternEditor.TO_EDITOR)

    def value(self, step):
        return self.document.step_value(name=TUNE, row=Row.KEYSWITCH, step=step)

    def top_row(self):
        """Return the roll's top row as drawn, the line under the header's lines, the step numbers and the heading's rule."""
        drawing = self.editor.roll_drawing
        first, last = self.editor.first_step, self.editor.first_step + self.editor.steps()
        return drawing.grid_lines(first=first, last=last, pitches=drawing.pitches_shown(self.app.size.height))[TOP_PITCH_LINE]

    async def test_the_key_opens_the_dialog_for_the_note_on_the_cursors_step_whatever_the_row(self):
        await self.press(Key.DOWN, Key.DOWN, keybindings.PianoRoll.KEYSWITCH)
        self.assertIsInstance(self.app.screen, KeyswitchDialog)
        await self.press(DIGITS[STACCATO_SLOT], PICK.DONE)
        self.assertEqual(self.value(FIRST_STEP), (STACCATO_SLOT,))

    async def test_a_step_no_note_covers_is_refused_and_no_note_is_drawn(self):
        await self.press(*[Key.RIGHT] * (EMPTY_STEP + 1), keybindings.PianoRoll.KEYSWITCH)
        self.assertNotIsInstance(self.app.screen, KeyswitchDialog)
        self.assertIn(errors.ERR_NO_NOTE_ON_STEP, self.text())
        self.assertFalse(self.editor.is_note(step=self.editor.step))

    async def test_a_step_with_keyswitches_has_a_magenta_light_on_the_top_row_and_no_other_has(self):
        self.assertNotIn(marks.MSG_KEYSWITCH_LIGHT, self.top_row().plain)
        self.document.set_step_value(name=TUNE, row=Row.KEYSWITCH, step=SECOND_STEP, value=[SUSTAIN_SLOT])
        line = self.top_row()
        self.assertEqual(line.plain.count(marks.MSG_KEYSWITCH_LIGHT), 1)
        column = line.plain.index(marks.MSG_KEYSWITCH_LIGHT)
        self.assertIn(Style.KEYSWITCH_LIGHT, [str(span.style) for span in line.spans if span.start <= column < span.end])
        self.editor.draw()
        self.assertIn(marks.MSG_KEYSWITCH_LIGHT, self.text())

    async def test_the_light_is_drawn_over_a_note_on_the_top_row_and_the_line_keeps_its_width(self):
        before = self.top_row()
        self.document.set_step_value(name=TUNE, row=Row.KEYSWITCH, step=FIRST_STEP, value=[SUSTAIN_SLOT])
        after = self.top_row()
        self.assertEqual(after.cell_len, before.cell_len)
        self.assertEqual(len(after.plain), len(before.plain))

    async def test_the_knife_has_the_cutting_key_and_stays_off_the_legend(self):
        self.assertEqual(first_key(keybindings.PianoRoll.KNIFE), Key.X)
        self.assertEqual(first_key(keybindings.PianoRoll.KEYSWITCH), Key.K)
        self.assertNotIn(keybindings.PianoRoll.KNIFE, keybindings.PianoRoll.IN_LEGEND)
        self.assertIn(keybindings.PianoRoll.KEYSWITCH, keybindings.PianoRoll.IN_LEGEND)
