# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Hocket pages: the list of hockets and the editor, whose Source track picks a track of the current song."""

from llamatron.engine.generators import hocket as hocket_plugin
from llamatron.engine.generators.hocket.model import HocketSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

NEW_ONE = 'swap'
GONE = 'nobody'


class TestHocketAdded(UITest):

    async def test_a_new_one_has_no_source(self):
        name = await self.add_generator(hocket_plugin.SECTION)
        self.assertIsNone(self.document.get_setlist().get_generator_settings(kind=hocket_plugin.NAME, name=name).get_source())


class TestHocketEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=hocket_plugin.SECTION)
        self.assertIsInstance(self.app.screen, PluginEditor)
        await self.select_field(labels.MSG_SOURCE_TRACK_LABEL)

    def source(self):
        return self.document.get_setlist().get_generator_settings(kind=hocket_plugin.NAME, name=ui_testing.TRADE).get_source()

    async def test_the_source_is_picked_from_the_songs_tracks_with_none_first(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [marks.MSG_NONE_SHOWN, ui_testing.DRUMS, ui_testing.LEAD])
        await self.press(Key.UP, Key.ENTER)
        self.assertEqual(self.source(), ui_testing.DRUMS)
        await self.press(keybindings.PluginEditor.CLEAR)
        self.assertIsNone(self.source())

    async def test_renaming_the_source_track_renames_the_source(self):
        self.document.rename_named(section=Section.TRACKS, old=ui_testing.LEAD, new=NEW_ONE)
        self.assertEqual(self.source(), NEW_ONE)

    async def test_a_source_the_song_lacks_is_still_offered_so_that_it_is_kept(self):
        self.document.change_set(self.document.generator(section=hocket_plugin.SECTION, name=ui_testing.TRADE).set_setting, name=HocketSetting.SOURCE, value=GONE)
        self.app.screen.draw()
        await self.press(Key.ENTER)
        self.assertIn(GONE, self.app.screen.options)
