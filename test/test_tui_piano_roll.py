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
"""The piano roll, the pattern editor's first page: placing, holding, cutting and moving notes, and what the rows then hold.

The harness song's tune pattern has four eighth-note steps: C (degree 1, gate 1/4), E (degree 3,
gate 1/4), an empty step with a gate, and an empty step, in octave 5, played by the lead track
alone under C Major, so the roll knows its scale and its track.
"""

from llamatron.composition.defaults import DEFAULT_OCTAVE
from llamatron.composition.file_format import Accidental, Direction, Row, STEP_SIZE_CHOICES
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS
from llamatron.tui.drawing import Box, NOTHING, SPACE, Style
from llamatron.composition.limits import MAX_OCTAVE
from llamatron.composition.file_format import ChordSymbol
from llamatron.composition.named_scale import scale_type_name
from llamatron.tui.components.chord_row import chord_value
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.chord_dialog import QUALITY_LIST, ChordDialog
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.strings.errors import (
    ERR_NO_NOTE_HERE, ERR_NO_ROOM_AFTER, ERR_NOTE_IS_ONE_STEP, ERR_NOTHING_TO_SPLIT,
)
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.tui.keys import Key, SHIFT_LEFT_RIGHT, SHIFT_UP_DOWN
from llamatron.tui.screens.grid_drawing import CELL_WIDTH
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.support.rational import Rational
from llamatron.tui.screens.roll_drawing import MARK_COLUMN, filled_columns
from llamatron.strings.labels import (
    MSG_ENTRY_SIZE_LABEL, MSG_SONG_ENTRY_SIZE_CHOICE, MSG_ROLL_ROW_LABEL, MSG_ROW_LABELS, MSG_SCALE_HEADER, MSG_SEVERAL_SCALES, MSG_STEP_HEADING,
)
from llamatron.strings.legends import MSG_LEGEND_WHAT, MSG_TO_EDITOR_WHAT, MSG_TO_ROLL_WHAT, MSG_ENTRY_SIZE_WHAT, MSG_SHRINK_WHAT, MSG_STRETCH_WHAT, KeyName
from llamatron.strings.marks import (
    MSG_CURSOR_BLOCK, MSG_DRUM_LETTER_ROW, MSG_ENTRY_SIZE_SHOWN, MSG_FROM_SONG_SHOWN, MSG_NOTE_CELL, MSG_NOTE_CELL_WITH_MARK,
    MSG_GHOST_LINE, MSG_GRAB_NOTE_MARK, MSG_NOTE_UNDER_CURSOR_WITH_MARK, MSG_NOTE_EDGE, MSG_NOTE_UNDER_CURSOR,
    MSG_OUT_OF_RANGE_CELL, MSG_ROLL_OCTAVE_ONLY, MSG_TOGGLE_ON, MSG_DIRECTION_HEADER, MSG_HEADER_CELL_GAP, MSG_HEADER_INDENT, MSG_STEPS_HEADER,
    MSG_TIME_SIGNATURE_SHOWN,
)
from llamatron.composition.defaults import DEFAULT_TIME_SIGNATURE
from llamatron.composition.naming import words
import re

# The header's two lines come after the page's own header: its two lines and the rule.
HEADER_LINES = 3
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from rendering import render_song
from ui_testing import fixed_text, KEY_SHOWN, LEAD, REVERSED, ROW_SHOWN, TUNE, UITest, key_name, key_of

# The tune's notes, as the roll numbers its rows: degree 1 and 3 of a seven-note scale in octave 5.
SCALE_SIZE = 7
# Rows are half steps when the scale is known, so an octave is twelve rows and E is four above C.
C_PITCH = DEFAULT_OCTAVE * HALF_STEPS_PER_OCTAVE
E_PITCH = C_PITCH + 4
D_PITCH = C_PITCH + 2
D_SHARP_PITCH = C_PITCH + 3
C_SHARP_PITCH = C_PITCH + 1
D_DEGREE = 2
# The tune's steps.
C_STEP = 0
E_STEP = 1
EMPTY_STEP = 2
LAST_STEP = 3
SIXTEENTH = '1/16'
EIGHTH = '1/8'
QUARTER = '1/4'
HALF = '1/2'
WHOLE = '1'
# How Live labels octave 5, which the rows show.
SHOWN_OCTAVE = 3
SCENE_TWO = 1
SECOND_SCALE = 'other scale'
NEW_PATTERN = 'blank'
# A two-cell bar, as a note covering two steps is drawn.
TWO_CELLS = MSG_NOTE_CELL + MSG_NOTE_EDGE + MSG_NOTE_CELL
# Half a step, as a 1/16 note on 1/8 steps fills its cell, and a gate of a step and a half.
HALF_A_STEP = Rational(1, 2)
THREE_SIXTEENTHS = '3/16'


