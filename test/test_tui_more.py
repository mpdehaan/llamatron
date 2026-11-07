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

"""Pages and edges of the text UI that the other tests don't press: chains, generators, the arp
settings, grabs, the pattern editor's refusals, scenes, Arrange and the Song page."""

import os
from unittest import mock

from test_tui_pages import UITest
from llamatron.composition.file_format import CellSetting, Direction, GeneratorKind, Row, Section
from llamatron.composition.generator_settings import ArpSetting, written_name
from llamatron.generators.arp import ChordOrder, OctaveJump
from llamatron.tui.document import DEFAULT_SCALE

from rendering import render_song
from llamatron.tui.arrange import ArrangePage, ClipPage, ScenePage
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, MessageDialog, PromptDialog
from llamatron.tui.pages import ArpEditor, ArpsPage, AutoRatchetsPage, ChainEditor, ChainsPage, MainPage, OffsetsEditor, SongPage, TrackEditor
from llamatron.tui.pattern_editor import PatternEditor


class TestChainsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('c')
        self.assertIsInstance(self.app.screen, ChainsPage)

    def chains(self):
        return self.document.song().get_chain_names()

    async def test_adding_renaming_copying_and_moving(self):
        await self.press('+')
        await self.type('lift')
        await self.press('enter')
        self.assertEqual(self.chains(), ['named', 'empty', 'lift'])
        await self.press('n')
        self.app.screen.value = 'rise'
        await self.press('enter')
        self.assertEqual(self.chains(), ['named', 'empty', 'rise'])
        await self.press('c')
        self.assertEqual(self.chains(), ['named', 'empty', 'rise', 'rise copy'])
        await self.press('u')
        self.assertEqual(self.chains(), ['named', 'empty', 'rise copy', 'rise'])

    async def test_renaming_a_chain_updates_the_clips_that_use_it(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.CHAIN, 'named')
        await self.press('n')
        self.app.screen.value = 'bright'
        await self.press('enter')
        self.assertEqual(self.document.cell(0, 'lead').get_chain_name(), 'bright')

    async def test_deleting_an_unused_chain_asks_first(self):
        await self.press('down', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertEqual(self.chains(), ['named'])

    async def test_a_chain_in_use_cannot_be_deleted(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.CHAIN, 'named')
        await self.press('backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('track lead', self.text())
        self.assertIn('named', self.chains())


class TestChainEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('c', 'enter')
        self.assertIsInstance(self.app.screen, ChainEditor)

    def steps(self):
        return self.chain_steps('named')

    async def test_changing_copying_moving_and_removing_steps(self):
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, ['arp: up', 'auto_ratchet: rolls'])
        self.app.screen.place = 1
        await self.press('enter')
        self.assertEqual(self.steps(), [(GeneratorKind.AUTO_RATCHET, 'rolls'), (GeneratorKind.AUTO_RATCHET, 'rolls')])
        await self.press('down', 'enter')
        self.app.screen.place = 0
        await self.press('enter')
        self.assertEqual(self.steps(), [(GeneratorKind.AUTO_RATCHET, 'rolls'), (GeneratorKind.ARP, 'up')])
        await self.press('c')
        self.assertEqual(self.steps(), [(GeneratorKind.AUTO_RATCHET, 'rolls'), (GeneratorKind.ARP, 'up'), (GeneratorKind.ARP, 'up')])
        await self.press('up', 'up', 'd')
        self.assertEqual(self.steps(), [(GeneratorKind.ARP, 'up'), (GeneratorKind.AUTO_RATCHET, 'rolls'), (GeneratorKind.ARP, 'up')])
        await self.press('backspace', 'backspace')
        self.assertEqual(self.steps(), [(GeneratorKind.ARP, 'up')])
        render_song(self.document.song())

    async def test_a_step_cannot_move_past_the_ends(self):
        await self.press('u')
        self.assertEqual(self.steps(), [(GeneratorKind.ARP, 'up'), (GeneratorKind.AUTO_RATCHET, 'rolls')])

    async def test_adding_needs_a_generator_first(self):
        # The chain's own steps go first, since a generator a chain uses can't be deleted.
        await self.press('backspace', 'backspace')
        self.delete_every_generator()
        await self.press('+')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Nothing to add', self.text())


class TestGeneratorLists(UITest):

    async def test_adding_moving_and_deleting_arpeggiators(self):
        await self.press('g', 'enter')
        self.assertIsInstance(self.app.screen, ArpsPage)
        await self.press('+')
        await self.type('fast')
        await self.press('enter')
        self.assertEqual(self.document.song().get_generator_names(GeneratorKind.ARP), ['up', 'fast'])
        await self.press('u')
        self.assertEqual(self.document.song().get_generator_names(GeneratorKind.ARP), ['fast', 'up'])
        await self.press('backspace', 'y')
        self.assertEqual(self.document.song().get_generator_names(GeneratorKind.ARP), ['up'])

    async def test_an_arpeggiator_in_a_chain_cannot_be_deleted(self):
        await self.press('g', 'enter', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('chain named', self.text())

    async def test_renaming_an_arpeggiator_updates_its_chains(self):
        await self.press('g', 'enter', 'n')
        self.app.screen.value = 'climb'
        await self.press('enter')
        self.assertEqual(self.chain_steps('named')[0], (GeneratorKind.ARP, 'climb'))

    async def test_copying_and_moving_autoratchets(self):
        await self.press('g', 'down', 'enter')
        self.assertIsInstance(self.app.screen, AutoRatchetsPage)
        await self.press('c')
        self.assertEqual(self.auto_ratchet('rolls copy').get_counts(), [1, 4])
        await self.press('u')
        self.assertEqual(self.document.song().get_generator_names(GeneratorKind.AUTO_RATCHET), ['rolls copy', 'rolls'])


class TestArpSettings(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press('g', 'enter', 'enter')
        self.assertIsInstance(self.app.screen, ArpEditor)

    def up(self):
        return self.arp('up')

    async def test_choosing_a_step_and_an_order(self):
        await self.press('enter')
        self.app.screen.place = self.app.screen.options.index('1/4')
        await self.press('enter', 'down', 'enter')
        self.app.screen.place = self.app.screen.options.index('random')
        await self.press('enter')
        self.assertEqual((self.up().get_step(), self.up().get_order()), ('1/4', written_name(ChordOrder.RANDOM)))

    async def test_typing_an_octave_range_and_going_back_to_one(self):
        await self.press('down', 'down', 'enter')
        self.app.screen.value = '3'
        await self.press('enter')
        self.assertEqual(self.up().get_octave_range(), 3)
        await self.press('enter')
        self.app.screen.value = '1'
        await self.press('enter')
        self.assertIsNone(self.up().get_octave_range())

    async def test_choosing_an_octave_jump(self):
        await self.press('down', 'down', 'down', 'enter')
        self.assertEqual(self.app.screen.options, ['after chord', 'after each note'])
        self.app.screen.place = 1
        await self.press('enter')
        self.assertEqual(self.up().get_octave_jump(), written_name(OctaveJump.AFTER_EACH_NOTE))
        await self.press('enter')
        self.app.screen.place = 0
        await self.press('enter')
        self.assertIsNone(self.up().get_octave_jump())

    async def test_a_seed_of_its_own_and_back_to_the_songs(self):
        await self.press(*['down'] * 5, '+')
        self.assertEqual(self.up().get_seed(), 1)
        await self.press('backspace')
        self.assertIsNone(self.up().get_seed())
        self.assertIn('(song)', self.text())

    async def test_typing_an_offset_too_big_starts_a_new_number(self):
        self.document.set_generator_setting(Section.ARPS, 'up', ArpSetting.OFFSETS, [0, -3])
        await self.press(*['down'] * 4, 'enter')
        self.assertIsInstance(self.app.screen, OffsetsEditor)
        await self.press('2', '5')
        self.assertEqual(self.up().get_offsets()[0], 5)
        await self.press('right', '4')
        self.assertEqual(self.up().get_offsets()[1], -4)


class TestTrackSettingsEdges(UITest):

    async def test_a_cc_lane_turns_up_or_down_from_none(self):
        await self.press('t', 'enter')
        self.assertIsInstance(self.app.screen, TrackEditor)
        await self.select_field('CC 1')
        await self.press('+')
        self.assertEqual(self.track('lead').get_cc_numbers(), [1, None, None, None])
        await self.select_field('CC 2')
        await self.press('-')
        self.assertEqual(self.track('lead').get_cc_numbers(), [1, 0, None, None])

    async def test_deleting_a_track_that_others_grab_from_says_so(self):
        self.document.set_cell_setting(0, 'lead', CellSetting.GRAB_TRACK, 'drums')
        await self.press('t', 'down', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('1 clip(s) that grab from it will', self.text())
        self.assertIn('stop grabbing', self.text())
        await self.press('y')
        self.assertIsNone(self.document.cell(0, 'lead').get_grab_track())


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


class TestSongPageEdges(UITest):

    async def test_saving_a_new_song_asks_for_a_name_and_an_empty_one_does_nothing(self):
        await self.press('s', 's')
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = '  '
        await self.press('enter')
        self.assertIsNone(self.document.path)

    async def test_a_save_that_fails_is_explained(self):
        os.mkdir('taken.yml')
        await self.press('s', 'w')
        self.app.screen.value = 'taken.yml'
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn("Can't save", self.text())

    async def test_new_and_load_ask_first_with_unsaved_changes(self):
        self.document.changed()
        await self.press('s', 'n')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('tab', 'l')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press('y')
        self.assertNotIsInstance(self.app.screen, SongPage)

    async def test_choosing_a_scale_needs_one_first(self):
        self.document.set_scale_name(None)
        for name in self.document.song().get_scale_names():
            self.document.delete_scale(name)
        await self.press('s', 'down', 'down', 'down', 'enter')
        self.assertIn('Add a scale first', self.text())


class TestQuitting(UITest):

    async def test_quitting_with_unsaved_changes_asks_and_then_quits(self):
        self.document.changed()
        with mock.patch.object(self.app, 'exit') as leave:
            await self.press('q')
            self.assertIsInstance(self.app.screen, ConfirmDialog)
            await self.press('n')
            leave.assert_not_called()
            self.assertIsInstance(self.app.screen, MainPage)
            await self.press('q', 'y')
            leave.assert_called_once()
