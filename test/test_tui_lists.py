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

"""The Tracks, Scales, Generators and Chains pages and their editors."""

from ui_testing import UITest
from llamatron.composition.file_format import CellSetting, GeneratorKind, Section, TrackSetting
from llamatron.composition.generator_settings import ArpSetting, written_name
from llamatron.composition.named_scale import scale_type_name
from llamatron.generators.arp import ChordOrder, OctaveJump
from llamatron.note import NoteName
from llamatron.scale import ScaleType
from llamatron.tui.base import ChoiceDialog, ConfirmDialog, GridChoiceDialog, MessageDialog
from llamatron.tui.document import DEFAULT_SCALE
from llamatron.tui.pages import (
    ArpEditor, ArpsPage, AutoRatchetEditor, AutoRatchetsPage, ChainEditor, ChainsPage, OffsetsEditor,
    TrackEditor,
)
from rendering import render_song


class TestTracksPage(UITest):
    """The Tracks page and a track's settings."""

    async def test_tracks(self):
        await self.press('t', '+')
        await self.type('bass')
        await self.press('enter')
        self.assertEqual(self.document.song().get_track_names(), ['lead', 'drums', 'bass'])
        await self.press('n')
        self.app.screen.value = 'low'
        await self.press('enter', 'u')
        self.assertEqual(self.document.song().get_track_names(), ['lead', 'low', 'drums'])
        await self.press('c')
        self.assertIn('low copy', self.document.song().get_track_names())

    async def test_a_tracks_settings(self):
        await self.press('t', 'enter')
        self.assertIsInstance(self.app.screen, TrackEditor)
        await self.select_field('Mute')
        await self.press('enter')
        self.assertTrue(self.track('lead').is_muted())
        await self.press('enter')
        self.assertFalse(self.track('lead').is_muted())
        await self.select_field('Transpose')
        await self.press('+', '+')
        self.assertEqual(self.track('lead').get_transpose(), 2)
        await self.select_field('CC 1')
        await self.press('enter')
        self.app.screen.value = '74'
        await self.press('enter')
        self.assertEqual(self.track('lead').get_cc_numbers(), [74, None, None, None])
        await self.press('backspace')
        self.assertNotIn(TrackSetting.CC, self.track('lead').to_data())
        await self.select_field('Drum')
        await self.press('enter')
        self.assertTrue(self.track('lead').is_drum())
        self.assertIn('(drum track)', self.text())
        await self.press('tab')
        self.assertIn('drum', self.text())
        render_song(self.document.song())

    async def test_deleting_a_track_says_it_deletes_its_clips(self):
        await self.press('t', 'backspace')
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('1 clip(s)', self.text())
        await self.press('y')
        self.assertEqual(self.document.song().get_track_names(), ['drums'])
        self.assertIsNone(self.document.cell(0, 'lead'))


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


