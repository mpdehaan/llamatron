# llamatron: a Python language and framework for producing MIDI clips.
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

"""The Patterns page and the pattern editor: its rows and row sets, drum patterns, directions, ties, rearranging and refusals."""

from fractions import Fraction

from ui_testing import KEY_SHOWN, QUIET_VALUE, ROW_SHOWN, UITest
from llamatron.composition.file_format import (
    CellSetting, Direction, REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, RegisterName, Row,
)
from llamatron.composition.limits import MAX_REGISTER_VALUE
from llamatron.composition.named_scale import scale_type_name
from llamatron.note import NoteName
from llamatron.scale import ScaleType
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, MessageDialog, PromptDialog
from llamatron.tui.document import Document
from llamatron.tui.pattern_editor import (
    ADVANCED, CC, DESCRIBE_TIED, NORMAL, NORMAL_ROWS, PatternEditor, REGISTERS, REGISTER_CHANGES, ROW_LABELS,
    ROW_SETS, ROW_SET_HEADERS, ROW_SET_NAMES, TOGGLE_ON,
)
from rendering import render_song


class TestPatternList(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p')

    def names(self):
        return self.document.song().get_pattern_names()

    async def test_plus_adds_one_and_opens_it(self):
        await self.press('+')
        self.app.screen.value = 'new'
        await self.press('enter')
        self.assertIn('new', self.names())
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.document.song().get_pattern('new').get_steps(), 16)

    async def test_u_and_d_move_the_selected_pattern(self):
        await self.press('d')
        self.assertEqual(self.names(), ['beat', 'tune', 'other'])
        self.assertEqual(self.app.screen.current(), 'tune')
        await self.press('u')
        self.assertEqual(self.names(), ['tune', 'beat', 'other'])

    async def test_s_sorts(self):
        await self.press('s')
        self.assertEqual(self.names(), ['beat', 'other', 'tune'])

    async def test_c_copies(self):
        await self.press('c')
        self.assertIn('tune copy', self.names())

    async def test_deleting_something_used_is_refused_and_says_what_uses_it(self):
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())
        await self.press('enter')
        self.assertIn('tune', self.names())

    async def test_a_refusal_lists_five_and_then_dots(self):
        for number in range(7):
            index = len(self.document.song().get_scenes())
            self.document.add_scene(index, f'x{number}')
            self.document.add_cell(index, 'lead', 'other')
        await self.press('down', 'down', 'backspace')
        text = self.text()
        self.assertEqual(text.count('(x'), 5)
        self.assertIn('... and 2 more', text)

    async def test_deleting_something_unused_confirms_first(self):
        await self.press('down', 'down', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertIn('other', self.names())
        await self.press('backspace', 'y')
        self.assertNotIn('other', self.names())

    async def test_a_duplicate_name_is_refused(self):
        await self.press('n')
        self.app.screen.value = 'beat'
        await self.press('enter')
        self.assertIn('tune', self.names())
        self.assertIn('already in use', self.text())

    async def test_renaming_updates_clips(self):
        await self.press('n')
        self.app.screen.value = 'melody'
        await self.press('enter')
        self.assertEqual(self.document.cell(0, 'lead').get_pattern_name(), 'melody')


# Names the tests give to the scales and chains they add.
SMALL_SCALE = 'small'


class PatternEditorTest(UITest):
    """Opens the tune pattern in the editor. Its tests are split across classes so that they run in parallel."""


    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'enter')
        self.editor = self.app.screen

    def value(self, row, step=None):
        return self.document.step_value('tune', row, self.editor.step if step is None else step)

    async def go_to_row(self, name):
        names = [row for row, _ in self.editor.rows()]
        for _ in range(names.index(name) - self.editor.row):
            await self.press('down')


