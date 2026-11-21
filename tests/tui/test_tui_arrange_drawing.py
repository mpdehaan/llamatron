# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What draws the Arrange page (tui/screens/arrange/arrange_drawing.py): a clip's text with its marks, and the grid's lines.

The page's own tests, in test_tui_arrange.py, check the grid as a person sees it. These check the
drawing on its own: what a clip says on the grid, how many lines the grid takes, and that the page
shows what the drawing drew.
"""

import unittest

from llamatron.composition import defaults
from llamatron.composition.file_format import ClipSlotSetting, Direction
from llamatron.tui import drawing, keybindings
from llamatron.tui.components import length_bar
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange import arrange_drawing
from llamatron.tui.screens.arrange.arrange_drawing import ArrangeDrawing, clip_text
from llamatron.tui.screens.arrange.arrange_page import ArrangePage
from llamatron.user_strings import marks, names
from tests.support import ui_testing
from tests.support.ui_testing import a_song, UITest

FIRST_SCENE = 0
SOME_REPEATS = 4
A_CLIP_NAME = 'the part that comes back'
# Scenes enough that they can't all fit on the test's screen.
MANY_SCENES = 30
# The number the first scene added by a test takes, well past the ones a song starts with.
FIRST_NEW_SCENE = 100


class TestCellText(unittest.TestCase):
    """What a clip says on the grid: its name, then a mark for each thing beyond its pattern."""

    def setUp(self):
        self.document = a_song()

    def clip_slot(self):
        return self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD)

    def set(self, *, setting, value):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=setting, value=value)

    def test_a_plain_clip_is_its_patterns_name(self):
        self.assertEqual(clip_text(self.clip_slot()), ui_testing.TUNE)

    def test_a_clip_with_a_name_of_its_own_shows_that_name(self):
        self.set(setting=ClipSlotSetting.NAME, value=A_CLIP_NAME)
        self.assertEqual(clip_text(self.clip_slot()), A_CLIP_NAME)

    def test_each_setting_beyond_the_pattern_adds_its_mark(self):
        for setting, value, mark in (
            (ClipSlotSetting.DIRECTION, Direction.REVERSE_A, marks.MSG_DIRECTION_MARK),
            (ClipSlotSetting.GRAB_TRACK, ui_testing.DRUMS, marks.MSG_GRAB_MARK),
            (ClipSlotSetting.LOOP, True, marks.MSG_LOOP_MARK),
        ):
            with self.subTest(setting=setting):
                self.setUp()
                self.set(setting=setting, value=value)
                self.assertEqual(clip_text(self.clip_slot()), marks.MSG_CLIP_WITH_MARKS.format(name=ui_testing.TUNE, marks=mark))

    def test_repeats_say_how_many_and_a_morph_adds_its_mark(self):
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=SOME_REPEATS)
        repeats = marks.MSG_REPEAT_MARK.format(repeat=SOME_REPEATS)
        self.assertEqual(clip_text(self.clip_slot()), marks.MSG_CLIP_WITH_MARKS.format(name=ui_testing.TUNE, marks=repeats))
        self.document.set_clip_slot_morph_target(index=FIRST_SCENE, track=ui_testing.LEAD, pattern=ui_testing.OTHER)
        self.assertEqual(clip_text(self.clip_slot()), marks.MSG_CLIP_WITH_MARKS.format(name=ui_testing.TUNE, marks=marks.MSG_MORPH_MARK + repeats))

    def test_one_repeat_is_no_mark(self):
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=defaults.DEFAULT_REPEAT)
        self.assertEqual(clip_text(self.clip_slot()), ui_testing.TUNE)

    def test_a_long_name_gives_way_so_that_the_marks_fit_the_cell(self):
        self.set(setting=ClipSlotSetting.NAME, value=A_CLIP_NAME)
        self.set(setting=ClipSlotSetting.LOOP, value=True)
        text = clip_text(self.clip_slot())
        self.assertTrue(text.endswith(marks.MSG_LOOP_MARK))
        self.assertLess(len(text), arrange_drawing.CELL_WIDTH)
        self.assertTrue(A_CLIP_NAME.startswith(text[:-len(marks.MSG_LOOP_MARK)].strip().rstrip(drawing.ELLIPSIS)))


class TestArrangeDrawing(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE)
        self.page = self.app.screen
        self.assertIsInstance(self.page, ArrangePage)

    def drawn(self):
        """Return the lines the drawing draws on the test's screen."""
        width, height = self.SIZE
        return self.page.drawing.body(width=width, height=height)

    async def test_the_page_draws_with_its_drawing(self):
        self.assertIsInstance(self.page.drawing, ArrangeDrawing)
        width, height = self.SIZE
        self.assertEqual([line.plain for line in self.page.body(width=width, height=height)], [line.plain for line in self.drawn()])

    async def test_the_grid_is_the_header_three_lines_a_scene_and_the_footer(self):
        scenes = len(self.document.song().get_scenes())
        self.assertEqual(len(self.drawn()), arrange_drawing.HEADER_LINES + scenes * arrange_drawing.SCENE_LINES + arrange_drawing.FOOTER_LINES)

    async def test_only_the_scenes_that_fit_are_drawn_and_the_cursors_scene_is_among_them(self):
        for number in range(MANY_SCENES):
            self.document.add_scene(index=len(self.document.song().get_scenes()), name=names.MSG_NEW_SCENE_NAME.format(number=number + FIRST_NEW_SCENE))
        self.document.record_edit()
        width, height = self.SIZE
        shown = self.page.drawing.visible_scenes(height)
        self.assertLess(len(shown), MANY_SCENES)
        self.assertEqual(len(self.drawn()), arrange_drawing.HEADER_LINES + len(shown) * arrange_drawing.SCENE_LINES + arrange_drawing.FOOTER_LINES)
        for _ in range(MANY_SCENES):
            self.press_at_once(Key.DOWN)
        self.assertIn(self.page.row, self.page.drawing.visible_scenes(height))

    async def test_the_frame_is_drawn_around_what_the_cursor_is_on_and_nowhere_when_that_is_off_screen(self):
        width, height = self.SIZE
        first, last = self.page.drawing.visible_tracks(width)
        shown = self.page.drawing.visible_scenes(height)
        self.assertIsNotNone(self.page.drawing.frame_place(shown=shown, first=first, last=last))
        self.assertIsNone(self.page.drawing.frame_place(shown=range(self.page.row + 1, self.page.row + 1), first=first, last=last))