class RollTest(UITest):
    """Opens the tune on the piano roll."""

    def header_cell_starts(self, line):
        """Return the columns at which the cells of a header line start, after the first: where a run of at least the cell gap's spaces ends at a word."""
        return [match.end() for match in re.finditer(SPACE + '{' + str(len(MSG_HEADER_CELL_GAP)) + ',}(?=\\S)', line.rstrip())]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.editor = self.app.screen
        self.roll = self.editor.roll

    async def test_the_roll_and_the_rows_share_one_label_column_so_the_step_columns_stay_put_when_tab_switches_views(self):
        # The user's choice of 2026-11-09: the roll's labels are short, so it takes the rows' width, and every step column lines up between the views.
        rows_width = self.editor.drawing.widest_label()
        self.assertGreater(rows_width, self.editor.roll_drawing.widest_label())
        self.assertEqual(self.editor.label_width(), rows_width)
        on_roll = [line for line in self.text().splitlines() if Box.DOUBLE_BAR in line]
        step_heading_on_roll = next(line for line in on_roll if MSG_STEP_HEADING in line)
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        step_heading_on_rows = next(line for line in self.text().splitlines() if MSG_STEP_HEADING in line and Box.DOUBLE_BAR in line)
        self.assertEqual(step_heading_on_roll, step_heading_on_rows)
        self.assertEqual(step_heading_on_roll.index(Box.DOUBLE_BAR), rows_width + 1)

    async def test_the_headers_two_lines_are_aligned_cells_time_under_steps_scale_under_step_size_and_entry_under_drum(self):
        # The user's layout of 2026-11-09: each column is as wide as its wider cell, so the second line's cells start where the first's do.
        header = self.app.screen.header_lines()
        first, second = self.text().splitlines()[header:header + 2]
        self.assertTrue(first.startswith(MSG_HEADER_INDENT + MSG_STEPS_HEADER.format(steps=self.document.song().get_pattern(TUNE).get_steps())))
        self.assertTrue(second.startswith(MSG_HEADER_INDENT + MSG_TIME_SIGNATURE_SHOWN.format(signature=DEFAULT_TIME_SIGNATURE, whose=MSG_FROM_SONG_SHOWN)))
        starts = self.header_cell_starts(first)
        self.assertEqual(len(starts), 3)
        self.assertEqual(self.header_cell_starts(second), starts[:2])
        self.assertEqual(second[starts[0]:].split(MSG_HEADER_CELL_GAP)[0], MSG_SCALE_HEADER.format(scale=DEFAULT_SCALE))
        self.assertTrue(second[starts[1]:].startswith(MSG_ENTRY_SIZE_SHOWN.format(size=EIGHTH, whose=MSG_FROM_SONG_SHOWN)))
        self.assertTrue(first[starts[2]:].startswith(MSG_DIRECTION_HEADER.format(direction=words(Direction.FORWARD))))

    def row(self, row):
        """Return a row's value on every step, with False where a toggle row was never written."""
        pattern = self.document.song().get_pattern(TUNE)
        return [bool(pattern.get_value(row=row, step=step)) if ROW_DESCRIPTIONS[row].is_on_or_off() else pattern.get_value(row=row, step=step) for step in range(pattern.get_steps())]

    def value(self, *, row, step):
        return self.document.step_value(name=TUNE, row=row, step=step)

    def roll_line(self, label):
        """Return the screen line of the row with a label, like C3 for the scale's root in octave 5."""
        return next(line for line in self.text().splitlines() if ROW_SHOWN.format(label=label) in line)