class TestPatternEditorGrid(PatternEditorTest):
    """Moving around the grid, and putting notes in and taking them out."""

    async def test_grid_size_comes_from_the_step_count_and_typing_never_grows_it(self):
        self.assertEqual(self.text().count('│ Degree'), 1)
        await self.press('right', 'right', 'right')
        await self.press('5', '5', '5')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 4)
        self.assertEqual(len(self.document.song().get_pattern('tune').get_row(Row.DEGREE)), 4)

    async def test_typing_does_not_move_the_cursor(self):
        await self.press('right', '5')
        self.assertEqual((self.editor.step, self.editor.row), (1, 0))

    async def test_arrows_move_between_steps_and_rows(self):
        await self.press('right')
        self.assertEqual(self.editor.step, 1)
        await self.press('down')
        self.assertEqual(self.editor.row_name(), 'gate')
        await self.press('down')
        self.assertEqual(self.editor.row_name(), 'dot')
        await self.press('up', 'left')
        self.assertEqual((self.editor.row_name(), self.editor.step), ('gate', 0))

    async def test_the_rows_are_all_there_in_order(self):
        self.assertEqual([name for name, _ in self.editor.rows()], NORMAL_ROWS)

    async def test_a_new_note_gets_the_default_octave_and_a_gate_of_one_step(self):
        self.document.set_default_octave(4)
        await self.press('right', 'right', 'right', '5')
        self.assertEqual(self.value('degree'), 5)
        self.assertIsNone(self.value('gate'))
        self.assertEqual(self.value('octave'), 4)
        self.assertIn('gate 1/8', self.text())

    async def test_a_new_note_keeps_a_gate_it_already_has(self):
        await self.press('right', 'right', '5')
        self.assertEqual(self.value('gate'), '1/8')

    async def test_a_degree_must_fit_the_scale(self):
        self.document.add_scale(SMALL_SCALE, NoteName.C, scale_type_name(ScaleType.MAJOR_PENTATONIC))
        self.document.set_scale_name(SMALL_SCALE)
        self.document.set_scene_scale(0, None)
        self.document.changed()
        await self.press('6')
        self.assertEqual(self.value('degree'), 1)
        await self.press('5')
        self.assertEqual(self.value('degree'), 5)
        await self.press('+')
        self.assertEqual(self.value('degree'), 5)

    async def test_backspace_empties_a_step_which_is_a_rest(self):
        await self.press('backspace')
        self.assertIsNone(self.value('degree'))
        self.assertIsNone(self.value('gate'))
        self.assertIsNone(self.value('octave'))
        self.assertIn('Step 1: empty', self.text())

    async def test_backspace_on_an_empty_step_does_nothing(self):
        await self.press('backspace', 'backspace', 'backspace')
        self.assertIn('Step 1: empty', self.text())

    async def test_an_empty_step_has_no_gate_to_change(self):
        await self.press('right', 'right', 'right')
        self.assertIn('Step 4: empty', self.text())
        await self.press('down', '+')
        self.assertIsNone(self.value('gate'))


