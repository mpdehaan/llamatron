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
"""The row of track names at the top of the Arrange page, where tracks are added, duplicated, inserted, moved,
renamed and deleted since the Tracks page went on 2026-11-07, and the track editor it opens."""

from ui_testing import UITest, back_key, forward_key, key_of
from llamatron.composition.file_format import REGISTER_NAMES, ClipSlotSetting, PatternSetting, TrackSetting
from llamatron.composition.limits import MAX_OCTAVE, MIN_OCTAVE
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.screens.chain_list_page import ChainListPage
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.strings.labels import MSG_CHAINS_LABEL, MSG_CC_REGISTER_LABEL, MSG_NAME_LABEL, MSG_TRACK_CRUMB, MSG_VELOCITY_REGISTER_LABEL
from llamatron.strings.names import MSG_NEW_SCENE_NAME, MSG_NEW_TRACK_NAME
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from rendering import render_song


LEAD = 'lead'
DRUMS = 'drums'
TRACK_1 = MSG_NEW_TRACK_NAME.format(number=1)
TRACK_3 = MSG_NEW_TRACK_NAME.format(number=3)
TRACK_4 = MSG_NEW_TRACK_NAME.format(number=4)
SCENE_1 = MSG_NEW_SCENE_NAME.format(number=1)
SECOND_SONG = 'second'
LOW = 'low'
LEAD_COPY = 'lead 2'
MUTE = 'Mute'
TRANSPOSE = 'Transpose'
LOWEST_OCTAVE = 'Lowest octave'
HIGHEST_OCTAVE = 'Highest octave'
# An octave typed into the range, in the file's numbering: middle C's.
TYPED_OCTAVE = 5
CC_1 = 'CC 1'
CC_2 = 'CC 2'
DRUM = 'Drum'
STOP_GRABBING = 'stop grabbing'
DRUM_TRACK_SHOWN = '(drum track)'
ONE_CLIP = '1 clip(s)'
ONE_GRABBER = '1 clip(s) that grab from it will'


