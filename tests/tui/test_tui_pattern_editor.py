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

"""The pattern editor's rows view: typing and stepping values, lengths and pitches, the other rows and the pattern's size."""

from fractions import Fraction

from tests.support.ui_testing import KEY_SHOWN, QUIET_VALUE, REVERSED, ROW_SHOWN, key_of
from llamatron.composition import defaults, limits
from llamatron.strings import errors, labels as labels_text, legends, marks, messages
from llamatron.composition import file_format
from llamatron.composition.file_format import Accidental, ChordSymbol, GateModifier, OctaveLabels, Row
from llamatron.composition.named_scale import scale_type_name
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.tui import drawing as drawing_values
from llamatron.tui.drawing import Align, Box, Style, fit
from llamatron.tui.screens.pattern import grid_drawing
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.document import Document
from llamatron.tui import keys
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.components.chord_row import chord_value
from llamatron.tui.components import pattern_rows
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor, Reconfigure, reconfigure_choices
from llamatron.tui.components import degree_row
from llamatron.composition import setlist
from llamatron.tui import keybindings
from tests.support.rendering import render_song
from tests.support.pattern_editor_testing import PatternEditorTest, open_section

# Names the tests give to their own things, and other values they use.
# Patterns added out of order, with a capital, to see a picker sort them.
UNSORTED_PATTERN_NAMES = ('zed', 'Alpha', 'mid')
# Typed into a search, and the one of those names it finds.
SEARCH_TEXT = 'al'
SEARCH_HIT = 'Alpha'
BEAT = 'beat'
TUNE = 'tune'
LEAD = 'lead'
EIGHTH = '1/8'
# Time signatures the tests set, as a file writes them.
WALTZ = '3/4'
THREE_EIGHT = '3/8'
CUT_TIME = '2/2'
FIVE_SIXTEENTHS = '5/16'
HALF = '1/2'
# The keys that doubled and halved a gate once, which now do nothing on the Gate row.
GATE_KEYS_REMOVED = ('*', '/')
# A pattern too wide for the screen, and a step about halfway along it.
LONG = 64
HALFWAY = 32
FROM_1_TO_127 = 'from 1 to 127'
FROM_1_TO_4096 = 'from 1 to 4096'
C_MAJOR_NOTES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
# The step of tune that holds nothing.
EMPTY_STEP = 2
# The rows open when the editor opens: the pinned rows, then each section's heading with its rows where the section starts open.
ROWS_AT_START = [*pattern_rows.PINNED_ROWS, *[name for section in pattern_rows.SECTIONS for name in (section, *(pattern_rows.SECTIONS[section] if section in keys.OPEN_AT_START else []))]]
SIXTEENTH = '1/16'


# Names the tests give to the scales and chains they add.
SMALL_SCALE = 'small'


