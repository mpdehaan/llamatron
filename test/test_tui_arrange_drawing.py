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
"""What draws the Arrange page (tui/screens/arrange_drawing.py): a clip's text with its marks, and the grid's lines.

The page's own tests, in test_tui_arrange.py, check the grid as a person sees it. These check the
drawing on its own: what a clip says on the grid, how many lines the grid takes, and that the page
shows what the drawing drew.
"""

import unittest

from ui_testing import DRUMS, LEAD, OTHER, TUNE, UITest, a_song
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import ClipSlotSetting, Direction
from llamatron.strings.names import MSG_NEW_SCENE_NAME
from llamatron.strings.marks import MSG_CLIP_WITH_MARKS, MSG_DIRECTION_MARK, MSG_GRAB_MARK, MSG_LOOP_MARK, MSG_MORPH_MARK, MSG_REPEAT_MARK
from llamatron.tui import keybindings
from llamatron.tui.drawing import ELLIPSIS
from llamatron.tui.keys import Key
from llamatron.tui.components.length_bar import TO_PLAY
from llamatron.tui.screens.arrange_drawing import ArrangeDrawing, CELL_WIDTH, CLIP_BAR, FOOTER_LINES, HEADER_LINES, SCENE_LINES, clip_text
from llamatron.tui.screens.arrange_page import ArrangePage

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
        return self.document.clip_slot(index=FIRST_SCENE, track=LEAD)

    def set(self, *, setting, value):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=setting, value=value)

    def test_a_plain_clip_is_its_patterns_name(self):
        self.assertEqual(clip_text(self.clip_slot()), TUNE)

    def test_a_clip_with_a_name_of_its_own_shows_that_name(self):
        self.set(setting=ClipSlotSetting.NAME, value=A_CLIP_NAME)
        self.assertEqual(clip_text(self.clip_slot()), A_CLIP_NAME)

    def test_each_setting_beyond_the_pattern_adds_its_mark(self):
        for setting, value, mark in (
            (ClipSlotSetting.DIRECTION, Direction.REVERSE_A, MSG_DIRECTION_MARK),
            (ClipSlotSetting.GRAB_TRACK, DRUMS, MSG_GRAB_MARK),
            (ClipSlotSetting.LOOP, True, MSG_LOOP_MARK),
        ):
            with self.subTest(setting=setting):
                self.setUp()
                self.set(setting=setting, value=value)
                self.assertEqual(clip_text(self.clip_slot()), MSG_CLIP_WITH_MARKS.format(name=TUNE, marks=mark))

    def test_repeats_say_how_many_and_a_morph_adds_its_mark(self):
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=LEAD, repeat=SOME_REPEATS)
        repeats = MSG_REPEAT_MARK.format(repeat=SOME_REPEATS)
        self.assertEqual(clip_text(self.clip_slot()), MSG_CLIP_WITH_MARKS.format(name=TUNE, marks=repeats))
        self.document.set_clip_slot_morph_target(index=FIRST_SCENE, track=LEAD, pattern=OTHER)
        self.assertEqual(clip_text(self.clip_slot()), MSG_CLIP_WITH_MARKS.format(name=TUNE, marks=MSG_MORPH_MARK + repeats))

    def test_one_repeat_is_no_mark(self):
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=LEAD, repeat=DEFAULT_REPEAT)
        self.assertEqual(clip_text(self.clip_slot()), TUNE)

    def test_a_long_name_gives_way_so_that_the_marks_fit_the_cell(self):
        self.set(setting=ClipSlotSetting.NAME, value=A_CLIP_NAME)
        self.set(setting=ClipSlotSetting.LOOP, value=True)
        text = clip_text(self.clip_slot())
        self.assertTrue(text.endswith(MSG_LOOP_MARK))
        self.assertLess(len(text), CELL_WIDTH)
        self.assertTrue(A_CLIP_NAME.startswith(text[:-len(MSG_LOOP_MARK)].strip().rstrip(ELLIPSIS)))


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
        self.assertEqual(len(self.drawn()), HEADER_LINES + scenes * SCENE_LINES + FOOTER_LINES)

    async def test_only_the_scenes_that_fit_are_drawn_and_the_cursors_scene_is_among_them(self):
        for number in range(MANY_SCENES):
            self.document.add_scene(index=len(self.document.song().get_scenes()), name=MSG_NEW_SCENE_NAME.format(number=number + FIRST_NEW_SCENE))
        self.document.record_edit()
        width, height = self.SIZE
        shown = self.page.drawing.visible_scenes(height)
        self.assertLess(len(shown), MANY_SCENES)
        self.assertEqual(len(self.drawn()), HEADER_LINES + len(shown) * SCENE_LINES + FOOTER_LINES)
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
        return ArrangeDrawing.clip_bar(CLIP_BAR, lengths=self.lengths, clip_slot=clip_slot, index=FIRST_SCENE, track=track, played=played)

    def test_a_clip_that_is_not_playing_is_drawn_as_its_length_and_a_looping_clip_full(self):
        self.assertTrue(self.document.clip_slot(index=FIRST_SCENE, track=DRUMS).loops())
        self.assertEqual(self.bar_for(track=DRUMS), CLIP_BAR.full())
        self.assertEqual(self.bar_for(track=LEAD), CLIP_BAR.draw(amount=self.lengths.clip_seconds(index=FIRST_SCENE, track=LEAD), total=self.lengths.scene_play_seconds(FIRST_SCENE)))
        self.assertNotIn(TO_PLAY, self.bar_for(track=LEAD))

    def test_a_playing_clips_bar_fills_from_the_left_as_it_plays_and_a_looping_clips_over_one_play_of_the_scene(self):
        scene_seconds = self.lengths.scene_play_seconds(FIRST_SCENE)
        half_way = self.bar_for(track=LEAD, played=scene_seconds / 2)
        self.assertIn(TO_PLAY, half_way)
        self.assertTrue(half_way.index(TO_PLAY) > 0)
        self.assertEqual(self.bar_for(track=LEAD, played=scene_seconds), self.bar_for(track=LEAD))
        looping = self.bar_for(track=DRUMS, played=scene_seconds / 2)
        self.assertIn(TO_PLAY, looping)
        self.assertEqual(len(looping), len(CLIP_BAR.full()))
        self.assertEqual(self.bar_for(track=DRUMS, played=0.0), TO_PLAY * len(CLIP_BAR.full()))
