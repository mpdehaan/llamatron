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

"""The Arrange page, the scene and clip pages, grabs and the Registers page."""

from ui_testing import KEY_SHOWN, UITest, fixed_text, back_key, forward_key, key_of, key_name
from llamatron.composition.defaults import DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REPEAT
from llamatron.composition.file_format import (
    AT_LIMITS,
    REGISTER_ADD_ROWS,
    FOLLOW_ACTION_CHOICES,
    FollowAction,
    ClipSlotSetting,
    Direction,
    REGISTER_NAMES,
    RegisterName,
    RegisterSetting,
    Row,
    Section,
)
from llamatron.generators.blend import BlendMode
from llamatron.tui.screens.arrange_drawing import CELL_WIDTH, CLIP_BAR, SCENE_BAR, SCENE_BAR_COLUMN, SCENE_WIDTH
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.drawing import Box, NOTHING, SPACE, Style
from llamatron.tui.screens.chain_list_page import ChainListPage
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.scene_page import ScenePage
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.tui.document import Document
from llamatron.tui.keys import Key, SHIFT_LEFT_RIGHT, SHIFT_UP_DOWN
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.registers_page import RegistersPage
from llamatron.strings.errors import ERR_LAST_SCENE_SHOWN, ERR_LAST_TRACK_SHOWN, ERR_LOOP_SCENES_INTRO, ERR_OUT_OF_ORDER
from llamatron.strings.labels import MSG_SCALE_LABEL as CLIP_SCALE_LABEL
from llamatron.strings.labels import (
    MSG_CHAINS_LABEL,
    MSG_FOLLOW_ACTION_LABEL, MSG_FOLLOW_ACTION_NAMES, MSG_CLIP_CRUMB, MSG_NAME_LABEL, MSG_SCENE_CRUMB, MSG_REGISTER_FIELD_LABEL, MSG_REGISTER_NUMBER_FIELDS, MSG_RESET_LABEL,
    MSG_REGISTER_AT_LIMIT_FIELD, MSG_REGISTER_RESET_EACH_SCENE_FIELD, MSG_REGISTER_ALLOWED_INC_MAX_FIELD, MSG_AT_LIMIT_NAMES, Crumb, MSG_PATTERN_CRUMB, MSG_PATTERN_LABEL, MSG_REPEAT_LABEL,
)
from llamatron.strings.marks import MSG_CHAIN_JOIN, MSG_CRUMB_SEPARATOR
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.strings.legends import MSG_LEGEND_WHAT, MSG_MOVE_SCENE_WHAT, MSG_MOVE_TRACK_WHAT, MSG_OPEN_PATTERN_WHAT, What, KeyName
from llamatron.strings.messages import MSG_MOVING, MSG_MOVING_SCENE
from llamatron.strings.names import MSG_TRACK_PATTERN_NAME
from llamatron.strings.marks import MSG_FROM_SET_SHOWN
from llamatron.strings.labels import MSG_REGISTER_COLUMNS
from llamatron.tui.screens.arrange_page import MOVING_CLIP, MOVING_SCENE
from llamatron.strings.marks import MSG_CLIP_NAMED_FOR_PATTERN, MSG_ADD_ROW_MARK
from llamatron.tui import keybindings
from llamatron.tui.screens.field import Heading
from rendering import render_song

# Names the tests give to their own things, and other values they use.
PATTERNS_PAGE = 'Patterns page'
# How many words of a dialog's message to look for, since the dialog wraps it.
FIRST_WORDS = 5
LEAD = 'lead'
T19 = 't19'
TWO = 'two'
ONE = 'one'
ONE_COPY = 'one 2'
SCENE_3 = 'scene 3'
BEAT = 'beat'
TUNE = 'tune'
# An add past a narrow Allowed Inc Max, and that narrow limit.
BIG_ADD = 12
NARROW_INC_MAX = 4
RIFF = 'riff'
EXTRA11 = 'extra11'
REPEAT = 'Repeat'
MORPH_TO = 'Morph to'
MORPH_DIRECTION = 'Morph direction'
OTHER = 'other'
NAMED = 'named'
LOOP = 'Loop'
CHAIN = MSG_CHAINS_LABEL
GRAB_TRACK = 'Grab track'
DRUMS = 'drums'
CIRCULAR_GRAB = 'Circular grab'
THIS_PATTERN_HAS_NONE_YET = 'this pattern has none yet'
TUNE_G = 'tune g'
NO_OTHER_TRACKS = 'No other tracks'
INTRO = 'intro'
LENGTH = 'Length'
SCALE = 'Scale'
TEMPO = 'Tempo'
TEMPO_RAMPS_TO = 'Tempo ramps to'
DIRECTION = 'Direction'


# How the control keys are shown in a legend, each with a + of its own.
CONTROL_KEYS_SHOWN = [key_name(keybindings.Page.SAVE), key_name(keybindings.Page.OPEN_SET), key_name(keybindings.Page.EXPORT)]


# A scale a clip takes of its own on the clip page.
CLIP_SCALE = 'D Dorian'
CLIP_SCALE_ROOT = 'D'
CLIP_SCALE_KIND = 'dorian'

