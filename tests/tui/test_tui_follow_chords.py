# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The tracker's Follow Chords pages: the list of them and the editor, whose Chords from picks a track of the current song."""

from llamatron.model.objects.generator_settings import FollowChordsSetting
from llamatron.model.schema.file_format import GeneratorKind, Section
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.follow_chords_editor import FollowChordsEditor
from llamatron.user_strings import labels, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

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
        await self.select_field(labels.MSG_CHORDS_FROM_LABEL)

    def followed(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.FOLLOW_CHORDS, name=ui_testing.FOLLOWS).get_chords_from()

    async def test_the_track_is_picked_from_the_songs_tracks_with_none_first(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [marks.MSG_NONE_SHOWN, ui_testing.DRUMS, ui_testing.LEAD])
        await self.press(Key.UP, Key.ENTER)
        self.assertEqual(self.followed(), ui_testing.DRUMS)
        await self.press(keybindings.FollowChordsEditor.CLEAR)
        self.assertIsNone(self.followed())

    async def test_renaming_the_track_followed_renames_it_here(self):
        self.document.rename_named(section=Section.TRACKS, old=ui_testing.LEAD, new=NEW_ONE)
        self.assertEqual(self.followed(), NEW_ONE)

    async def test_a_track_the_song_lacks_is_still_offered_so_that_it_is_kept(self):
        self.document.change(self.document.generator(section=Section.FOLLOW_CHORDS, name=ui_testing.FOLLOWS).set_setting, name=FollowChordsSetting.CHORDS_FROM, value=GONE)
        self.app.screen.draw()
        await self.press(Key.ENTER)
        self.assertIn(GONE, self.app.screen.options)
