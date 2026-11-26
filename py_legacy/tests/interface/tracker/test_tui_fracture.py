# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of Fracture on Arrange: after a question, every clip of the song gets a pattern of its own.

The song has two scenes and two tracks. The lead plays the tune in both scenes and the drums
play the tune in the second, so the tune is shared by three clips, and the beat by one.
"""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.model.schema.file_format import ClipSlotSetting
from llamatron.user_strings import messages
from tests.support import ui_testing
from tests.support.ui_testing import UITest

LEAD = 'lead'
DRUMS = 'drums'
FIRST = 0
SECOND = 1
TUNE_2 = 'tune-2'
TUNE_3 = 'tune-3'
OTHER_2 = 'other-2'
COPIES = 2
CHANGED_STEPS = 8


class TestFracture(UITest):
    """The key on Arrange, its question, and what yes and no leave."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_clip_slot(index=SECOND, track=LEAD, pattern=ui_testing.TUNE)
        self.document.add_clip_slot(index=SECOND, track=DRUMS, pattern=ui_testing.TUNE)
        self.document.record_edit()
        await self.press(keybindings.MainPage.ARRANGE)

    def patterns_played(self):
        """Return the pattern each clip plays, scene by scene and track by track."""
        song = self.document.song()
        return [scene.get_clip_slot(track).get_pattern_name() for scene in song.get_scenes() for track in song.get_track_names() if scene.has_clip_slot(track)]

    async def test_the_key_asks_first_and_no_changes_nothing(self):
        await self.press(keybindings.ArrangePage.FRACTURE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_FRACTURE_TITLE, self.text())
        await self.press(ui_testing.ANSWER_NO)
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertEqual(self.patterns_played(), [ui_testing.TUNE, ui_testing.BEAT, ui_testing.TUNE, ui_testing.TUNE])

    async def test_yes_gives_every_clip_a_pattern_of_its_own_numbered_from_the_first(self):
        await self.press(keybindings.ArrangePage.FRACTURE, *ui_testing.ANSWER_YES)
        self.assertEqual(self.patterns_played(), [ui_testing.TUNE, ui_testing.BEAT, TUNE_2, TUNE_3])
        self.assertIn(messages.MSG_FRACTURED.format(count=COPIES), self.text())
        setlist = self.document.get_setlist()
        # A copy holds what the pattern held, in the pattern's group, and is a pattern apart.
        self.assertEqual(setlist.get_pattern(TUNE_2).get_group(), setlist.get_pattern(ui_testing.TUNE).get_group())
        self.assertEqual(setlist.get_pattern(TUNE_3).get_steps(), setlist.get_pattern(ui_testing.TUNE).get_steps())
        setlist.get_pattern(TUNE_2).set_steps(CHANGED_STEPS)
        self.assertNotEqual(setlist.get_pattern(ui_testing.TUNE).get_steps(), CHANGED_STEPS)

    async def test_a_pattern_a_clip_names_twice_in_its_own_list_stays_one_pattern(self):
        self.document.set_clip_slot_setting(index=SECOND, track=LEAD, setting=ClipSlotSetting.PATTERNS, value=[ui_testing.TUNE, ui_testing.OTHER, ui_testing.TUNE])
        self.document.set_clip_slot_setting(index=SECOND, track=DRUMS, setting=ClipSlotSetting.PATTERNS, value=[ui_testing.OTHER, ui_testing.TUNE])
        self.document.record_edit()
        await self.press(keybindings.ArrangePage.FRACTURE, *ui_testing.ANSWER_YES)
        scene = self.document.song().get_scenes()[SECOND]
        # The first scene's clip keeps the pattern; a later clip plays a copy, the same copy each time its own list names the pattern.
        self.assertEqual(scene.get_clip_slot(LEAD).get_pattern_names(), [TUNE_2, ui_testing.OTHER, TUNE_2])
        self.assertEqual(scene.get_clip_slot(DRUMS).get_pattern_names(), [OTHER_2, TUNE_3])

    async def test_a_song_with_nothing_shared_says_so(self):
        await self.press(keybindings.ArrangePage.FRACTURE, *ui_testing.ANSWER_YES)
        before = self.patterns_played()
        await self.press(keybindings.ArrangePage.FRACTURE, *ui_testing.ANSWER_YES)
        self.assertEqual(self.patterns_played(), before)
        self.assertIn(messages.MSG_NOTHING_TO_FRACTURE, self.text())

    async def test_one_undo_puts_every_clip_back_on_the_shared_pattern(self):
        names = self.document.get_setlist().get_pattern_names()
        await self.press(keybindings.ArrangePage.FRACTURE, *ui_testing.ANSWER_YES)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.patterns_played(), [ui_testing.TUNE, ui_testing.BEAT, ui_testing.TUNE, ui_testing.TUNE])
        self.assertEqual(self.document.get_setlist().get_pattern_names(), names)
        await self.press(keybindings.Page.REDO)
        self.assertEqual(self.patterns_played(), [ui_testing.TUNE, ui_testing.BEAT, TUNE_2, TUNE_3])
