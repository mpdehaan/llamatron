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

"""The Arrange page, the scene and clip pages, grabs and the Registers page."""

from ui_testing import UITest, fixed_text
from llamatron.composition.defaults import DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REPEAT
from llamatron.composition.file_format import CellSetting, Direction, REGISTER_NAMES, RegisterName, Row, Section
from llamatron.composition.register import MSG_OUT_OF_ORDER
from llamatron.generators.blend import BlendMode
from llamatron.tui.arrange import ArrangePage, ClipPage, RESET_LABEL, ScenePage
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, MessageDialog
from llamatron.tui.document import DEFAULT_SCALE, Document
from llamatron.tui.pages import MainPage
from llamatron.tui.registers_page import FIELD_LABEL, NUMBER_FIELDS, RegistersPage, WRAP_FIELD
from rendering import render_song


class TestArrange(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a')
        self.page = self.app.screen

    def scenes(self):
        return [scene.get_name() for scene in self.document.song().get_scenes()]

    async def test_empty_clips_and_the_last_row_show_a_plus(self):
        self.assertEqual(self.text().count('+'), 2 + 1 + self.text().count('« + »'))

    async def test_scenes_show_their_time(self):
        self.assertIn('0:01', self.text().split('\n')[4])

    async def test_plus_adds_a_scene_below_the_cursor(self):
        await self.press('+')
        self.assertEqual(len(self.scenes()), 3)
        self.assertEqual(self.page.row, 1)

    async def test_u_and_d_move_scenes_in_render_order(self):
        await self.press('d')
        self.assertEqual(self.scenes(), ['two', 'one'])
        song = render_song(self.document.song())
        self.assertEqual([scene.name for scene in song.scenes], ['two', 'one'])

    async def test_copy_and_delete_on_the_scene_name_act_on_the_scene(self):
        await self.press('c')
        self.assertEqual(self.scenes(), ['one', 'one copy', 'two'])
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('clip(s)', self.text())
        await self.press('y')
        self.assertEqual(self.scenes(), ['one', 'two'])

    async def test_enter_on_a_blank_clip_picks_a_pattern_and_opens_it(self):
        await self.press('right', 'down', 'enter')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press('down', 'enter')
        self.assertIsInstance(self.app.screen, ClipPage)
        self.assertEqual(self.document.cell(1, 'lead').to_data(), {CellSetting.PATTERN: 'beat'})

    async def test_no_patterns_is_explained(self):
        # The clips go first, since a pattern a clip plays can't be deleted.
        for index, scene in enumerate(self.document.song().get_scenes()):
            for track in scene.get_track_names():
                self.document.delete_cell(index, track)
        for name in self.document.song().get_pattern_names():
            self.document.delete_pattern(name)
        await self.press('right', 'down', 'enter')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Patterns page', self.text())

    async def test_enter_on_a_scene_opens_its_settings(self):
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ScenePage)

    async def test_copy_and_paste_a_clip(self):
        await self.press('right', 'c', 'down', 'v')
        self.assertEqual(self.document.cell(1, 'lead').to_data(), {CellSetting.PATTERN: 'tune'})
        self.document.set_cell_setting(1, 'lead', CellSetting.REPEAT, 2)
        self.assertEqual(self.document.cell(0, 'lead').get_repeat(), DEFAULT_REPEAT)

    async def test_delete_a_clip_confirms(self):
        await self.press('right', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertIsNone(self.document.cell(0, 'lead'))

    async def test_every_clip_looping_is_shown(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.LOOP, True)
        self.document.changed()
        self.app.screen.draw()
        await self.pilot.pause()
        self.assertIn('every clip loops', self.text())

    async def test_scrolls_to_keep_the_cursor_on_screen(self):
        for number in range(20):
            self.document.add_track(f't{number}')
        self.document.changed()
        await self.press(*['right'] * 22)
        self.assertIn('t19', self.text())


class TestArrangeSmallTerminal(UITest):
    SIZE = (60, 18)

    async def test_nothing_breaks(self):
        for name in ['a', 'right', 'tab', 'p', 'enter', 'tab', 'tab']:
            await self.press(name)
        self.assertIsInstance(self.app.screen, MainPage)


class TestArrangeScrolling(UITest):

    async def test_many_tracks_scroll_sideways(self):
        for number in range(12):
            self.document.add_track(f'extra{number}')
        await self.press('a')
        page = self.app.screen
        self.assertIsInstance(page, ArrangePage)
        self.assertIn('›', self.text())
        await self.press(*['right'] * 14)
        self.assertGreater(page.left, 0)
        self.assertIn('extra11', self.text())
        await self.press(*['left'] * 14)
        self.assertEqual(page.left, 0)

    async def test_many_scenes_scroll_down_and_back(self):
        for number in range(60):
            self.document.add_scene(2, f'more {number}')
        await self.press('a')
        page = self.app.screen
        await self.press(*['down'] * 61)
        self.assertGreater(page.top, 0)
        self.assertIn('+', self.text())
        await self.press(*['up'] * 61)
        self.assertEqual(page.top, 0)


class TestClipPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a', 'right', 'enter')
        self.page = self.app.screen

    def cell(self):
        return self.document.cell(0, 'lead')

    def labels(self):
        return [field.label for field in self.page.fields()]

    async def go_to(self, label):
        self.page.place = self.labels().index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_repeat_is_always_available(self):
        self.assertIn('Repeat', self.labels())
        await self.go_to('Repeat')
        await self.press('+')
        self.assertEqual(self.cell().get_repeat(), 2)
        self.assertEqual(self.document.clip_seconds(0, 'lead'), 2)

    async def test_morph_only_appears_with_a_repeat_above_one(self):
        self.assertNotIn('Morph to', self.labels())
        await self.go_to('Repeat')
        await self.press('+')
        self.assertIn('Morph to', self.labels())
        self.assertNotIn('Morph direction', self.labels())

    async def test_choosing_a_second_pattern_offers_a_direction(self):
        await self.go_to('Repeat')
        await self.press('+')
        await self.go_to('Morph to')
        await self.press('enter', 'down', 'enter')
        self.assertEqual(self.cell().get_morph_target(), 'beat')
        self.assertEqual(self.cell().get_morph_style(), BlendMode.LEFT)
        await self.go_to('Morph direction')
        await self.press('+')
        self.assertEqual(self.cell().get_morph_style(), BlendMode.RIGHT)
        await self.press('+')
        self.assertEqual(self.cell().get_morph_style(), BlendMode.MIDDLE)
        render_song(self.document.song())

    async def test_going_back_to_one_repeat_removes_the_morph(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.REPEAT, 2)
        self.document.set_cell_morph_target(0, 'lead', 'other')
        await self.go_to('Repeat')
        await self.press('-')
        self.assertEqual(self.cell().to_data(), {CellSetting.PATTERN: 'tune'})

    async def test_loop_is_a_toggle(self):
        await self.go_to('Loop')
        await self.press('enter')
        self.assertTrue(self.cell().loops())
        await self.press('enter')
        self.assertFalse(self.cell().loops())

    async def test_chain_can_be_chosen_and_removed(self):
        await self.go_to('Chain')
        await self.press('enter', 'down', 'enter')
        self.assertEqual(self.cell().get_chain_name(), 'named')
        await self.press('backspace')
        self.assertIsNone(self.cell().get_chain_name())

    async def test_shows_its_length(self):
        self.assertIn('0:01', self.text())


class TestRhythmAndNotesFromOnAClip(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a', 'right', 'enter')
        self.page = self.app.screen

    def cell(self):
        return self.document.cell(0, 'lead')

    async def go_to(self, label):
        self.page.place = [field.label for field in self.page.fields()].index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_they_are_at_the_bottom_of_the_page(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.REPEAT, 2)
        self.document.set_cell_morph_target(0, 'lead', 'other')
        labels = [field.label for field in self.page.fields()]
        self.assertEqual(labels[-1], 'Grab track')

    async def test_choosing_none_clears(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        await self.go_to('Grab track')
        await self.press('enter')
        self.app.screen.place = 0
        await self.press('enter')
        self.assertIsNone(self.cell().get_grab_track())

    async def test_choosing_a_grab_track(self):
        await self.go_to('Grab track')
        await self.press('enter')
        self.assertEqual(self.app.screen.options, ['(none)', 'drums'])
        self.app.screen.place = 1
        await self.press('enter')
        self.assertEqual(self.cell().get_grab_track(), 'drums')

    async def test_a_circular_grab_is_refused_with_a_message(self):
        self.document.set_cell_setting(0, 'drums', CellSetting.GRAB_TRACK, 'lead')
        await self.go_to('Grab track')
        await self.press('enter')
        self.app.screen.place = 1
        await self.press('enter')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Circular grab', self.text())
        self.assertIn('a circle: lead → drums →', self.text())
        self.assertIn('Remove the grab from another clip in this scene first.', self.text())
        self.assertIsNone(self.cell().get_grab_track())

    async def test_says_when_the_grab_track_has_no_grab_steps_to_change(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        self.page.draw()
        await self.pilot.pause()
        self.assertIn('this pattern has none yet', self.text())
        self.document.set_step_value('tune', Row.GRAB, 0, True)
        self.page.draw()
        await self.pilot.pause()
        self.assertNotIn('this pattern has none yet', self.text())
        render_song(self.document.song())

    async def test_the_grid_marks_them(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        await self.press('tab')
        self.assertIn('tune g', self.text())

    async def test_a_pattern_in_use_this_way_cannot_be_deleted(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.REPEAT, 2)
        self.document.set_cell_morph_target(0, 'lead', 'other')
        await self.press('tab', 'tab', 'p', 'down', 'down', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())

    async def test_the_result_saves_and_loads(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        self.document.save('x.yml')
        self.assertEqual(Document.load('x.yml').cell(0, 'lead').to_data(), self.cell().to_data())


class TestGrabEdges(UITest):

    async def test_pasting_a_clip_onto_the_track_it_grabs_from_drops_the_grab(self):
        self.document.set_cell_setting(0, 'drums', CellSetting.GRAB_TRACK, 'lead')
        await self.press('a', 'right', 'right', 'c', 'left', 'v')
        self.assertEqual(self.document.cell(0, 'lead').get_pattern_name(), 'beat')
        self.assertIsNone(self.document.cell(0, 'lead').get_grab_track())
        self.assertIn('without its grab from lead', self.text())

    async def test_pasting_elsewhere_keeps_the_grab(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        await self.press('a', 'right', 'c', 'down', 'v')
        self.assertEqual(self.document.cell(1, 'lead').get_grab_track(), 'drums')

    async def test_choosing_a_grab_track_needs_another_track(self):
        self.document.delete_track('drums')
        await self.press('a', 'right', 'enter')
        page = self.app.screen
        self.assertIsInstance(page, ClipPage)
        page.place = [field.label for field in page.fields()].index('Grab track')
        await self.press('enter')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('No other tracks', self.text())


class TestScenePage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('a', 'enter')
        self.page = self.app.screen

    def scene(self):
        return self.document.song().get_scenes()[0]

    async def go_to(self, label):
        self.page.place = [field.label for field in self.page.fields()].index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_shows_the_length_of_its_longest_clip(self):
        self.assertIn('Length', self.text())
        self.assertIn('0:01', self.text())

    async def test_scale_can_be_set_and_cleared(self):
        await self.go_to('Scale')
        await self.press('enter', 'down', 'enter')
        self.assertEqual(self.scene().get_scale_name(), DEFAULT_SCALE)
        await self.press('backspace')
        self.assertIsNone(self.scene().get_scale_name())

    async def test_tempo_and_ramp(self):
        await self.go_to('Tempo')
        await self.press('+')
        self.assertEqual(self.scene().get_tempo_setting(), 121)
        await self.go_to('Tempo ramps to')
        await self.press('+')
        self.assertEqual((self.scene().get_tempo_start(), self.scene().get_tempo_end()), (121, 122))
        self.assertIsNone(self.scene().get_tempo_setting())
        render_song(self.document.song())
        await self.press('backspace')
        self.assertEqual(self.scene().get_tempo_setting(), 121)
        self.assertIsNone(self.scene().get_tempo_end())

    async def test_repeat(self):
        await self.go_to('Repeat')
        await self.press('+')
        self.assertEqual(self.scene().get_repeat(), 2)
        self.assertEqual(self.document.scene_seconds(0), 2)

    async def test_rename(self):
        await self.press('enter')
        self.app.screen.value = 'intro'
        await self.press('enter')
        self.assertEqual(self.scene().get_name(), 'intro')


    async def test_it_can_reset_each_register(self):
        label = RESET_LABEL.format(name=RegisterName.BX)
        await self.go_to(label)
        await self.press('enter')
        self.assertEqual(self.scene().get_reset_names(), [RegisterName.BX])
        await self.press('enter')
        self.assertEqual(self.scene().get_reset_names(), [])


class TestScenesAndClipsEdges(UITest):

    async def scene_page(self):
        await self.press('a', 'enter')
        self.assertIsInstance(self.app.screen, ScenePage)
        return self.app.screen

    async def go_to(self, page, label):
        page.place = [field.label for field in page.fields()].index(label)
        page.draw()
        await self.pilot.pause()

    def scene(self):
        return self.document.song().get_scenes()[0]

    async def test_tempo_with_a_ramp_moves_the_start_and_clearing_removes_both(self):
        self.document.set_scene_tempo(0, 100)
        self.document.set_scene_tempo_ramp(0, 120)
        page = await self.scene_page()
        await self.go_to(page, 'Tempo')
        await self.press('+')
        self.assertEqual((self.scene().get_tempo_start(), self.scene().get_tempo_end()), (101, 120))
        await self.press('backspace')
        self.assertEqual((self.scene().get_tempo_setting(), self.scene().get_tempo_start(), self.scene().get_tempo_end()), (None, None, None))

    async def test_choosing_the_songs_scale_clears_the_scenes(self):
        self.document.set_scene_scale(0, DEFAULT_SCALE)
        page = await self.scene_page()
        await self.go_to(page, 'Scale')
        await self.press('enter')
        self.app.screen.place = 0
        await self.press('enter')
        self.assertIsNone(self.scene().get_scale_name())

    async def clip_page(self):
        await self.press('a', 'right', 'enter')
        self.assertIsInstance(self.app.screen, ClipPage)
        return self.app.screen

    async def test_choosing_none_clears_the_chain(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.CHAIN, 'named')
        page = await self.clip_page()
        await self.go_to(page, 'Chain')
        await self.press('enter')
        self.app.screen.place = 0
        await self.press('enter')
        self.assertIsNone(self.document.cell(0, 'lead').get_chain_name())

    async def test_stepping_past_the_last_direction_goes_back_to_the_patterns(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.DIRECTION, Direction.EITHERWAY)
        page = await self.clip_page()
        await self.go_to(page, 'Direction')
        await self.press('+')
        self.assertIsNone(self.document.cell(0, 'lead').get_direction())

    async def test_deleting_a_clip_asks_first(self):
        await self.press('a', 'right', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertIsNone(self.document.cell(0, 'lead'))


# What shows when a register's settings would be out of order.
OUT_OF_ORDER_START = fixed_text(MSG_OUT_OF_ORDER)


class TestRegistersPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('r')
        self.page = self.app.screen

    def label(self, name, what):
        return FIELD_LABEL.format(name=name, what=what)

    def register(self, name):
        return self.document.register(name)

    async def test_it_opens_from_the_main_screen_with_every_register(self):
        self.assertIsInstance(self.page, RegistersPage)
        labels = [field.label for field in self.page.fields()]
        for name in REGISTER_NAMES:
            for _, what in NUMBER_FIELDS:
                self.assertIn(self.label(name, what), labels)
            self.assertIn(self.label(name, WRAP_FIELD), labels)

    async def test_numbers_change_and_go_back_to_their_defaults(self):
        await self.select_field(self.label(RegisterName.BX, 'maximum'))
        await self.press('+')
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), DEFAULT_REGISTER_MAXIMUM + 1)
        await self.press('backspace')
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), DEFAULT_REGISTER_MAXIMUM)
        self.assertNotIn(Section.REGISTERS, self.document.song().to_data())

    async def test_a_typed_number_can_be_negative(self):
        lowest = -50
        await self.select_field(self.label(RegisterName.DX, 'minimum'))
        await self.press('enter')
        self.app.screen.value = str(lowest)
        await self.press('enter')
        self.assertEqual(self.register(RegisterName.DX).get_minimum(), lowest)
        render_song(self.document.song())

    async def test_settings_out_of_order_are_refused_with_the_reason(self):
        await self.select_field(self.label(RegisterName.AX, 'minimum'))
        await self.press('+')
        self.assertEqual(self.register(RegisterName.AX).get_minimum(), DEFAULT_REGISTER_MINIMUM)
        self.assertIn(OUT_OF_ORDER_START, self.text())

    async def test_wrapping_toggles(self):
        await self.select_field(self.label(RegisterName.CX, WRAP_FIELD))
        await self.press('enter')
        self.assertTrue(self.register(RegisterName.CX).wraps())
        await self.press('enter')
        self.assertFalse(self.register(RegisterName.CX).wraps())

    async def test_settings_save_and_load(self):
        await self.select_field(self.label(RegisterName.AX, 'maximum'))
        await self.press('-')
        self.document.save('x.yml')
        self.assertEqual(Document.load('x.yml').register(RegisterName.AX).get_maximum(), DEFAULT_REGISTER_MAXIMUM - 1)