class TestArrangePage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE)
        self.page = self.app.screen

    def scenes(self):
        return [scene.get_name() for scene in self.document.song().get_scenes()]

    async def test_a_scene_crumb_says_it_is_a_scene(self):
        # Scenes have no list page of their own, so the crumb under ARRANGE says what it leads to.
        await self.press(Key.ENTER)
        scene = self.document.song().get_scenes()[0].get_name()
        self.assertIn(MSG_SCENE_CRUMB.format(name=scene), self.crumbs_line())

    async def test_p_on_a_clip_opens_its_pattern_with_arrange_before_the_pattern_in_the_crumbs_and_esc_comes_back_to_the_clip(self):
        # The user's choice of 2026-11-09: P jumps from a clip to its pattern, and the crumbs say the way back, which is this page, not the Patterns page.
        await self.press(Key.RIGHT)
        place = (self.page.row, self.page.column)
        self.assertTrue(self.page.on_clip_slot())
        clip_slot = self.document.clip_slot(index=0, track=LEAD)
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.ArrangePage.OPEN_PATTERN)) + MSG_LEGEND_WHAT.format(what=MSG_OPEN_PATTERN_WHAT), self.text())
        await self.press(keybindings.ArrangePage.OPEN_PATTERN)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.screen.item, clip_slot.get_pattern_name())
        trail = MSG_CRUMB_SEPARATOR.join([Crumb.ARRANGE, MSG_PATTERN_CRUMB.format(name=clip_slot.get_pattern_name())])
        self.assertIn(SPACE + trail + SPACE, self.crumbs_line())
        self.assertNotIn(Crumb.PATTERNS, self.crumbs_line())
        await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, self.page)
        self.assertEqual((self.page.row, self.page.column), place)

    async def test_p_opens_no_pattern_on_a_scene_a_track_an_empty_cell_or_the_add_row_and_on_a_scene_opens_scene_view(self):
        # The page opens on the first scene's name; Down is the second scene's name, Right the empty cell beside it, Up twice the track's name and Down three times the + row.
        shown = KEY_SHOWN.format(label=key_name(keybindings.ArrangePage.OPEN_PATTERN)) + MSG_LEGEND_WHAT.format(what=MSG_OPEN_PATTERN_WHAT)
        for keys in ([], [Key.DOWN], [Key.RIGHT], [Key.UP, Key.UP], [Key.DOWN, Key.DOWN, Key.DOWN]):
            await self.press(*keys)
            with self.subTest(place=(self.page.row, self.page.column)):
                self.assertFalse(self.page.on_clip_slot() and self.document.clip_slot(index=self.page.row, track=self.page.track()) is not None)
                self.assertNotIn(shown, self.text())
                scene_name = self.page.on_scene_name() and not self.page.on_plus_row()
                await self.press(keybindings.ArrangePage.OPEN_PATTERN)
                self.assertIs(self.app.screen, self.page)
                self.assertEqual(self.page.inset is not None, scene_name)
                if scene_name:
                    await self.press(keybindings.ArrangePage.CLOSE_INSET)

    def grid_lines(self):
        return self.text().splitlines()

    def line_with(self, text):
        """Return the number of the first screen line containing text."""
        for number, line in enumerate(self.grid_lines()):
            if text in line:
                return number
        self.fail(text)

    def assert_framed(self, *, text, height, above=1):
        """Check that one double-lined frame is drawn around height lines, with text on an inside line and the top edge above lines up."""
        lines = self.grid_lines()
        number = self.line_with(text) - above + 1
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)
        self.assertIn(Box.DOUBLE_TOP_LEFT, lines[number - 1])
        self.assertIn(Box.DOUBLE_BOTTOM_LEFT, lines[number + height])
        left = lines[number - 1].index(Box.DOUBLE_TOP_LEFT)
        right = lines[number - 1].index(Box.DOUBLE_TOP_RIGHT)
        for inside in lines[number:number + height]:
            self.assertEqual(inside[left], Box.DOUBLE_BAR)
            self.assertEqual(inside[right], Box.DOUBLE_BAR)
        inside = lines[number + above - 1]
        self.assertLess(left, inside.index(text))
        self.assertGreater(right, inside.index(text) + len(text) - 1)

    async def test_an_empty_clip_slot_shows_plus_and_add_only_under_the_cursor(self):
        # The + row and the + after the track names are always there; an empty clip slot is blank until the cursor arrives.
        self.assertNotIn(What.ADD.center(CELL_WIDTH), self.text())
        self.assertEqual(self.text().count(MSG_ADD_ROW_MARK.center(CELL_WIDTH)), 1)
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertIn(What.ADD.center(CELL_WIDTH), self.text())
        self.assertEqual(self.text().count(MSG_ADD_ROW_MARK.center(CELL_WIDTH)), 2)

    async def test_a_frame_marks_the_scene_the_clip_the_track_or_the_plus_row_under_the_cursor(self):
        self.assert_framed(text=ONE, height=2)
        await self.press(Key.RIGHT)
        self.assert_framed(text=TUNE, height=2)
        await self.press(Key.DOWN)
        self.assert_framed(text=What.ADD, height=2, above=2)
        await self.press(Key.UP, Key.UP)
        self.assert_framed(text=LEAD, height=1)
        await self.press(Key.DOWN, Key.DOWN, Key.DOWN)
        self.assertTrue(self.page.on_plus_row())
        # The + row's frame starts at the left edge, so the + is looked for just inside it, past the header's own +.
        lines = self.grid_lines()
        number = self.line_with(Box.DOUBLE_BAR + SPACE * (SCENE_BAR_COLUMN - 1) + MSG_ADD_ROW_MARK)
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)
        self.assertEqual(lines[number - 1][0], Box.DOUBLE_TOP_LEFT)
        self.assertEqual(lines[number + 1][0], Box.DOUBLE_BOTTOM_LEFT)
        self.assertEqual(lines[number][SCENE_WIDTH - 1], Box.DOUBLE_BAR)

    async def test_the_header_and_the_scene_column_keep_their_rule_and_the_corner_is_blank(self):
        lines = self.grid_lines()
        rule = self.line_with(Box.CROSS)
        self.assertEqual(lines[rule][:SCENE_WIDTH], Box.RULE * SCENE_WIDTH)
        self.assertEqual(lines[rule - 1][:SCENE_WIDTH].strip(), NOTHING)
        self.assertEqual(lines[rule - 1][SCENE_WIDTH], Box.BAR)
        self.assertEqual(lines[self.line_with(ONE)][SCENE_WIDTH], Box.BAR)

    async def test_length_bars_show_each_clip_against_its_scene_and_each_scene_against_the_longest(self):
        # In scene two, tune plays twice and other once for half as long, and scene one is half as long as scene two.
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.document.set_clip_slot_setting(index=1, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.add_clip_slot(index=1, track=DRUMS, pattern=OTHER)
        await self.press(Key.DOWN)
        lines = self.grid_lines()
        self.assertIn(CLIP_BAR.draw(amount=1, total=2), lines[self.line_with(OTHER) + 1])
        self.assertIn(CLIP_BAR.full(), lines[self.line_with(TUNE) + 1])
        self.assertIn(SCENE_BAR.draw(amount=1, total=2), lines[self.line_with(ONE) + 1])
        self.assertIn(SCENE_BAR.full(), lines[self.line_with(TWO) + 1])

    async def test_a_looping_clip_fills_its_bar(self):
        self.assertIn(CLIP_BAR.full(), self.grid_lines()[self.line_with(BEAT) + 1])

    async def test_the_last_scene_and_the_last_track_cannot_be_deleted(self):
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(len(self.scenes()), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(SPACE.join(ERR_LAST_SCENE_SHOWN.split()[:FIRST_WORDS]), self.text())
        await self.press(Key.ENTER)
        self.assertEqual(len(self.scenes()), 1)
        await self.press(Key.UP, Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(len(self.document.song().get_track_names()), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(SPACE.join(ERR_LAST_TRACK_SHOWN.split()[:FIRST_WORDS]), self.text())
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.song().get_track_names()), 1)

    async def test_scenes_show_their_time(self):
        self.assertIn('0:01', self.grid_lines()[self.line_with(ONE)])

    async def test_a_adds_a_scene_below_the_cursor(self):
        await self.press(keybindings.ArrangePage.ADD_SCENE)
        self.assertEqual(len(self.scenes()), 3)
        self.assertEqual(self.page.row, 1)

    async def test_move_mode_carries_a_scene_in_render_order_and_one_move_is_one_undo_step(self):
        # Move mode, the user's design: M on a scene's name picks it up, Up and Down carry it, and Enter, Esc or M drops it.
        await self.press(keybindings.ArrangePage.MOVE_SCENE)
        self.assertEqual(self.page.moving, MOVING_SCENE)
        self.assertIn(MSG_MOVING.format(what=MSG_MOVING_SCENE.format(name=ONE)), self.text())
        await self.press(forward_key(keybindings.ArrangePage.CARRY_SCENE))
        self.assertEqual(self.scenes(), [TWO, ONE])
        self.assertEqual(self.page.row, 1)
        song = render_song(self.document.song())
        self.assertEqual([scene.get_name() for scene in song.get_rows()], [TWO, ONE])
        # Past the bottom it stays, and Up carries it back; Esc drops it where it is and stays on Arrange.
        await self.press(forward_key(keybindings.ArrangePage.CARRY_SCENE), back_key(keybindings.ArrangePage.CARRY_SCENE), forward_key(keybindings.ArrangePage.CARRY_SCENE))
        self.assertEqual(self.scenes(), [TWO, ONE])
        await self.press(Key.ESCAPE)
        self.assertIsNone(self.page.moving)
        self.assertIs(self.app.screen, self.page)
        # The three carries were one move, so one undo puts the scenes back.
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.scenes(), [ONE, TWO])

    async def test_the_box_is_green_while_something_is_carried_and_m_or_enter_drops_it(self):
        width, height = self.SIZE

        def styles():
            return {span.style for line in self.page.drawing.body(width=width, height=height) for span in line.spans}
        self.assertNotIn(Style.DETAILS_LOCKED, styles())
        await self.press(keybindings.ArrangePage.MOVE_SCENE)
        self.assertIn(Style.DETAILS_LOCKED, styles())
        await self.press(keybindings.ArrangePage.MOVE_SCENE)
        self.assertIsNone(self.page.moving)
        await self.press(keybindings.ArrangePage.MOVE_SCENE, Key.ENTER)
        self.assertIsNone(self.page.moving)

    async def test_a_clip_moves_only_into_an_empty_cell_passing_over_full_ones(self):
        # The user's rule: a clip is carried to the nearest empty cell the arrow points to, and stays when there is none.
        await self.press(Key.RIGHT)
        moved = self.document.clip_slot(index=0, track=self.page.track())
        track = self.page.track()
        await self.press(keybindings.ArrangePage.MOVE_CLIP)
        self.assertEqual(self.page.moving, MOVING_CLIP)
        empty = [index for index in range(len(self.scenes())) if self.document.clip_slot(index=index, track=track) is None]
        await self.press(Key.DOWN)
        if empty:
            self.assertEqual(self.page.row, empty[0])
            self.assertIsNone(self.document.clip_slot(index=0, track=track))
            self.assertEqual(self.document.clip_slot(index=empty[0], track=track).to_data(), moved.to_data())
        else:
            self.assertEqual(self.page.row, 0)
        await self.press(Key.ENTER)
        self.assertIsNone(self.page.moving)

    async def test_nothing_on_arrange_takes_shift_with_an_arrow_and_the_legend_names_the_move_keys(self):
        """Scenes and tracks move in Move mode, M, the user's design, since a terminal may not send Shift with an arrow."""
        every = [name for item in self.page.key_table() for name in item.keys]
        for name in (*SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT):
            self.assertNotIn(name, every)
        before = self.document.setlist().to_data()
        await self.press(*SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT)
        self.assertEqual(self.document.setlist().to_data(), before)
        self.assertIn(KEY_SHOWN.format(label=KeyName.M) + MSG_LEGEND_WHAT.format(what=MSG_MOVE_SCENE_WHAT), self.text())
        await self.press(Key.UP, Key.RIGHT)
        self.assertIn(KEY_SHOWN.format(label=KeyName.M) + MSG_LEGEND_WHAT.format(what=MSG_MOVE_TRACK_WHAT), self.text())

    async def test_insert_puts_a_blank_scene_above_from_anywhere_on_the_row(self):
        await self.press(Key.RIGHT, Key.DOWN, keybindings.ArrangePage.INSERT_SCENE)
        self.assertEqual(self.scenes(), [ONE, SCENE_3, TWO])
        self.assertEqual(self.page.row, 1)
        self.assertEqual(self.document.song().get_scenes()[1].get_track_names(), [])

    async def test_copy_and_delete_on_the_scene_name_act_on_the_scene(self):
        await self.press(keybindings.ArrangePage.COPY_SCENE)
        self.assertEqual(self.scenes(), [ONE, ONE_COPY, TWO])
        self.assertEqual(self.page.row, 1)
        self.assertIsNotNone(self.document.clip_slot(index=1, track=LEAD))
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('clip(s)', self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.scenes(), [ONE, TWO])

    async def test_enter_on_a_blank_clip_picks_a_pattern_and_stays_on_arrange_until_enter_again(self):
        # The user's rule: adding a clip doesn't open it; Enter on the clip again does.
        await self.press(Key.RIGHT, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(BEAT)
        self.assertIs(self.app.screen, self.page)
        self.assertEqual(self.document.clip_slot(index=1, track=LEAD).to_data(), {ClipSlotSetting.PATTERN: BEAT})
        await self.press(keybindings.ArrangePage.EDIT_CLIP)
        self.assertIsInstance(self.app.screen, ClipPage)

    async def test_b_on_an_empty_cell_makes_a_blank_pattern_named_after_the_track_and_opens_it(self):
        # The user's design, as Live makes a new clip in an empty slot: a blank pattern, a clip of it, and the pattern editor on it.
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertIsNone(self.document.clip_slot(index=1, track=LEAD))
        await self.press(keybindings.ArrangePage.BLANK_PATTERN)
        name = MSG_TRACK_PATTERN_NAME.format(track=LEAD, number=1)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.screen.item, name)
        self.assertEqual(self.document.clip_slot(index=1, track=LEAD).get_pattern_name(), name)
        self.assertFalse(self.document.has_notes(name))
        # Esc comes back to the cell, and the next blank pattern on the track takes the next number.
        await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, self.page)
        await self.press(keybindings.ArrangePage.DELETE_CLIP, keybindings.ConfirmDialog.YES, keybindings.ArrangePage.BLANK_PATTERN)
        self.assertEqual(self.app.screen.item, MSG_TRACK_PATTERN_NAME.format(track=LEAD, number=2))

    async def test_no_patterns_is_explained(self):
        # The clips go first, since a pattern a clip plays can't be deleted.
        for index, scene in enumerate(self.document.song().get_scenes()):
            for track in scene.get_track_names():
                self.document.delete_clip_slot(index=index, track=track)
        for name in self.document.song().get_pattern_names():
            self.document.delete_named(section=Section.PATTERNS, name=name)
        await self.press(Key.RIGHT, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(PATTERNS_PAGE, self.text())

    async def test_enter_on_a_scene_opens_its_settings(self):
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)

    async def test_copy_and_paste_a_clip(self):
        await self.press(Key.RIGHT, keybindings.ArrangePage.COPY_CLIP, Key.DOWN, keybindings.ArrangePage.PASTE_CLIP)
        self.assertEqual(self.document.clip_slot(index=1, track=LEAD).to_data(), {ClipSlotSetting.PATTERN: TUNE})
        self.document.set_clip_slot_setting(index=1, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_repeat(), DEFAULT_REPEAT)

    async def test_delete_a_clip_confirms(self):
        await self.press(Key.RIGHT, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD))

    async def test_scrolls_to_keep_the_cursor_on_screen(self):
        for number in range(20):
            self.document.add_track(f't{number}')
        self.document.changed()
        await self.press(*[Key.RIGHT] * 22)
        self.assertIn(T19, self.text())