class TestPianoRoll(RollTest):
    """The roll opens first, shows the notes as bars, and moves by pitch and step."""

    async def test_a_note_pattern_opens_on_the_roll_with_the_cursor_on_its_first_note(self):
        self.assertIsInstance(self.editor, PatternEditor)
        self.assertTrue(self.editor.on_roll())
        self.assertTrue(self.app.on_roll)
        self.assertEqual((self.editor.step, self.roll.pitch), (C_STEP, C_PITCH))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))

    async def test_the_header_says_the_scale_and_the_entry_size(self):
        self.assertIn(MSG_SCALE_HEADER.format(scale=DEFAULT_SCALE), self.text())
        self.assertIn(MSG_ENTRY_SIZE_SHOWN.format(size=EIGHTH, whose=MSG_FROM_SONG_SHOWN), self.text())
        await self.pick_entry_size(QUARTER)
        self.assertIn(MSG_ENTRY_SIZE_SHOWN.format(size=QUARTER, whose=NOTHING), self.text())

    async def test_rows_are_labelled_with_the_note_its_octave_and_the_degree(self):
        self.assertIn(MSG_ROLL_ROW_LABEL.format(note=f'{NoteName.E}{SHOWN_OCTAVE}', degree=3), self.text())
        self.assertIn(MSG_ROLL_ROW_LABEL.format(note=f'{NoteName.B}{SHOWN_OCTAVE - 1}', degree=SCALE_SIZE), self.text())

    async def test_a_note_covers_the_steps_its_gate_reaches_as_one_bar(self):
        # E's quarter-note gate reaches over the empty step after it, so its bar runs through the divider.
        self.assertIn(TWO_CELLS, self.roll_line(f'{NoteName.E}{SHOWN_OCTAVE}'))

    async def test_a_gate_is_cut_where_the_next_note_starts(self):
        # C's gate would reach step 2, but E starts there, so C's bar is one cell: the cursor's.
        line = self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}')
        self.assertIn(MSG_NOTE_UNDER_CURSOR, line)
        self.assertNotIn(MSG_NOTE_CELL, line)

    async def test_up_and_down_move_the_pitch_and_stop_at_the_ends(self):
        # Up and Down move by rows, which are the scale's degrees unless a sharp or flat has a row of its own.
        await self.press(Key.UP, Key.UP)
        self.assertEqual(self.roll.pitch, E_PITCH)
        await self.press(Key.DOWN)
        self.assertEqual(self.roll.pitch, D_PITCH)
        for _ in range(self.roll.highest_pitch() + 1):
            await self.press(Key.UP)
        self.assertEqual(self.roll.pitch, self.roll.highest_pitch())
        self.assertEqual(self.roll.note_at(self.roll.pitch), (SCALE_SIZE, MAX_OCTAVE, None))

    async def test_left_right_and_the_ends_move_the_step_and_stop_at_the_edges(self):
        await self.press(Key.RIGHT)
        self.assertEqual(self.editor.step, E_STEP)
        await self.press(Key.END)
        self.assertEqual(self.editor.step, LAST_STEP)
        # The roll never goes round: Right on the last step and Left on the first stay where they are.
        await self.press(Key.RIGHT)
        self.assertEqual(self.editor.step, LAST_STEP)
        await self.press(Key.HOME)
        self.assertEqual(self.editor.step, C_STEP)
        await self.press(Key.LEFT)
        self.assertEqual(self.editor.step, C_STEP)

    async def test_tab_goes_to_the_rows_and_tab_again_comes_back_and_the_choice_is_kept_for_other_patterns(self):
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.PatternEditor.TO_EDITOR)) + MSG_LEGEND_WHAT.format(what=MSG_TO_EDITOR_WHAT), self.text())
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        self.assertFalse(self.editor.on_roll())
        self.assertIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.DEGREE]), self.text())
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.PatternEditor.TO_ROLL)) + MSG_LEGEND_WHAT.format(what=MSG_TO_ROLL_WHAT), self.text())
        # Another note pattern opens on the rows too, until Tab opens the roll again.
        await self.press(Key.ESCAPE, Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertFalse(self.app.screen.on_roll())
        await self.press(keybindings.PatternEditor.TO_ROLL)
        self.assertTrue(self.app.screen.on_roll())

    async def test_a_drum_pattern_has_no_roll(self):
        await self.press(Key.ESCAPE, Key.DOWN, Key.ENTER)
        self.assertFalse(self.app.screen.on_roll())
        self.assertIn(ROW_SHOWN.format(label=MSG_DRUM_LETTER_ROW), self.text())
        self.assertFalse(self.app.screen.has_roll())
        self.assertNotIn(first_key(keybindings.PatternEditor.TO_ROLL), [name for item in self.app.screen.keys() for name in item.keys])

    async def test_the_description_is_of_the_step_under_the_cursor(self):
        await self.press(Key.RIGHT, Key.UP)
        self.assertIn(f'Step 2: {NoteName.E}{SHOWN_OCTAVE}', self.text())


class TestPlacingNotes(RollTest):
    """Space paints a note of the entry size, in ties, and cuts what it lands on."""

    async def test_space_places_a_note_of_one_step_at_the_cursor(self):
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP)
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [1, 3, D_DEGREE, None])
        self.assertEqual(self.value(row=Row.OCTAVE, step=EMPTY_STEP), DEFAULT_OCTAVE)
        self.assertIsNone(self.value(row=Row.GATE, step=EMPTY_STEP))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.D}{SHOWN_OCTAVE}'))
        render_song(self.document.song())

    async def test_a_longer_entry_size_writes_ties_never_a_gate(self):
        await self.pick_entry_size(QUARTER)
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.value(row=Row.GATE, step=EMPTY_STEP), None)
        self.assertEqual(self.row(Row.TIE), [False, False, False, True])

    async def test_an_entry_size_shorter_than_a_step_writes_a_gate(self):
        await self.pick_entry_size(SIXTEENTH)
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.value(row=Row.GATE, step=EMPTY_STEP), '1/16')
        self.assertEqual(self.row(Row.TIE), [False, False, False, False])

    async def test_e_opens_a_picker_of_entry_sizes_with_the_songs_first_and_the_patterns_own_marked(self):
        pattern = self.document.song().get_pattern(TUNE)
        await self.press(keybindings.PianoRoll.ENTRY_SIZE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.title, MSG_ENTRY_SIZE_LABEL)
        self.assertEqual(self.app.screen.options, [MSG_SONG_ENTRY_SIZE_CHOICE, *STEP_SIZE_CHOICES])
        # The pattern has no entry size of its own yet, so the picker opens on the song's.
        self.assertEqual(self.app.screen.options[self.app.screen.place], MSG_SONG_ENTRY_SIZE_CHOICE)
        await self.pick(HALF)
        self.assertEqual(pattern.get_written_entry_size(), HALF)
        self.assertIn(MSG_ENTRY_SIZE_SHOWN.format(size=HALF, whose=NOTHING), self.text())
        # The picker opens on the pattern's own size, and the song's choice takes the pattern's own away.
        await self.press(keybindings.PianoRoll.ENTRY_SIZE)
        self.assertEqual(self.app.screen.options[self.app.screen.place], HALF)
        await self.pick(MSG_SONG_ENTRY_SIZE_CHOICE)
        self.assertIsNone(pattern.get_written_entry_size())
        self.assertIn(MSG_ENTRY_SIZE_SHOWN.format(size=EIGHTH, whose=MSG_FROM_SONG_SHOWN), self.text())

    async def test_esc_in_the_entry_size_picker_changes_nothing(self):
        before = self.document.setlist().to_data()
        await self.press(keybindings.PianoRoll.ENTRY_SIZE, Key.DOWN, Key.DOWN, Key.ESCAPE)
        self.assertIs(self.app.screen, self.editor)
        self.assertEqual(self.document.setlist().to_data(), before)

    async def test_the_legend_shows_the_entry_size_key_and_the_brackets_that_drag(self):
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.PianoRoll.ENTRY_SIZE)) + MSG_LEGEND_WHAT.format(what=MSG_ENTRY_SIZE_WHAT), self.text())
        self.assertIn(KEY_SHOWN.format(label=KeyName.LEFT_BRACKET) + MSG_LEGEND_WHAT.format(what=MSG_SHRINK_WHAT), self.text())
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=MSG_STRETCH_WHAT), self.text())

    async def test_nothing_on_the_roll_takes_shift_with_an_arrow(self):
        """The roll's keys are plain ones, the user's choice of 2026-11-09: the octave jump went, and [ and ] drag."""
        every = [name for item in self.editor.key_table() for name in item.keys]
        for name in (*SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT):
            self.assertNotIn(name, every)
        before = (self.editor.step, self.roll.pitch)
        await self.press(*SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT)
        self.assertEqual((self.editor.step, self.roll.pitch), before)

    async def test_a_note_running_past_the_end_is_cut_there(self):
        await self.pick_entry_size(HALF)
        await self.press(Key.END, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.TIE), [False, False, False, False])
        self.assertEqual(self.value(row=Row.DEGREE, step=LAST_STEP), 1)

    async def test_placing_inside_a_held_note_at_another_pitch_cuts_it_and_the_rest_carries_on(self):
        # A half note from step 1 covers the whole pattern, taking E with it; an E on step 3 then cuts it, and step 4 goes on as a C of its own.
        await self.press(keybindings.PianoRoll.ERASE)
        await self.pick_entry_size(HALF)
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [1, None, None, None])
        self.assertEqual(self.row(Row.TIE), [False, True, True, True])
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, Key.UP)
        await self.pick_entry_size(EIGHTH)
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [1, None, 3, 1])
        self.assertEqual(self.row(Row.OCTAVE), [DEFAULT_OCTAVE, None, DEFAULT_OCTAVE, DEFAULT_OCTAVE])
        self.assertEqual(self.row(Row.TIE), [False, True, False, False])
        self.assertEqual(self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}').count(MSG_NOTE_CELL), 3)
        render_song(self.document.song())

    async def test_placing_on_a_held_notes_head_at_another_pitch_leaves_the_rest_as_its_own_note(self):
        await self.press(keybindings.PianoRoll.ERASE)
        await self.pick_entry_size(HALF)
        await self.press(keybindings.PianoRoll.PLACE)
        await self.pick_entry_size(EIGHTH)
        await self.press(Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [D_DEGREE, 1, None, None])
        self.assertEqual(self.row(Row.TIE), [False, False, True, True])
        self.assertEqual(self.value(row=Row.OCTAVE, step=E_STEP), DEFAULT_OCTAVE)

    async def test_enter_draws_and_erases_exactly_as_space_does(self):
        # The user's choice of 2026-11-09: Space and Enter do the same here as everywhere else, and the chord picker moved to H.
        enter = key_of(binding=keybindings.PianoRoll.PLACE, key=Key.ENTER)
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, enter)
        self.assertEqual(self.row(Row.DEGREE), [1, 3, D_DEGREE, None])
        self.assertIsInstance(self.app.screen, PatternEditor)
        await self.press(enter)
        self.assertEqual(self.row(Row.DEGREE), [1, 3, None, None])
        self.assertIn(f'« {key_name(keybindings.PianoRoll.PLACE)} »', self.text())
        self.assertIn(f'« {key_name(keybindings.PianoRoll.CHORD)} »', self.text())

    async def test_space_on_a_notes_head_erases_the_note_as_backspace_does(self):
        await self.press(keybindings.PianoRoll.PLACE)
        erased_with_space = self.document.song().get_pattern(TUNE).to_data()
        self.assertEqual(self.row(Row.DEGREE), [None, 3, None, None])
        await self.press(keybindings.Page.UNDO, keybindings.PianoRoll.ERASE)
        self.assertEqual(self.document.song().get_pattern(TUNE).to_data(), erased_with_space)

    async def test_space_in_the_middle_of_a_note_held_by_its_gate_erases_the_whole_note(self):
        # E's gate reaches over step 3, so the cursor there is in E's middle.
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [1, None, None, None])
        self.assertIsNone(self.value(row=Row.GATE, step=E_STEP))

    async def test_space_anywhere_on_a_tied_note_erases_the_note_with_its_ties_and_space_again_draws_a_new_one(self):
        await self.press(keybindings.PianoRoll.ERASE)
        await self.pick_entry_size(HALF)
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [1, None, None, None])
        self.assertEqual(self.row(Row.TIE), [False, True, True, True])
        drawn = self.document.song().get_pattern(TUNE).to_data()
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [None, None, None, None])
        self.assertEqual(self.row(Row.TIE), [False, False, False, False])
        # Erasing with Space is one undo step, which brings the whole note back.
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.song().get_pattern(TUNE).to_data(), drawn)
        await self.press(keybindings.Page.REDO)
        # A second Space draws a new note of the entry size where the cursor is, cut at the pattern's end, not the note that was erased.
        await self.press(keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [None, None, 1, None])
        self.assertEqual(self.row(Row.TIE), [False, False, False, True])

    async def test_placing_under_a_gates_reach_cuts_the_gate_where_the_new_note_starts(self):
        # E's quarter-note gate reaches over step 3; a D there cuts it to the step, so the two never sound together.
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.row(Row.DEGREE), [1, 3, D_DEGREE, None])
        self.assertEqual(self.value(row=Row.GATE, step=E_STEP), EIGHTH)
        self.assertNotIn(MSG_NOTE_EDGE + MSG_NOTE_CELL, self.roll_line(f'{NoteName.E}{SHOWN_OCTAVE}'))
        render_song(self.document.song())

    async def test_a_note_shorter_than_a_step_fills_part_of_its_cell_and_so_does_a_gates_last_step(self):
        # E's gate of a step and a half runs through the divider into half of step 3's cell.
        columns = filled_columns(HALF_A_STEP)
        self.document.set_step_value(name=TUNE, row=Row.GATE, step=E_STEP, value=THREE_SIXTEENTHS)
        self.document.changed()
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertIn(MSG_NOTE_CELL + MSG_NOTE_EDGE + MSG_NOTE_EDGE * columns + SPACE * (CELL_WIDTH - columns), self.roll_line(f'{NoteName.E}{SHOWN_OCTAVE}'))
        # A 1/16 note on 1/8 steps fills half its cell, shaded under the cursor, and cuts E's gate to the step.
        await self.pick_entry_size(SIXTEENTH)
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertIn(MSG_CURSOR_BLOCK * columns + SPACE * (CELL_WIDTH - columns), self.roll_line(f'{NoteName.D}{SHOWN_OCTAVE}'))
        self.assertEqual(self.value(row=Row.GATE, step=E_STEP), EIGHTH)
        await self.press(Key.UP)
        self.assertIn(MSG_NOTE_EDGE * columns + SPACE * (CELL_WIDTH - columns), self.roll_line(f'{NoteName.D}{SHOWN_OCTAVE}'))
        # The bar is never empty and never full, so that a short note is seen to be short.
        self.assertEqual(filled_columns(Rational(1, 100)), 1)
        self.assertEqual(filled_columns(Rational(99, 100)), CELL_WIDTH - 1)

    async def test_the_rows_show_what_was_painted(self):
        await self.pick_entry_size(QUARTER)
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.PLACE, keybindings.PatternEditor.TO_EDITOR)
        self.assertIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.TIE]), self.text())
        self.assertEqual(self.app.screen.row_for(Row.TIE).cell_text(step=LAST_STEP), MSG_TOGGLE_ON)