class TestPatternEditorLengthsAndPitches(PatternEditorTest):
    """The gate, dot, step size, accidental, octave and chord rows."""

    async def test_plus_and_minus_step_through_plain_lengths(self):
        await self.go_to_row(Row.GATE)
        await self.press('+')
        self.assertEqual(self.value('gate'), '1/2')
        await self.press('-', '-')
        self.assertEqual(self.value('gate'), '1/8')

    async def test_a_gate_cannot_go_below_the_shortest_length(self):
        await self.go_to_row(Row.GATE)
        for _ in range(8):
            await self.press('-')
        self.assertEqual(self.value('gate'), '1/64')

    async def test_star_and_slash_double_and_halve(self):
        await self.go_to_row(Row.GATE)
        await self.press('*')
        self.assertEqual(self.value('gate'), '1/2')
        await self.press('/', '/')
        self.assertEqual(self.value('gate'), '1/8')

    async def test_backspace_on_a_gate_makes_it_one_step(self):
        await self.go_to_row(Row.GATE)
        await self.press('backspace')
        self.assertIsNone(self.value('gate'))

    async def test_enter_types_a_gate_as_a_whole_number_or_a_fraction(self):
        await self.go_to_row(Row.GATE)
        await self.press('enter')
        self.app.screen.value = '5/16'
        await self.press('enter')
        self.assertEqual(self.value('gate'), '5/16')
        for typed in ['0.25', '0', '9']:
            await self.press('enter')
            self.app.screen.value = typed
            await self.press('enter')
            with self.subTest(typed=typed):
                self.assertEqual(self.value('gate'), '5/16')

    async def test_the_dot_row_makes_a_gate_dotted_or_a_triplet(self):
        await self.go_to_row(Row.DOT)
        await self.press('+')
        self.assertEqual(self.value('dot'), 'd')
        self.assertIn('gate 1/4 dotted', self.text())
        await self.press('+')
        self.assertEqual(self.value('dot'), 't')
        await self.press('backspace')
        self.assertIsNone(self.value('dot'))

    async def test_e_sets_the_pattern_step_size_and_blank_uses_the_song(self):
        await self.press('e')
        self.app.screen.value = '1/8'
        await self.press('enter')
        self.assertEqual(self.document.song().get_pattern('tune').get_step_size(), Fraction(1, 8))
        self.assertIn('Step size 1/8', self.text())
        await self.press('e')
        self.app.screen.value = ''
        await self.press('enter')
        self.assertIsNone(self.document.song().get_pattern('tune').get_step_size())
        self.assertIn("Step size 1/16 (the song's)", self.text())

    async def test_space_and_plus_and_minus_cycle_sharp_and_flat(self):
        await self.go_to_row(Row.ACCIDENTAL)
        await self.press('space')
        self.assertEqual(self.value('accidental'), '#')
        await self.press('+')
        self.assertEqual(self.value('accidental'), 'b')
        await self.press('space')
        self.assertIsNone(self.value('accidental'))
        await self.press('-')
        self.assertEqual(self.value('accidental'), 'b')

    async def test_octave_uses_whatever_is_typed(self):
        await self.go_to_row(Row.OCTAVE)
        await self.press('7')
        self.assertEqual(self.value('octave'), 7)
        await self.press('+', '+', '+')
        self.assertEqual(self.value('octave'), 8)
        for _ in range(12):
            await self.press('-')
        self.assertEqual(self.value('octave'), -2)

    async def test_chord_cycles_through_the_symbols(self):
        await self.go_to_row(Row.CHORD)
        seen = []
        for _ in range(4):
            await self.press('+')
            seen.append(self.value('chord'))
        self.assertEqual(seen, ['M', 'm', 'dim', 'aug'])
        await self.press('-', '-', '-', '-', '-')
        self.assertEqual(self.value('chord'), 13)
        await self.press('-')
        self.assertEqual(self.value('chord'), 11)


class TestPatternEditorOtherRowsAndSize(PatternEditorTest):
    """The remaining rows, and changing how many steps a pattern has."""

    async def test_velocity_probability_and_ratchet(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press('-')
        self.assertEqual(self.value('velocity'), 126)
        await self.press('enter')
        self.app.screen.value = '60'
        await self.press('enter')
        self.assertEqual(self.value('velocity'), 60)
        await self.press('down', '-')
        self.assertEqual(self.value('probability'), 99)
        await self.press('pagedown')
        await self.go_to_row(Row.RATCHET)
        await self.press('+')
        self.assertEqual(self.value('ratchet'), 2)

    async def test_a_typed_value_out_of_range_is_refused(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press('enter')
        self.app.screen.value = '500'
        await self.press('enter')
        self.assertIsNone(self.value('velocity'))
        self.assertIn('from 1 to 127', self.text())

    async def test_glide_toggles_with_space_and_shows_a_star(self):
        await self.go_to_row(Row.GLIDE)
        self.assertEqual(self.editor.cell_text('glide', 0), ' ')
        await self.press('space')
        self.assertIs(self.value('glide'), True)
        self.assertEqual(self.editor.cell_text('glide', 0), '*')
        await self.press('space')
        self.assertIs(self.value('glide'), False)
        self.assertEqual(self.editor.cell_text('glide', 0), ' ')

    async def test_an_empty_step_has_nothing_to_change_but_cc_values(self):
        await self.press('right', 'right')
        await self.go_to_row(Row.VELOCITY)
        labels = [item.shown_label() for item in self.editor.keys()]
        self.assertNotIn('Enter', labels)
        self.assertNotIn('+', labels)

    async def test_the_result_builds_and_saves(self):
        await self.press('5')
        await self.go_to_row(Row.GLIDE)
        await self.press('space')
        render_song(self.document.song())
        self.document.save('x.yml')
        Document.load('x.yml')

    async def test_shortening_asks_only_if_it_loses_something(self):
        await self.press('r')
        self.app.screen.value = '1'
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 4)
        await self.press('r')
        self.app.screen.value = '9'
        await self.press('enter')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 9)
        await self.press('r')
        self.app.screen.value = '5'
        await self.press('enter')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 5)

    async def test_a_pattern_keeps_at_least_one_step(self):
        await self.press('r')
        self.app.screen.value = '0'
        await self.press('enter')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 4)
        self.assertIn('from 1 to 4096', self.text())
        await self.press('r')
        self.app.screen.value = '1'
        await self.press('enter', 'y', 'x')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 1)

    async def test_insert_and_remove_step(self):
        await self.press('right', 'i')
        self.assertEqual(self.document.song().get_pattern('tune').get_row(Row.DEGREE), [1, None, 3, None, None])
        await self.press('x')
        self.assertEqual(self.document.song().get_pattern('tune').get_row(Row.DEGREE), [1, 3, None, None])

    async def test_long_patterns_wrap_and_stay_on_screen(self):
        await self.press('r')
        self.app.screen.value = '200'
        await self.press('enter')
        await self.press(*['right'] * 100)
        self.assertEqual(self.editor.step, 100)
        self.assertIn('101', self.text())

    async def test_the_header_shows_the_time(self):
        self.assertIn('0:01', self.text())