class TestArrangeTracks(UITest):
    """The header row: Up from the first scene reaches the track names, and Right past them reaches the +."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE, Key.UP)
        self.page = self.app.screen

    def tracks(self):
        return self.document.song().get_track_names()

    async def test_up_from_the_first_scene_lands_on_the_first_track(self):
        self.assertIsInstance(self.page, ArrangePage)
        self.assertTrue(self.page.on_track_name())
        self.assertEqual(self.page.track(), LEAD)

    async def test_the_plus_after_the_last_track_adds_one(self):
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertTrue(self.page.on_track_plus())
        await self.press(Key.ENTER)
        self.assertEqual(self.tracks(), [LEAD, DRUMS, TRACK_3])
        self.assertEqual(self.page.track(), TRACK_3)

    async def test_a_adds_a_track_from_any_track_name_and_names_it_by_number(self):
        await self.press(keybindings.ArrangePage.ADD_TRACK)
        self.assertEqual(self.tracks(), [LEAD, DRUMS, TRACK_3])
        await self.press(keybindings.ArrangePage.ADD_TRACK)
        self.assertEqual(self.tracks(), [LEAD, DRUMS, TRACK_3, TRACK_4])
        self.assertEqual(self.page.track(), TRACK_4)

    async def test_right_stops_at_the_plus(self):
        await self.press(Key.RIGHT, Key.RIGHT, Key.RIGHT, Key.RIGHT)
        self.assertTrue(self.page.on_track_plus())

    async def test_enter_opens_the_track_editor_with_a_track_crumb(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, TrackEditor)
        self.assertIn(MSG_TRACK_CRUMB.format(name=LEAD), self.crumbs_line())

    async def test_copy_adds_a_copy_to_the_right_with_its_clips(self):
        await self.press(keybindings.ArrangePage.COPY_TRACK)
        self.assertEqual(self.tracks(), [LEAD, LEAD_COPY, DRUMS])
        self.assertEqual(self.page.track(), LEAD_COPY)
        self.assertIsNotNone(self.document.clip_slot(index=0, track=LEAD_COPY))

    async def test_insert_puts_a_blank_track_before_this_one(self):
        await self.press(Key.RIGHT, keybindings.ArrangePage.INSERT_TRACK)
        self.assertEqual(self.tracks(), [LEAD, TRACK_3, DRUMS])
        self.assertIsNone(self.document.clip_slot(index=0, track=TRACK_3))
        self.assertEqual(self.page.track(), TRACK_3)

    async def test_move_mode_carries_the_track_and_the_cursor_follows(self):
        await self.press(keybindings.ArrangePage.MOVE_TRACK, forward_key(keybindings.ArrangePage.CARRY_TRACK))
        self.assertEqual(self.tracks(), [DRUMS, LEAD])
        self.assertEqual(self.page.track(), LEAD)
        await self.press(forward_key(keybindings.ArrangePage.CARRY_TRACK))
        self.assertEqual(self.tracks(), [DRUMS, LEAD])
        await self.press(back_key(keybindings.ArrangePage.CARRY_TRACK), Key.ENTER)
        self.assertEqual(self.tracks(), [LEAD, DRUMS])
        self.assertEqual(self.page.track(), LEAD)
        self.assertIsNone(self.page.moving)
        self.assertEqual([column.get_name() for column in render_song(self.document.song()).get_columns()], [LEAD, DRUMS])

    async def test_deleting_a_track_says_it_deletes_its_clips(self):
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(ONE_CLIP, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.tracks(), [DRUMS])
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD))
        self.assertTrue(self.page.on_track_name())

    async def test_deleting_a_track_that_others_grab_from_says_so(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        await self.press(Key.RIGHT, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(ONE_GRABBER, self.text())
        self.assertIn(STOP_GRABBING, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD).get_grab_track())

    async def test_an_empty_song_starts_on_the_track_plus(self):
        self.empty_the_arrangement()
        await self.press(Key.ESCAPE, keybindings.MainPage.ARRANGE)
        page = self.app.screen
        self.assertTrue(page.on_plus_row())
        await self.press(Key.UP)
        self.assertTrue(page.on_track_plus())
        await self.press(Key.ENTER)
        self.assertEqual(self.tracks(), [TRACK_1])

    async def test_a_new_song_starts_with_one_track_and_one_scene(self):
        self.document.add_song(SECOND_SONG)
        self.assertEqual(self.tracks(), [TRACK_1])
        self.assertEqual([scene.get_name() for scene in self.document.song().get_scenes()], [SCENE_1])
        self.assertEqual(self.document.lengths().song_seconds(), 0)

    async def test_paste_and_add_scene_keys_are_not_on_the_header(self):
        shown = [item.keys[0] for item in self.page.key_table()]
        self.assertNotIn(first_key(keybindings.ArrangePage.PASTE_CLIP), shown)
        await self.press(keybindings.ArrangePage.PASTE_CLIP)
        self.assertEqual(len(self.document.song().get_scenes()), 2)
        self.assertEqual(self.tracks(), [LEAD, DRUMS])


class TestChainListPage(UITest):
    """The list of chains a track runs, opened from the track editor's Chains field: A adds, U and D move, Bksp takes one out."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        await self.select_field(MSG_CHAINS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainListPage)

    async def test_chains_are_added_moved_and_taken_out_in_the_order_they_run(self):
        names = sorted(self.document.song().get_chain_names())
        await self.press(keybindings.ChainListPage.ADD, Key.ENTER, keybindings.ChainListPage.ADD, Key.DOWN, Key.ENTER)
        self.assertEqual(self.track(LEAD).get_chain_names(), names[:2])
        await self.press(keybindings.ChainListPage.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.track(LEAD).get_chain_names(), list(reversed(names[:2])))
        await self.press(keybindings.ChainListPage.REMOVE)
        self.assertEqual(self.track(LEAD).get_chain_names(), [names[0]])
        self.assertIn(MSG_CHAINS_LABEL.upper(), self.text())