class TestArrangeSmallTerminal(UITest):
    SIZE = (60, 18)

    async def test_nothing_breaks(self):
        for name in [keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER, Key.ESCAPE, Key.ESCAPE]:
            await self.press(name)
        self.assertIsInstance(self.app.screen, MainPage)


class TestArrangeScrolling(UITest):

    async def test_many_tracks_scroll_sideways(self):
        for number in range(12):
            self.document.add_track(f'extra{number}')
        await self.press(keybindings.MainPage.ARRANGE)
        page = self.app.screen
        self.assertIsInstance(page, ArrangePage)
        self.assertIn('›', self.text())
        await self.press(*[Key.RIGHT] * 14)
        self.assertGreater(page.left, 0)
        self.assertIn(EXTRA11, self.text())
        await self.press(*[Key.LEFT] * 14)
        self.assertEqual(page.left, 0)

    async def test_many_scenes_scroll_down_and_back(self):
        for number in range(60):
            self.document.add_scene(index=2, name=f'more {number}')
        await self.press(keybindings.MainPage.ARRANGE)
        page = self.app.screen
        await self.press(*[Key.DOWN] * 61)
        self.assertGreater(page.top, 0)
        self.assertIn('+', self.text())
        await self.press(*[Key.UP] * 61)
        self.assertEqual(page.top, 0)


class TestClipPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.page = self.app.screen

    async def test_the_crumb_pairs_the_scene_and_the_track(self):
        # A clip is where a scene's row and a track's column meet, not a child of the scene.
        scene = self.document.song().get_scenes()[0].get_name()
        self.assertIn(MSG_CLIP_CRUMB.format(scene=scene, track=LEAD), self.crumbs_line())

    def clip_slot(self):
        return self.document.clip_slot(index=0, track=LEAD)

    def labels(self):
        return [field.label for field in self.page.fields()]

    def follow_action_text(self):
        return next(field.value() for field in self.page.fields() if field.label == MSG_FOLLOW_ACTION_LABEL)

    async def test_the_scale_field_gives_the_clip_a_scale_of_its_own_and_takes_it_away(self):
        self.document.add_scale(name=CLIP_SCALE, root=CLIP_SCALE_ROOT, kind=CLIP_SCALE_KIND)
        self.document.record_edit()
        self.assertIsNone(self.clip_slot().get_scale_name())
        await self.select_field(CLIP_SCALE_LABEL)
        await self.press(Key.ENTER)
        await self.type(CLIP_SCALE)
        await self.press(Key.ENTER)
        self.assertEqual(self.clip_slot().get_scale_name(), CLIP_SCALE)
        await self.press(Key.ENTER)
        for _ in self.document.song().get_scale_names():
            await self.press(Key.UP)
        await self.press(Key.ENTER)
        self.assertIsNone(self.clip_slot().get_scale_name())

    async def test_advance_shows_the_sets_default_until_the_clip_sets_its_own_and_is_chosen_from_the_three_values(self):
        # No (default) choice; a clip that sets nothing shows the File page's Default follow action, saying it comes from the set, the user's design.
        self.assertIsNone(self.clip_slot().get_written_follow_action())
        self.assertEqual(self.follow_action_text(), MSG_FROM_SET_SHOWN.format(value=MSG_FOLLOW_ACTION_NAMES[FollowAction.WITH_SCENE]))
        self.document.set_default_follow_action(FollowAction.OFF)
        self.assertEqual(self.follow_action_text(), MSG_FROM_SET_SHOWN.format(value=MSG_FOLLOW_ACTION_NAMES[FollowAction.OFF]))
        self.document.set_default_follow_action(FollowAction.WITH_SCENE)
        self.assertIsNone(self.clip_slot().get_written_follow_action())
        await self.select_field(MSG_FOLLOW_ACTION_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [MSG_FOLLOW_ACTION_NAMES[choice] for choice in FOLLOW_ACTION_CHOICES])
        await self.press(Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.clip_slot().get_written_follow_action(), FollowAction.OFF)
        self.assertEqual(self.follow_action_text(), MSG_FOLLOW_ACTION_NAMES[FollowAction.OFF])
        # Left and Right step through the values, With Scene, Next and Off, and stop at the ends.
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.clip_slot().get_written_follow_action(), FollowAction.NEXT)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.clip_slot().get_written_follow_action(), FollowAction.WITH_SCENE)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.clip_slot().get_written_follow_action(), FollowAction.WITH_SCENE)
        # No export reads it: the song still renders and exports with the clip set either way.
        self.assertTrue(render_song(self.document.song(), seed=1).get_rows())

    async def test_p_opens_the_pattern_from_any_field_with_this_pages_crumbs_before_the_pattern_and_esc_comes_back_to_the_field(self):
        # The user's choice of 2026-11-09 (B): the page has one pattern, so P works wherever the triangle is, and the crumbs say the way back.
        scene = self.document.song().get_scenes()[0].get_name()
        for label in (MSG_PATTERN_LABEL, MSG_REPEAT_LABEL):
            with self.subTest(label=label):
                await self.select_field(label)
                self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.ClipPage.OPEN_PATTERN)) + MSG_LEGEND_WHAT.format(what=MSG_OPEN_PATTERN_WHAT), self.text())
                await self.press(keybindings.ClipPage.OPEN_PATTERN)
                self.assertIsInstance(self.app.screen, PatternEditor)
                self.assertEqual(self.app.screen.item, self.clip_slot().get_pattern_name())
                trail = MSG_CRUMB_SEPARATOR.join([
                    Crumb.ARRANGE, MSG_CLIP_CRUMB.format(scene=scene, track=LEAD), MSG_PATTERN_CRUMB.format(name=self.clip_slot().get_pattern_name()),
                ])
                self.assertIn(SPACE + trail + SPACE, self.crumbs_line())
                await self.press(Key.ESCAPE)
                self.assertIs(self.app.screen, self.page)
                self.assertEqual(self.page.field().label, label)

    async def go_to(self, label):
        self.page.place = self.labels().index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_the_name_field_names_the_clip_and_the_grid_shows_it(self):
        self.assertEqual(self.labels()[0], MSG_NAME_LABEL)
        self.assertIn(MSG_CLIP_NAMED_FOR_PATTERN.format(pattern=TUNE), self.text())
        await self.go_to(MSG_NAME_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = RIFF
        await self.press(Key.ENTER)
        self.assertEqual(self.clip_slot().get_name(), RIFF)
        self.assertEqual(self.clip_slot().to_data(), {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.NAME: RIFF})
        self.assertEqual(render_song(self.document.song()).get_rows()[0].get_name(), ONE)
        await self.press(Key.ESCAPE)
        self.assertIn(RIFF, self.text())
        self.assertNotIn(TUNE, self.text().splitlines()[4])
        await self.press(Key.ENTER)
        await self.go_to(MSG_NAME_LABEL)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.clip_slot().get_name())

    async def test_repeat_is_always_available(self):
        self.assertIn(REPEAT, self.labels())
        await self.go_to(REPEAT)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.clip_slot().get_repeat(), 2)
        self.assertEqual(self.document.lengths().clip_seconds(index=0, track=LEAD), 2)

    async def test_morph_only_appears_with_a_repeat_above_one(self):
        self.assertNotIn(MORPH_TO, self.labels())
        await self.go_to(REPEAT)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertIn(MORPH_TO, self.labels())
        self.assertNotIn(MORPH_DIRECTION, self.labels())

    async def test_choosing_a_second_pattern_offers_a_direction(self):
        await self.go_to(REPEAT)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        await self.go_to(MORPH_TO)
        await self.press(Key.ENTER)
        await self.pick(BEAT)
        self.assertEqual(self.clip_slot().get_morph_target(), BEAT)
        self.assertEqual(self.clip_slot().get_morph_style(), BlendMode.LEFT)
        await self.go_to(MORPH_DIRECTION)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.clip_slot().get_morph_style(), BlendMode.RIGHT)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.clip_slot().get_morph_style(), BlendMode.MIDDLE)
        render_song(self.document.song())

    async def test_going_back_to_one_repeat_removes_the_morph(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.set_clip_slot_morph_target(index=0, track=LEAD, pattern=OTHER)
        await self.go_to(REPEAT)
        await self.press(key_of(binding=keybindings.ClipPage.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.clip_slot().to_data(), {ClipSlotSetting.PATTERN: TUNE})

    async def test_loop_is_a_toggle_and_warns_when_every_clip_in_the_scene_loops(self):
        await self.go_to(LOOP)
        await self.press(Key.ENTER)
        self.assertTrue(self.clip_slot().loops())
        # The other clip in the scene already loops, so this one looping leaves the scene with no end.
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(ERR_LOOP_SCENES_INTRO, ' '.join(self.app.screen.messages))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        await self.press(Key.ENTER)
        self.assertFalse(self.clip_slot().loops())

    async def test_chains_are_added_on_their_list_page_and_cleared_from_the_field(self):
        await self.go_to(CHAIN)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainListPage)
        await self.press(keybindings.ChainListPage.ADD)
        await self.pick(NAMED)
        await self.press(keybindings.ChainListPage.ADD)
        await self.pick(NAMED)
        self.assertEqual(self.clip_slot().get_chain_names(), [NAMED, NAMED])
        await self.press(Key.ESCAPE)
        self.assertIn(MSG_CHAIN_JOIN.join([NAMED, NAMED]), self.text())
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.clip_slot().get_chain_names(), [])

    async def test_shows_its_length(self):
        self.assertIn('0:01', self.text())


