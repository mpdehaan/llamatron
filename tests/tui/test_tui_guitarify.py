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

"""Tests for the Guitarify editor, its two sections, and the editor of its bar of strokes."""

from tests.support.ui_testing import PICKED, UITest
from llamatron.composition import file_format
from llamatron.composition.file_format import GeneratorKind, GuitarifySetting, ReadyBar, Section, SingleNotes, Stroke, Tuning
from llamatron.composition import generator_settings
from llamatron.composition import guitar_bars
from llamatron.strings import labels, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.guitar_bar_editor import CELL_LENGTHS, GuitarBarEditor
from llamatron.tui.screens.generators.guitarify_editor import GuitarifyEditor

FIRST_CELL = 0
SECOND_CELL = 1


class GuitarifyTest(UITest):
    """A test that opens the Guitarify the shared song holds."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.GUITARIFIES)
        self.assertIsInstance(self.app.screen, GuitarifyEditor)

    def guitar(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.GUITARIFY, name=PICKED)

    def written(self):
        return self.guitar().to_data()


class TestGuitarifyAdded(UITest):

    async def test_a_new_one_shapes_and_plays_the_default_bar_with_nothing_written(self):
        name = await self.add_generator(Section.GUITARIFIES)
        self.assertIsInstance(self.app.screen, GuitarifyEditor)
        guitar = self.document.song().get_generator_settings(kind=GeneratorKind.GUITARIFY, name=name)
        self.assertTrue(guitar.shapes())
        self.assertTrue(guitar.strikes())
        self.assertEqual(guitar.get_bar(), list(guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR].strokes))
        self.assertEqual(guitar.to_data(), {})


class TestGuitarifyEditor(GuitarifyTest):

    async def test_the_two_sections_are_closed_until_opened(self):
        text = self.text()
        self.assertIn(labels.MSG_GUITAR_SHAPE_SECTION, text)
        self.assertIn(labels.MSG_GUITAR_STROKES_SECTION, text)
        self.assertNotIn(labels.MSG_GUITAR_TUNING_LABEL, text)
        await self.select_field(labels.MSG_GUITAR_TUNING_LABEL)
        self.assertIn(labels.MSG_GUITAR_TUNING_LABEL, self.text())

    async def test_a_closed_section_says_when_something_inside_is_set(self):
        self.assertNotIn(marks.MSG_SECTION_SET, self.text())
        self.document.set_generator_setting(section=Section.GUITARIFIES, name=PICKED, setting=GuitarifySetting.CAPO, value=2)
        await self.press(Key.DOWN)
        self.assertIn(marks.MSG_SECTION_SET, self.text())

    async def test_each_half_is_switched_off_and_on(self):
        await self.select_field(labels.MSG_GUITAR_SHAPE_LABEL)
        await self.press(keybindings.GuitarifyEditor.TOGGLE)
        self.assertFalse(self.guitar().shapes())
        await self.press(keybindings.GuitarifyEditor.TOGGLE)
        self.assertTrue(self.guitar().shapes())
        self.assertNotIn(GuitarifySetting.SHAPE, self.written())
        await self.select_field(labels.MSG_GUITAR_STROKES_LABEL)
        await self.press(keybindings.GuitarifyEditor.TOGGLE)
        self.assertFalse(self.guitar().strikes())

    async def test_the_tuning_steps_through_its_choices_and_stops_at_the_ends(self):
        await self.select_field(labels.MSG_GUITAR_TUNING_LABEL)
        self.assertIn(labels.MSG_GUITAR_TUNING_NAMES[Tuning.STANDARD], self.text())
        await self.press(keybindings.GuitarifyEditor.LESS)
        self.assertEqual(self.guitar().get_tuning(), Tuning.STANDARD)
        await self.press(keybindings.GuitarifyEditor.MORE)
        self.assertEqual(self.guitar().get_tuning(), Tuning.DROP_D)
        self.assertIn(labels.MSG_GUITAR_TUNING_NAMES[Tuning.DROP_D], self.text())
        await self.press(keybindings.GuitarifyEditor.LESS)
        self.assertNotIn(GuitarifySetting.TUNING, self.written())

    async def test_the_tuning_is_picked_from_a_list(self):
        await self.select_field(labels.MSG_GUITAR_TUNING_LABEL)
        await self.press(Key.ENTER)
        await self.pick(labels.MSG_GUITAR_TUNING_NAMES[Tuning.DADGAD])
        self.assertEqual(self.guitar().get_tuning(), Tuning.DADGAD)

    async def test_the_position_is_open_or_a_fret_and_stops_at_the_last_fret(self):
        await self.select_field(labels.MSG_GUITAR_POSITION_LABEL)
        self.assertIn(marks.MSG_GUITAR_OPEN_POSITION, self.text())
        await self.press(keybindings.GuitarifyEditor.MORE)
        self.assertEqual(self.guitar().get_position(), 1)
        self.assertIn(marks.MSG_GUITAR_FRET.format(fret=1), self.text())
        await self.press(*[keybindings.GuitarifyEditor.MORE] * (generator_settings.MAX_GUITAR_FRET + 1))
        self.assertEqual(self.guitar().get_position(), generator_settings.MAX_GUITAR_FRET)
        await self.press(Key.BACKSPACE)
        self.assertNotIn(GuitarifySetting.POSITION, self.written())

    async def test_the_capo_is_typed(self):
        await self.select_field(labels.MSG_GUITAR_CAPO_LABEL)
        await self.press(Key.ENTER)
        await self.type('3')
        await self.press(Key.ENTER)
        self.assertEqual(self.guitar().get_capo(), 3)

    async def test_single_notes_step_through_leave_power_chord_and_scale_chord(self):
        await self.select_field(labels.MSG_GUITAR_SINGLE_NOTES_LABEL)
        await self.press(keybindings.GuitarifyEditor.MORE)
        self.assertEqual(self.guitar().get_single_notes(), SingleNotes.POWER_CHORD)
        self.assertIn(labels.MSG_GUITAR_SINGLE_NOTES_NAMES[SingleNotes.POWER_CHORD], self.text())
        await self.press(keybindings.GuitarifyEditor.MORE)
        self.assertEqual(self.guitar().get_single_notes(), SingleNotes.SCALE_CHORD)

    async def test_let_ring_is_a_toggle(self):
        await self.select_field(labels.MSG_GUITAR_LET_RING_LABEL)
        await self.press(keybindings.GuitarifyEditor.TOGGLE)
        self.assertTrue(self.guitar().lets_ring())
        await self.press(keybindings.GuitarifyEditor.TOGGLE)
        self.assertNotIn(GuitarifySetting.LET_RING, self.written())

    async def test_the_spread_is_shown_in_milliseconds_and_left_out_at_its_default(self):
        await self.select_field(labels.MSG_GUITAR_SPREAD_LABEL)
        self.assertIn(marks.MSG_GUITAR_MILLISECONDS.format(milliseconds=generator_settings.DEFAULT_GUITAR_SPREAD), self.text())
        await self.press(keybindings.GuitarifyEditor.MORE)
        self.assertEqual(self.guitar().get_spread(), generator_settings.DEFAULT_GUITAR_SPREAD + 1)
        await self.press(keybindings.GuitarifyEditor.LESS)
        self.assertNotIn(GuitarifySetting.SPREAD, self.written())

    async def test_upstroke_strings_down_to_none_means_every_string(self):
        await self.select_field(labels.MSG_GUITAR_UPSTROKE_LABEL)
        await self.press(*[keybindings.GuitarifyEditor.LESS] * 6)
        self.assertEqual(self.guitar().get_upstroke(), generator_settings.EVERY_STRING)
        self.assertIn(marks.MSG_GUITAR_EVERY_STRING, self.text())

    async def test_the_bar_field_names_the_ready_made_bar_and_opens_its_editor(self):
        await self.select_field(labels.MSG_GUITAR_BAR_LABEL)
        self.assertIn(labels.MSG_READY_BAR_NAMES[guitar_bars.DEFAULT_BAR], self.text())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GuitarBarEditor)
        await self.press(keybindings.GuitarBarEditor.MORE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, GuitarifyEditor)
        self.assertIn(labels.MSG_OWN_BAR, self.text())


class TestGuitarBarEditor(GuitarifyTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.select_field(labels.MSG_GUITAR_BAR_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GuitarBarEditor)

    def default(self):
        return guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR]

    async def test_it_shows_each_cells_stroke_and_says_the_cursors_in_words(self):
        text = self.text()
        first = self.default().strokes[FIRST_CELL]
        self.assertIn(marks.MSG_STROKE_MARKS[first], text)
        self.assertIn(messages.MSG_GUITAR_CELL_ACCENTED_NOTE.format(number=FIRST_CELL + 1, stroke=labels.MSG_GUITAR_STROKE_NAMES[first]), text)
        await self.press(Key.RIGHT)
        second = self.default().strokes[SECOND_CELL]
        self.assertIn(messages.MSG_GUITAR_CELL_NOTE.format(number=SECOND_CELL + 1, stroke=labels.MSG_GUITAR_STROKE_NAMES[second]), self.text())

    async def test_the_brackets_step_the_cursors_stroke_and_stop_at_both_ends(self):
        first = self.default().strokes[FIRST_CELL]
        await self.press(keybindings.GuitarBarEditor.MORE)
        self.assertEqual(self.guitar().get_bar()[FIRST_CELL], file_format.STROKES[file_format.STROKES.index(first) + 1])
        await self.press(*[keybindings.GuitarBarEditor.MORE] * len(file_format.STROKES))
        self.assertEqual(self.guitar().get_bar()[FIRST_CELL], file_format.STROKES[-1])
        await self.press(*[keybindings.GuitarBarEditor.LESS] * (len(file_format.STROKES) + 1))
        self.assertEqual(self.guitar().get_bar()[FIRST_CELL], file_format.STROKES[0])
        self.assertEqual(self.guitar().get_bar()[SECOND_CELL:], list(self.default().strokes[SECOND_CELL:]))

    async def test_space_accents_the_cursors_cell(self):
        was = self.default().accents[FIRST_CELL]
        await self.press(keybindings.GuitarBarEditor.ACCENT)
        self.assertEqual(self.guitar().get_accents()[FIRST_CELL], not was)
        await self.press(keybindings.GuitarBarEditor.ACCENT)
        self.assertEqual(self.guitar().get_accents(), list(self.default().accents))

    async def test_cells_are_inserted_and_removed_within_their_limits(self):
        count = len(self.default().strokes)
        await self.press(keybindings.GuitarBarEditor.INSERT_CELL)
        self.assertEqual(self.guitar().get_bar(), [Stroke.NOTHING, *self.default().strokes])
        self.assertEqual(self.guitar().get_accents(), [False, *self.default().accents])
        await self.press(keybindings.GuitarBarEditor.REMOVE_CELL)
        self.assertEqual(self.guitar().get_bar(), list(self.default().strokes))
        await self.press(*[keybindings.GuitarBarEditor.INSERT_CELL] * generator_settings.MAX_GUITAR_BAR)
        self.assertEqual(len(self.guitar().get_bar()), generator_settings.MAX_GUITAR_BAR)
        await self.press(*[keybindings.GuitarBarEditor.REMOVE_CELL] * (generator_settings.MAX_GUITAR_BAR + count))
        self.assertEqual(len(self.guitar().get_bar()), 1)

    async def test_the_cursor_stops_at_both_ends(self):
        await self.press(Key.LEFT)
        self.assertEqual(self.app.screen.step, FIRST_CELL)
        await self.press(*[Key.RIGHT] * (len(self.default().strokes) + 2))
        self.assertEqual(self.app.screen.step, len(self.default().strokes) - 1)

    async def test_the_cell_length_steps_round_its_choices(self):
        start = CELL_LENGTHS.index(self.default().cell)
        for step in range(1, len(CELL_LENGTHS) + 1):
            await self.press(keybindings.GuitarBarEditor.CELL_LENGTH)
            self.assertEqual(self.guitar().get_cell(), CELL_LENGTHS[(start + step) % len(CELL_LENGTHS)])

    async def test_a_ready_made_bar_replaces_strokes_accents_and_cell_length(self):
        await self.press(keybindings.GuitarBarEditor.READY_BARS)
        await self.pick(labels.MSG_READY_BAR_NAMES[ReadyBar.GALLOP])
        gallop = guitar_bars.READY_BARS[ReadyBar.GALLOP]
        self.assertEqual((self.guitar().get_cell(), self.guitar().get_bar(), self.guitar().get_accents()), (gallop.cell, list(gallop.strokes), list(gallop.accents)))

    async def test_the_picker_opens_on_the_bar_it_holds_and_esc_changes_nothing(self):
        await self.press(keybindings.GuitarBarEditor.READY_BARS)
        self.assertEqual(self.app.screen.options[self.app.screen.place], labels.MSG_READY_BAR_NAMES[guitar_bars.DEFAULT_BAR])
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, GuitarBarEditor)
        self.assertEqual(self.guitar().to_data(), {})

    async def test_a_long_bar_scrolls_with_the_cursor(self):
        await self.press(*[keybindings.GuitarBarEditor.INSERT_CELL] * generator_settings.MAX_GUITAR_BAR, *[Key.RIGHT] * generator_settings.MAX_GUITAR_BAR)
        self.assertEqual(self.app.screen.step, generator_settings.MAX_GUITAR_BAR - 1)
        self.assertIn(str(generator_settings.MAX_GUITAR_BAR), self.text())
