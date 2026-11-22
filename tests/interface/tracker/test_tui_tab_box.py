# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tab box of a settings page, on the clip page: the row of tabs the cursor stops on, Left and Right choosing a tab and
stopping at the ends, Tab going to the row, the box keeping its tallest tab's height, and a built-in generator's tab, which
edits the clip's own built-in, marks it on or off and opens its parts on it."""

from llamatron.engine.generators import arp as arp_plugin, chords as chords_plugin
from llamatron.engine.generators.arp import strings as arp_strings
from llamatron.engine.generators.chords import strings as chords_strings
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.arrange.track_editor import TrackEditor
from llamatron.interface.tracker.screens.shared.offsets_editor import OffsetsEditor
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting
from llamatron.user_strings import labels, marks, messages
from tests.support import ui_testing
from tests.support.ui_testing import back_key, forward_key, UITest

FIRST_SCENE = 0


class TestTheTabBoxOnTheClipPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))
        await self.pilot.pause()
        self.page = self.app.screen

    def clip_slot(self):
        return self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD)

    def chosen(self):
        box = self.page.tab_box()
        return box.tabs[self.page.chosen_tab(box)].label

    async def test_basics_is_chosen_first_and_the_tabs_are_in_the_order_they_apply(self):
        box = self.page.tab_box()
        names = [tab.label for tab in box.tabs]
        self.assertEqual(self.chosen(), labels.MSG_BASICS_TAB)
        self.assertLess(names.index(chords_strings.MSG_TAB_LABEL), names.index(labels.MSG_USER_TAB))
        self.assertEqual(names[-2:], [labels.MSG_BYPASS_WHEN_TAB, labels.MSG_SKIP_WHEN_TAB])
        self.assertIn(labels.MSG_BASICS_TAB, self.text())

    async def test_tab_goes_to_the_row_of_tabs_whose_keys_choose_a_tab_and_stop_at_the_ends(self):
        await self.press(keybindings.FieldPage.TO_TABS)
        self.assertEqual(self.page.field().label, labels.MSG_TABS_LABEL)
        await self.press(back_key(keybindings.FieldPage.ALONG_TABS))
        self.assertEqual(self.chosen(), labels.MSG_BASICS_TAB)
        await self.press(Key.RIGHT, forward_key(keybindings.FieldPage.ALONG_TABS))
        self.assertEqual(self.chosen(), arp_strings.MSG_TAB_LABEL)
        await self.press(*[Key.RIGHT] * len(self.page.tab_box().tabs))
        self.assertEqual(self.chosen(), labels.MSG_SKIP_WHEN_TAB)

    async def test_the_box_keeps_its_height_whichever_tab_is_chosen(self):
        heights = set()
        await self.press(keybindings.FieldPage.TO_TABS)
        for _ in self.page.tab_box().tabs:
            heights.add(len(self.text().splitlines()))
            await self.press(Key.RIGHT)
        self.assertEqual(len(heights), 1)

    async def test_a_field_in_another_tab_is_reached_by_choosing_its_tab(self):
        await self.select_field(labels.MSG_REPEAT_LABEL)
        await self.select_field(labels.MSG_SET_REGISTER_LABEL.format(name=file_format.REGISTER_NAMES[0]))
        self.assertEqual(self.chosen(), labels.MSG_REGISTERS_TAB)

    async def test_a_built_in_tab_switches_the_clips_own_on_and_marks_its_tab(self):
        chords = marks.MSG_TAB_WITH_MARK.format(name=chords_strings.MSG_TAB_LABEL, mark=marks.MSG_FIELD_TOGGLE_OFF)
        self.assertIn(chords, self.text())
        await self.press(keybindings.FieldPage.TO_TABS, Key.RIGHT, Key.DOWN)
        self.assertEqual(self.page.field().label, labels.MSG_ENABLED_LABEL)
        await self.press(Key.SPACE)
        self.assertEqual(self.clip_slot().to_data()[ClipSlotSetting.BUILT_IN], {chords_plugin.NAME: {file_format.GENERATOR_ENABLED: True}})
        self.assertIn(marks.MSG_TAB_WITH_MARK.format(name=chords_strings.MSG_TAB_LABEL, mark=marks.MSG_TOGGLE_ON), self.text())
        await self.press(Key.SPACE)
        self.assertNotIn(ClipSlotSetting.BUILT_IN, self.clip_slot().to_data())

    async def test_a_built_in_tabs_part_opens_its_page_on_the_clips_own(self):
        await self.select_field(labels.MSG_OFFSETS_LABEL)
        self.assertEqual(self.chosen(), arp_strings.MSG_TAB_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OffsetsEditor)
        self.assertIsNotNone(self.clip_slot().get_built_in(arp_plugin.NAME).get_offsets())
        self.assertIn(labels.MSG_BUILT_IN_WORD, self.text())


class TestWhatOverridesWhat(UITest):
    """A clip's built-in tab says when it overrides its track's, both being on, and a track's names the clips overriding it."""

    async def test_the_clips_and_the_tracks_tabs_say_which_stands_in_for_which(self):
        track = self.document.song().get_track(ui_testing.LEAD)
        clip_slot = self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD)
        word = chords_strings.MSG_TAB_LABEL.lower()
        self.document.change_set(track.set_built_in_setting, kind=chords_plugin.NAME, name=file_format.GENERATOR_ENABLED, value=True)
        self.document.change_set(clip_slot.set_built_in_setting, kind=chords_plugin.NAME, name=file_format.GENERATOR_ENABLED, value=True)
        self.app.chosen_tabs[ClipPage.__name__] = chords_strings.MSG_TAB_LABEL
        self.app.chosen_tabs[TrackEditor.__name__] = chords_strings.MSG_TAB_LABEL
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))
        await self.pilot.pause()
        self.assertIn(messages.MSG_BUILT_IN_OVERRIDES_TRACKS.format(word=word), self.text())
        self.app.screen.show_page(TrackEditor(holder=self.app.screen.holder, name=ui_testing.LEAD))
        await self.pilot.pause()
        scene = self.document.song().get_scenes()[FIRST_SCENE].get_name()
        clip = messages.MSG_BUILT_IN_OVERRIDING_CLIP.format(scene=scene, track=ui_testing.LEAD)
        self.assertIn(messages.MSG_BUILT_IN_OVERRIDDEN_ONCE.format(word=word, clips=clip), self.text())