class TestScalesPage(UITest):
    """The Scales page and its root and scale pickers."""

    async def test_the_default_scale_must_be_unset_before_deleting_it(self):
        await self.press('z', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('the song', self.text())
        await self.press('enter', 'tab', 's', 'down', 'down', 'down', 'backspace', 'tab', 'z', 'backspace', 'y')
        self.assertEqual(self.document.song().get_scale_names(), [])

    async def test_adding_a_scale_picks_a_root_a_kind_and_a_name(self):
        await self.press('z', '+')
        self.assertIn('root note', self.text())
        self.app.screen.place = self.app.screen.options.index('F#')
        await self.press('enter')
        self.app.screen.place = self.app.screen.options.index('dorian')
        await self.press('enter')
        self.assertEqual(self.app.screen.value, 'F# Dorian')
        self.app.screen.value = 'main'
        await self.press('enter')
        self.assertEqual(self.root_and_kind('main'), (NoteName.F_SHARP, scale_type_name(ScaleType.DORIAN)))

    def dialog_text(self):
        return str(self.app.screen.query_one('#dialog-view').render())

    async def open_scale_kinds(self):
        await self.press('z', '+')
        self.app.screen.place = self.app.screen.options.index('D')
        await self.press('enter')
        return self.app.screen

    async def test_roots_are_laid_out_like_a_keyboard(self):
        await self.press('z', '+')
        dialog = self.app.screen
        self.assertIsInstance(dialog, GridChoiceDialog)
        lines = self.dialog_text().splitlines()
        self.assertIn('C   C#   D   D#   E   F   F#   G   G#   A   A#   B', '\n'.join(lines))
        dialog.place = dialog.options.index('C')
        await self.press('right')
        self.assertEqual(dialog.options[dialog.place], 'C#')
        await self.press('down')
        self.assertEqual(dialog.options[dialog.place], 'Db')
        await self.press('right')
        self.assertEqual(dialog.options[dialog.place], 'D')

    async def test_scales_are_grouped_and_show_their_notes(self):
        await self.press('z', '+')
        self.app.screen.place = self.app.screen.options.index('D')
        await self.press('enter')
        dialog = self.app.screen
        text = self.dialog_text()
        for word in ['MODES', 'MINOR & MAJOR', 'SYMMETRIC', 'PENTATONIC & BLUES', 'whole half dim', 'ionian', 'egyptian']:
            self.assertIn(word, text)
        self.assertNotIn('diminished', text)
        self.assertNotIn('hirajoshi', text)
        self.assertLessEqual(len(text.splitlines()), 22)
        dialog.place = dialog.options.index('dorian')
        await self.press('down')
        self.assertEqual(dialog.options[dialog.place], 'phrygian')
        await self.press('up')
        self.assertIn('D dorian: D E F G A B C', self.dialog_text())
        await self.press('enter')
        self.assertEqual(self.app.screen.value, 'D Dorian')

    async def test_the_scale_picker_shows_its_other_page(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index('dorian')
        first = self.dialog_text().splitlines()
        for word in [' COMMON ', ' JAZZ & WORLD ', 'PgDn ▸', 'PgUp/PgDn', 'other page']:
            self.assertIn(word, '\n'.join(first))
        self.assertNotIn('◂ PgUp', '\n'.join(first))
        await self.press('pagedown')
        text = self.dialog_text()
        for word in ['MELODIC MINOR', 'MIDDLE EAST & EUROPE', 'EAST ASIA', 'INDIA', 'JAZZ', 'phrygian dom', 'mixolydian flat6', '◂ PgUp']:
            self.assertIn(word, text)
        self.assertNotIn('PgDn ▸', text)
        self.assertNotIn('natural minor', text)
        lines = text.splitlines()
        self.assertLessEqual(len(lines), 22)
        self.assertLessEqual(max(len(line) for line in lines), 76)
        # The cursor stays in its column, on the nearest row.
        self.assertEqual(dialog.options[dialog.place], 'lydian augmented')
        await self.press('pagedown')
        self.assertEqual(dialog.page, 1)
        await self.press('pageup', 'pageup')
        self.assertEqual(dialog.page, 0)

    async def test_both_scale_pages_are_the_same_size(self):
        dialog = await self.open_scale_kinds()
        sizes = []
        for page in range(len(dialog.pages)):
            dialog.page = page
            dialog.place = next(cell for row in dialog.grid for cell in row if isinstance(cell, int))
            dialog.draw()
            lines = self.dialog_text().splitlines()
            sizes.append((len(lines), {len(line) for line in lines}))
        self.assertEqual(len(set(map(str, sizes))), 1, sizes)
        self.assertEqual(len(sizes[0][1]), 1)

    async def test_a_long_title_does_not_widen_the_scale_picker(self):
        dialog = await self.open_scale_kinds()
        width = len(self.dialog_text().splitlines()[0])
        dialog.title = 'Change ' + 'a very long scale name ' * 4
        dialog.draw()
        self.assertEqual({len(line) for line in self.dialog_text().splitlines()}, {width})
        self.assertIn('JAZZ & WORLD', self.dialog_text())

    async def test_arrows_cross_to_the_other_page(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index('blues')
        await self.press('right')
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.options[dialog.place], 'lydian augmented')
        await self.press('left')
        self.assertEqual(dialog.page, 0)
        self.assertEqual(dialog.options[dialog.place], 'blues')
        await self.press('left', 'left', 'left')
        # The first page doesn't go round to the last.
        self.assertEqual(dialog.page, 0)
        self.assertEqual(dialog.options[dialog.place], 'dorian')
        await self.press('pagedown', 'right', 'right', 'right')
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.options[dialog.place], 'iwato')

    async def test_picking_a_world_scale(self):
        dialog = await self.open_scale_kinds()
        dialog.place = dialog.options.index('major')
        await self.press('pagedown', 'right', 'right')
        self.assertEqual(dialog.options[dialog.place], 'hirajoshi')
        self.assertIn('D hirajoshi: D E F A A#', self.dialog_text())
        await self.press('enter')
        self.app.screen.value = 'main'
        await self.press('enter')
        self.assertEqual(self.root_and_kind('main'), (NoteName.D, scale_type_name(ScaleType.HIRAJOSHI)))
        render_song(self.document.song())

    async def test_two_scales_can_be_the_same_notes(self):
        await self.press('z', 'c')
        self.assertEqual(self.root_and_kind('C Major copy'), (NoteName.C, scale_type_name(ScaleType.MAJOR)))

    async def test_changing_a_scale_keeps_its_name_and_changes_what_uses_it(self):
        await self.press('z', 'enter')
        self.app.screen.place = self.app.screen.options.index('D')
        await self.press('enter', 'enter')
        self.assertEqual(self.document.song().get_scale_name(), 'C Major')
        self.assertEqual(self.root_and_kind(DEFAULT_SCALE), (NoteName.D, scale_type_name(ScaleType.MAJOR)))

    async def test_renaming_a_scale_updates_what_uses_it(self):
        self.document.set_scene_scale(0, DEFAULT_SCALE)
        await self.press('z', 'n')
        self.app.screen.value = 'main'
        await self.press('enter')
        self.assertEqual(self.document.song().get_scale_name(), 'main')
        self.assertEqual(self.document.song().get_scenes()[0].get_scale_name(), 'main')
        render_song(self.document.song())


class TestGeneratorsAndChainsPages(UITest):
    """The Generators pages, their editors, and adding them to chains."""

    async def test_editing_an_arps_offsets_and_octaves(self):
        await self.press('g', 'enter', 'enter')
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.press('down', 'down', '+')
        self.assertEqual(self.arp('up').get_octave_range(), 2)
        await self.press('down', '+')
        self.assertEqual(self.arp('up').get_octave_jump(), written_name(OctaveJump.AFTER_EACH_NOTE))
        self.assertIn('after each note', self.text())
        await self.press('down', 'enter')
        self.assertIsInstance(self.app.screen, OffsetsEditor)
        self.assertEqual(self.arp('up').get_offsets(), [0] * 8)
        await self.press('right', '7', 'right', 'space', 'right', '-', '-', 'x', 'i')
        self.assertEqual(self.arp('up').get_offsets(), [0, 7, None, 0, 0, 0, 0, 0])
        await self.press('tab')
        self.assertIn('0 7 - 0 0 0 0 0', self.text())
        await self.press('backspace')
        self.assertIsNone(self.arp('up').get_offsets())
        render_song(self.document.song())

    async def test_offsets_have_one_to_sixteen_steps(self):
        self.document.set_generator_setting(Section.ARPS, 'up', ArpSetting.OFFSETS, [0] * 16)
        await self.press('g', 'enter', 'enter', *['down'] * 4, 'enter')
        self.assertNotIn('« I »', self.text())
        self.document.set_generator_setting(Section.ARPS, 'up', ArpSetting.OFFSETS, [3])
        await self.press('right')
        self.assertNotIn('« X »', self.text())

    async def test_arps_are_under_generators(self):
        await self.press('g')
        self.assertIn('Arpeggiators', self.text())
        self.assertIn('AutoRatchets', self.text())
        self.assertEqual(len(self.app.screen.rows()), 2)
        await self.press('enter')
        self.assertIsInstance(self.app.screen, ArpsPage)

    async def test_editing_an_arp(self):
        await self.press('g', 'enter', 'enter')
        self.assertIsInstance(self.app.screen, ArpEditor)
        await self.press('+')
        self.assertEqual(self.arp('up').get_step(), '1/4')
        await self.press('down', '+')
        self.assertEqual(self.arp('up').get_order(), written_name(ChordOrder.DOWN))

    async def test_adding_an_arp(self):
        await self.press('g', 'enter', '+')
        await self.type('rise')
        await self.press('enter')
        self.assertEqual(self.arp('rise').get_order(), written_name(ChordOrder.UP))
        self.document.song()

    async def test_an_auto_ratchet_can_be_made_edited_and_added_to_a_chain(self):
        await self.press('g', 'down', 'enter')
        self.assertIsInstance(self.app.screen, AutoRatchetsPage)
        await self.press('+')
        await self.type('fast')
        await self.press('enter')
        self.assertEqual(self.auto_ratchet('fast').get_counts(), [2])
        await self.press('enter')
        self.assertIsInstance(self.app.screen, AutoRatchetEditor)
        await self.press('enter')
        self.app.screen.value = '1 1 4'
        await self.press('enter')
        self.assertEqual(self.auto_ratchet('fast').get_counts(), [1, 1, 4])
        await self.press('tab', 'tab', 'tab', 'c', 'down', 'enter', '+')
        self.assertEqual(self.app.screen.options, ['arp: up', 'auto_ratchet: rolls', 'auto_ratchet: fast'])
        await self.press('down', 'down', 'enter')
        self.assertEqual(self.chain_steps('empty'), [(GeneratorKind.AUTO_RATCHET, 'fast')])
        render_song(self.document.song())

    async def test_bad_counts_are_refused(self):
        await self.press('g', 'down', 'enter', 'enter', 'enter')
        self.app.screen.value = '1 x'
        await self.press('enter')
        self.assertEqual(self.auto_ratchet('rolls').get_counts(), [1, 4])
        self.assertIn('whole numbers', self.text())

    async def test_deleting_an_auto_ratchet_in_a_chain_is_refused(self):
        self.document.add_chain_step('empty', GeneratorKind.AUTO_RATCHET, 'rolls')
        await self.press('g', 'down', 'enter', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('chain empty', self.text())

    async def test_deleting_an_arp_in_a_chain_is_refused(self):
        await self.press('g', 'enter', 'backspace')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('chain named', self.text())

    async def test_a_chain_can_add_a_named_arp(self):
        await self.press('c', 'down', 'enter')
        self.assertIsInstance(self.app.screen, ChainEditor)
        await self.press('+', 'enter')
        self.assertEqual(self.chain_steps('empty'), [(GeneratorKind.ARP, 'up')])
        self.document.song()

    async def test_adding_a_chain_step_needs_an_arp_first(self):
        for name in self.document.song().get_chain_names():
            self.document.delete_chain(name)
        self.delete_every_generator()
        self.document.add_chain(EMPTY_CHAIN)
        await self.press('c', 'enter', '+')
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('Generators', self.text())


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


EMPTY_CHAIN = 'x'


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
