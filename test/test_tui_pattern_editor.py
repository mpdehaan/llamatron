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

"""The Patterns page and the pattern editor: its rows and row sets, drum patterns, directions, ties, rearranging and refusals."""

from fractions import Fraction

from ui_testing import fixed_text, KEY_SHOWN, QUIET_VALUE, REVERSED, ROW_SHOWN, UITest, back_key, forward_key, key_name, key_of
from llamatron.tui.screens.main_page import MainPage
from llamatron.strings.marks import MSG_PATTERN_DIRECTION_SHOWN
from llamatron.composition.naming import words
from llamatron.composition.limits import MIN_DEGREE
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS, RowOfNumbers
from llamatron.composition.file_format import (
    Accidental,
    ClipSlotSetting,
    ChordSymbol,
    Direction,
    GateModifier,
    OctaveLabels,
    CONDITION_ROWS,
    REGISTER_ADD_ROWS,
    REGISTER_NOTE_ROWS,
    REGISTER_SET_ROWS,
    REGISTER_VELOCITY_ROWS,
    RegisterSetting,
    Comparison,
    RegisterName,
    RegisterUse,
    Row,
    Section,
)
from llamatron.composition.limits import MAX_OCTAVE, MAX_REGISTER_VALUE, MAX_STEPS, MIN_OCTAVE, MIN_STEPS
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.defaults import DEFAULT_TIME_SIGNATURE
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.tui.drawing import Align, Box, NOTHING, SPACE, Style, fit
from llamatron.tui.screens.grid_drawing import CELL_WIDTH
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.document import Document
from llamatron.tui.keys import HOME_END, Key, OPEN_AT_START, RowSection, SHIFT_LEFT_RIGHT, SHIFT_UP_DOWN
from llamatron.tui.components.pattern_rows import PINNED_ROWS, SECTIONS
from llamatron.tui.screens.pattern_editor import Munge, PatternEditor, Reconfigure, reconfigure_choices
from llamatron.tui.components.degree_row import GAUGE_ROWS_WITHOUT_SCALE
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.music.midi import MAX_CC_VALUE
from llamatron.strings.errors import (
    ERR_AT_ALLOWED_INC_MAX, ERR_BOTTOM_OF_SCALE, ERR_NOTHING_AFTER, ERR_NOTHING_BEFORE, ERR_NOTHING_TO_PIVOT, ERR_ONE_STEP, ERR_STEPS_OUT_OF_RANGE,
    ERR_TOP_OF_SCALE,
)
from llamatron.strings.labels import (
    MSG_CC_ROW_LABEL, MSG_SCALE_HEADER, MSG_SEVERAL_SCALES, MSG_MUNGE_CHOICES, MSG_ROW_LABELS, MSG_SECTION_HINTS, MSG_SECTION_LABEL,
    MSG_SECTION_NAMES,
)
from llamatron.strings.legends import MSG_TO_EDITOR_WHAT, MSG_TO_ROLL_WHAT, MSG_DRUM_ON_WHAT, MSG_LEGEND_WHAT, What, KeyName
from llamatron.strings.marks import (
    MSG_UNSET_MARK,
    MSG_BLOCKED_CELL, MSG_CC_LANE_OFF, MSG_CC_LANE_VARIES, MSG_GAUGE_BAR, MSG_FROM_SONG_SHOWN, MSG_MORE_AFTER,
    MSG_MORE_BEFORE, MSG_SECTION_CLOSED_MARK, MSG_SECTION_OPEN_MARK, MSG_SEARCH_SHOWN, MSG_STEPS_SHOWN, MSG_STEP_SIZE_SHOWN, MSG_TIME_SIGNATURE_SHOWN,
    MSG_REGISTER_ADDS, MSG_REGISTER_SUBTRACTS, MSG_TOGGLE_OFF, MSG_TOGGLE_ON,
)
from llamatron.strings.messages import (
    MSG_CHANGE_TYPE_EMPTY_QUESTION, MSG_DESCRIBE_CHORD, MSG_DESCRIBE_GATE_OVERRIDDEN, MSG_DESCRIBE_TIED, MSG_GRABBED_SOUND, MSG_SEARCH_STATUS,
)
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from rendering import render_song

# Names the tests give to their own things, and other values they use.
# Patterns added out of order, with a capital, to see a picker sort them.
UNSORTED_PATTERN_NAMES = ('zed', 'Alpha', 'mid')
# Typed into a search, and the one of those names it finds.
SEARCH_TEXT = 'al'
SEARCH_HIT = 'Alpha'
NEW = 'new'
BEAT = 'beat'
MELODY = 'melody'
TUNE = 'tune'
# Where a test saves the set to read the file back.
SAVED_SET = 'saved.yml'
TUNE_COPY = 'tune 2'
OTHER = 'other'
ALREADY_IN_USE = 'already in use'
LEAD = 'lead'
EIGHTH = '1/8'
# Time signatures the tests set, as a file writes them.
WALTZ = '3/4'
THREE_EIGHT = '3/8'
CUT_TIME = '2/2'
FIVE_SIXTEENTHS = '5/16'
HALF = '1/2'
QUARTER = '1/4'
# The keys that doubled and halved a gate before 2026-11-09, which now do nothing on the Gate row.
GATE_KEYS_REMOVED = ('*', '/')
# A pattern too wide for the screen, and a step about halfway along it.
LONG = 64
HALFWAY = 32
FROM_1_TO_127 = 'from 1 to 127'
FROM_1_TO_4096 = 'from 1 to 4096'
NO_OTHER_PATTERNS_TO_LOAD = 'no other patterns to load'
LETTERS = 'letters'
# What the Patterns page's + calls the first new pattern, and C major's notes from the root, as the gauge labels its rows.
NEW_PATTERN = 'pattern 4'
C_MAJOR_NOTES = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
# Two CC numbers for a track's first lane, the mod wheel and brightness, and a second track added to play tune.
MOD_WHEEL = 1
BRIGHTNESS = 74
SECOND_TRACK = 'second'
# The step of tune that holds nothing.
EMPTY_STEP = 2
# The register rows whose line is narrower than a file allows, and an Allowed Inc Max narrower than the default.
NARROWER_ROWS = {*REGISTER_ADD_ROWS.values(), *REGISTER_SET_ROWS.values()}
NARROW_INC_MAX = 4
# What Space or Enter goes through on a condition row, from blank, and back to blank.
COMPARISON_CYCLE = [Comparison.LESS, Comparison.MORE, Comparison.SAME, None]
# The rows open when the editor opens: the pinned rows, then each section's heading with its rows where the section starts open.
ROWS_AT_START = [*PINNED_ROWS, *[name for section in SECTIONS for name in (section, *(SECTIONS[section] if section in OPEN_AT_START else []))]]


def section_label(section, *, open_):
    """Return a section's heading as the grid shows it, with its mark for open or closed."""
    return MSG_SECTION_LABEL.format(mark=MSG_SECTION_OPEN_MARK if open_ else MSG_SECTION_CLOSED_MARK, name=MSG_SECTION_NAMES[section])


async def open_section(*, test, section):
    """Press Tab until the cursor is on a section's heading, and Space to open it if it's closed."""
    editor = test.app.screen
    while editor.row_name() != section:
        await test.press(Key.PAGE_DOWN)
    if not editor.rows_view.section_is_open(section):
        await test.press(Key.SPACE)
LOTS = 'lots'
NOT_AN_INTEGER = 'is not an integer'
LOUD = 'loud'
DIRECTION_PENDULUM = 'Direction pendulum'
TUNE_D = 'tune d'
DIRECTION = 'Direction'
QUARTER = '1/4'
SIXTEENTH = '1/16'


