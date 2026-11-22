# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tab box of a settings page, on the clip page: the row of tabs the cursor stops on, Left and Right choosing a tab and
stopping at the ends, Tab going to the row, the box keeping its tallest tab's height with a blank line under it, the arrows
inside the box, the grid of a table of statements, and a built-in generator's tab, which edits the clip's own built-in, marks it
on or off and opens its parts on it."""

from llamatron.engine.generators import arp as arp_plugin, chords as chords_plugin
from llamatron.engine.generators.arp import strings as arp_strings
from llamatron.engine.generators.chords import strings as chords_strings
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.drawing import Box
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.arrange.track_editor import TrackEditor
from llamatron.interface.tracker.screens.shared import statements, tab_box
from llamatron.interface.tracker.screens.shared.offsets_editor import OffsetsEditor
from llamatron.model.objects import conditions
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting, Operator
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


class TestTheArrowsInTheTabBox(UITest):
    """Inside the tab box, on the clip page's Basics tab: Left and Right go to the field beside in the next column and change
    nothing, Down keeps to a column and leaves the box at its foot, and Up from under the box comes in at the first column's foot."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))
        await self.pilot.pause()
        self.page = self.app.screen

    def under_cursor(self):
        return self.page.field().label

    async def test_left_and_right_go_across_the_columns_to_the_nearest_field_and_change_nothing(self):
        await self.select_field(labels.MSG_REPEAT_LABEL)
        before = self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).to_data()
        await self.press(Key.RIGHT)
        self.assertEqual(self.under_cursor(), labels.MSG_GRAB_TRACK_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.under_cursor(), labels.MSG_GRAB_TRACK_LABEL)
        await self.press(Key.LEFT)
        self.assertEqual(self.under_cursor(), labels.MSG_REPEAT_LABEL)
        await self.press(Key.LEFT)
        self.assertEqual(self.under_cursor(), labels.MSG_REPEAT_LABEL)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).to_data(), before)

    async def test_the_shorter_columns_last_field_is_the_nearest_from_further_down(self):
        await self.select_field(labels.MSG_FOLLOW_ACTION_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.under_cursor(), labels.MSG_GRAB_TRACK_LABEL)

    async def test_down_at_a_columns_foot_leaves_the_box_and_up_comes_back_at_the_first_columns_foot(self):
        await self.select_field(labels.MSG_GRAB_TRACK_LABEL)
        await self.press(Key.DOWN)
        self.assertEqual(self.page.cursor.get_place(), self.page.first_button_place())
        await self.press(Key.UP)
        self.assertEqual(self.under_cursor(), labels.MSG_FOLLOW_ACTION_LABEL)
        await self.press(Key.DOWN)
        self.assertEqual(self.page.cursor.get_place(), self.page.first_button_place())

    async def test_up_at_a_columns_head_goes_to_the_row_of_tabs(self):
        await self.select_field(labels.MSG_SCALE_LABEL)
        await self.press(Key.UP)
        self.assertEqual(self.under_cursor(), labels.MSG_TABS_LABEL)


class TestTheBoxesLook(UITest):
    """The box leaves a blank line under its tallest tab's last line, and a table of statements is a grid that keeps its size
    whatever its lines hold."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))
        await self.pilot.pause()
        self.page = self.app.screen

    def lines_in_the_box(self):
        lines = self.text().splitlines()
        tabs_tops = next(place for place, line in enumerate(lines) if line.startswith(Box.TOP_LEFT))
        bottom = next(place for place, line in enumerate(lines) if line.startswith(Box.BOTTOM_LEFT))
        return lines[tabs_tops + tab_box.TAB_ROW_LINES:bottom]

    def inside_of_the_box(self):
        return [line.strip(Box.BAR + drawing.SPACE) for line in self.lines_in_the_box()]

    def bars_in_the_box(self):
        """Return where each line inside the box has a bar, the box's own sides among them."""
        return [[place for place, character in enumerate(line) if character == Box.BAR] for line in self.lines_in_the_box()]

    async def show_the_clip(self):
        self.app.screen.show_page(ClipPage(holder=self.app.screen.holder, index=FIRST_SCENE, track=ui_testing.LEAD))
        await self.pilot.pause()

    async def test_the_tallest_tab_ends_with_a_blank_line(self):
        await self.press(keybindings.FieldPage.TO_TABS)
        lasts = []
        for _ in self.page.tab_box().tabs:
            inside = self.inside_of_the_box()
            lasts.append(next(place for place in reversed(range(len(inside))) if inside[place]))
            self.assertEqual(inside[-1], drawing.NOTHING)
            await self.press(Key.RIGHT)
        self.assertEqual(max(lasts), len(inside) - 2)

    async def test_the_statements_are_a_grid_that_keeps_its_size(self):
        self.app.chosen_tabs[ClipPage.__name__] = labels.MSG_BYPASS_WHEN_TAB
        await self.show_the_clip()
        empty = self.inside_of_the_box()
        bars = self.bars_in_the_box()
        top = next(line for line in empty if line.startswith(Box.TOP_LEFT))
        self.assertEqual(top.count(Box.TOP_TEE), statements.COLUMNS - 1)
        self.assertEqual(sum(line.startswith(Box.BOTTOM_LEFT) for line in empty), 1)
        clip_slot = self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD)
        summing = conditions.with_operator(statement=conditions.new_statement(file_format.REGISTER_NAMES[0]), operator=Operator.REMAINDER)
        self.document.change_set(clip_slot.set_statement, name=ClipSlotSetting.BYPASS_WHEN, place=0, statement=summing)
        await self.show_the_clip()
        self.assertEqual(self.bars_in_the_box(), bars)
        self.assertIn(Operator.REMAINDER, self.text())


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