class TestPatternEditor(PatternEditorTest):
    """Moving around the grid, and putting notes in and taking them out."""

    async def test_home_and_end_work_but_stay_off_the_legend(self):
        shown = [name for item in self.editor.shown_keys() for name in item.keys]
        every = [name for item in self.editor.keys() for name in item.keys]
        for name in keys.HOME_END:
            self.assertIn(name, every)
            self.assertNotIn(name, shown)
        await self.press(Key.END)
        self.assertEqual(self.editor.step, self.document.song().get_pattern(TUNE).get_steps() - 1)
        await self.press(Key.HOME)
        self.assertEqual(self.editor.step, 0)

    async def test_space_on_the_degree_row_takes_a_note_off_and_puts_the_first_degree_on(self):
        pattern = self.document.song().get_pattern(TUNE)
        self.assertEqual(self.editor.rows_view.row_name(), Row.DEGREE)
        self.assertIsNotNone(pattern.get_value(row=Row.DEGREE, step=self.editor.step))
        await self.press(keybindings.DegreeRow.TOGGLE_NOTE)
        self.assertIsNone(pattern.get_value(row=Row.DEGREE, step=self.editor.step))
        await self.press(keybindings.DegreeRow.TOGGLE_NOTE)
        self.assertEqual(pattern.get_value(row=Row.DEGREE, step=self.editor.step), limits.MIN_DEGREE)

    async def test_r_offers_the_whole_pattern_actions_in_order_and_esc_leaves_the_pattern_alone(self):
        before = self.document.song().get_pattern(TUNE).to_data()
        await self.press(keybindings.PatternEditor.RECONFIGURE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, reconfigure_choices(drum=False))
        self.assertNotIn(legends.What.MUNGE, self.app.screen.options)
        self.assertEqual(self.app.screen.options[Reconfigure.RENAME], legends.What.RENAME)
        self.assertEqual(self.app.screen.options[Reconfigure.DRUM], legends.MSG_DRUM_ON_WHAT)
        await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, self.editor)
        self.assertEqual(self.document.song().get_pattern(TUNE).to_data(), before)

    async def test_the_brackets_are_two_legend_entries_on_the_number_rows_less_and_more(self):
        # [ and ] are each named with what it does, where the legend once read [/] adjust.
        while self.editor.row_name() != Row.VELOCITY:
            await self.press(Key.DOWN)
        less = KEY_SHOWN.format(label=legends.KeyName.LEFT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.LESS)
        more = KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.MORE)
        self.assertIn(less, self.text())
        self.assertIn(more, self.text())
        self.assertLess(self.text().index(less), self.text().index(more))
        self.assertNotIn(KEY_SHOWN.format(label=legends.KeyName.BRACKETS), self.text())

    async def test_grid_size_comes_from_the_step_count_and_typing_never_grows_it(self):
        self.assertEqual(self.text().count('│ Degree'), 1)
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT)
        await self.press('5', '5', '5')
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 4)
        self.assertEqual(len(self.document.song().get_pattern(TUNE).get_row(Row.DEGREE)), 4)

    async def test_typing_does_not_move_the_cursor(self):
        await self.press(Key.RIGHT, '5')
        self.assertEqual((self.editor.step, self.editor.rows_view.row), (1, 0))

    async def test_arrows_move_between_steps_and_rows(self):
        await self.press(Key.RIGHT)
        self.assertEqual(self.editor.step, 1)
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), Row.OCTAVE)
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), RowSection.BASICS)
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), Row.ACCIDENTAL)
        await self.press(Key.UP, Key.UP, Key.LEFT)
        self.assertEqual((self.editor.row_name(), self.editor.step), (Row.OCTAVE, 0))

    async def test_the_rows_are_all_there_in_order(self):
        # The pinned rows come first, then each section's heading, with its rows under the headings of the sections open at the start.
        self.assertEqual([row.name for row in self.editor.rows_view.reachable()], ROWS_AT_START)
        self.assertEqual([row.name for row in self.editor.rows_view.pinned_rows()], pattern_rows.PINNED_ROWS)
        self.assertEqual([row.name for row in self.editor.rows_view.scrolled_rows()], ROWS_AT_START[len(pattern_rows.PINNED_ROWS):])

    async def test_a_new_note_gets_the_default_octave_and_a_gate_of_one_step(self):
        self.document.set_default_octave(4)
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT, '5')
        self.assertEqual(self.value(row=Row.DEGREE), 5)
        self.assertIsNone(self.value(row=Row.GATE))
        self.assertEqual(self.value(row=Row.OCTAVE), 4)
        self.assertIn('gate 1/8', self.text())

    async def test_a_new_note_keeps_a_gate_it_already_has(self):
        await self.press(Key.RIGHT, Key.RIGHT, '5')
        self.assertEqual(self.value(row=Row.GATE), EIGHTH)

    async def test_the_gauge_stops_at_the_scales_top_and_bottom_and_says_where_the_octave_is_changed(self):
        # In a five-note scale, 6 can't be typed, and + from the top stays on 5 and says so, rather than carrying into the next octave.
        self.document.add_scale(name=SMALL_SCALE, root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR_PENTATONIC))
        self.document.set_scale_name(SMALL_SCALE)
        self.document.set_scene_scale(index=0, name=None)
        self.document.changed()
        octave = self.value(row=Row.OCTAVE)
        await self.press('6')
        self.assertEqual(self.value(row=Row.DEGREE), 1)
        await self.press('5')
        self.assertEqual(self.value(row=Row.DEGREE), 5)
        await self.press(keybindings.DegreeRow.MORE)
        self.assertEqual((self.value(row=Row.DEGREE), self.value(row=Row.OCTAVE)), (5, octave))
        self.assertIn(errors.ERR_TOP_OF_SCALE.format(scale=SMALL_SCALE), self.text())
        await self.press('1', keybindings.DegreeRow.LESS)
        self.assertEqual((self.value(row=Row.DEGREE), self.value(row=Row.OCTAVE)), (1, octave))
        self.assertIn(errors.ERR_BOTTOM_OF_SCALE.format(scale=SMALL_SCALE), self.text())
        # The next key clears the message, and - in the middle of the scale says nothing.
        await self.press('3', keybindings.DegreeRow.LESS)
        self.assertEqual(self.value(row=Row.DEGREE), 2)
        self.assertNotIn(errors.ERR_BOTTOM_OF_SCALE.format(scale=SMALL_SCALE), self.text())

    async def test_a_degree_past_the_scale_in_a_file_is_shown_within_the_scale_an_octave_up(self):
        # Seven notes in C major, so 9 is degree 2 of the next octave: the gauge and the number say 2, Octave one higher, and the file keeps 9.
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=0, value=9)
        self.document.changed()
        await self.press(Key.RIGHT, Key.LEFT)
        degree = self.editor.row_for(Row.DEGREE)
        self.assertEqual(degree.shown_degree(step=0), 2)
        self.assertEqual(degree.octave_shift(step=0), 1)
        self.assertEqual(degree.cell_lines(step=0)[-1], '2')
        shown_octave = self.document.song().shown_octave(self.value(row=Row.OCTAVE) + 1)
        self.assertEqual(self.editor.cell_text(name=Row.OCTAVE, step=0), str(shown_octave))
        self.assertEqual(self.value(row=Row.DEGREE), 9)
        # Nudging writes it back within the scale, with the octave moved up to match, so the note doesn't change pitch.
        octave = self.value(row=Row.OCTAVE)
        await self.press(keybindings.DegreeRow.MORE)
        self.assertEqual((self.value(row=Row.DEGREE), self.value(row=Row.OCTAVE)), (3, octave + 1))

    async def test_the_gauge_is_labelled_with_the_scales_notes_and_fills_to_the_degree(self):
        degree = self.editor.row_for(Row.DEGREE)
        self.assertEqual(degree.labels(), [*reversed(C_MAJOR_NOTES), labels_text.MSG_ROW_LABELS[Row.DEGREE]])
        # Step 2 is degree 3: the three lowest rows are bars, and the rest blank.
        lines = degree.cell_lines(step=1)
        self.assertEqual(lines, [*[drawing_values.NOTHING] * 4, *[marks.MSG_GAUGE_BAR] * 3, '3'])
        self.assertEqual(degree.cell_lines(step=2), [drawing_values.NOTHING] * 8)
        self.assertTrue(degree.rule_after())
        self.assertIn(labels_text.MSG_SCALE_HEADER.format(scale=setlist.DEFAULT_SCALE), self.text())

    async def test_a_pattern_under_two_scales_has_a_numbered_gauge_and_the_header_says_so(self):
        self.document.add_scale(name=SMALL_SCALE, root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR_PENTATONIC))
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.document.set_scene_scale(index=1, name=SMALL_SCALE)
        self.document.changed()
        await self.press(Key.LEFT, Key.RIGHT)
        degree = self.editor.row_for(Row.DEGREE)
        self.assertIsNone(degree.scale_name())
        self.assertEqual(degree.labels(), [str(number) for number in range(degree_row.GAUGE_ROWS_WITHOUT_SCALE, 0, -1)] + [labels_text.MSG_ROW_LABELS[Row.DEGREE]])
        self.assertIn(labels_text.MSG_SEVERAL_SCALES, self.text())

    async def test_the_description_says_when_ties_override_the_gate(self):
        await self.go_to_row(Row.GATE)
        await self.press(keybindings.GateRow.MORE)
        self.assertNotIn(messages.MSG_DESCRIBE_GATE_OVERRIDDEN, self.text())
        self.document.set_step_value(name=TUNE, row=Row.TIE, step=1, value=True)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertIn(messages.MSG_DESCRIBE_GATE_OVERRIDDEN, self.text())
        # A blank gate is one step, which ties only lengthen, so there's nothing to warn about.
        await self.press(Key.BACKSPACE)
        self.assertNotIn(messages.MSG_DESCRIBE_GATE_OVERRIDDEN, self.text())

    async def test_deleting_a_note_clears_the_ties_that_followed_it(self):
        self.document.set_step_value(name=TUNE, row=Row.TIE, step=2, value=True)
        self.document.set_step_value(name=TUNE, row=Row.TIE, step=3, value=True)
        await self.press(Key.RIGHT, Key.BACKSPACE)
        self.assertIsNone(self.value(row=Row.DEGREE))
        self.assertEqual([self.value(row=Row.TIE, step=step) for step in range(4)], [False, False, False, False])
        self.assertEqual(self.value(row=Row.DEGREE, step=0), 1)

    async def test_backspace_empties_a_step_which_is_a_rest(self):
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.value(row=Row.DEGREE))
        self.assertIsNone(self.value(row=Row.GATE))
        self.assertIsNone(self.value(row=Row.OCTAVE))
        self.assertIn('Step 1: empty', self.text())

    async def test_backspace_on_an_empty_step_does_nothing(self):
        await self.press(Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        self.assertIn('Step 1: empty', self.text())

    async def test_an_empty_step_has_no_gate_to_change(self):
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT)
        self.assertIn('Step 4: empty', self.text())
        await self.press(Key.DOWN, keybindings.GateRow.MORE)
        self.assertIsNone(self.value(row=Row.GATE))

    async def test_typing_in_the_load_over_picker_searches_and_tab_completes(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        await self.reconfigure(Reconfigure.LOAD_OVER)
        dialog = self.app.screen
        await self.type(SEARCH_TEXT)
        self.assertEqual(dialog.options[dialog.place], SEARCH_HIT)
        self.assertIn(marks.MSG_SEARCH_SHOWN.format(text=SEARCH_TEXT), self.text())
        self.assertNotIn(BEAT, self.text())
        await self.press(Key.TAB)
        self.assertEqual(dialog.typed, SEARCH_HIT)
        await self.press(Key.BACKSPACE, Key.BACKSPACE)
        self.assertEqual(dialog.typed, SEARCH_HIT[:-2])
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 1)

    async def test_esc_cancels_the_picker_with_or_without_text_typed(self):
        await self.reconfigure(Reconfigure.LOAD_OVER)
        await self.type(SEARCH_TEXT)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternEditor)
        await self.reconfigure(Reconfigure.LOAD_OVER)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_the_load_over_picker_lists_the_other_patterns_sorted_ignoring_case(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        await self.reconfigure(Reconfigure.LOAD_OVER)
        shown = self.app.screen.options
        self.assertEqual(shown, sorted(shown, key=str.lower))
        self.assertNotIn(TUNE, shown)
        self.assertEqual(set(shown), set(self.document.song().get_pattern_names()) - {TUNE})

class TestPatternEditorLengthsAndPitches(PatternEditorTest):
    """The gate, dot, step size, accidental, octave and chord rows."""

    async def test_plus_and_minus_step_through_plain_lengths(self):
        await self.go_to_row(Row.GATE)
        await self.press(key_of(binding=keybindings.GateRow.MORE, key=Key.PLUS))
        self.assertEqual(self.value(row=Row.GATE), HALF)
        await self.press(key_of(binding=keybindings.GateRow.LESS, key=Key.MINUS), key_of(binding=keybindings.GateRow.LESS, key=Key.MINUS))
        self.assertEqual(self.value(row=Row.GATE), EIGHTH)

    async def test_a_gate_cannot_go_below_the_shortest_length(self):
        await self.go_to_row(Row.GATE)
        for _ in range(8):
            await self.press(keybindings.GateRow.LESS)
        self.assertEqual(self.value(row=Row.GATE), '1/64')

    async def test_the_brackets_step_a_gate_through_the_plain_lengths(self):
        await self.go_to_row(Row.GATE)
        await self.press(keybindings.GateRow.MORE)
        self.assertEqual(self.value(row=Row.GATE), HALF)
        await self.press(keybindings.GateRow.LESS, keybindings.GateRow.LESS)
        self.assertEqual(self.value(row=Row.GATE), EIGHTH)

    async def test_a_gate_has_no_keys_to_double_or_halve_it(self):
        """A gate is stepped with the brackets or typed with Enter, which keeps the legend and the help short."""
        await self.go_to_row(Row.GATE)
        before = self.value(row=Row.GATE)
        await self.press(*GATE_KEYS_REMOVED)
        self.assertEqual(self.value(row=Row.GATE), before)
        self.assertIs(self.app.screen, self.editor)

    async def test_backspace_on_a_gate_makes_it_one_step(self):
        await self.go_to_row(Row.GATE)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.value(row=Row.GATE))

    async def test_enter_types_a_gate_as_a_whole_number_or_a_fraction(self):
        await self.go_to_row(Row.GATE)
        await self.press(Key.ENTER)
        self.app.screen.value = FIVE_SIXTEENTHS
        await self.press(Key.ENTER)
        self.assertEqual(self.value(row=Row.GATE), FIVE_SIXTEENTHS)
        for typed in ['0.25', '0', '9']:
            await self.press(Key.ENTER)
            self.app.screen.value = typed
            await self.press(Key.ENTER)
            with self.subTest(typed=typed):
                self.assertEqual(self.value(row=Row.GATE), FIVE_SIXTEENTHS)

    async def test_the_dot_row_makes_a_gate_dotted_or_a_triplet(self):
        await self.go_to_row(Row.DOT)
        await self.press(keybindings.DotRow.MORE)
        self.assertEqual(self.value(row=Row.DOT), GateModifier.DOTTED)
        self.assertIn('gate 1/4 dotted', self.text())
        await self.press(keybindings.DotRow.MORE)
        self.assertEqual(self.value(row=Row.DOT), GateModifier.TRIPLET)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.value(row=Row.DOT))

    async def test_e_sets_the_pattern_step_size_and_blank_uses_the_song(self):
        await self.reconfigure(Reconfigure.STEP_SIZE)
        self.app.screen.value = EIGHTH
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_step_size(), Fraction(1, 8))
        self.assertIn(marks.MSG_STEP_SIZE_SHOWN.format(size=EIGHTH, whose=drawing_values.NOTHING), self.text())
        await self.reconfigure(Reconfigure.STEP_SIZE)
        self.app.screen.value = ''
        await self.press(Key.ENTER)
        self.assertIsNone(self.document.song().get_pattern(TUNE).get_step_size())
        self.assertIn(marks.MSG_STEP_SIZE_SHOWN.format(size=SIXTEENTH, whose=marks.MSG_FROM_SONG_SHOWN), self.text())

    async def test_space_and_plus_and_minus_cycle_sharp_and_flat(self):
        await self.go_to_row(Row.ACCIDENTAL)
        await self.press(Key.SPACE)
        self.assertEqual(self.value(row=Row.ACCIDENTAL), '#')
        await self.press(key_of(binding=keybindings.AccidentalRow.MORE, key=Key.PLUS))
        self.assertEqual(self.value(row=Row.ACCIDENTAL), Accidental.FLAT)
        await self.press(Key.SPACE)
        self.assertIsNone(self.value(row=Row.ACCIDENTAL))
        await self.press(key_of(binding=keybindings.AccidentalRow.LESS, key=Key.MINUS))
        self.assertEqual(self.value(row=Row.ACCIDENTAL), Accidental.FLAT)

    async def test_the_brackets_cycle_sharp_and_flat_and_the_legend_names_space_or_enter_and_the_brackets(self):
        # The one adjust system: [ dec and ] inc on every row, with Space or Enter going to the next choice.
        await self.go_to_row(Row.ACCIDENTAL)
        await self.press(keybindings.AccidentalRow.MORE)
        self.assertEqual(self.value(row=Row.ACCIDENTAL), Accidental.SHARP)
        await self.press(keybindings.AccidentalRow.MORE, keybindings.AccidentalRow.LESS, keybindings.AccidentalRow.LESS)
        self.assertIsNone(self.value(row=Row.ACCIDENTAL))
        await self.press(key_of(binding=keybindings.AccidentalRow.NEXT, key=Key.ENTER))
        self.assertEqual(self.value(row=Row.ACCIDENTAL), Accidental.SHARP)
        text = self.text()
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.SPACE_ENTER) + legends.MSG_LEGEND_WHAT.format(what=legends.What.NEXT), text)
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.LEFT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.LESS), text)
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.MORE), text)
        # The Chord row keeps Enter for its picker, so Space alone goes to the next chord there.
        await self.go_to_row(Row.CHORD)
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.SPACE) + legends.MSG_LEGEND_WHAT.format(what=legends.What.NEXT), self.text())
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.MORE), self.text())

    async def test_octave_uses_whatever_is_typed_in_lives_labels_and_stores_the_files_numbering(self):
        song = self.document.song()
        await self.go_to_row(Row.OCTAVE)
        await self.press('7')
        self.assertEqual(self.value(row=Row.OCTAVE), song.stored_octave(7))
        await self.press(keybindings.OctaveRow.MORE, keybindings.OctaveRow.MORE, keybindings.OctaveRow.MORE)
        self.assertEqual(self.value(row=Row.OCTAVE), limits.MAX_OCTAVE)
        for _ in range(12):
            await self.press(keybindings.OctaveRow.LESS)
        self.assertEqual(self.value(row=Row.OCTAVE), limits.MIN_OCTAVE)
        self.assertEqual(song.shown_octave(limits.MIN_OCTAVE), -2)

    async def test_octave_is_typed_and_shown_from_0_with_llamatrons_labels(self):
        self.document.set_octave_labels(OctaveLabels.LLAMATRON)
        await self.go_to_row(Row.OCTAVE)
        await self.press('1', '0')
        self.assertEqual(self.value(row=Row.OCTAVE), limits.MAX_OCTAVE)
        await self.press(keybindings.OctaveRow.MORE)
        self.assertEqual(self.value(row=Row.OCTAVE), limits.MAX_OCTAVE)
        self.assertIn(str(limits.MAX_OCTAVE), self.app.screen.cell_text(name=Row.OCTAVE, step=self.editor.step))

    async def test_chord_steps_through_the_symbols_and_stops_at_the_first_and_the_last(self):
        await self.go_to_row(Row.CHORD)
        seen = []
        for _ in range(4):
            await self.press(keybindings.ChordRow.MORE)
            seen.append(self.value(row=Row.CHORD))
        self.assertEqual(seen, ['M', 'm', ChordSymbol.DIMINISHED, ChordSymbol.AUGMENTED])
        # [ goes back to none, the first choice, and stops there, never round to the last.
        await self.press(*[keybindings.ChordRow.LESS] * 5)
        self.assertIsNone(self.value(row=Row.CHORD))
        await self.press(keybindings.ChordRow.MORE)
        self.assertEqual(self.value(row=Row.CHORD), 'M')
        # ] stops at the last symbol, and [ goes back from the last.
        last = chord_value(file_format.CHORD_SYMBOLS[-1])
        before_last = chord_value(file_format.CHORD_SYMBOLS[-2])
        await self.press(*[keybindings.ChordRow.MORE] * (len(file_format.CHORD_SYMBOLS) + 1))
        self.assertEqual(self.value(row=Row.CHORD), last)
        await self.press(keybindings.ChordRow.LESS)
        self.assertEqual(self.value(row=Row.CHORD), before_last)