async def munge(*, test, choice):
    """Open the munge dialog in a test's editor and pick one of its ways of rearranging the steps."""
    await test.reconfigure(Reconfigure.MUNGE)
    test.assertIsInstance(test.app.screen, ChoiceDialog)
    test.assertEqual(test.app.screen.options, MSG_MUNGE_CHOICES)
    await test.press(*([Key.DOWN] * choice), Key.ENTER)


class TestPatternsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS)

    def names(self):
        return self.document.song().get_pattern_names()

    async def test_a_adds_one_and_opens_it(self):
        await self.press(keybindings.PatternsPage.ADD)
        self.app.screen.value = NEW
        await self.press(Key.ENTER)
        self.assertIn(NEW, self.names())
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.document.song().get_pattern(NEW).get_steps(), 16)

    async def test_u_and_d_move_the_selected_pattern(self):
        await self.press(keybindings.PatternsPage.MOVE, Key.DOWN, Key.ENTER)
        self.assertEqual(self.names(), [BEAT, TUNE, OTHER])
        self.assertEqual(self.app.screen.current(), TUNE)
        await self.press(keybindings.PatternsPage.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.names(), [TUNE, BEAT, OTHER])

    async def test_s_sorts(self):
        await self.press(keybindings.PatternsPage.SORT)
        self.assertEqual(self.names(), [BEAT, OTHER, TUNE])

    async def test_c_copies(self):
        await self.press(keybindings.PatternsPage.COPY)
        self.assertIn(TUNE_COPY, self.names())

    async def test_deleting_something_used_is_refused_and_says_what_uses_it(self):
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())
        await self.press(Key.ENTER)
        self.assertIn(TUNE, self.names())

    async def test_a_refusal_lists_five_and_then_dots(self):
        for number in range(7):
            index = len(self.document.song().get_scenes())
            self.document.add_scene(index=index, name=f'x{number}')
            self.document.add_clip_slot(index=index, track=LEAD, pattern=OTHER)
        await self.press(Key.DOWN, Key.DOWN, Key.BACKSPACE)
        text = self.text()
        self.assertEqual(text.count('(x'), 5)
        self.assertIn('... and 2 more', text)

    async def test_deleting_something_unused_confirms_first(self):
        await self.press(Key.DOWN, Key.DOWN, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertIn(OTHER, self.names())
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertNotIn(OTHER, self.names())

    async def test_a_duplicate_name_is_refused(self):
        await self.press(keybindings.PatternsPage.RENAME)
        self.app.screen.value = BEAT
        await self.press(Key.ENTER)
        self.assertIn(TUNE, self.names())
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_renaming_updates_clips(self):
        await self.press(keybindings.PatternsPage.RENAME)
        self.app.screen.value = MELODY
        await self.press(Key.ENTER)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_pattern_name(), MELODY)

    async def test_slash_searches_the_list_and_enter_keeps_the_place(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        self.assertEqual(self.app.screen.current(), TUNE)
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(SEARCH_TEXT)
        self.assertEqual(self.app.screen.current(), SEARCH_HIT)
        self.assertIn(MSG_SEARCH_STATUS.format(text=SEARCH_TEXT), self.text())
        self.assertNotIn(BEAT, self.text())
        await self.press(Key.TAB)
        self.assertEqual(self.app.screen.typed, SEARCH_HIT)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.current(), SEARCH_HIT)
        self.assertIn(BEAT, self.text())
        self.assertFalse(self.app.screen.searching)

    async def test_esc_ends_a_search_and_puts_the_cursor_back(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        await self.press(Key.DOWN, keybindings.PatternsPage.SEARCH)
        await self.type(SEARCH_TEXT)
        self.assertEqual(self.app.screen.current(), SEARCH_HIT)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.app.screen.current(), BEAT)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)


# Names the tests give to the scales and chains they add.
SMALL_SCALE = 'small'


class PatternEditorTest(UITest):
    """Opens the tune pattern in the editor, on its rows past the piano roll. Its tests are split across classes so that they run in parallel."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def value(self, *, row, step=None):
        return self.document.step_value(name=TUNE, row=row, step=self.editor.step if step is None else step)

    async def go_to_row(self, name):
        """Move the cursor to a row, opening the section that has it first if it's closed."""
        if name not in [row.name for row in self.editor.rows_view.reachable()]:
            await open_section(test=self, section=self.editor.rows_view.section_of(name))
        names = [row.name for row in self.editor.rows_view.reachable()]
        while self.editor.rows_view.row != names.index(name):
            await self.press(Key.DOWN if self.editor.rows_view.row < names.index(name) else Key.UP)


class TestTheRowsLimitsAreTheFiles(PatternEditorTest):
    """A row of numbers stops where the row's one description says, which is what a file's values are checked against (composition/row_descriptions.py)."""

    async def test_every_row_of_numbers_stops_at_the_limits_a_file_is_checked_against(self):
        for name, described in ROW_DESCRIPTIONS.items():
            # The register rows that change a register step through a shorter line than a file allows, by the user's design: TestRegisterChangeRows holds them to it.
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


