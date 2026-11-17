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

"""The tracker's Follow Chords pages: the list of them and the editor, whose Chords from picks a track of the current song."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import FollowChordsSetting
from llamatron.strings.labels import MSG_CHORDS_FROM_LABEL
from llamatron.strings.marks import MSG_NONE_SHOWN
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.follow_chords_editor import FollowChordsEditor
from tests.support.ui_testing import DRUMS, FOLLOWS, LEAD, UITest

NEW_ONE = 'harmony'
GONE = 'nobody'


class TestFollowChordsAdded(UITest):

    async def test_a_new_one_follows_no_track(self):
        name = await self.add_generator(Section.FOLLOW_CHORDS)
        self.assertIsNone(self.document.song().get_generator_settings(kind=GeneratorKind.FOLLOW_CHORDS, name=name).get_chords_from())


class TestFollowChordsEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.FOLLOW_CHORDS)
        self.assertIsInstance(self.app.screen, FollowChordsEditor)
        await self.select_field(MSG_CHORDS_FROM_LABEL)

    def followed(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.FOLLOW_CHORDS, name=FOLLOWS).get_chords_from()

    async def test_the_track_is_picked_from_the_songs_tracks_with_none_first(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [MSG_NONE_SHOWN, DRUMS, LEAD])
        await self.press(Key.UP, Key.ENTER)
        self.assertEqual(self.followed(), DRUMS)
        await self.press(keybindings.FollowChordsEditor.CLEAR)
        self.assertIsNone(self.followed())

    async def test_renaming_the_track_followed_renames_it_here(self):
        self.document.rename_named(section=Section.TRACKS, old=LEAD, new=NEW_ONE)
        self.assertEqual(self.followed(), NEW_ONE)

    async def test_a_track_the_song_lacks_is_still_offered_so_that_it_is_kept(self):
        self.document.set_generator_setting(section=Section.FOLLOW_CHORDS, name=FOLLOWS, setting=FollowChordsSetting.CHORDS_FROM, value=GONE)
        self.app.screen.draw()
        await self.press(Key.ENTER)
        self.assertIn(GONE, self.app.screen.options)