class TestShapingNotes(RollTest):
    """The knife, longer and shorter, the accidental and erasing, on the note under the cursor."""

    async def test_the_knife_splits_a_held_note_into_two(self):
        await self.press(keybindings.PianoRoll.ERASE)
        await self.pick_entry_size(HALF)
        await self.press(keybindings.PianoRoll.PLACE, Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.KNIFE)
        self.assertEqual(self.row(Row.DEGREE), [1, None, 1, None])
        self.assertEqual(self.row(Row.OCTAVE)[EMPTY_STEP], DEFAULT_OCTAVE)
        self.assertEqual(self.row(Row.TIE), [False, True, False, True])
        # Two bars with the divider between them, the second under the cursor, where the step starts a beat.
        self.assertIn(TWO_CELLS + Box.DOUBLE_BAR + MSG_NOTE_UNDER_CURSOR + MSG_NOTE_EDGE + MSG_NOTE_CELL, self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))

    async def test_the_knife_needs_a_held_step(self):
        await self.press(keybindings.PianoRoll.KNIFE)
        self.assertIn(ERR_NOTHING_TO_SPLIT, self.text())
        await self.press(Key.UP, keybindings.PianoRoll.KNIFE)
        self.assertIn(ERR_NOTHING_TO_SPLIT, self.text())

    async def test_shift_right_drags_one_more_step_onto_the_note_and_shift_left_takes_it_off(self):
        await self.press(Key.RIGHT, Key.UP, Key.UP, keybindings.PianoRoll.LONGER)
        self.assertEqual(self.row(Row.TIE), [False, False, False, True])
        self.assertIn(MSG_NOTE_UNDER_CURSOR + MSG_NOTE_EDGE + MSG_NOTE_CELL + MSG_NOTE_EDGE + MSG_NOTE_CELL, self.roll_line(f'{NoteName.E}{SHOWN_OCTAVE}'))
        await self.press(keybindings.PianoRoll.LONGER)
        self.assertIn(ERR_NO_ROOM_AFTER, self.text())
        await self.press(keybindings.PianoRoll.SHORTER)
        self.assertEqual(self.row(Row.TIE), [False, False, False, False])

    async def test_shift_left_shortens_a_gate_by_a_step_down_to_one(self):
        await self.press(Key.RIGHT, Key.UP, Key.UP, keybindings.PianoRoll.SHORTER)
        self.assertIsNone(self.value(row=Row.GATE, step=E_STEP))
        await self.press(keybindings.PianoRoll.SHORTER)
        self.assertIn(ERR_NOTE_IS_ONE_STEP, self.text())

    async def test_shift_right_after_a_gate_adds_a_tie_past_its_reach(self):
        self.assertEqual(self.value(row=Row.GATE, step=E_STEP), QUARTER)
        await self.press(Key.RIGHT, Key.UP, Key.UP, keybindings.PianoRoll.LONGER)
        self.assertEqual(self.value(row=Row.GATE, step=E_STEP), QUARTER)
        self.assertTrue(self.value(row=Row.TIE, step=LAST_STEP))

    async def test_dragging_a_note_shorter_than_a_step_makes_it_a_whole_step_first(self):
        await self.pick_entry_size(SIXTEENTH)
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, keybindings.PianoRoll.PLACE, keybindings.PianoRoll.LONGER)
        self.assertIsNone(self.value(row=Row.GATE, step=EMPTY_STEP))
        self.assertEqual(self.row(Row.TIE), [False, False, False, False])
        await self.press(keybindings.PianoRoll.LONGER)
        self.assertEqual(self.row(Row.TIE), [False, False, False, True])
        # The drag never goes below a step: that's what the entry size is for.
        await self.press(keybindings.PianoRoll.SHORTER, keybindings.PianoRoll.SHORTER)
        self.assertIn(ERR_NOTE_IS_ONE_STEP, self.text())
        self.assertIsNone(self.value(row=Row.GATE, step=EMPTY_STEP))

    async def test_g_marks_the_note_under_the_cursor_to_grab_and_the_bar_shows_a_reversed_g(self):
        await self.press(keybindings.PianoRoll.GRAB)
        self.assertTrue(self.value(row=Row.GRAB, step=C_STEP))
        self.assertIn(MSG_NOTE_UNDER_CURSOR_WITH_MARK.format(mark=REVERSED.format(text=MSG_GRAB_NOTE_MARK)), self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))
        await self.press(Key.UP)
        self.assertIn(MSG_NOTE_CELL_WITH_MARK.format(mark=REVERSED.format(text=MSG_GRAB_NOTE_MARK)), self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))
        # The mark is in reverse video so that it reads against the bar, and it stays on the note when a sharp moves it to a row of its own.
        cell = self.editor.roll_drawing.note_cell(mark=MSG_GRAB_NOTE_MARK, selected=False)
        self.assertEqual([(span.start, span.end, span.style) for span in cell.spans], [(MARK_COLUMN, MARK_COLUMN + 1, Style.REVERSE)])
        await self.press(Key.DOWN, keybindings.PianoRoll.ACCIDENTAL)
        self.assertIn(MSG_NOTE_UNDER_CURSOR_WITH_MARK.format(mark=REVERSED.format(text=MSG_GRAB_NOTE_MARK)), self.roll_line(f'{NoteName.C_SHARP}{SHOWN_OCTAVE}'))
        # G again unmarks it, leaving a plain bar, and G on an empty cell says so.
        await self.press(keybindings.PianoRoll.GRAB)
        self.assertFalse(self.value(row=Row.GRAB, step=C_STEP))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C_SHARP}{SHOWN_OCTAVE}'))
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.GRAB)
        self.assertIn(ERR_NO_NOTE_HERE, self.text())

    async def test_a_grab_on_an_empty_step_from_a_file_sits_on_the_root(self):
        self.document.set_step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP, value=True)
        self.document.changed()
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertEqual(self.roll.pitch_of(EMPTY_STEP), C_PITCH)
        self.assertEqual(self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}').count(MSG_NOTE_CELL_WITH_MARK.format(mark=REVERSED.format(text=MSG_GRAB_NOTE_MARK))), 1)

    async def test_the_accidental_cycles_and_the_note_moves_to_the_row_that_sounds_it(self):
        # C sharp gets a row of its own above C, with the bar plain since the row says what it is; C flat sounds as B, a degree, so it sits on the B row.
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        self.assertEqual(self.value(row=Row.ACCIDENTAL, step=C_STEP), Accidental.SHARP)
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C_SHARP}{SHOWN_OCTAVE}'))
        self.assertNotIn(Accidental.SHARP, self.roll_line(f'{NoteName.C_SHARP}{SHOWN_OCTAVE}').split(Box.DOUBLE_BAR, 1)[1])
        self.assertNotIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        self.assertEqual(self.value(row=Row.ACCIDENTAL, step=C_STEP), Accidental.FLAT)
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.B}{SHOWN_OCTAVE - 1}'))
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        self.assertIsNone(self.value(row=Row.ACCIDENTAL, step=C_STEP))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))

    async def test_backspace_erases_the_note_and_its_ties(self):
        await self.press(keybindings.PianoRoll.ERASE)
        await self.pick_entry_size(HALF)
        await self.press(keybindings.PianoRoll.PLACE, Key.RIGHT, keybindings.PianoRoll.ERASE)
        self.assertEqual(self.row(Row.DEGREE), [None, None, None, None])
        self.assertEqual(self.row(Row.TIE), [False, False, False, False])

    async def test_the_keys_say_when_there_is_no_note_under_the_cursor(self):
        await self.press(Key.UP, keybindings.PianoRoll.LONGER)
        self.assertIn(ERR_NO_NOTE_HERE, self.text())
        self.assertEqual(self.editor.step, C_STEP)
        await self.press(Key.RIGHT, keybindings.PianoRoll.ERASE)
        self.assertIn(ERR_NO_NOTE_HERE, self.text())
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        self.assertIn(ERR_NO_NOTE_HERE, self.text())
        self.assertEqual(self.row(Row.DEGREE), [1, 3, None, None])