class TestDrumPatterns(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'down', 'enter')
        self.editor = self.app.screen

    def value(self, row):
        return self.document.step_value('beat', row, self.editor.step)

    async def test_takes_letters_in_upper_or_lower_case(self):
        await self.press('right', 'f')
        self.assertEqual(self.value('degree'), 'F')
        await self.press('G')
        self.assertEqual(self.value('degree'), 'G')

    async def test_a_new_hit_gets_the_drum_octave(self):
        self.document.set_default_drum_octave(2)
        await self.press('i', 'c')
        self.assertEqual(self.value('octave'), 2)

    async def test_has_no_chord_row(self):
        self.assertNotIn('chord', [name for name, _ in self.editor.rows()])
        self.assertIn('│ Note', self.text())

    async def test_numbers_do_nothing(self):
        await self.press('5')
        self.assertEqual(self.value('degree'), 'C')

    async def test_the_toggle_asks_before_clearing_notes(self):
        await self.press('t')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertTrue(self.document.song().get_pattern('beat').is_drum())
        await self.press('t', 'y')
        self.assertFalse(self.document.song().get_pattern('beat').is_drum())
        self.assertFalse(self.document.has_notes('beat'))

    async def test_it_builds(self):
        await self.press('right', 'f')
        render_song(self.document.song())


class TestPatternEditorRefusals(UITest):

    async def open(self, name):
        await self.press('p', *['down'] * self.document.song().get_pattern_names().index(name), 'enter')
        self.editor = self.app.screen
        self.assertIsInstance(self.editor, PatternEditor)

    async def go_to_row(self, name):
        names = [row for row, _ in self.editor.rows()]
        for _ in range(names.index(name) - self.editor.row):
            await self.press('down')

    async def test_flip_and_swap_say_when_there_is_nothing_to_move(self):
        await self.open('other')
        await self.press('f')
        self.assertIn('no steps after this one', self.text())
        await self.press('s')
        self.assertIn('no other steps to swap', self.text())

    async def test_load_over_needs_another_pattern(self):
        # Only one pattern can stay, so the scenes that play the others go first, as a person would have to delete them.
        for index in reversed(range(len(self.document.song().get_scenes()))):
            self.document.delete_scene(index)
        for name in self.document.song().get_pattern_names():
            if name != 'tune':
                self.document.delete_pattern(name)
        await self.open('tune')
        await self.press('l')
        self.assertIn('no other patterns to load', self.text())

    async def test_load_over_a_pattern_with_notes_asks_first(self):
        await self.open('tune')
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('other')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertEqual(self.document.song().get_pattern('tune').get_row(Row.DEGREE), [5])

    async def test_the_step_count_must_be_a_sensible_number(self):
        await self.open('tune')
        for text, message in [('lots', 'not a whole number'), ('0', 'Steps must be from 1 to 4096')]:
            await self.press('r')
            self.app.screen.value = text
            await self.press('enter')
            self.assertIn(message, self.text())
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 4)

    async def test_shortening_past_steps_that_hold_something_asks_first(self):
        await self.open('tune')
        await self.press('r')
        self.app.screen.value = '1'
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertEqual(self.document.song().get_pattern('tune').get_steps(), 1)

    async def test_a_typed_velocity_must_be_in_range(self):
        await self.open('tune')
        await self.go_to_row(Row.VELOCITY)
        for text, message in [('loud', 'not a whole number'), ('200', 'Velocity must be from 1 to 127')]:
            await self.press('enter')
            self.app.screen.value = text
            await self.press('enter')
            self.assertIn(message, self.text())
        self.assertIsNone(self.document.step_value('tune', Row.VELOCITY, 0))

    async def test_turning_a_pattern_with_notes_into_drums_asks_first(self):
        await self.open('tune')
        await self.press('t')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('letters', self.text())
        await self.press('y')
        self.assertTrue(self.document.song().get_pattern('tune').is_drum())
        self.assertIsNone(self.document.song().get_pattern('tune').get_row(Row.DEGREE))

    async def test_renaming_to_a_name_in_use_is_refused(self):
        await self.open('tune')
        await self.press('n')
        self.app.screen.value = 'beat'
        await self.press('enter')
        self.assertIn('already in use', self.text())
        self.assertTrue(self.document.song().has_pattern('tune'))

    async def test_backspace_on_a_gate_makes_it_one_step(self):
        await self.open('tune')
        await self.go_to_row(Row.GATE)
        await self.press('backspace')
        self.assertIsNone(self.document.step_value('tune', Row.GATE, 0))

    async def test_an_octave_without_a_value_starts_from_the_default(self):
        await self.open('other')
        await self.go_to_row(Row.OCTAVE)
        await self.press('+')
        self.assertEqual(self.document.step_value('other', Row.OCTAVE, 0), self.document.song().get_default_octave() + 1)

    async def test_a_long_pattern_draws_more_than_one_block(self):
        self.document.set_steps('tune', 64)
        await self.open('tune')
        self.assertGreater(self.text().count('│ Degree'), 1)