class TestPatternEditorOtherRowsAndSize(PatternEditorTest):
    """The remaining rows, and changing how many steps a pattern has."""

    async def test_the_brackets_nudge_a_value_and_plus_equals_and_minus_still_do(self):
        # The cursor opens on the Degree row of the first step, which holds degree 1.
        await self.press(keybindings.DegreeRow.MORE, keybindings.DegreeRow.MORE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=0), 3)
        await self.press(keybindings.DegreeRow.LESS)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=0), 2)
        await self.press(key_of(binding=keybindings.DegreeRow.MORE, key=Key.EQUALS), key_of(binding=keybindings.DegreeRow.MORE, key=Key.PLUS))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=0), 4)
        await self.press(key_of(binding=keybindings.DegreeRow.LESS, key=Key.MINUS))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=0), 3)
        # The legend names the brackets alone, one entry each, and never + or -.
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.LEFT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.LESS), self.text())
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET) + legends.MSG_LEGEND_WHAT.format(what=legends.What.MORE), self.text())
        self.assertEqual(legends.KeyName.LEFT_BRACKET, Key.LEFT_BRACKET)
        self.assertEqual(legends.KeyName.RIGHT_BRACKET, Key.RIGHT_BRACKET)
        self.assertNotIn(KEY_SHOWN.format(label=Key.PLUS), self.text())

    async def test_nothing_on_the_rows_takes_shift_with_an_arrow(self):
        """The rows' keys are plain ones: the bar jump and the Shift+Up and Shift+Down nudge went."""
        every = [name for item in self.editor.key_table() for name in item.keys]
        for name in (*keys.SHIFT_UP_DOWN, *keys.SHIFT_LEFT_RIGHT):
            self.assertNotIn(name, every)
        before = self.document.setlist().to_data()
        await self.press(Key.RIGHT, *keys.SHIFT_UP_DOWN, *keys.SHIFT_LEFT_RIGHT)
        self.assertEqual(self.document.setlist().to_data(), before)
        self.assertEqual(self.editor.step, 1)

    async def test_the_rules_are_dim_with_a_plain_joint_where_a_beat_edge_crosses(self):
        # The beat edges are bold double bars down the rows and the rules are dim, so the joint where they cross is plain, between the two, and breaks neither line.
        drawing = self.editor.drawing
        rules = (drawing.top_rule(first=0, last=self.editor.steps()), drawing.inner_rule(first=0, last=self.editor.steps()), drawing.bottom_rule(first=0, last=self.editor.steps()))
        beat_joints = (Box.DOUBLE_TOP_TEE, Box.DOUBLE_CROSS, Box.DOUBLE_BOTTOM_TEE)
        for rule, joint in zip(rules, beat_joints):
            self.assertIn(joint, rule.plain)
            self.assertEqual(rule.style, Style.PLAIN)
            dim = {offset for span in rule.spans if span.style == Style.DIM for offset in range(span.start, span.end)}
            self.assertEqual({span.style for span in rule.spans}, {Style.DIM}, rule.plain)
            for offset, character in enumerate(rule.plain):
                self.assertEqual(offset in dim, character != joint, (rule.plain, offset))

    async def test_a_cell_that_cannot_take_a_value_shows_the_blocked_mark_and_its_row_has_no_keys_there(self):
        # Step 3 of tune is empty: Octave, Chord and Velocity are blocked there, while Tie and the CC rows aren't, since a rest can hold them.
        for row in (Row.OCTAVE, Row.CHORD, Row.VELOCITY):
            self.assertEqual(self.editor.row_for(row).cell_lines(step=EMPTY_STEP), [marks.MSG_BLOCKED_CELL], row)
        self.assertEqual(self.editor.row_for(Row.TIE).cell_lines(step=EMPTY_STEP), [marks.MSG_TOGGLE_OFF])
        self.assertEqual(self.editor.row_for(Row.CC1).cell_lines(step=EMPTY_STEP), [QUIET_VALUE])
        # Two empty steps, where every row open but Degree, Tie and the headings is blocked, and two notes, where only Tie is; the Chord section is opened, where Inversion and Tension are blocked on every step, since neither note has a chord.
        await open_section(test=self, section=RowSection.CHORD)
        await self.press(*[Key.UP] * len(self.editor.rows_view.reachable()))
        blocked_rows = [Row.OCTAVE, *[row for section in (*keys.OPEN_AT_START, RowSection.CHORD) for row in pattern_rows.SECTIONS[section] if row != Row.TIE]]
        rows = [*self.editor.rows_view.pinned_rows(), *self.editor.rows_view.scrolled_rows()]
        blocked_cells = [(row.name, step) for row in rows for step in range(self.editor.steps()) if row.cell_lines(step=step) == [marks.MSG_BLOCKED_CELL]]
        self.assertEqual(len(blocked_cells), 2 * len(blocked_rows) + 2 + 2 + 2)
        self.assertEqual([step for name, step in blocked_cells if name == Row.TENSION], list(range(self.editor.steps())))
        self.assertEqual([step for name, step in blocked_cells if name == Row.INVERSION], list(range(self.editor.steps())))
        self.assertEqual([step for name, step in blocked_cells if name == Row.TIE], [0, 1])
        # The cursor can sit on a blocked cell, where the row's keys leave the legend.
        await self.press(Key.RIGHT, Key.RIGHT)
        while self.editor.row_name() != Row.VELOCITY:
            await self.press(Key.DOWN)
        self.assertFalse(self.editor.row_for(Row.VELOCITY).editable())
        self.assertNotIn(KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET), self.text())
        self.assertIn(REVERSED.format(text=fit(text=marks.MSG_BLOCKED_CELL, width=grid_drawing.CELL_WIDTH, align=Align.CENTER)), self.text())
        # Marking the step to grab opens Octave, Velocity and Chord, since the step's chord is built on the grabbed note.
        self.document.set_step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP, value=True)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=EMPTY_STEP, value=limits.MIN_DEGREE)
        self.document.changed()
        await self.press(Key.LEFT, Key.RIGHT)
        self.assertTrue(self.editor.row_for(Row.VELOCITY).editable())
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.RIGHT_BRACKET), self.text())
        self.assertEqual(self.editor.row_for(Row.OCTAVE).cell_lines(step=EMPTY_STEP), [str(self.document.song().shown_octave(self.document.song().get_default_octave()))])
        self.assertNotEqual(self.editor.row_for(Row.CHORD).cell_lines(step=EMPTY_STEP), [marks.MSG_BLOCKED_CELL])
        self.assertFalse(self.editor.row_for(Row.CHORD).blocked(step=EMPTY_STEP))

    async def test_s_sets_the_pattern_time_signature_and_blank_uses_the_song(self):
        self.assertIn(marks.MSG_TIME_SIGNATURE_SHOWN.format(signature=defaults.DEFAULT_TIME_SIGNATURE, whose=marks.MSG_FROM_SONG_SHOWN), self.text())
        await self.reconfigure(Reconfigure.TIME_SIGNATURE)
        self.app.screen.value = WALTZ
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_written_time_signature(), WALTZ)
        self.assertIn(marks.MSG_TIME_SIGNATURE_SHOWN.format(signature=WALTZ, whose=drawing_values.NOTHING), self.text())
        await self.reconfigure(Reconfigure.TIME_SIGNATURE)
        self.app.screen.value = drawing_values.NOTHING
        await self.press(Key.ENTER)
        self.assertIsNone(self.document.song().get_pattern(TUNE).get_written_time_signature())
        self.assertIn(marks.MSG_TIME_SIGNATURE_SHOWN.format(signature=defaults.DEFAULT_TIME_SIGNATURE, whose=marks.MSG_FROM_SONG_SHOWN), self.text())

    async def test_the_step_numbers_on_beats_are_bold(self):
        # The tune has four 1/8 steps, so in 4/4 the first and third start a beat.
        beats = [self.editor.drawing.starts_a_beat(step) for step in range(4)]
        self.assertEqual(beats, [True, False, True, False])
        self.document.set_time_signature(THREE_EIGHT)
        self.assertEqual([self.editor.drawing.starts_a_beat(step) for step in range(4)], [True, True, True, True])
        self.document.set_pattern_time_signature(name=TUNE, time_signature=CUT_TIME)
        self.assertEqual([self.editor.drawing.starts_a_beat(step) for step in range(4)], [True, False, False, False])
        # The step heading, the one step on a beat and its double left edge are the only bold spans on the numbers line.
        lines = self.editor.drawing.grid_lines(first=0, last=4)
        head = lines[1]
        self.assertEqual(len([span for span in head.spans if span.style == Style.BOLD]), 3)
        # The beat's edge is a bold double line down the block, through single rules, ending in a double bottom tee where the dividers close over the first heading, and the other edges stay single.
        self.assertEqual(str(lines[0]).count(Box.DOUBLE_TOP_TEE), 1)
        closing = next(number for number, line in enumerate(lines) if Box.DOUBLE_BOTTOM_TEE in str(line))
        self.assertEqual(str(lines[closing]).count(Box.DOUBLE_BOTTOM_TEE), 1)
        # Down to that rule, every row has the beat's double bar and every rule its double cross.
        for line in lines[1:closing]:
            if Box.LEFT_TEE in str(line):
                # The rule under the gauge's number, where the beat line crosses it.
                self.assertEqual(str(line).count(Box.DOUBLE_CROSS), 1)
                continue
            self.assertEqual(str(line).count(Box.DOUBLE_BAR), 1)
            # The label's edge, the three steps off the beat and the right edge.
            self.assertEqual(str(line).count(Box.BAR), 5)
        self.assertNotIn(Box.DOUBLE_BAR, str(lines[0]))
        self.assertEqual(str(lines[0]).count(Box.TOP_TEE), 3)

    async def test_velocity_probability_and_ratchet(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press(keybindings.NumberRow.LESS)
        self.assertEqual(self.value(row=Row.VELOCITY), 126)
        await self.press(Key.ENTER)
        self.app.screen.value = '60'
        await self.press(Key.ENTER)
        self.assertEqual(self.value(row=Row.VELOCITY), 60)
        await self.go_to_row(Row.PROBABILITY)
        await self.press(keybindings.NumberRow.LESS)
        self.assertEqual(self.value(row=Row.PROBABILITY), 99)
        await self.go_to_row(Row.RATCHET)
        await self.press(keybindings.NumberRow.MORE)
        self.assertEqual(self.value(row=Row.RATCHET), 2)

    async def test_a_typed_value_out_of_range_is_refused(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press(Key.ENTER)
        self.app.screen.value = '500'
        await self.press(Key.ENTER)
        self.assertIsNone(self.value(row=Row.VELOCITY))
        self.assertIn(FROM_1_TO_127, self.text())

    async def test_glide_toggles_with_space_and_shows_the_dot_like_tie(self):
        # The dot was chosen over a bar into the next step.
        await self.go_to_row(Row.GLIDE)
        glide = self.editor.row_for(Row.GLIDE)
        self.assertEqual(glide.cell_text(step=0), marks.MSG_TOGGLE_OFF)
        await self.press(Key.SPACE)
        self.assertIs(self.value(row=Row.GLIDE), True)
        self.assertEqual(glide.cell_text(step=0), marks.MSG_TOGGLE_ON)
        self.assertIsNone(glide.edge_text(step=1))
        await self.press(Key.SPACE)
        self.assertIs(self.value(row=Row.GLIDE), False)
        self.assertEqual(glide.cell_text(step=0), marks.MSG_TOGGLE_OFF)
        self.assertIsNone(glide.edge_text(step=1))
        # Enter toggles like Space, and the legend shows the two as one key.
        self.assertIn(KEY_SHOWN.format(label=legends.KeyName.SPACE_ENTER), self.text())
        await self.press(Key.ENTER)
        self.assertIs(self.value(row=Row.GLIDE), True)
        await self.press(Key.ENTER)
        self.assertIs(self.value(row=Row.GLIDE), False)

    async def test_accent_toggles_with_space_and_shows_the_dot(self):
        await self.go_to_row(Row.ACCENT)
        accent = self.editor.row_for(Row.ACCENT)
        self.assertEqual(accent.cell_text(step=0), marks.MSG_TOGGLE_OFF)
        await self.press(Key.SPACE)
        self.assertIs(self.value(row=Row.ACCENT), True)
        self.assertEqual(accent.cell_text(step=0), marks.MSG_TOGGLE_ON)
        await self.press(Key.ENTER)
        self.assertIs(self.value(row=Row.ACCENT), False)
        # Accent sits straight under Velocity.
        shown = [row.name for row in self.editor.rows_view.reachable()]
        self.assertEqual(shown.index(Row.ACCENT), shown.index(Row.VELOCITY) + 1)

    async def test_the_accidental_shows_only_a_sharp_or_a_flat(self):
        await self.go_to_row(Row.ACCIDENTAL)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=0), drawing_values.NOTHING)
        await self.press(Key.SPACE)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=0), Accidental.SHARP)
        await self.press(Key.SPACE)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=0), Accidental.FLAT)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=2), drawing_values.NOTHING)

    async def test_an_empty_step_has_nothing_to_change_but_cc_values(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await self.go_to_row(Row.VELOCITY)
        labels = [item.shown_label() for item in self.editor.keys()]
        self.assertNotIn(legends.KeyName.ENTER, labels)
        self.assertNotIn('+', labels)

    async def test_the_result_builds_and_saves(self):
        await self.press('5')
        await self.go_to_row(Row.GLIDE)
        await self.press(Key.SPACE)
        render_song(self.document.song())
        self.document.save(path='x.yml')
        Document.load('x.yml')

    async def test_shortening_asks_only_if_it_loses_something(self):
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = '1'
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 4)
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = '9'
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 9)
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = '5'
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 5)

    async def test_a_pattern_keeps_at_least_one_step(self):
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = '0'
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 4)
        self.assertIn(FROM_1_TO_4096, self.text())
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = '1'
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        if self.app.screen.view() is self.app.screen.roll:
            await self.press(keybindings.PatternEditor.TO_EDITOR)
        await self.press(keybindings.PatternRows.REMOVE_STEP)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_steps(), 1)

    async def test_insert_and_remove_step(self):
        await self.press(Key.RIGHT, keybindings.PatternRows.INSERT_STEP)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_row(Row.DEGREE), [1, None, 3, None, None])
        await self.press(keybindings.PatternRows.REMOVE_STEP)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_row(Row.DEGREE), [1, 3, None, None])

    async def test_long_patterns_scroll_sideways_to_keep_the_cursor_on_screen(self):
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = str(LONG)
        await self.press(Key.ENTER)
        shown = self.editor.drawing.steps_shown(self.SIZE[0])
        self.assertIn(marks.MSG_STEPS_SHOWN.format(before=drawing_values.NOTHING, first=1, last=shown, after=marks.MSG_MORE_AFTER), self.text())
        await self.press(*[Key.RIGHT] * HALFWAY)
        self.assertEqual(self.editor.step, HALFWAY)
        self.assertEqual(self.editor.first_step, HALFWAY - shown + 1)
        self.assertIn(marks.MSG_STEPS_SHOWN.format(before=marks.MSG_MORE_BEFORE, first=HALFWAY - shown + 2, last=HALFWAY + 1, after=marks.MSG_MORE_AFTER), self.text())
        self.assertIn(str(HALFWAY + 1), self.text())
        self.assertNotIn(ROW_SHOWN.format(label=labels_text.MSG_ROW_LABELS[Row.DEGREE]) + '  1  ', self.text())
        # Moving left past the window's first step scrolls it back one step.
        await self.press(*[Key.LEFT] * shown)
        self.assertEqual(self.editor.first_step, HALFWAY - shown)
        # Left on the first step stays there, since no cursor goes round, and End shows the end of the pattern.
        await self.press(Key.HOME, Key.LEFT)
        self.assertEqual(self.editor.step, 0)
        self.assertEqual(self.editor.first_step, 0)
        await self.press(Key.END)
        self.assertEqual(self.editor.step, LONG - 1)
        self.assertIn(marks.MSG_STEPS_SHOWN.format(before=marks.MSG_MORE_BEFORE, first=LONG - shown + 1, last=LONG, after=drawing_values.NOTHING), self.text())

    async def test_home_and_end_go_to_the_ends(self):
        await self.press(keybindings.PatternEditor.RESIZE)
        self.app.screen.value = str(LONG)
        await self.press(Key.ENTER)
        await self.press(Key.END)
        self.assertEqual(self.editor.step, LONG - 1)
        await self.press(Key.HOME)
        self.assertEqual(self.editor.step, 0)

    async def test_the_header_shows_the_time(self):
        self.assertIn('0:01', self.text())