class TestChordsOnTheRoll(RollTest):
    """A chord's other notes are thin lines that can't be edited on their own, a sharp or flat among them on a row of its own, and Enter picks the chord."""

    def ghost(self):
        """Return the thin line of a chord's note over one step."""
        return MSG_GHOST_LINE * CELL_WIDTH

    async def test_a_scale_chords_other_notes_are_thin_lines_on_their_degrees(self):
        # The C on step 1 as a scale triad: lines on E and G, over that step alone, and the C itself stays solid.
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=C_STEP, value=chord_value(ChordSymbol.SCALE_TRIAD))
        await self.press(Key.RIGHT, Key.LEFT)
        e_line = self.roll_line(f'{NoteName.E}{SHOWN_OCTAVE}')
        self.assertIn(self.ghost(), e_line)
        self.assertLess(e_line.index(self.ghost()), e_line.index(TWO_CELLS))
        self.assertIn(self.ghost(), self.roll_line(f'{NoteName.G}{SHOWN_OCTAVE}'))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))
        self.assertNotIn(self.ghost(), self.roll_line(f'{NoteName.D}{SHOWN_OCTAVE}'))

    async def test_a_named_chords_note_outside_the_scale_gets_a_row_of_its_own_between_two_degrees(self):
        # C minor in C major: Eb is drawn on a D# row between D and E, which exists for it, and G on its own row.
        sharp_row = f'{NoteName.D_SHARP}{SHOWN_OCTAVE}'
        self.assertNotIn(ROW_SHOWN.format(label=sharp_row), self.text())
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=C_STEP, value=ChordSymbol.MINOR)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertIn(self.ghost(), self.roll_line(sharp_row))
        self.assertIn(self.ghost(), self.roll_line(f'{NoteName.G}{SHOWN_OCTAVE}'))
        for label in (f'{NoteName.D}{SHOWN_OCTAVE}', f'{NoteName.E}{SHOWN_OCTAVE}'):
            self.assertNotIn(self.ghost(), self.roll_line(label))
        # The row's label is the note alone, the rows around it keep their degrees, and the row goes with the chord.
        self.assertIn(MSG_ROLL_ROW_LABEL.format(note=f'{NoteName.D}{SHOWN_OCTAVE}', degree=D_DEGREE), self.text())
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=C_STEP, value=None)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertNotIn(ROW_SHOWN.format(label=sharp_row), self.text())

    async def test_the_accidental_key_moves_the_note_to_a_row_of_its_own_and_the_cursor_follows(self):
        # A D drawn on step 4: . makes it D#, on a row above D that appears for it, then Db, on a row below D, then D again.
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual((self.value(row=Row.DEGREE, step=LAST_STEP), self.roll.pitch), (D_DEGREE, D_PITCH))
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        self.assertEqual((self.value(row=Row.ACCIDENTAL, step=LAST_STEP), self.roll.pitch), (Accidental.SHARP, D_SHARP_PITCH))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.D_SHARP}{SHOWN_OCTAVE}'))
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        # A C major scale spells its rows with sharps, so the Db sits on a row labelled C#3; the description line still says Db.
        self.assertEqual((self.value(row=Row.ACCIDENTAL, step=LAST_STEP), self.roll.pitch), (Accidental.FLAT, C_SHARP_PITCH))
        self.assertIn(MSG_NOTE_UNDER_CURSOR, self.roll_line(f'{NoteName.C_SHARP}{SHOWN_OCTAVE}'))
        self.assertNotIn(ROW_SHOWN.format(label=f'{NoteName.D_SHARP}{SHOWN_OCTAVE}'), self.text())
        await self.press(keybindings.PianoRoll.ACCIDENTAL)
        self.assertEqual((self.value(row=Row.ACCIDENTAL, step=LAST_STEP), self.roll.pitch), (None, D_PITCH))
        self.assertNotIn(ROW_SHOWN.format(label=f'{NoteName.C_SHARP}{SHOWN_OCTAVE}'), self.text())

    async def test_space_on_a_row_between_two_degrees_writes_the_degree_below_sharpened(self):
        # The C minor chord's Eb puts a D# row on the roll, two rows above C; a note drawn there on step 4 is degree 2 with a sharp.
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=C_STEP, value=ChordSymbol.MINOR)
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT, Key.UP, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.roll.pitch, D_SHARP_PITCH)
        self.assertEqual((self.value(row=Row.DEGREE, step=LAST_STEP), self.value(row=Row.ACCIDENTAL, step=LAST_STEP)), (D_DEGREE, Accidental.SHARP))

    async def test_a_scale_spelled_with_flats_writes_a_row_between_degrees_as_the_degree_above_flattened(self):
        self.document.set_scale_root(name=DEFAULT_SCALE, root=NoteName.B_FLAT)
        await self.press(Key.RIGHT, Key.LEFT)
        # Bb major: a half step above its second degree, C, is Db, the third degree flattened, and the degrees themselves are unchanged.
        self.assertEqual(self.roll.note_at(C_PITCH + 3), (3, DEFAULT_OCTAVE, Accidental.FLAT))
        self.assertEqual(self.roll.note_at(C_PITCH + 2), (D_DEGREE, DEFAULT_OCTAVE, None))

    async def test_a_ghost_runs_through_the_dividers_as_far_as_its_note_does(self):
        # A C on step 3 held by a tie on step 4, as a scale fifth: the G's hollow bar covers both steps in one piece.
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=EMPTY_STEP, value=1)
        self.document.set_step_value(name=TUNE, row=Row.TIE, step=LAST_STEP, value=True)
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=EMPTY_STEP, value=chord_value(ChordSymbol.SCALE_FIFTH))
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertIn(MSG_GHOST_LINE * (CELL_WIDTH * 2 + 1), self.roll_line(f'{NoteName.G}{SHOWN_OCTAVE}'))

    async def test_a_named_chord_has_no_ghosts_when_the_scale_is_not_known_and_a_scale_chord_still_has(self):
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=C_STEP, value=ChordSymbol.MINOR)
        self.document.add_scale(name=SECOND_SCALE, root=NoteName.D, kind=scale_type_name(ScaleType.MINOR))
        self.document.add_clip_slot(index=SCENE_TWO, track=LEAD, pattern=TUNE)
        self.document.set_scene_scale(index=SCENE_TWO, name=SECOND_SCALE)
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assertIn(fixed_text(MSG_SEVERAL_SCALES), self.text())
        self.assertFalse(self.rows_with_ghosts())
        self.document.set_step_value(name=TUNE, row=Row.CHORD, step=C_STEP, value=chord_value(ChordSymbol.SCALE_TRIAD))
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertTrue(self.rows_with_ghosts())

    def rows_with_ghosts(self):
        """Return the roll's row lines that hold a chord's thin line, which the rules, made of the same character, are not."""
        return [line for line in self.text().splitlines() if line.startswith(ROW_SHOWN.format(label=NOTHING).rstrip()) and self.ghost() in line.split(Box.DOUBLE_BAR, 1)[-1]]

    def pick_quality(self, symbol):
        """Put the Chord dialog's cursor on a quality, which Enter then takes."""
        self.app.screen.places[QUALITY_LIST] = self.app.screen.qualities.index(symbol)

    async def test_h_picks_the_chord_of_the_note_under_the_cursor_from_any_of_its_cells_and_none_takes_it_away(self):
        await self.press(keybindings.PianoRoll.CHORD)
        self.assertIsInstance(self.app.screen, ChordDialog)
        self.assertIsNone(self.app.screen.choice().quality)
        self.pick_quality(ChordSymbol.MINOR7)
        await self.press(Key.ENTER)
        self.assertEqual(self.value(row=Row.CHORD, step=C_STEP), ChordSymbol.MINOR7)
        # The E holds steps 2 and 3: from its last cell, Enter picks the E's chord, and it opens on the chord it has. The C's minor seventh put an Eb row between D and E, so E is three rows up.
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, Key.UP, Key.UP, keybindings.PianoRoll.CHORD)
        self.pick_quality(ChordSymbol.MAJOR)
        await self.press(Key.ENTER)
        self.assertEqual(self.value(row=Row.CHORD, step=E_STEP), ChordSymbol.MAJOR)
        await self.press(keybindings.PianoRoll.CHORD)
        self.assertEqual(self.app.screen.choice().quality, ChordSymbol.MAJOR)
        self.pick_quality(None)
        await self.press(Key.ENTER)
        self.assertIsNone(self.value(row=Row.CHORD, step=E_STEP))
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_h_needs_a_note_under_the_cursor(self):
        await self.press(Key.RIGHT, Key.RIGHT, keybindings.PianoRoll.CHORD)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertIn(ERR_NO_NOTE_HERE, self.text())

    async def test_a_note_that_grabs_takes_a_chord_and_shows_its_g_alone_with_no_thin_lines(self):
        # The user asked on 2026-11-09: a grab step holds a chord, built on whatever note the grab takes, which the roll can't know, so the G is all the roll shows.
        await self.press(keybindings.PianoRoll.GRAB, keybindings.PianoRoll.CHORD)
        self.assertIsInstance(self.app.screen, ChordDialog)
        self.pick_quality(ChordSymbol.MINOR7)
        await self.press(Key.ENTER)
        self.assertEqual(self.value(row=Row.CHORD, step=C_STEP), ChordSymbol.MINOR7)
        self.assertTrue(self.value(row=Row.GRAB, step=C_STEP))
        self.assertIn(MSG_NOTE_UNDER_CURSOR_WITH_MARK.format(mark=REVERSED.format(text=MSG_GRAB_NOTE_MARK)), self.roll_line(f'{NoteName.C}{SHOWN_OCTAVE}'))
        self.assertNotIn(self.ghost(), self.roll_line(f'{NoteName.G}{SHOWN_OCTAVE}'))
        self.assertNotIn(ROW_SHOWN.format(label=f'{NoteName.D_SHARP}{SHOWN_OCTAVE}'), self.text())
        # Unmarking the grab brings the chord's thin lines back, on the step's own note.
        await self.press(keybindings.PianoRoll.GRAB)
        self.assertIn(self.ghost(), self.roll_line(f'{NoteName.G}{SHOWN_OCTAVE}'))