if __name__ == '__main__':
    unittest.main()


class TestClipBar(UITest):
    """A clip's length bar on its own: its seconds against the scene's play, full for a looping clip, and a read head while the clip plays."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE)
        self.lengths = self.document.lengths()

    def bar_for(self, *, track, played=None):
        clip_slot = self.document.clip_slot(index=FIRST_SCENE, track=track)
        return ArrangeDrawing.clip_bar(arrange_drawing.CLIP_BAR, lengths=self.lengths, clip_slot=clip_slot, index=FIRST_SCENE, track=track, played=played)

    def test_a_clip_that_is_not_playing_is_drawn_as_its_length_and_a_looping_clip_full(self):
        self.assertTrue(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.DRUMS).loops())
        self.assertEqual(self.bar_for(track=ui_testing.DRUMS), arrange_drawing.CLIP_BAR.full())
        self.assertEqual(self.bar_for(track=ui_testing.LEAD), arrange_drawing.CLIP_BAR.draw(amount=self.lengths.clip_seconds(index=FIRST_SCENE, track=ui_testing.LEAD), total=self.lengths.scene_play_seconds(FIRST_SCENE)))
        self.assertNotIn(length_bar.TO_PLAY, self.bar_for(track=ui_testing.LEAD))

    def test_a_playing_clips_bar_fills_from_the_left_as_it_plays_and_a_looping_clips_over_one_play_of_the_scene(self):
        scene_seconds = self.lengths.scene_play_seconds(FIRST_SCENE)
        half_way = self.bar_for(track=ui_testing.LEAD, played=scene_seconds / 2)
        self.assertIn(length_bar.TO_PLAY, half_way)
        self.assertTrue(half_way.index(length_bar.TO_PLAY) > 0)
        self.assertEqual(self.bar_for(track=ui_testing.LEAD, played=scene_seconds), self.bar_for(track=ui_testing.LEAD))
        looping = self.bar_for(track=ui_testing.DRUMS, played=scene_seconds / 2)
        self.assertIn(length_bar.TO_PLAY, looping)
        self.assertEqual(len(looping), len(arrange_drawing.CLIP_BAR.full()))
        self.assertEqual(self.bar_for(track=ui_testing.DRUMS, played=0.0), length_bar.TO_PLAY * len(arrange_drawing.CLIP_BAR.full()))