class TestPatternEditor(PatternEditorTest):
    """Moving around the grid, and putting notes in and taking them out."""

    async def test_home_and_end_work_but_stay_off_the_legend(self):
        shown = [name for item in self.editor.shown_keys() for name in item.keys]
        every = [name for item in self.editor.keys() for name in item.keys]
        for name in HOME_END:
            self.assertIn(name, every)
            self.assertNotIn(name, shown)
        await self.press(Key.END)
        self.assertEqual(self.editor.step, self.document.song().get_pattern(TUNE).get_steps() - 1)
        await self.press(Key.HOME)
        self.assertEqual(self.editor.step, 0)

    async def test_r_offers_the_whole_pattern_actions_in_order_and_esc_leaves_the_pattern_alone(self):
        before = self.document.song().get_pattern(TUNE).to_data()
        await self.press(keybindings.PatternEditor.RECONFIGURE)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, reconfigure_choices(drum=False))
        self.assertEqual(self.app.screen.options[Reconfigure.MUNGE], What.MUNGE)
        self.assertEqual(self.app.screen.options[Reconfigure.RENAME], What.RENAME)
        self.assertEqual(self.app.screen.options[Reconfigure.DRUM], MSG_DRUM_ON_WHAT)
        await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, self.editor)
        self.assertEqual(self.document.song().get_pattern(TUNE).to_data(), before)

    async def test_the_brackets_are_two_legend_entries_on_the_number_rows_less_and_more(self):
        # The user asked on 2026-11-09 for [ and ] each named with what it does, where the legend read [/] adjust.
        while self.editor.row_name() != Row.VELOCITY:
            await self.press(Key.DOWN)
        less = KEY_SHOWN.format(label=KeyName.LEFT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.LESS)
        more = KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.MORE)
        self.assertIn(less, self.text())
        self.assertIn(more, self.text())
        self.assertLess(self.text().index(less), self.text().index(more))
        self.assertNotIn(KEY_SHOWN.format(label=KeyName.BRACKETS), self.text())

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
        self.assertEqual([row.name for row in self.editor.rows_view.pinned_rows()], PINNED_ROWS)
        self.assertEqual([row.name for row in self.editor.rows_view.scrolled_rows()], ROWS_AT_START[len(PINNED_ROWS):])

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
        # In a five-note scale, 6 can't be typed, and + from the top stays on 5 and says so, as the user chose over carrying into the next octave.
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
        self.assertIn(ERR_TOP_OF_SCALE.format(scale=SMALL_SCALE), self.text())
        await self.press('1', keybindings.DegreeRow.LESS)
        self.assertEqual((self.value(row=Row.DEGREE), self.value(row=Row.OCTAVE)), (1, octave))
        self.assertIn(ERR_BOTTOM_OF_SCALE.format(scale=SMALL_SCALE), self.text())
        # The next key clears the message, and - in the middle of the scale says nothing.
        await self.press('3', keybindings.DegreeRow.LESS)
        self.assertEqual(self.value(row=Row.DEGREE), 2)
        self.assertNotIn(ERR_BOTTOM_OF_SCALE.format(scale=SMALL_SCALE), self.text())

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
        self.assertEqual(degree.labels(), [*reversed(C_MAJOR_NOTES), MSG_ROW_LABELS[Row.DEGREE]])
        # Step 2 is degree 3: the three lowest rows are bars, and the rest blank.
        lines = degree.cell_lines(step=1)
        self.assertEqual(lines, [*[NOTHING] * 4, *[MSG_GAUGE_BAR] * 3, '3'])
        self.assertEqual(degree.cell_lines(step=2), [NOTHING] * 8)
        self.assertTrue(degree.rule_after())
        self.assertIn(MSG_SCALE_HEADER.format(scale=DEFAULT_SCALE), self.text())

    async def test_a_pattern_under_two_scales_has_a_numbered_gauge_and_the_header_says_so(self):
        self.document.add_scale(name=SMALL_SCALE, root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR_PENTATONIC))
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.document.set_scene_scale(index=1, name=SMALL_SCALE)
        self.document.changed()
        await self.press(Key.LEFT, Key.RIGHT)
        degree = self.editor.row_for(Row.DEGREE)
        self.assertIsNone(degree.scale_name())
        self.assertEqual(degree.labels(), [str(number) for number in range(GAUGE_ROWS_WITHOUT_SCALE, 0, -1)] + [MSG_ROW_LABELS[Row.DEGREE]])
        self.assertIn(MSG_SEVERAL_SCALES, self.text())

    async def test_the_description_says_when_ties_override_the_gate(self):
        await self.go_to_row(Row.GATE)
        await self.press(keybindings.GateRow.MORE)
        self.assertNotIn(MSG_DESCRIBE_GATE_OVERRIDDEN, self.text())
        self.document.set_step_value(name=TUNE, row=Row.TIE, step=1, value=True)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertIn(MSG_DESCRIBE_GATE_OVERRIDDEN, self.text())
        # A blank gate is one step, which ties only lengthen, so there's nothing to warn about.
        await self.press(Key.BACKSPACE)
        self.assertNotIn(MSG_DESCRIBE_GATE_OVERRIDDEN, self.text())

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
        self.assertIn(MSG_SEARCH_SHOWN.format(text=SEARCH_TEXT), self.text())
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
        """A gate is stepped with the brackets or typed with Enter, the user's choice of 2026-11-09, which keeps the legend and the help short."""
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
        self.assertIn(MSG_STEP_SIZE_SHOWN.format(size=EIGHTH, whose=NOTHING), self.text())
        await self.reconfigure(Reconfigure.STEP_SIZE)
        self.app.screen.value = ''
        await self.press(Key.ENTER)
        self.assertIsNone(self.document.song().get_pattern(TUNE).get_step_size())
        self.assertIn(MSG_STEP_SIZE_SHOWN.format(size=SIXTEENTH, whose=MSG_FROM_SONG_SHOWN), self.text())

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
        # The one adjust system, the user's words of 2026-11-09: [ dec and ] inc on every row, with Space or Enter going to the next choice.
        await self.go_to_row(Row.ACCIDENTAL)
        await self.press(keybindings.AccidentalRow.MORE)
        self.assertEqual(self.value(row=Row.ACCIDENTAL), Accidental.SHARP)
        await self.press(keybindings.AccidentalRow.MORE, keybindings.AccidentalRow.LESS, keybindings.AccidentalRow.LESS)
        self.assertIsNone(self.value(row=Row.ACCIDENTAL))
        await self.press(key_of(binding=keybindings.AccidentalRow.NEXT, key=Key.ENTER))
        self.assertEqual(self.value(row=Row.ACCIDENTAL), Accidental.SHARP)
        text = self.text()
        self.assertIn(KEY_SHOWN.format(label=KeyName.SPACE_ENTER) + MSG_LEGEND_WHAT.format(what=What.NEXT), text)
        self.assertIn(KEY_SHOWN.format(label=KeyName.LEFT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.LESS), text)
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.MORE), text)
        # The Chord row keeps Enter for its picker, so Space alone goes to the next chord there.
        await self.go_to_row(Row.CHORD)
        self.assertIn(KEY_SHOWN.format(label=KeyName.SPACE) + MSG_LEGEND_WHAT.format(what=What.NEXT), self.text())
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.MORE), self.text())

    async def test_octave_uses_whatever_is_typed_in_lives_labels_and_stores_the_files_numbering(self):
        song = self.document.song()
        await self.go_to_row(Row.OCTAVE)
        await self.press('7')
        self.assertEqual(self.value(row=Row.OCTAVE), song.stored_octave(7))
        await self.press(keybindings.OctaveRow.MORE, keybindings.OctaveRow.MORE, keybindings.OctaveRow.MORE)
        self.assertEqual(self.value(row=Row.OCTAVE), MAX_OCTAVE)
        for _ in range(12):
            await self.press(keybindings.OctaveRow.LESS)
        self.assertEqual(self.value(row=Row.OCTAVE), MIN_OCTAVE)
        self.assertEqual(song.shown_octave(MIN_OCTAVE), -2)

    async def test_octave_is_typed_and_shown_from_0_with_llamatrons_labels(self):
        self.document.set_octave_labels(OctaveLabels.LLAMATRON)
        await self.go_to_row(Row.OCTAVE)
        await self.press('1', '0')
        self.assertEqual(self.value(row=Row.OCTAVE), MAX_OCTAVE)
        await self.press(keybindings.OctaveRow.MORE)
        self.assertEqual(self.value(row=Row.OCTAVE), MAX_OCTAVE)
        self.assertIn(str(MAX_OCTAVE), self.app.screen.cell_text(name=Row.OCTAVE, step=self.editor.step))

    async def test_chord_cycles_through_the_symbols(self):
        await self.go_to_row(Row.CHORD)
        seen = []
        for _ in range(4):
            await self.press(keybindings.ChordRow.MORE)
            seen.append(self.value(row=Row.CHORD))
        self.assertEqual(seen, ['M', 'm', ChordSymbol.DIMINISHED, ChordSymbol.AUGMENTED])
        await self.press(keybindings.ChordRow.LESS, keybindings.ChordRow.LESS, keybindings.ChordRow.LESS, keybindings.ChordRow.LESS, keybindings.ChordRow.LESS)
        self.assertEqual(self.value(row=Row.CHORD), 13)
        # The brackets step the same way: ] on from 13 comes round to none and then the first symbol, and [ goes back.
        await self.press(keybindings.ChordRow.MORE, keybindings.ChordRow.MORE)
        self.assertEqual(self.value(row=Row.CHORD), 'M')
        await self.press(keybindings.ChordRow.LESS, keybindings.ChordRow.LESS)
        self.assertEqual(self.value(row=Row.CHORD), 13)
        await self.press(keybindings.ChordRow.LESS)
        self.assertEqual(self.value(row=Row.CHORD), 11)


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
        self.assertIn(KEY_SHOWN.format(label=KeyName.LEFT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.LESS), self.text())
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.MORE), self.text())
        self.assertEqual(KeyName.LEFT_BRACKET, Key.LEFT_BRACKET)
        self.assertEqual(KeyName.RIGHT_BRACKET, Key.RIGHT_BRACKET)
        self.assertNotIn(KEY_SHOWN.format(label=Key.PLUS), self.text())

    async def test_nothing_on_the_rows_takes_shift_with_an_arrow(self):
        """The rows' keys are plain ones, the user's choice of 2026-11-09: the bar jump and the Shift+Up and Shift+Down nudge went."""
        every = [name for item in self.editor.key_table() for name in item.keys]
        for name in (*SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT):
            self.assertNotIn(name, every)
        before = self.document.setlist().to_data()
        await self.press(Key.RIGHT, *SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT)
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
            self.assertEqual(self.editor.row_for(row).cell_lines(step=EMPTY_STEP), [MSG_BLOCKED_CELL], row)
        self.assertEqual(self.editor.row_for(Row.TIE).cell_lines(step=EMPTY_STEP), [MSG_TOGGLE_OFF])
        self.assertEqual(self.editor.row_for(Row.CC1).cell_lines(step=EMPTY_STEP), [QUIET_VALUE])
        # Two empty steps, where every row open but Degree, Tie and the headings is blocked, and two notes, where only Tie is; the Chord section is opened, where Inversion and Tension are blocked on every step, since neither note has a chord.
        await open_section(test=self, section=RowSection.CHORD)
        await self.press(*[Key.UP] * len(self.editor.rows_view.reachable()))
        blocked_rows = [Row.OCTAVE, *[row for section in (*OPEN_AT_START, RowSection.CHORD) for row in SECTIONS[section] if row != Row.TIE]]
        rows = [*self.editor.rows_view.pinned_rows(), *self.editor.rows_view.scrolled_rows()]
        blocked_cells = [(row.name, step) for row in rows for step in range(self.editor.steps()) if row.cell_lines(step=step) == [MSG_BLOCKED_CELL]]
        self.assertEqual(len(blocked_cells), 2 * len(blocked_rows) + 2 + 2 + 2)
        self.assertEqual([step for name, step in blocked_cells if name == Row.TENSION], list(range(self.editor.steps())))
        self.assertEqual([step for name, step in blocked_cells if name == Row.INVERSION], list(range(self.editor.steps())))
        self.assertEqual([step for name, step in blocked_cells if name == Row.TIE], [0, 1])
        # The cursor can sit on a blocked cell, where the row's keys leave the legend.
        await self.press(Key.RIGHT, Key.RIGHT)
        while self.editor.row_name() != Row.VELOCITY:
            await self.press(Key.DOWN)
        self.assertFalse(self.editor.row_for(Row.VELOCITY).editable())
        self.assertNotIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET), self.text())
        self.assertIn(REVERSED.format(text=fit(text=MSG_BLOCKED_CELL, width=CELL_WIDTH, align=Align.CENTER)), self.text())
        # Marking the step to grab opens Octave, Velocity and Chord, since the step's chord is built on the grabbed note.
        self.document.set_step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP, value=True)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=EMPTY_STEP, value=MIN_DEGREE)
        self.document.changed()
        await self.press(Key.LEFT, Key.RIGHT)
        self.assertTrue(self.editor.row_for(Row.VELOCITY).editable())
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET), self.text())
        self.assertEqual(self.editor.row_for(Row.OCTAVE).cell_lines(step=EMPTY_STEP), [str(self.document.song().shown_octave(self.document.song().get_default_octave()))])
        self.assertNotEqual(self.editor.row_for(Row.CHORD).cell_lines(step=EMPTY_STEP), [MSG_BLOCKED_CELL])
        self.assertFalse(self.editor.row_for(Row.CHORD).blocked(step=EMPTY_STEP))

    async def test_s_sets_the_pattern_time_signature_and_blank_uses_the_song(self):
        self.assertIn(MSG_TIME_SIGNATURE_SHOWN.format(signature=DEFAULT_TIME_SIGNATURE, whose=MSG_FROM_SONG_SHOWN), self.text())
        await self.reconfigure(Reconfigure.TIME_SIGNATURE)
        self.app.screen.value = WALTZ
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_written_time_signature(), WALTZ)
        self.assertIn(MSG_TIME_SIGNATURE_SHOWN.format(signature=WALTZ, whose=NOTHING), self.text())
        await self.reconfigure(Reconfigure.TIME_SIGNATURE)
        self.app.screen.value = NOTHING
        await self.press(Key.ENTER)
        self.assertIsNone(self.document.song().get_pattern(TUNE).get_written_time_signature())
        self.assertIn(MSG_TIME_SIGNATURE_SHOWN.format(signature=DEFAULT_TIME_SIGNATURE, whose=MSG_FROM_SONG_SHOWN), self.text())

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
        # The user chose the dot over a bar into the next step on 2026-11-09.
        await self.go_to_row(Row.GLIDE)
        glide = self.editor.row_for(Row.GLIDE)
        self.assertEqual(glide.cell_text(step=0), MSG_TOGGLE_OFF)
        await self.press(Key.SPACE)
        self.assertIs(self.value(row=Row.GLIDE), True)
        self.assertEqual(glide.cell_text(step=0), MSG_TOGGLE_ON)
        self.assertIsNone(glide.edge_text(step=1))
        await self.press(Key.SPACE)
        self.assertIs(self.value(row=Row.GLIDE), False)
        self.assertEqual(glide.cell_text(step=0), MSG_TOGGLE_OFF)
        self.assertIsNone(glide.edge_text(step=1))
        # Enter toggles like Space, and the legend shows the two as one key.
        self.assertIn(KEY_SHOWN.format(label=KeyName.SPACE_ENTER), self.text())
        await self.press(Key.ENTER)
        self.assertIs(self.value(row=Row.GLIDE), True)
        await self.press(Key.ENTER)
        self.assertIs(self.value(row=Row.GLIDE), False)

    async def test_the_accidental_shows_only_a_sharp_or_a_flat(self):
        await self.go_to_row(Row.ACCIDENTAL)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=0), NOTHING)
        await self.press(Key.SPACE)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=0), Accidental.SHARP)
        await self.press(Key.SPACE)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=0), Accidental.FLAT)
        self.assertEqual(self.editor.cell_text(name=Row.ACCIDENTAL, step=2), NOTHING)

    async def test_an_empty_step_has_nothing_to_change_but_cc_values(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await self.go_to_row(Row.VELOCITY)
        labels = [item.shown_label() for item in self.editor.keys()]
        self.assertNotIn(KeyName.ENTER, labels)
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
        self.assertIn(MSG_STEPS_SHOWN.format(before=NOTHING, first=1, last=shown, after=MSG_MORE_AFTER), self.text())
        await self.press(*[Key.RIGHT] * HALFWAY)
        self.assertEqual(self.editor.step, HALFWAY)
        self.assertEqual(self.editor.first_step, HALFWAY - shown + 1)
        self.assertIn(MSG_STEPS_SHOWN.format(before=MSG_MORE_BEFORE, first=HALFWAY - shown + 2, last=HALFWAY + 1, after=MSG_MORE_AFTER), self.text())
        self.assertIn(str(HALFWAY + 1), self.text())
        self.assertNotIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.DEGREE]) + '  1  ', self.text())
        # Moving left past the window's first step scrolls it back one step.
        await self.press(*[Key.LEFT] * shown)
        self.assertEqual(self.editor.first_step, HALFWAY - shown)
        # Left on the first step stays there, since no cursor goes round, and End shows the end of the pattern.
        await self.press(Key.HOME, Key.LEFT)
        self.assertEqual(self.editor.step, 0)
        self.assertEqual(self.editor.first_step, 0)
        await self.press(Key.END)
        self.assertEqual(self.editor.step, LONG - 1)
        self.assertIn(MSG_STEPS_SHOWN.format(before=MSG_MORE_BEFORE, first=LONG - shown + 1, last=LONG, after=NOTHING), self.text())

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