class TestRollRanges(UITest):
    """The rows outside the playing track's octaves, and a pattern played under more than one scale."""

    async def test_rows_outside_the_tracks_octaves_are_marked_off(self):
        self.document.set_track_lowest_octave(name=LEAD, octave=DEFAULT_OCTAVE)
        self.document.set_track_highest_octave(name=LEAD, octave=DEFAULT_OCTAVE)
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        text = self.text()
        self.assertIn(MSG_OUT_OF_RANGE_CELL, text)
        in_range = next(line for line in text.splitlines() if ROW_SHOWN.format(label=f'{NoteName.D}{SHOWN_OCTAVE}') in line)
        self.assertNotIn(MSG_OUT_OF_RANGE_CELL, in_range)
        marked = next(line for line in text.splitlines() if ROW_SHOWN.format(label=f'{NoteName.B}{SHOWN_OCTAVE - 1}') in line)
        self.assertIn(MSG_OUT_OF_RANGE_CELL, marked)

    async def test_a_pattern_under_several_scales_has_numbered_rows(self):
        self.document.add_scale(name=SECOND_SCALE, root=NoteName.D, kind=scale_type_name(ScaleType.MINOR))
        self.document.add_clip_slot(index=SCENE_TWO, track=LEAD, pattern=TUNE)
        self.document.set_scene_scale(index=SCENE_TWO, name=SECOND_SCALE)
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        text = self.text()
        self.assertIn(fixed_text(MSG_SEVERAL_SCALES), text)
        self.assertIn(MSG_ROLL_ROW_LABEL.format(note=MSG_ROLL_OCTAVE_ONLY.format(octave=SHOWN_OCTAVE), degree=1), text)
        # Placing still works, by degree.
        await self.press(Key.RIGHT, Key.RIGHT, Key.UP, keybindings.PianoRoll.PLACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=EMPTY_STEP), D_DEGREE)

    async def test_an_empty_pattern_opens_on_the_root_in_the_default_octave(self):
        self.document.add_pattern(name=NEW_PATTERN)
        await self.press(keybindings.MainPage.PATTERNS, *[Key.DOWN] * self.document.song().get_pattern_names().index(NEW_PATTERN), Key.ENTER)
        self.assertEqual(self.app.screen.roll.pitch, C_PITCH)


class TestRollOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_the_roll_fits_with_its_keys_and_description(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        text = self.text()
        self.assertIn(MSG_NOTE_UNDER_CURSOR, text)
        self.assertIn('Step 1:', text)
        for item in self.app.screen.shown_keys():
            self.assertIn(KEY_SHOWN.format(label=item.shown_label()), text)
        # The cursor's row stays on screen as it climbs the octaves.
        for _ in range(SCALE_SIZE * 3):
            await self.press(Key.UP)
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.PatternEditor.BACK)), self.text())
        self.assertIn(ROW_SHOWN.format(label=f'{NoteName.C}{SHOWN_OCTAVE + 3}'), self.text())