class TestTrackEditor(UITest):
    """A track's settings, opened with Enter on its name."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER)
        self.assertIsInstance(self.app.screen, TrackEditor)

    async def test_a_tracks_settings(self):
        await self.select_field(MUTE)
        await self.press(Key.ENTER)
        self.assertTrue(self.track(LEAD).is_muted())
        await self.press(Key.ENTER)
        self.assertFalse(self.track(LEAD).is_muted())
        await self.select_field(TRANSPOSE)
        await self.press(key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET), key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.track(LEAD).get_transpose(), 2)
        await self.select_field(CC_1)
        await self.press(Key.ENTER)
        self.app.screen.value = '74'
        await self.press(Key.ENTER)
        self.assertEqual(self.track(LEAD).get_cc_numbers(), [74, None, None, None])
        await self.press(Key.BACKSPACE)
        self.assertNotIn(TrackSetting.CC, self.track(LEAD).to_data())
        await self.select_field(DRUM)
        await self.press(Key.ENTER)
        self.assertTrue(self.track(LEAD).is_drum())
        self.assertIn(DRUM_TRACK_SHOWN, self.text())
        await self.press(Key.ESCAPE)
        self.assertIn(PatternSetting.DRUM, self.text())
        render_song(self.document.song())

    async def test_a_lane_and_the_velocity_bind_to_registers_and_unbind(self):
        more = key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET)
        await self.select_field(MSG_CC_REGISTER_LABEL.format(number=2))
        await self.press(more, more)
        self.assertEqual(self.track(LEAD).get_cc_registers(), [None, REGISTER_NAMES[1], None, None])
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.track(LEAD).get_cc_registers(), [None] * len(REGISTER_NAMES))
        await self.select_field(MSG_VELOCITY_REGISTER_LABEL)
        await self.press(more)
        self.assertEqual(self.track(LEAD).get_velocity_register(), REGISTER_NAMES[0])
        self.assertEqual(self.track(LEAD).to_data(), {TrackSetting.VELOCITY_REGISTER: REGISTER_NAMES[0]})
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.track(LEAD).get_velocity_register())

    async def test_a_tracks_octave_range_in_the_sets_octave_labels(self):
        song = self.document.song()
        await self.select_field(LOWEST_OCTAVE)
        self.assertIn(str(song.shown_octave(MIN_OCTAVE)), self.text())
        await self.press(key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.track(LEAD).get_lowest_octave(), MIN_OCTAVE + 1)
        await self.select_field(HIGHEST_OCTAVE)
        await self.press(key_of(binding=keybindings.TrackEditor.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.track(LEAD).get_highest_octave(), MAX_OCTAVE - 1)
        # Typed in the set's octave labels, and stored in the file's numbering.
        await self.press(Key.ENTER)
        self.app.screen.value = str(song.shown_octave(TYPED_OCTAVE))
        await self.press(Key.ENTER)
        self.assertEqual(self.track(LEAD).get_highest_octave(), TYPED_OCTAVE)
        # The lowest can't be nudged past the highest.
        await self.select_field(LOWEST_OCTAVE)
        await self.press(*[key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET)] * (MAX_OCTAVE - MIN_OCTAVE))
        self.assertEqual(self.track(LEAD).get_lowest_octave(), TYPED_OCTAVE)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.track(LEAD).get_lowest_octave(), MIN_OCTAVE)
        self.assertEqual(self.track(LEAD).to_data(), {TrackSetting.HIGHEST_OCTAVE: TYPED_OCTAVE})
        render_song(song)

    async def test_the_name_field_renames_the_track_everywhere(self):
        await self.select_field(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = LOW
        await self.press(Key.ENTER)
        self.assertEqual(self.track(LOW).get_transpose(), 0)
        self.assertEqual(self.document.song().get_track_names(), [LOW, DRUMS])
        self.assertIsNotNone(self.document.clip_slot(index=0, track=LOW))
        self.assertIn(MSG_TRACK_CRUMB.format(name=LOW), self.crumbs_line())
        await self.press(Key.ESCAPE)
        self.assertIn(LOW, self.text())

    async def test_a_cc_lane_turns_up_or_down_from_none(self):
        await self.select_field(CC_1)
        await self.press(key_of(binding=keybindings.TrackEditor.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.track(LEAD).get_cc_numbers(), [1, None, None, None])
        await self.select_field(CC_2)
        await self.press(key_of(binding=keybindings.TrackEditor.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.track(LEAD).get_cc_numbers(), [1, 0, None, None])