class TestDirectionsAndGrab(UITest):

    async def test_a_pattern_chooses_a_direction(self):
        await self.press('p', 'enter', 'p')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], 'forward    first step to last')
        self.assertEqual(self.app.screen.options[1], 'reverse a  step 1, then backward from the last')
        self.app.screen.place = 4
        await self.press('enter')
        self.assertEqual(self.document.song().get_pattern('tune').get_direction(), Direction.PENDULUM)
        self.assertIn('Direction pendulum', self.text())
        render_song(self.document.song())

    async def clip_page(self):
        await self.press('a', 'right', 'enter')
        return self.app.screen

    async def go_to(self, page, label):
        page.place = [field.label for field in page.fields()].index(label)
        page.draw()
        await self.pilot.pause()

    async def test_a_clip_shows_the_patterns_direction_until_it_overrides_it(self):
        self.document.set_direction('tune', Direction.ALTERNATE)
        page = await self.clip_page()
        self.assertIn('(pattern: alternate)', self.text())
        await self.go_to(page, 'Direction')
        await self.press('right')
        self.assertEqual(self.document.cell(0, 'lead').get_direction(), Direction.FORWARD)
        await self.press('right')
        self.assertEqual(self.document.cell(0, 'lead').get_direction(), Direction.REVERSE_A)
        await self.press('backspace')
        self.assertIsNone(self.document.cell(0, 'lead').get_direction())

    async def test_a_clip_direction_can_be_chosen_from_a_list(self):
        page = await self.clip_page()
        await self.go_to(page, 'Direction')
        await self.press('enter')
        self.assertEqual(self.app.screen.options[0], "(pattern)  use each pattern's direction")
        self.assertEqual(self.app.screen.options[1], 'forward    first step to last')
        self.app.screen.place = self.app.screen.options.index('brownian   on 50%, back 25%, stay 25%')
        await self.press('enter')
        self.assertEqual(self.document.cell(0, 'lead').get_direction(), Direction.BROWNIAN)

    async def test_the_grid_marks_a_clip_with_its_own_direction(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.DIRECTION, Direction.RANDOM)
        await self.press('a')
        self.assertIn('tune d', self.text())

    async def test_the_grab_row_is_always_in_the_advanced_rows(self):
        await self.press('p', 'enter')
        self.assertNotIn(ROW_SHOWN.format(label=ROW_LABELS[Row.GRAB]), self.text())
        await self.press('pagedown')
        self.assertIn(ROW_SHOWN.format(label=ROW_LABELS[Row.GRAB]), self.text())
        self.assertIn(ROW_SET_HEADERS[ADVANCED], self.text())

    async def test_marking_a_step_with_space(self):
        await self.press('p', 'enter', 'pagedown')
        while self.app.screen.row_name() != Row.GRAB:
            await self.press('down')
        await self.press('space')
        self.assertTrue(self.document.step_value('tune', Row.GRAB, 0))
        self.assertEqual(self.app.screen.cell_text('grab', 0), '*')
        render_song(self.document.song())


class TestDirectionsAndGrabOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_everything_still_fits_with_the_grab_row(self):
        await self.press('p', 'enter', 'pagedown')
        text = self.text()
        self.assertIn(ROW_SHOWN.format(label=ROW_LABELS[Row.GRAB]), text)
        self.assertIn('Step 1:', text)
        for item in self.app.screen.key_table():
            self.assertIn(f'« {item.shown_label()} »', text)


class TestRowSets(UITest):
    """PgDn and PgUp step the rows under Degree through the editor's sets of rows."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'enter')
        self.editor = self.app.screen

    async def go_to_set(self, row_set):
        """Press PgDn until a set of rows shows."""
        while self.app.row_set != row_set:
            await self.press('pagedown')

    def shown(self, row):
        return ROW_SHOWN.format(label=ROW_LABELS[row])

    async def test_pgdn_goes_through_every_set_in_order_and_round(self):
        for row_set, rows in ROW_SETS.items():
            self.assertEqual(self.app.row_set, row_set)
            text = self.text()
            for row in rows:
                self.assertIn(self.shown(row), text)
            await self.press('pagedown')
        self.assertEqual(self.app.row_set, NORMAL)

    async def test_pgup_goes_back(self):
        await self.press('pageup')
        self.assertEqual(self.app.row_set, list(ROW_SETS)[-1])
        await self.press('pagedown')
        self.assertEqual(self.app.row_set, NORMAL)

    async def test_the_key_names_the_next_set(self):
        self.assertIn(ROW_SET_NAMES[ADVANCED], self.text())

    async def test_cc_rows_take_values_even_on_a_rest(self):
        await self.go_to_set(CC)
        rest = 2
        value = 100
        await self.press('right', 'right', 'down')
        self.assertEqual(self.editor.row_name(), Row.CC1)
        self.assertEqual(self.editor.cell_text(Row.CC1, rest), QUIET_VALUE)
        await self.press(*str(value))
        self.assertEqual(self.document.step_value('tune', Row.CC1, rest), value)
        await self.press('+')
        self.assertEqual(self.document.step_value('tune', Row.CC1, rest), value + 1)
        await self.press('backspace')
        self.assertIsNone(self.document.step_value('tune', Row.CC1, rest))
        while self.editor.row_name() != Row.SLIDE:
            await self.press('down')
        await self.press('space')
        self.assertIs(self.document.step_value('tune', Row.SLIDE, rest), True)
        self.assertEqual(self.editor.cell_text(Row.SLIDE, rest), TOGGLE_ON)
        render_song(self.document.song())

    async def test_the_set_stays_for_other_patterns(self):
        await self.press('pagedown', 'tab', 'enter')
        self.assertIn(self.shown(Row.RATCHET_OFFSET), self.text())

    async def test_switching_keeps_degree_and_otherwise_goes_to_it(self):
        for _ in ROW_SETS:
            await self.press('down', 'pagedown')
            self.assertEqual(self.editor.row_name(), Row.DEGREE)

    async def test_typing_a_ratchet_offset_and_going_negative(self):
        await self.go_to_set(ADVANCED)
        while self.editor.row_name() != Row.RATCHET_OFFSET:
            await self.press('down')
        typed = 2
        await self.press(str(typed))
        self.assertEqual(self.document.step_value('tune', Row.RATCHET_OFFSET, 0), typed)
        presses = typed + 1
        await self.press(*['-'] * presses)
        self.assertEqual(self.document.step_value('tune', Row.RATCHET_OFFSET, 0), typed - presses)
        self.assertEqual(self.editor.cell_text(Row.RATCHET_OFFSET, 0), str(typed - presses))

    async def test_unset_register_changes_show_a_dot(self):
        await self.go_to_set(REGISTER_CHANGES)
        for row in REGISTER_ADD_ROWS.values():
            self.assertEqual(self.editor.cell_text(row, 0), QUIET_VALUE)

    async def test_register_changes_take_typed_values_including_negative_ones_even_on_a_rest(self):
        await self.go_to_set(REGISTER_CHANGES)
        rest = 2
        typed = -3
        row = REGISTER_ADD_ROWS[RegisterName.BX]
        await self.press('right', 'right')
        while self.editor.row_name() != row:
            await self.press('down')
        await self.press('enter')
        self.app.screen.value = str(typed)
        await self.press('enter')
        self.assertEqual(self.document.step_value('tune', row, rest), typed)
        await self.press('enter')
        self.app.screen.value = str(MAX_REGISTER_VALUE + 1)
        await self.press('enter')
        self.assertEqual(self.document.step_value('tune', row, rest), typed)
        render_song(self.document.song())

    async def test_register_uses_are_toggles_on_notes(self):
        await self.go_to_set(REGISTERS)
        row = REGISTER_VELOCITY_ROWS[RegisterName.CX]
        while self.editor.row_name() != row:
            await self.press('down')
        await self.press('space')
        self.assertIs(self.document.step_value('tune', row, 0), True)
        self.assertEqual(self.editor.cell_text(row, 0), TOGGLE_ON)
        await self.press('backspace')
        self.assertIs(self.document.step_value('tune', row, 0), False)

    async def test_a_drum_pattern_has_no_rows_that_move_notes(self):
        await self.go_to_set(REGISTERS)
        await self.press('tab', 'down', 'enter')
        rows = [name for name, _ in self.app.screen.rows()]
        for name in REGISTER_NOTE_ROWS.values():
            self.assertNotIn(name, rows)
        for name in REGISTER_VELOCITY_ROWS.values():
            self.assertIn(name, rows)

    async def test_on_a_drum_note_row_a_and_f_are_notes(self):
        await self.press('tab', 'down', 'enter')
        editor = self.app.screen
        await self.press('right', 'a')
        self.assertEqual(self.document.step_value('beat', Row.DEGREE, 1), 'A')
        self.assertEqual(self.app.row_set, NORMAL)
        await self.press('f')
        self.assertEqual(self.document.step_value('beat', Row.DEGREE, 1), 'F')
        labels = [item.shown_label() for item in editor.key_table()]
        self.assertNotIn('F', labels)

    async def test_on_other_drum_rows_f_is_a_command(self):
        await self.press('tab', 'down', 'enter', 'down')
        labels = [item.shown_label() for item in self.app.screen.key_table()]
        self.assertIn('F', labels)


class TestAdvancedRowsOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_every_set_of_rows_fits(self):
        await self.press('p', 'enter')
        for _ in ROW_SETS:
            text = self.text()
            self.assertIn('Step 1:', text)
            for item in self.app.screen.key_table():
                self.assertIn(KEY_SHOWN.format(label=item.shown_label()), text)
            await self.press('pagedown')


class TestTieRow(UITest):
    """Tie is on the normal rows, works only on empty steps, and holds the note before it."""

    EMPTY_STEP = 2

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('p', 'enter')
        self.editor = self.app.screen
        while self.editor.row_name() != Row.TIE:
            await self.press('down')

    def tie(self, step):
        return self.document.step_value('tune', Row.TIE, step)

    async def test_it_is_a_normal_row_and_toggles_on_an_empty_step(self):
        self.assertIn(ROW_SHOWN.format(label=ROW_LABELS[Row.TIE]), self.text())
        await self.press(*['right'] * self.EMPTY_STEP)
        await self.press('space')
        self.assertIs(self.tie(self.EMPTY_STEP), True)
        self.assertEqual(self.editor.cell_text(Row.TIE, self.EMPTY_STEP), TOGGLE_ON)
        self.assertIn(DESCRIBE_TIED.format(step=self.EMPTY_STEP + 1), self.text())
        render_song(self.document.song())
        await self.press('backspace')
        self.assertIs(self.tie(self.EMPTY_STEP), False)

    async def test_a_step_with_a_note_has_no_tie_keys(self):
        labels = [item.shown_label() for item in self.editor.key_table()]
        self.assertNotIn('Space', labels)
        await self.press('space')
        self.assertFalse(self.tie(0))

    async def test_typing_a_degree_on_a_tied_step_removes_the_tie(self):
        await self.press(*['right'] * self.EMPTY_STEP, 'space')
        while self.editor.row_name() != Row.DEGREE:
            await self.press('up')
        await self.press('5')
        self.assertIs(self.tie(self.EMPTY_STEP), False)
        self.assertEqual(self.document.step_value('tune', Row.DEGREE, self.EMPTY_STEP), 5)
        render_song(self.document.song())

    async def test_shortening_past_a_tie_asks_first(self):
        last = self.editor.steps() - 1
        await self.press(*['right'] * last, 'space')
        await self.press('r')
        self.app.screen.value = str(last)
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)


# A five-step pattern the rearranging tests flip and swap, with a different value on every step.
LONG_PATTERN = 'long'


LONG_PATTERN_STEPS = 5


LONG_PATTERN_ROWS = {
    Row.DEGREE: [1, 2, 3, 4, 5],
    Row.GATE: ['1/4', '1/8', '1/16', '1/2', '1'],
    Row.VELOCITY: [10, 20, 30, 40, 50],
}


class TestRearrangingAPattern(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.add_pattern_with_rows(LONG_PATTERN, LONG_PATTERN_STEPS, LONG_PATTERN_ROWS)
        await self.press('p', 'down', 'down', 'down', 'enter')
        self.editor = self.app.screen

    def rows(self, row=Row.DEGREE):
        return self.document.song().get_pattern(LONG_PATTERN).get_row(row)

    async def test_flip_reverses_everything_after_the_cursor(self):
        await self.press('right', 'f')
        self.assertEqual(self.rows(), [1, 2, 5, 4, 3])

    async def test_every_row_moves_with_its_step(self):
        await self.press('right', 'f')
        self.assertEqual(self.rows(Row.GATE), ['1/4', '1/8', '1', '1/2', '1/16'])
        self.assertEqual(self.rows(Row.VELOCITY), [10, 20, 50, 40, 30])

    async def test_flip_twice_puts_it_back_and_the_cursor_stays(self):
        await self.press('right', 'f', 'f')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_flip_on_the_last_step_says_why_nothing_happens(self):
        await self.press('left', 'f')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertIn('no steps after', self.text())

    async def test_swap_exchanges_both_sides_of_the_cursor(self):
        await self.press('right', 's')
        self.assertEqual(self.rows(), [3, 4, 5, 2, 1])
        self.assertEqual(self.rows(Row.GATE), ['1/16', '1/2', '1', '1/8', '1/4'])

    async def test_the_cursor_stays_on_its_step_so_swapping_twice_puts_it_back(self):
        await self.press('right', 's')
        self.assertEqual(self.editor.step, 3)
        self.assertEqual(self.document.step_value(LONG_PATTERN, Row.DEGREE, self.editor.step), 2)
        await self.press('s')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_swap_at_either_end(self):
        await self.press('s')
        self.assertEqual(self.rows(), [2, 3, 4, 5, 1])
        self.assertEqual(self.editor.step, 4)

    async def test_the_time_stays_the_same(self):
        before = self.document.pattern_length(LONG_PATTERN)
        await self.press('right', 'f', 's')
        self.assertEqual(self.document.pattern_length(LONG_PATTERN), before)

    async def test_load_replaces_everything_after_asking(self):
        await self.press('l')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertNotIn(LONG_PATTERN, self.app.screen.options)
        self.app.screen.place = self.app.screen.options.index('beat')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('n')
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('beat')
        await self.press('enter', 'y')
        song = self.document.song()
        self.assertEqual(song.get_pattern(LONG_PATTERN).to_data(), song.get_pattern('beat').to_data())
        self.assertEqual(self.editor.steps(), 2)
        self.assertIn('│ Note', self.text())

    async def test_a_loaded_copy_is_separate(self):
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('beat')
        await self.press('enter', 'y', 'right', 'f')
        self.assertEqual(self.document.step_value(LONG_PATTERN, Row.DEGREE, 1), 'F')
        self.assertIsNone(self.document.step_value('beat', Row.DEGREE, 1))

    async def test_load_keeps_the_name_and_what_uses_it(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.PATTERN, LONG_PATTERN)
        await self.press('l')
        self.app.screen.place = self.app.screen.options.index('other')
        await self.press('enter', 'y')
        self.assertEqual(self.document.song().get_scenes()[0].get_cell('lead').get_pattern_name(), LONG_PATTERN)
        render_song(self.document.song())

    async def test_the_old_keys_moved(self):
        await self.press('r')
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertEqual(self.app.screen.value, '5')