class TestRhythmAndNotesFromOnAClip(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.page = self.app.screen

    def clip_slot(self):
        return self.document.clip_slot(index=0, track=LEAD)

    async def go_to(self, label):
        self.page.place = [field.label for field in self.page.fields()].index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_they_are_at_the_bottom_of_the_page(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.set_clip_slot_morph_target(index=0, track=LEAD, pattern=OTHER)
        # Grab track is the last of the fields that shape the notes; only Follow action, which real-time playback alone reads, comes after it, and then the sections of Density, Swell and Articulate, and the Play and Stop buttons.
        fields = self.page.fields()
        first_heading = next(place for place, field in enumerate(fields) if isinstance(field, Heading))
        labels = [field.label for field in fields[:first_heading]]
        self.assertEqual(labels[-2:], [GRAB_TRACK, MSG_FOLLOW_ACTION_LABEL])

    async def test_choosing_none_clears(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        await self.go_to(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.app.screen.place = 0
        await self.press(Key.ENTER)
        self.assertIsNone(self.clip_slot().get_grab_track())

    async def test_choosing_a_grab_track(self):
        await self.go_to(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.options, ['(none)', DRUMS])
        self.app.screen.place = 1
        await self.press(Key.ENTER)
        self.assertEqual(self.clip_slot().get_grab_track(), DRUMS)

    async def test_a_circular_grab_is_refused_with_a_message(self):
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        await self.go_to(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.app.screen.place = 1
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(CIRCULAR_GRAB, self.text())
        self.assertIn('a circle: lead → drums →', self.text())
        self.assertIn('Remove the grab from another clip in this scene first.', self.text())
        self.assertIsNone(self.clip_slot().get_grab_track())

    async def test_says_when_the_grab_track_has_no_grab_steps_to_change(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        self.page.draw()
        await self.pilot.pause()
        self.assertIn(THIS_PATTERN_HAS_NONE_YET, self.text())
        self.document.set_step_value(name=TUNE, row=Row.GRAB, step=0, value=True)
        self.page.draw()
        await self.pilot.pause()
        self.assertNotIn(THIS_PATTERN_HAS_NONE_YET, self.text())
        render_song(self.document.song())

    async def test_the_grid_marks_them(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        await self.press(Key.ESCAPE)
        self.assertIn(TUNE_G, self.text())

    async def test_a_pattern_in_use_this_way_cannot_be_deleted(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.set_clip_slot_morph_target(index=0, track=LEAD, pattern=OTHER)
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.DOWN, Key.DOWN, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())

    async def test_the_result_saves_and_loads(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        self.document.save(path='x.yml')
        self.assertEqual(Document.load('x.yml').clip_slot(index=0, track=LEAD).to_data(), self.clip_slot().to_data())


class TestGrabEdges(UITest):

    async def test_pasting_a_clip_onto_the_track_it_grabs_from_drops_the_grab(self):
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.RIGHT, keybindings.ArrangePage.COPY_CLIP, Key.LEFT, keybindings.ArrangePage.PASTE_CLIP)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_pattern_name(), BEAT)
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD).get_grab_track())
        self.assertIn('without its grab from lead', self.text())

    async def test_pasting_elsewhere_keeps_the_grab(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, keybindings.ArrangePage.COPY_CLIP, Key.DOWN, keybindings.ArrangePage.PASTE_CLIP)
        self.assertEqual(self.document.clip_slot(index=1, track=LEAD).get_grab_track(), DRUMS)

    async def test_choosing_a_grab_track_needs_another_track(self):
        self.document.delete_named(section=Section.TRACKS, name=DRUMS)
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        page = self.app.screen
        self.assertIsInstance(page, ClipPage)
        page.place = [field.label for field in page.fields()].index(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(NO_OTHER_TRACKS, self.text())


class TestScenePage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.page = self.app.screen

    def scene(self):
        return self.document.song().get_scenes()[0]

    async def go_to(self, label):
        self.page.place = [field.label for field in self.page.fields()].index(label)
        self.page.draw()
        await self.pilot.pause()

    async def test_shows_the_length_of_its_longest_clip(self):
        self.assertIn(LENGTH, self.text())
        self.assertIn('0:01', self.text())

    async def test_scale_can_be_set_and_cleared(self):
        await self.go_to(SCALE)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(self.scene().get_scale_name(), DEFAULT_SCALE)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.scene().get_scale_name())

    async def test_tempo_and_ramp(self):
        await self.go_to(TEMPO)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.scene().get_tempo_setting(), 121)
        await self.go_to(TEMPO_RAMPS_TO)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual((self.scene().get_tempo_start(), self.scene().get_tempo_end()), (121, 122))
        self.assertIsNone(self.scene().get_tempo_setting())
        render_song(self.document.song())
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.scene().get_tempo_setting(), 121)
        self.assertIsNone(self.scene().get_tempo_end())

    async def test_repeat(self):
        await self.go_to(REPEAT)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.scene().get_repeat(), 2)
        self.assertEqual(self.document.lengths().scene_seconds(0), 2)

    async def test_rename(self):
        await self.press(Key.ENTER)
        self.app.screen.value = INTRO
        await self.press(Key.ENTER)
        self.assertEqual(self.scene().get_name(), INTRO)


    async def test_it_can_reset_each_register(self):
        label = MSG_RESET_LABEL.format(name=RegisterName.BX)
        await self.go_to(label)
        await self.press(Key.ENTER)
        self.assertEqual(self.scene().get_reset_names(), [RegisterName.BX])
        await self.press(Key.SPACE)
        self.assertEqual(self.scene().get_reset_names(), [])


class TestScenesAndClipsEdges(UITest):

    async def scene_page(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)
        return self.app.screen

    async def go_to(self, page, label):
        page.place = [field.label for field in page.fields()].index(label)
        page.draw()
        await self.pilot.pause()

    def scene(self):
        return self.document.song().get_scenes()[0]

    async def test_tempo_with_a_ramp_moves_the_start_and_clearing_removes_both(self):
        self.document.set_scene_tempo(index=0, tempo=100)
        self.document.set_scene_tempo_ramp(index=0, end=120)
        page = await self.scene_page()
        await self.go_to(page, TEMPO)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual((self.scene().get_tempo_start(), self.scene().get_tempo_end()), (101, 120))
        await self.press(Key.BACKSPACE)
        self.assertEqual((self.scene().get_tempo_setting(), self.scene().get_tempo_start(), self.scene().get_tempo_end()), (None, None, None))

    async def test_choosing_the_songs_scale_clears_the_scenes(self):
        self.document.set_scene_scale(index=0, name=DEFAULT_SCALE)
        page = await self.scene_page()
        await self.go_to(page, SCALE)
        await self.press(Key.ENTER)
        self.app.screen.place = 0
        await self.press(Key.ENTER)
        self.assertIsNone(self.scene().get_scale_name())

    async def clip_page(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        return self.app.screen

    async def test_removing_the_last_chain_on_its_list_page_leaves_none(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.CHAIN, value=NAMED)
        page = await self.clip_page()
        await self.go_to(page, CHAIN)
        await self.press(Key.ENTER)
        await self.press(keybindings.ChainListPage.REMOVE)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_chain_names(), [])

    async def test_stepping_past_the_last_direction_goes_back_to_the_patterns(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.EITHERWAY)
        page = await self.clip_page()
        await self.go_to(page, DIRECTION)
        await self.press(key_of(binding=keybindings.ClipPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD).get_direction())

    async def test_deleting_a_clip_asks_first(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsNone(self.document.clip_slot(index=0, track=LEAD))


# What shows when a register's settings would be out of order.
OUT_OF_ORDER_START = fixed_text(ERR_OUT_OF_ORDER)


class TestRegistersPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.REGISTERS)
        self.page = self.app.screen

    def label(self, *, name, what):
        return MSG_REGISTER_FIELD_LABEL.format(name=name, what=what)

    def register(self, name):
        return self.document.register(name)

    async def test_it_opens_from_the_main_screen_with_every_register(self):
        self.assertIsInstance(self.page, RegistersPage)
        labels = [field.label for field in self.page.fields()]
        for name in REGISTER_NAMES:
            for _, what in MSG_REGISTER_NUMBER_FIELDS:
                self.assertIn(self.label(name=name, what=what), labels)
            for what in (MSG_REGISTER_AT_LIMIT_FIELD, MSG_REGISTER_RESET_EACH_SCENE_FIELD, MSG_REGISTER_ALLOWED_INC_MAX_FIELD):
                self.assertIn(self.label(name=name, what=what), labels)

    async def test_it_is_a_grid_the_arrows_move_over_stopping_at_every_edge(self):
        # The user's design: a row for each register and a column for each setting, the cursor stopping at every edge.
        columns = len(self.page.fields()) // len(REGISTER_NAMES)
        await self.press(Key.UP, Key.LEFT)
        self.assertEqual(self.page.place, 0)
        await self.press(Key.DOWN, Key.RIGHT)
        self.assertEqual(self.page.place, columns + 1)
        await self.press(*[Key.DOWN] * len(REGISTER_NAMES), *[Key.RIGHT] * columns)
        self.assertEqual(self.page.place, len(self.page.fields()) - 1)
        self.assertEqual(self.page.field().label, self.label(name=REGISTER_NAMES[-1], what=MSG_REGISTER_RESET_EACH_SCENE_FIELD))
        for heading in MSG_REGISTER_COLUMNS:
            self.assertIn(heading, self.text())

    async def test_numbers_change_and_go_back_to_their_defaults(self):
        await self.select_field(self.label(name=RegisterName.BX, what=RegisterSetting.MAXIMUM))
        await self.press(key_of(binding=keybindings.RegistersPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), DEFAULT_REGISTER_MAXIMUM + 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), DEFAULT_REGISTER_MAXIMUM)
        self.assertNotIn(Section.REGISTERS, self.document.song().to_data())

    async def test_a_typed_number_can_be_negative(self):
        lowest = -50
        await self.select_field(self.label(name=RegisterName.DX, what=RegisterSetting.MINIMUM))
        await self.press(Key.ENTER)
        self.app.screen.value = str(lowest)
        await self.press(Key.ENTER)
        self.assertEqual(self.register(RegisterName.DX).get_minimum(), lowest)
        render_song(self.document.song())

    async def test_settings_out_of_order_are_refused_with_the_reason(self):
        await self.select_field(self.label(name=RegisterName.AX, what=RegisterSetting.MINIMUM))
        await self.press(key_of(binding=keybindings.RegistersPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.register(RegisterName.AX).get_minimum(), DEFAULT_REGISTER_MINIMUM)
        self.assertIn(OUT_OF_ORDER_START, self.text())

    async def test_at_limit_steps_through_its_choices_and_reset_each_scene_toggles(self):
        await self.select_field(self.label(name=RegisterName.CX, what=MSG_REGISTER_AT_LIMIT_FIELD))
        await self.press(key_of(binding=keybindings.RegistersPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.register(RegisterName.CX).get_at_limit(), AT_LIMITS[1])
        self.assertIn(MSG_AT_LIMIT_NAMES[AT_LIMITS[1]], self.text())
        await self.press(key_of(binding=keybindings.RegistersPage.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.register(RegisterName.CX).get_at_limit(), AT_LIMITS[0])
        self.assertNotIn(Section.REGISTERS, self.document.song().to_data())
        await self.select_field(self.label(name=RegisterName.CX, what=MSG_REGISTER_RESET_EACH_SCENE_FIELD))
        await self.press(Key.ENTER)
        self.assertTrue(self.register(RegisterName.CX).resets_each_scene())
        await self.press(Key.ENTER)
        self.assertFalse(self.register(RegisterName.CX).resets_each_scene())

    async def test_a_lower_allowed_inc_max_brings_the_adds_within_it_and_undo_brings_them_back(self):
        add_row = REGISTER_ADD_ROWS[RegisterName.AX]
        self.document.set_step_value(name=TUNE, row=add_row, step=0, value=BIG_ADD)
        self.document.set_step_value(name=TUNE, row=add_row, step=1, value=-BIG_ADD)
        self.document.record_edit()
        await self.select_field(self.label(name=RegisterName.AX, what=MSG_REGISTER_ALLOWED_INC_MAX_FIELD))
        await self.press(Key.ENTER)
        self.app.screen.value = str(NARROW_INC_MAX)
        await self.press(Key.ENTER)
        self.assertEqual(self.register(RegisterName.AX).get_allowed_inc_max(), NARROW_INC_MAX)
        self.assertEqual([self.document.step_value(name=TUNE, row=add_row, step=step) for step in (0, 1)], [NARROW_INC_MAX, -NARROW_INC_MAX])
        await self.press(keybindings.Page.UNDO)
        self.assertEqual([self.document.step_value(name=TUNE, row=add_row, step=step) for step in (0, 1)], [BIG_ADD, -BIG_ADD])

    async def test_settings_save_and_load(self):
        await self.select_field(self.label(name=RegisterName.AX, what=RegisterSetting.MAXIMUM))
        await self.press(key_of(binding=keybindings.RegistersPage.LESS, key=Key.LEFT_BRACKET))
        self.document.save(path='x.yml')
        self.assertEqual(Document.load('x.yml').register(RegisterName.AX).get_maximum(), DEFAULT_REGISTER_MAXIMUM - 1)
