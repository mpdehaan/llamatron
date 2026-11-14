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
"""The tracker's Hocket pages: the list of hockets and the editor, whose Source track picks a track of the current song."""

from ui_testing import DRUMS, LEAD, TRADE, UITest
from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import HocketSetting
from llamatron.strings.labels import MSG_SOURCE_TRACK_LABEL
from llamatron.strings.marks import MSG_NONE_SHOWN
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.hocket_editor import HocketEditor

NEW_ONE = 'swap'
GONE = 'nobody'


class TestHocketAdded(UITest):

    async def test_a_new_one_has_no_source(self):
        name = await self.add_generator(Section.HOCKETS)
        self.assertIsNone(self.document.song().get_generator_settings(kind=GeneratorKind.HOCKET, name=name).get_source())


class TestHocketEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.HOCKETS)
        self.assertIsInstance(self.app.screen, HocketEditor)
        await self.select_field(MSG_SOURCE_TRACK_LABEL)

    def source(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.HOCKET, name=TRADE).get_source()

    async def test_the_source_is_picked_from_the_songs_tracks_with_none_first(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [MSG_NONE_SHOWN, DRUMS, LEAD])
        await self.press(Key.UP, Key.ENTER)
        self.assertEqual(self.source(), DRUMS)
        await self.press(keybindings.HocketEditor.CLEAR)
        self.assertIsNone(self.source())

    async def test_renaming_the_source_track_renames_the_source(self):
        self.document.rename_named(section=Section.TRACKS, old=LEAD, new=NEW_ONE)
        self.assertEqual(self.source(), NEW_ONE)

    async def test_a_source_the_song_lacks_is_still_offered_so_that_it_is_kept(self):
        self.document.set_generator_setting(section=Section.HOCKETS, name=TRADE, setting=HocketSetting.SOURCE, value=GONE)
        self.app.screen.draw()
        await self.press(Key.ENTER)
        self.assertIn(GONE, self.app.screen.options)