class TestDrumPatterns(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.DOWN, Key.ENTER)
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


class TestPatternEditorRefusals(UITest):

    async def open(self, name):
        """Open a pattern on its rows, which a drum pattern opens on and a note pattern reaches past its piano roll."""
        await self.press(keybindings.MainPage.PATTERNS, *[Key.DOWN] * self.document.song().get_pattern_names().index(name), Key.ENTER)
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


class TestDirectionsAndGrab(UITest):

    async def test_a_pattern_chooses_a_direction(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        await self.reconfigure(Reconfigure.DIRECTION)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[0], 'forward    first step to last')
        self.assertEqual(self.app.screen.options[1], 'reverse a  step 1, then backward from the last')
        self.app.screen.place = 4
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_pattern(TUNE).get_direction(), Direction.PENDULUM)
        self.assertIn(DIRECTION_PENDULUM, self.text())
        render_song(self.document.song())

    async def clip_page(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        return self.app.screen

    async def go_to(self, page, label):
        page.place = [field.label for field in page.fields()].index(label)
        page.draw()
        await self.pilot.pause()

    async def test_a_clip_shows_the_patterns_direction_until_it_overrides_it(self):
        self.document.set_direction(name=TUNE, direction=Direction.ALTERNATE)
        page = await self.clip_page()
        self.assertIn(MSG_PATTERN_DIRECTION_SHOWN.format(direction=words(Direction.ALTERNATE)), self.text())
        await self.go_to(page, DIRECTION)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_direction(), Direction.FORWARD)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_direction(), Direction.REVERSE_A)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD).get_direction())

    async def test_a_clip_direction_can_be_chosen_from_a_list(self):
        page = await self.clip_page()
        await self.go_to(page, DIRECTION)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.options[0], "(pattern)  use each pattern's direction")
        self.assertEqual(self.app.screen.options[1], 'forward    first step to last')
        self.app.screen.place = self.app.screen.options.index('brownian   on 50%, back 25%, stay 25%')
        await self.press(Key.ENTER)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_direction(), Direction.BROWNIAN)

    async def test_the_grid_marks_a_clip_with_its_own_direction(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.RANDOM)
        await self.press(keybindings.MainPage.ARRANGE)
        self.assertIn(TUNE_D, self.text())

    async def test_the_grab_row_is_in_the_advanced_section_whose_hint_the_header_shows(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.assertNotIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.GRAB]), self.text())
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.app.screen.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        self.assertIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.GRAB]), self.text())
        self.assertIn(MSG_SECTION_HINTS[RowSection.ADVANCED], self.text())

    async def test_marking_an_empty_step_gives_it_the_root_as_its_own_note_and_opens_the_note_rows_chord_among_them(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await open_section(test=self, section=RowSection.ADVANCED)
        await self.press(Key.RIGHT, Key.RIGHT)
        editor = self.app.screen
        self.assertFalse(editor.is_note())
        while editor.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        await self.press(Key.SPACE)
        self.assertTrue(self.document.step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=EMPTY_STEP), MIN_DEGREE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.OCTAVE, step=EMPTY_STEP), self.document.song().get_default_octave())
        self.assertTrue(editor.is_note())
        # The description names no note, since what a grab step plays is whatever the other track played.
        self.assertIn(MSG_GRABBED_SOUND, self.text())
        # Velocity takes a value on the step now, and so does Chord, which is built on the grabbed note.
        self.assertTrue(editor.row_for(Row.VELOCITY).editable())
        self.assertTrue(editor.row_for(Row.CHORD).editable())
        await self.press(Key.SPACE)
        self.assertFalse(self.document.step_value(name=TUNE, row=Row.GRAB, step=EMPTY_STEP))
        self.assertNotIn(MSG_GRABBED_SOUND, self.text())
        self.assertTrue(editor.row_for(Row.CHORD).editable())
        render_song(self.document.song())

    async def test_a_grab_step_takes_a_chord_and_the_description_names_the_chord_and_no_note(self):
        # The user asked on 2026-11-09 for a grab step to hold a chord, built on the grabbed note.
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.document.set_step_value(name=TUNE, row=Row.GRAB, step=0, value=True)
        self.document.changed()
        editor = self.app.screen
        await open_section(test=self, section=RowSection.CHORD)
        await self.press(Key.DOWN)
        self.assertEqual(editor.row_name(), Row.CHORD)
        self.assertTrue(editor.row_for(Row.CHORD).editable())
        await self.press(keybindings.ChordRow.NEXT)
        chord = self.document.step_value(name=TUNE, row=Row.CHORD, step=0)
        self.assertIsNotNone(chord)
        self.assertEqual(editor.row_for(Row.CHORD).cell_lines(step=0), [str(chord)])
        self.assertIn(MSG_GRABBED_SOUND, self.text())
        self.assertIn(MSG_DESCRIBE_CHORD.format(chord=chord), self.text())
        render_song(self.document.song())

    async def test_marking_a_step_with_space(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.app.screen.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        await self.press(Key.SPACE)
        self.assertTrue(self.document.step_value(name=TUNE, row=Row.GRAB, step=0))
        self.assertEqual(self.app.screen.cell_text(name=Row.GRAB, step=0), MSG_TOGGLE_ON)
        render_song(self.document.song())


class TestDirectionsAndGrabOnAUsualConsole(UITest):
    SIZE = (80, 24)

    async def test_everything_still_fits_with_the_grab_row(self):
        # Grab is the last advanced row, so on a short console the rows scroll down to it as the cursor arrives.
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.app.screen.row_name() != Row.GRAB:
            await self.press(Key.DOWN)
        text = self.text()
        self.assertIn(ROW_SHOWN.format(label=MSG_ROW_LABELS[Row.GRAB]), text)
        self.assertIn('Step 1:', text)
        for item in self.app.screen.shown_keys():
            self.assertIn(f'« {item.shown_label()} »', text)


class TestSections(UITest):
    """The rows under Octave come in sections headed by rows of the grid: Space or Enter opens and closes one, PgUp and PgDn jump between them, and Tab opens the roll over them."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def shown(self, row):
        return ROW_SHOWN.format(label=MSG_ROW_LABELS[row])

    def heading_shown(self, section):
        """Return a section's heading as the screen shows it, after the bar, or after the reversed mark when the cursor is on it."""
        label = SPACE + section_label(section, open_=self.editor.rows_view.section_is_open(section))
        return REVERSED.format(text=fit(text=label, width=self.editor.drawing.label_width())) if self.editor.row_name() == section else Box.BAR + label

    def grid_lines_shown(self):
        """Return the screen's lines from the grid's top rule to its bottom rule."""
        lines = self.text().splitlines()
        top = next(number for number, line in enumerate(lines) if line.startswith(Box.TOP_LEFT))
        bottom = next(number for number, line in enumerate(lines) if line.startswith(Box.BOTTOM_LEFT))
        return lines[top:bottom + 1]

    def line_of_heading(self, section):
        lines = self.grid_lines_shown()
        return next(number for number, line in enumerate(lines) if self.heading_shown(section) in line), lines

    async def test_no_divider_crosses_a_heading_and_the_rules_around_it_close_and_reopen_the_dividers(self):
        """The dividers above a heading end in bottom tees, the ones below an open heading start in top tees, two closed headings share an unbroken rule, and a closed last heading sits on a plain bottom rule (the user's ask of 2026-11-09)."""
        # Basics is open and under a row, Octave; Timing, open too, is under the closed Chord heading, whose rule it shares.
        self.assertIn(RowSection.BASICS, self.app.open_sections)
        at, lines = self.line_of_heading(RowSection.BASICS)
        heading = lines[at]
        self.assertEqual(heading.rstrip().count(Box.BAR), 2, heading)
        self.assertNotIn(Box.DOUBLE_BAR, heading)
        above = lines[at - 1]
        self.assertIn(Box.BOTTOM_TEE, above)
        self.assertIn(Box.DOUBLE_BOTTOM_TEE, above)
        for joint in (Box.CROSS, Box.DOUBLE_CROSS, Box.TOP_TEE):
            self.assertNotIn(joint, above)
        below = lines[at + 1]
        self.assertIn(Box.TOP_TEE, below)
        self.assertIn(Box.DOUBLE_TOP_TEE, below)
        self.assertNotIn(Box.CROSS, below)
        # Advanced and CCs are closed: their headings share a rule with no joints at all. Timing is closed first so that both headings fit on this screen.
        await self.press(*[forward_key(keybindings.PatternRows.SECTION)] * 3, keybindings.SectionRow.CLOSE)
        self.assertEqual(self.editor.row_name(), RowSection.TIMING)
        at, lines = self.line_of_heading(RowSection.ADVANCED)
        between = lines[at + 1]
        self.assertEqual(between.rstrip(), Box.LEFT_TEE + Box.RULE * (len(between.rstrip()) - 2) + Box.RIGHT_TEE)
        self.assertIn(self.heading_shown(RowSection.CC), lines[at + 2])
        # With Basics and Timing closed every heading fits, and the last row is the closed Reg. Cond heading, so the bottom rule under it has no tees.
        await self.press(back_key(keybindings.PatternRows.SECTION), back_key(keybindings.PatternRows.SECTION), keybindings.SectionRow.CLOSE)
        self.assertEqual(self.editor.row_name(), RowSection.BASICS)
        _, lines = self.line_of_heading(RowSection.REGISTER_COND)
        bottom = lines[-1].rstrip()
        self.assertIn(self.heading_shown(RowSection.REGISTER_COND), lines[-2])
        self.assertEqual(bottom, Box.BOTTOM_LEFT + Box.RULE * (len(bottom) - 2) + Box.BOTTOM_RIGHT)

    async def test_the_sections_open_at_the_start_show_their_rows_and_the_rest_show_only_their_headings(self):
        self.assertEqual(self.app.open_sections, set(OPEN_AT_START))
        text = self.text()
        names = [row.name for row in self.editor.rows_view.reachable()]
        for section, rows in SECTIONS.items():
            self.assertIn(section, names)
            for row in rows:
                if section in OPEN_AT_START:
                    self.assertIn(row, names, row)
                else:
                    self.assertNotIn(row, names, row)
                    self.assertNotIn(self.shown(row), text, row)
        self.assertIn(self.heading_shown(RowSection.BASICS), text)

    async def test_page_down_goes_from_heading_to_heading_and_stops_at_the_last_and_page_up_goes_back_and_stops_at_the_first(self):
        for section in SECTIONS:
            await self.press(Key.PAGE_DOWN)
            self.assertEqual(self.editor.row_name(), section)
        await self.press(Key.PAGE_DOWN)
        self.assertEqual(self.editor.row_name(), list(SECTIONS)[-1])
        for section in reversed(list(SECTIONS)[:-1]):
            await self.press(Key.PAGE_UP)
            self.assertEqual(self.editor.row_name(), section)
        await self.press(Key.PAGE_UP)
        self.assertEqual(self.editor.row_name(), list(SECTIONS)[0])
        # From the Degree row, above every heading, PgUp stays put and PgDn reaches the first heading.
        await self.press(Key.UP, Key.UP, Key.PAGE_UP)
        self.assertEqual(self.editor.row_name(), Row.DEGREE)
        await self.press(Key.PAGE_DOWN)
        self.assertEqual(self.editor.row_name(), list(SECTIONS)[0])
        self.assertFalse(self.editor.on_roll())

    async def test_space_and_enter_open_and_close_a_section_and_the_cursor_stays_on_its_heading(self):
        await open_section(test=self, section=RowSection.ADVANCED)
        self.assertEqual(self.editor.row_name(), RowSection.ADVANCED)
        self.assertIn(RowSection.ADVANCED, self.app.open_sections)
        self.assertIn(self.heading_shown(RowSection.ADVANCED), self.text())
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), Row.PROBABILITY)
        await self.press(Key.UP, Key.ENTER)
        self.assertNotIn(RowSection.ADVANCED, self.app.open_sections)
        self.assertEqual(self.editor.row_name(), RowSection.ADVANCED)
        self.assertNotIn(self.shown(Row.PROBABILITY), self.text())
        await self.press(Key.DOWN)
        self.assertEqual(self.editor.row_name(), RowSection.CC)

    async def test_the_heading_shows_its_mark_and_the_cursor_on_it_reverses_the_label_and_keeps_the_step(self):
        await self.press(Key.RIGHT, Key.PAGE_DOWN)
        self.assertEqual((self.editor.row_name(), self.editor.step), (RowSection.BASICS, 1))
        self.assertIn(self.heading_shown(RowSection.BASICS), self.text())
        await self.press(Key.DOWN)
        self.assertEqual((self.editor.row_name(), self.editor.step), (Row.ACCIDENTAL, 1))
        self.assertIn(Box.BAR + SPACE + section_label(RowSection.BASICS, open_=True), self.text())
        await self.press(Key.PAGE_DOWN, Key.PAGE_DOWN, Key.PAGE_DOWN, Key.PAGE_DOWN)
        self.assertIn(self.heading_shown(RowSection.CC), self.text())

    async def test_the_label_column_is_as_wide_as_the_widest_row_whether_its_section_is_open_or_not(self):
        width = self.editor.drawing.label_width()
        await open_section(test=self, section=RowSection.ADVANCED)
        self.assertEqual(self.editor.drawing.label_width(), width)
        self.assertEqual(width, len(MSG_ROW_LABELS[Row.RATCHET_OFFSET]) + 2)

    async def test_the_open_sections_stay_for_other_patterns_and_under_the_roll(self):
        await open_section(test=self, section=RowSection.ADVANCED)
        await self.press(keybindings.PatternEditor.TO_ROLL)
        self.assertTrue(self.editor.on_roll())
        self.assertNotIn(Key.PAGE_DOWN, [name for item in self.editor.keys() for name in item.keys])
        await self.press(keybindings.PatternEditor.TO_EDITOR, Key.ESCAPE, Key.ENTER)
        self.assertIn(RowSection.ADVANCED, self.app.open_sections)
        self.assertIn(Row.RATCHET_OFFSET, [row.name for row in self.app.screen.rows_view.reachable()])

    async def test_cc_rows_take_values_even_on_a_rest(self):
        await open_section(test=self, section=RowSection.CC)
        rest = 2
        value = 100
        await self.press(Key.RIGHT, Key.RIGHT)
        while self.editor.row_name() != Row.CC1:
            await self.press(Key.DOWN)
        self.assertEqual(self.editor.cell_text(name=Row.CC1, step=rest), QUIET_VALUE)
        await self.press(*str(value))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.CC1, step=rest), value)
        await self.press(keybindings.CcRow.MORE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.CC1, step=rest), value + 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.step_value(name=TUNE, row=Row.CC1, step=rest))
        while self.editor.row_name() != Row.SLIDE:
            await self.press(Key.DOWN)
        await self.press(Key.SPACE)
        self.assertIs(self.document.step_value(name=TUNE, row=Row.SLIDE, step=rest), True)
        self.assertEqual(self.editor.cell_text(name=Row.SLIDE, step=rest), MSG_TOGGLE_ON)
        render_song(self.document.song())

    async def test_a_cc_row_is_one_line_and_its_label_says_the_cc_number_the_tracks_playing_the_pattern_send(self):
        await open_section(test=self, section=RowSection.CC)
        row = self.editor.row_for(Row.CC1)
        cc_1 = MSG_ROW_LABELS[Row.CC1]
        # tune is played by lead alone, whose lanes send nothing yet, so the lane is off; the value stays a one-line number.
        self.assertEqual(row.labels(), [MSG_CC_ROW_LABEL.format(label=cc_1, number=MSG_CC_LANE_OFF)])
        self.assertEqual(row.cell_lines(step=0), [QUIET_VALUE])
        self.document.set_step_value(name=TUNE, row=Row.CC1, step=0, value=MAX_CC_VALUE)
        self.assertEqual(row.cell_lines(step=0), [str(MAX_CC_VALUE)])
        # Giving lead a number puts it in the label, and a second track playing tune with another number makes the label say they differ.
        self.document.set_track_cc_number(name=LEAD, lane=0, number=BRIGHTNESS)
        self.assertEqual(row.label(), MSG_CC_ROW_LABEL.format(label=cc_1, number=str(BRIGHTNESS)))
        while self.editor.row_name() != Row.CC1:
            await self.press(Key.DOWN)
        self.assertIn(ROW_SHOWN.format(label=row.label()), self.text())
        self.document.add_track(SECOND_TRACK)
        self.document.add_clip_slot(index=0, track=SECOND_TRACK, pattern=TUNE)
        self.document.set_track_cc_number(name=SECOND_TRACK, lane=0, number=MOD_WHEEL)
        self.assertEqual(row.label(), MSG_CC_ROW_LABEL.format(label=cc_1, number=MSG_CC_LANE_VARIES))
        self.document.set_track_cc_number(name=SECOND_TRACK, lane=0, number=BRIGHTNESS)
        self.assertEqual(row.label(), MSG_CC_ROW_LABEL.format(label=cc_1, number=str(BRIGHTNESS)))
        # A pattern no track plays keeps the plain label.
        await self.press(Key.ESCAPE, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_ROLL)
        self.assertEqual(self.app.screen.item, OTHER)
        self.assertEqual(self.app.screen.row_for(Row.CC1).label(), cc_1)

    async def test_typing_a_ratchet_offset_and_going_negative(self):
        await open_section(test=self, section=RowSection.ADVANCED)
        while self.editor.row_name() != Row.RATCHET_OFFSET:
            await self.press(Key.DOWN)
        typed = 2
        await self.press(str(typed))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.RATCHET_OFFSET, step=0), typed)
        presses = typed + 1
        await self.press(*[keybindings.NumberRow.LESS] * presses)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.RATCHET_OFFSET, step=0), typed - presses)
        self.assertEqual(self.editor.cell_text(name=Row.RATCHET_OFFSET, step=0), str(typed - presses))

    async def test_unset_register_changes_show_a_dot(self):
        await open_section(test=self, section=RowSection.REGISTER_MOD)
        for row in REGISTER_ADD_ROWS.values():
            self.assertEqual(self.editor.cell_text(name=row, step=0), QUIET_VALUE)

    async def test_register_changes_take_typed_values_including_negative_ones_even_on_a_rest(self):
        await open_section(test=self, section=RowSection.REGISTER_MOD)
        rest = 2
        typed = -3
        row = REGISTER_ADD_ROWS[RegisterName.BX]
        await self.press(Key.RIGHT, Key.RIGHT)
        while self.editor.row_name() != row:
            await self.press(Key.DOWN)
        await self.press(Key.ENTER)
        self.app.screen.value = str(typed)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=rest), typed)
        await self.press(Key.ENTER)
        self.app.screen.value = str(MAX_REGISTER_VALUE + 1)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=rest), typed)
        render_song(self.document.song())

    async def test_register_uses_cycle_add_subtract_and_off_on_notes_and_on_empty_steps_alike(self):
        # The user's design of 2026-11-09: Space or Enter cycles +, - and blank, where the rows were toggles.
        await open_section(test=self, section=RowSection.REGISTER_APPLY)
        row = REGISTER_VELOCITY_ROWS[RegisterName.CX]
        while self.editor.row_name() != row:
            await self.press(Key.DOWN)
        self.assertEqual(self.editor.cell_text(name=row, step=0), MSG_TOGGLE_OFF)
        await self.press(keybindings.RegisterRow.NEXT)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.ADD)
        self.assertEqual(self.editor.cell_text(name=row, step=0), MSG_REGISTER_ADDS)
        await self.press(key_of(binding=keybindings.RegisterRow.NEXT, key=Key.ENTER))
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.SUBTRACT)
        self.assertEqual(self.editor.cell_text(name=row, step=0), MSG_REGISTER_SUBTRACTS)
        await self.press(keybindings.RegisterRow.NEXT)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.OFF)
        self.assertEqual(self.editor.cell_text(name=row, step=0), MSG_TOGGLE_OFF)
        await self.press(keybindings.RegisterRow.LESS)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.SUBTRACT)
        await self.press(keybindings.RegisterRow.MORE, keybindings.RegisterRow.MORE)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.ADD)
        self.assertIn(KEY_SHOWN.format(label=KeyName.LEFT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.LESS), self.text())
        self.assertIn(KEY_SHOWN.format(label=KeyName.RIGHT_BRACKET) + MSG_LEGEND_WHAT.format(what=What.MORE), self.text())
        await self.press(keybindings.RegisterRow.CLEAR)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=0), RegisterUse.OFF)
        self.assertIn(f'« {key_name(keybindings.RegisterRow.NEXT)} »', self.text())
        # No register setting is locked out for want of a note: every register row works on an empty step, where the render has nothing to move.
        await self.press(*[Key.RIGHT] * EMPTY_STEP)
        for name in (*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values()):
            self.assertTrue(self.editor.row_for(name).editable(), name)
            self.assertNotEqual(self.editor.row_for(name).cell_lines(step=EMPTY_STEP), [MSG_BLOCKED_CELL], name)
        await self.press(keybindings.RegisterRow.NEXT)
        self.assertEqual(self.document.step_value(name=TUNE, row=row, step=EMPTY_STEP), RegisterUse.ADD)
        self.assertEqual(self.editor.cell_text(name=row, step=EMPTY_STEP), MSG_REGISTER_ADDS)
        render_song(self.document.song())

    async def test_a_drum_pattern_has_no_rows_that_move_notes(self):
        await open_section(test=self, section=RowSection.REGISTER_APPLY)
        await self.press(Key.ESCAPE, Key.DOWN, Key.ENTER)
        rows = [row.name for row in self.app.screen.rows_view.reachable()]
        for name in REGISTER_NOTE_ROWS.values():
            self.assertNotIn(name, rows)
        for name in REGISTER_VELOCITY_ROWS.values():
            self.assertIn(name, rows)

    async def test_on_a_drum_note_row_a_and_f_are_notes(self):
        await self.press(Key.ESCAPE, Key.DOWN, Key.ENTER)
        editor = self.app.screen
        await self.press(Key.RIGHT, NoteName.A.lower())
        self.assertEqual(self.document.step_value(name=BEAT, row=Row.DEGREE, step=1), NoteName.A)
        await self.press(NoteName.F.lower())
        self.assertEqual(self.document.step_value(name=BEAT, row=Row.DEGREE, step=1), NoteName.F)
        labels = [item.shown_label() for item in editor.key_table()]
        self.assertNotIn(NoteName.F, labels)

    async def test_on_other_drum_rows_d_removes_a_step(self):
        await self.press(Key.ESCAPE, Key.DOWN, Key.ENTER)
        labels = [item.shown_label() for item in self.app.screen.key_table()]
        self.assertNotIn(NoteName.D, labels)
        await self.press(Key.DOWN)
        labels = [item.shown_label() for item in self.app.screen.key_table()]
        self.assertIn(NoteName.D, labels)


class TestSectionsOnAUsualConsole(UITest):
    SIZE = (80, 24)

    def assert_fits(self):
        text = self.text()
        self.assertIn('Step 1:', text)
        for item in self.app.screen.shown_keys():
            self.assertIn(KEY_SHOWN.format(label=item.shown_label()), text)

    async def test_every_heading_and_every_row_fits_with_every_section_open(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assert_fits()
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        for section in SECTIONS:
            await open_section(test=self, section=section)
            self.assert_fits()
        # Down through every row: the rows scroll so that the cursor's row, its heading included, is always on screen.
        editor = self.app.screen
        for _ in editor.rows_view.reachable():
            await self.press(Key.DOWN)
            # The label follows the bar, or the reversed mark on a heading under the cursor.
            self.assertIn(SPACE + editor.rows_view.current_row().labels()[-1], self.text(), editor.row_name())
            self.assert_fits()


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
        self.add_pattern_with_rows(name=LONG_PATTERN, steps=LONG_PATTERN_STEPS, rows=LONG_PATTERN_ROWS)
        await self.press(keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def rows(self, *, row=Row.DEGREE):
        return self.document.song().get_pattern(LONG_PATTERN).get_row(row)

    async def test_reverse_after_reverses_everything_after_the_cursor(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 5, 4, 3])

    async def test_every_row_moves_with_its_step(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(row=Row.GATE), [QUARTER, EIGHTH, '1', HALF, SIXTEENTH])
        self.assertEqual(self.rows(row=Row.VELOCITY), [10, 20, 50, 40, 30])

    async def test_reversing_after_twice_puts_it_back_and_the_cursor_stays(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_reverse_after_on_the_last_step_says_why_nothing_happens(self):
        await self.press(Key.END)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertIn(ERR_NOTHING_AFTER, self.text())

    async def test_pivot_exchanges_both_sides_of_the_cursor(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.rows(), [3, 4, 5, 2, 1])
        self.assertEqual(self.rows(row=Row.GATE), [SIXTEENTH, HALF, '1', EIGHTH, QUARTER])

    async def test_the_cursor_stays_on_its_step_so_pivoting_twice_puts_it_back(self):
        await self.press(Key.RIGHT)
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.editor.step, 3)
        self.assertEqual(self.document.step_value(name=LONG_PATTERN, row=Row.DEGREE, step=self.editor.step), 2)
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        self.assertEqual(self.editor.step, 1)

    async def test_pivot_at_either_end(self):
        await munge(test=self, choice=Munge.PIVOT)
        self.assertEqual(self.rows(), [2, 3, 4, 5, 1])
        self.assertEqual(self.editor.step, 4)

    async def test_reverse_before_and_after_and_the_whole_pattern(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        await munge(test=self, choice=Munge.REVERSE_AFTER)
        self.assertEqual(self.rows(), [1, 2, 3, 5, 4])
        await munge(test=self, choice=Munge.REVERSE_BEFORE)
        self.assertEqual(self.rows(), [2, 1, 3, 5, 4])
        await munge(test=self, choice=Munge.REVERSE)
        self.assertEqual(self.rows(), [4, 5, 3, 1, 2])
        self.assertEqual(self.editor.step, 2)

    async def test_randomize_keeps_every_step_and_is_an_edit(self):
        await munge(test=self, choice=Munge.RANDOMIZE)
        self.assertEqual(sorted(self.rows()), [1, 2, 3, 4, 5])
        self.assertTrue(self.document.is_dirty())

    async def test_the_time_stays_the_same(self):
        before = self.document.lengths().pattern_length(LONG_PATTERN)
        await self.press(Key.RIGHT, NoteName.F.lower())
        self.assertEqual(self.document.lengths().pattern_length(LONG_PATTERN), before)

    async def test_load_replaces_everything_after_asking(self):
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertNotIn(LONG_PATTERN, self.app.screen.options)
        self.app.screen.place = self.app.screen.options.index(BEAT)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(self.rows(), [1, 2, 3, 4, 5])
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.place = self.app.screen.options.index(BEAT)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        song = self.document.song()
        self.assertEqual(song.get_pattern(LONG_PATTERN).to_data(), song.get_pattern(BEAT).to_data())
        self.assertEqual(self.editor.steps(), 2)
        self.assertIn('│ Note', self.text())

    async def test_a_loaded_copy_is_separate(self):
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.place = self.app.screen.options.index(BEAT)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES, Key.RIGHT, NoteName.F.lower())
        self.assertEqual(self.document.step_value(name=LONG_PATTERN, row=Row.DEGREE, step=1), NoteName.F)
        self.assertIsNone(self.document.step_value(name=BEAT, row=Row.DEGREE, step=1))

    async def test_load_keeps_the_name_and_what_uses_it(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.PATTERN, value=LONG_PATTERN)
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.app.screen.place = self.app.screen.options.index(OTHER)
        await self.press(Key.ENTER, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song().get_scenes()[0].get_clip_slot(LEAD).get_pattern_name(), LONG_PATTERN)
        render_song(self.document.song())

    async def test_the_old_keys_moved(self):
        await self.press(keybindings.PatternEditor.RESIZE)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertEqual(self.app.screen.value, '5')


class TestTheEditorsTwoViews(UITest):
    """The piano roll and the rows are two views of one shape, each with its cursor, its keys and its drawing, and the editor asks whichever is showing."""

    async def test_the_editor_asks_the_view_that_is_showing_and_tab_changes_which(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        editor = self.app.screen
        self.assertIs(editor.view(), editor.roll)
        self.assertIs(editor.view().drawing, editor.roll_drawing)
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        self.assertIs(editor.view(), editor.rows_view)
        self.assertIs(editor.view().drawing, editor.drawing)
        await self.press(keybindings.PatternEditor.TO_ROLL)
        self.assertIs(editor.view(), editor.roll)

    async def test_each_view_says_what_tab_does_and_whether_its_legend_lists_the_step_keys(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        editor = self.app.screen
        self.assertEqual(editor.roll.other_view_what(), MSG_TO_EDITOR_WHAT)
        self.assertEqual(editor.rows_view.other_view_what(), MSG_TO_ROLL_WHAT)
        self.assertFalse(editor.roll.lists_step_keys())
        self.assertTrue(editor.rows_view.lists_step_keys())
        # The roll neither inserts nor removes a step, the user's rule, as Live's piano roll never did; the rows view does both, in its legend.
        self.assertEqual(editor.roll.step_keys(can_remove=True), [])
        on_roll = {name for item in editor.keys() for name in item.keys}
        self.assertNotIn(first_key(keybindings.PatternRows.INSERT_STEP), on_roll)
        self.assertNotIn(first_key(keybindings.PatternRows.REMOVE_STEP), on_roll)
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        on_rows = {name: item.shown for item in editor.keys() for name in item.keys}
        self.assertEqual((on_rows[first_key(keybindings.PatternRows.INSERT_STEP)], on_rows[first_key(keybindings.PatternRows.REMOVE_STEP)]), (True, True))

    async def test_both_views_list_the_keys_that_move_the_cursor_and_then_their_own(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        editor = self.app.screen
        for view in (editor.roll, editor.rows_view):
            moving = [name for item in view.move_keys() for name in item.keys]
            for name in (Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT, *HOME_END):
                self.assertIn(name, moving)
        # Only the rows have section headings to jump between.
        self.assertNotIn(Key.PAGE_DOWN, [name for item in editor.roll.move_keys() for name in item.keys])
        self.assertIn(Key.PAGE_DOWN, [name for item in editor.rows_view.move_keys() for name in item.keys])
        self.assertTrue(editor.roll.keys())

    async def test_a_drum_pattern_shows_only_the_rows_and_its_note_row_takes_letters(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.DOWN, Key.ENTER)
        editor = self.app.screen
        self.assertTrue(editor.is_drum())
        self.assertIs(editor.view(), editor.rows_view)
        self.assertNotIn(first_key(keybindings.PatternEditor.TO_ROLL), [name for item in editor.keys() for name in item.keys])
        # On the Note row the letter D is a note, so it can't remove a step there, and it can on the row below.
        self.assertTrue(editor.rows_view.takes_note_letters())
        self.assertFalse(any(item.what == What.REMOVE_STEP for item in editor.keys()))
        await self.press(Key.DOWN)
        self.assertFalse(editor.rows_view.takes_note_letters())
        self.assertTrue(any(item.what == What.REMOVE_STEP for item in editor.keys()))
        self.assertFalse(editor.roll.takes_note_letters())

