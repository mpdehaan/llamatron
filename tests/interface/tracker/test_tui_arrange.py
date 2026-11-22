# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Arrange page, the scene and clip pages, grabs and the Registers page."""

from llamatron.interface.tracker import drawing, keybindings, keys as keys_values
from llamatron.interface.tracker.cursor import NoSuchPlace
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.document import Document
from llamatron.interface.tracker.drawing import Box, Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange import arrange_drawing, arrange_page
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage, ArrangePlace
from llamatron.interface.tracker.screens.arrange.clip_page import AddRow, ClipPage, PatternRow
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.interface.tracker.screens.generators.generator_list_page import GeneratorListPage
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.interface.tracker.screens.set.registers_page import RegistersPage
from llamatron.interface.tracker.screens.shared.field import Heading
from llamatron.interface.tracker.screens.shared.generator_names import listed_generator
from llamatron.model.objects import setlist
from llamatron.model.objects.scene import TempoRamp
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, Direction, DrawName, FollowAction, PatternOrder, RampPart, RampWay, RegisterName, RegisterSetting, Row, Section
from llamatron.model.values.blend_mode import BlendMode
from llamatron.user_strings import errors, labels as labels_text, legends, marks, messages, names
from tests.support import ui_testing
from tests.support.rendering import render_song
from tests.support.ui_testing import back_key, fixed_text, forward_key, key_name, key_of, UITest

# Names the tests give to their own things, and other values they use.
PATTERNS_PAGE = 'Patterns page'
# How many words of a dialog's message to look for, since the dialog wraps it.
FIRST_WORDS = 5
LEAD = 'lead'
NEW_LINE = '\n'
T19 = 't19'
TWO = 'two'
ONE = 'one'
ONE_COPY = 'one-2'
NEW_SCENE = 'scene-1'
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
CHAIN = labels_text.MSG_GENERATORS_FIELD_LABEL
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
DIRECTION = labels_text.MSG_DIRECTION_LABEL
LEAD_1 = 'lead-1'
ONE_MORE = 1


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

    async def test_the_cursor_is_steered_to_a_clip_a_scene_and_a_track_by_name_and_says_what_it_is_on(self):
        tracks = self.document.track_names()
        last_scene = self.scenes()[-1]
        await self.go_to_clip(scene=last_scene, track=tracks[-1])
        self.assertTrue(self.page.on_clip_slot())
        self.assert_cursor_on(ArrangePlace(scene=len(self.scenes()) - 1, track=tracks[-1]))
        await self.go_to_track(tracks[0])
        self.assertTrue(self.page.on_track_name())
        self.assert_cursor_on(ArrangePlace(track=tracks[0]))
        await self.go_to_scene(self.scenes()[0])
        self.assertTrue(self.page.on_scene_name())
        self.assert_cursor_on(ArrangePlace(scene=0))
        # From the + row, which has the scene column alone, the way to a clip leaves upward first.
        await self.press(*[Key.DOWN] * len(self.scenes()))
        self.assertTrue(self.page.on_plus_row())
        self.assert_cursor_on(None)
        await self.go_to_clip(scene=0, track=tracks[0])
        self.assert_cursor_on(ArrangePlace(scene=0, track=tracks[0]))
        with self.assertRaises(NoSuchPlace):
            self.page.key_toward(ArrangePlace(scene=len(self.scenes()), track=tracks[0]))

    async def test_a_scene_crumb_says_it_is_a_scene(self):
        # Scenes have no list page of their own, so the crumb under ARRANGE says what it leads to.
        await self.press(Key.ENTER)
        scene = self.document.song().get_scenes()[0].get_name()
        self.assertIn(labels_text.MSG_SCENE_CRUMB.format(name=scene), self.crumbs_line())

    async def test_p_on_a_clip_opens_its_pattern_with_arrange_before_the_pattern_in_the_crumbs_and_esc_comes_back_to_the_clip(self):
        # P jumps from a clip to its pattern, and the crumbs say the way back, which is this page, not the Patterns page.
        await self.press(Key.RIGHT)
        place = (self.page.row, self.page.column)
        self.assertTrue(self.page.on_clip_slot())
        clip_slot = self.document.clip_slot(index=0, track=LEAD)
        self.assertIn(ui_testing.KEY_SHOWN.format(label=key_name(keybindings.ArrangePage.OPEN_PATTERN)) + legends.MSG_LEGEND_WHAT.format(what=legends.MSG_OPEN_PATTERN_WHAT), self.text())
        await self.press(keybindings.ArrangePage.OPEN_PATTERN)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.screen.item, clip_slot.get_pattern_name())
        trail = marks.MSG_CRUMB_SEPARATOR.join([labels_text.Crumb.ARRANGE, labels_text.MSG_PATTERN_CRUMB.format(name=clip_slot.get_pattern_name())])
        self.assertIn(drawing.SPACE + trail + drawing.SPACE, self.crumbs_line())
        self.assertNotIn(labels_text.Crumb.PATTERNS, self.crumbs_line())
        await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, self.page)
        self.assertEqual((self.page.row, self.page.column), place)

    async def test_jump_opens_no_pattern_on_a_scene_a_track_an_empty_cell_or_the_add_row_and_scene_view_has_a_key_of_its_own(self):
        # The page opens on the first scene's name; Down is the second scene's name, Right the empty cell beside it, Up twice the track's name and Down three times the + row.
        shown = ui_testing.KEY_SHOWN.format(label=key_name(keybindings.ArrangePage.OPEN_PATTERN)) + legends.MSG_LEGEND_WHAT.format(what=legends.MSG_OPEN_PATTERN_WHAT)
        for keys in ([], [Key.DOWN], [Key.RIGHT], [Key.UP, Key.UP], [Key.DOWN, Key.DOWN, Key.DOWN]):
            await self.press(*keys)
            with self.subTest(place=(self.page.row, self.page.column)):
                self.assertFalse(self.page.on_clip_slot() and self.document.clip_slot(index=self.page.row, track=self.page.track()) is not None)
                self.assertNotIn(shown, self.text())
                scene_name = self.page.on_scene_name() and not self.page.on_plus_row()
                # Jump to pattern does nothing away from a clip, and it is a key of its own now, so it never opens Scene View either.
                await self.press(keybindings.ArrangePage.OPEN_PATTERN)
                self.assertIs(self.app.screen, self.page)
                self.assertIsNone(self.page.inset)
                if scene_name:
                    await self.press(keybindings.ArrangePage.SCENE_VIEW)
                    self.assertIsNotNone(self.page.inset)
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
        self.assertNotIn(legends.What.ADD.center(arrange_drawing.CELL_WIDTH), self.text())
        self.assertEqual(self.text().count(marks.MSG_ADD_ROW_MARK.center(arrange_drawing.CELL_WIDTH)), 1)
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertIn(legends.What.ADD.center(arrange_drawing.CELL_WIDTH), self.text())
        self.assertEqual(self.text().count(marks.MSG_ADD_ROW_MARK.center(arrange_drawing.CELL_WIDTH)), 2)

    async def test_a_frame_marks_the_scene_the_clip_the_track_or_the_plus_row_under_the_cursor(self):
        self.assert_framed(text=ONE, height=2)
        await self.press(Key.RIGHT)
        self.assert_framed(text=TUNE, height=2)
        await self.press(Key.DOWN)
        self.assert_framed(text=legends.What.ADD, height=2, above=2)
        await self.press(Key.UP, Key.UP)
        self.assert_framed(text=LEAD, height=1)
        await self.press(Key.DOWN, Key.DOWN, Key.DOWN)
        self.assertTrue(self.page.on_plus_row())
        # The + row's frame starts at the left edge, so the + is looked for just inside it, past the header's own +.
        lines = self.grid_lines()
        number = self.line_with(Box.DOUBLE_BAR + drawing.SPACE * (arrange_drawing.SCENE_BAR_COLUMN - 1) + marks.MSG_ADD_ROW_MARK)
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)
        self.assertEqual(lines[number - 1][0], Box.DOUBLE_TOP_LEFT)
        self.assertEqual(lines[number + 1][0], Box.DOUBLE_BOTTOM_LEFT)
        self.assertEqual(lines[number][arrange_drawing.SCENE_WIDTH - 1], Box.DOUBLE_BAR)

    async def test_the_header_and_the_scene_column_keep_their_rule_and_the_corner_is_blank(self):
        lines = self.grid_lines()
        rule = self.line_with(Box.CROSS)
        self.assertEqual(lines[rule][:arrange_drawing.SCENE_WIDTH], Box.RULE * arrange_drawing.SCENE_WIDTH)
        self.assertEqual(lines[rule - 1][:arrange_drawing.SCENE_WIDTH].strip(), drawing.NOTHING)
        self.assertEqual(lines[rule - 1][arrange_drawing.SCENE_WIDTH], Box.BAR)
        self.assertEqual(lines[self.line_with(ONE)][arrange_drawing.SCENE_WIDTH], Box.BAR)

    async def test_length_bars_show_each_clip_against_its_scene_and_each_scene_against_the_longest(self):
        # In scene two, tune plays twice and other once for half as long, and scene one is half as long as scene two.
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.document.set_clip_slot_setting(index=1, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.add_clip_slot(index=1, track=DRUMS, pattern=OTHER)
        await self.press(Key.DOWN)
        lines = self.grid_lines()
        self.assertIn(arrange_drawing.CLIP_BAR.draw(amount=1, total=2), lines[self.line_with(OTHER) + 1])
        self.assertIn(arrange_drawing.CLIP_BAR.full(), lines[self.line_with(TUNE) + 1])
        self.assertIn(arrange_drawing.SCENE_BAR.draw(amount=1, total=2), lines[self.line_with(ONE) + 1])
        self.assertIn(arrange_drawing.SCENE_BAR.full(), lines[self.line_with(TWO) + 1])

    async def test_a_looping_clip_fills_its_bar(self):
        self.assertIn(arrange_drawing.CLIP_BAR.full(), self.grid_lines()[self.line_with(BEAT) + 1])

    async def test_the_last_scene_and_the_last_track_cannot_be_deleted(self):
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(len(self.scenes()), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(drawing.SPACE.join(errors.ERR_LAST_SCENE_SHOWN.split()[:FIRST_WORDS]), self.text())
        await self.press(Key.ENTER)
        self.assertEqual(len(self.scenes()), 1)
        await self.press(Key.UP, Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertEqual(len(self.document.song().get_track_names()), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(drawing.SPACE.join(errors.ERR_LAST_TRACK_SHOWN.split()[:FIRST_WORDS]), self.text())
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.song().get_track_names()), 1)

    async def test_scenes_show_their_time(self):
        self.assertIn('0:01', self.grid_lines()[self.line_with(ONE)])

    async def test_a_adds_a_scene_below_the_cursor(self):
        await self.press(keybindings.ArrangePage.ADD_SCENE)
        self.assertEqual(len(self.scenes()), 3)
        self.assertEqual(self.page.row, 1)

    async def test_move_mode_carries_a_scene_in_render_order_and_one_move_is_one_undo_step(self):
        # Move mode: M on a scene's name picks it up, Up and Down carry it, and Enter, Esc or M drops it.
        await self.press(keybindings.ArrangePage.MOVE_SCENE)
        self.assertEqual(self.page.moving, arrange_page.MOVING_SCENE)
        self.assertIn(messages.MSG_MOVING.format(what=messages.MSG_MOVING_SCENE.format(name=ONE)), self.text())
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
        # A clip is carried to the nearest empty cell the arrow points to, and stays when there is none.
        await self.press(Key.RIGHT)
        moved = self.document.clip_slot(index=0, track=self.page.track())
        track = self.page.track()
        await self.press(keybindings.ArrangePage.MOVE_CLIP)
        self.assertEqual(self.page.moving, arrange_page.MOVING_CLIP)
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
        """Scenes and tracks move in Move mode, M, since a terminal may not send Shift with an arrow."""
        every = [name for item in self.page.key_table() for name in item.keys]
        for name in (*keys_values.SHIFT_UP_DOWN, *keys_values.SHIFT_LEFT_RIGHT):
            self.assertNotIn(name, every)
        before = self.document.get_setlist().to_data()
        await self.press(*keys_values.SHIFT_UP_DOWN, *keys_values.SHIFT_LEFT_RIGHT)
        self.assertEqual(self.document.get_setlist().to_data(), before)
        self.assertIn(ui_testing.KEY_SHOWN.format(label=legends.KeyName.M) + legends.MSG_LEGEND_WHAT.format(what=legends.MSG_MOVE_SCENE_WHAT), self.text())
        await self.press(Key.UP, Key.RIGHT)
        self.assertIn(ui_testing.KEY_SHOWN.format(label=legends.KeyName.M) + legends.MSG_LEGEND_WHAT.format(what=legends.MSG_MOVE_TRACK_WHAT), self.text())

    async def test_insert_puts_a_blank_scene_above_from_anywhere_on_the_row(self):
        await self.press(Key.RIGHT, Key.DOWN, keybindings.ArrangePage.INSERT_SCENE)
        self.assertEqual(self.scenes(), [ONE, NEW_SCENE, TWO])
        self.assertEqual(self.page.row, 1)
        self.assertEqual(self.document.song().get_scenes()[1].get_track_names(), [])

    async def test_a_scene_copied_with_copies_of_its_patterns_plays_patterns_of_its_own(self):
        original = self.document.clip_slot(index=0, track=LEAD).get_pattern_names()
        await self.press(keybindings.ArrangePage.COPY_SCENE, Key.DOWN, Key.ENTER)
        copied = self.document.clip_slot(index=1, track=LEAD).get_pattern_names()
        self.assertNotEqual(copied, original)
        self.assertTrue(all(self.document.get_setlist().has_pattern(name) for name in copied))

    async def test_copy_and_delete_on_the_scene_name_act_on_the_scene(self):
        await self.press(keybindings.ArrangePage.COPY_SCENE, Key.ENTER)
        self.assertEqual(self.scenes(), [ONE, ONE_COPY, TWO])
        self.assertEqual(self.page.row, 1)
        self.assertIsNotNone(self.document.clip_slot(index=1, track=LEAD))
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn('clip(s)', self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.scenes(), [ONE, TWO])

    async def test_enter_on_a_blank_clip_picks_a_pattern_and_stays_on_arrange_until_enter_again(self):
        # Adding a clip doesn't open it; Enter on the clip again does.
        await self.press(Key.RIGHT, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(BEAT)
        self.assertIs(self.app.screen, self.page)
        self.assertEqual(self.document.clip_slot(index=1, track=LEAD).to_data(), {ClipSlotSetting.PATTERN: BEAT})
        await self.press(keybindings.ArrangePage.EDIT_CLIP)
        self.assertIsInstance(self.app.screen, ClipPage)

    async def test_b_on_an_empty_cell_makes_a_blank_pattern_named_after_the_track_and_opens_it(self):
        # As Live makes a new clip in an empty slot: a blank pattern, a clip of it, and the pattern editor on it.
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertIsNone(self.document.clip_slot(index=1, track=LEAD))
        await self.press(keybindings.ArrangePage.BLANK_PATTERN)
        name = names.MSG_NUMBERED_NAME.format(base=LEAD, number=1)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.screen.item, name)
        self.assertEqual(self.document.clip_slot(index=1, track=LEAD).get_pattern_name(), name)
        self.assertFalse(self.document.has_notes(name))
        # A pattern made here goes in the group named after its track.
        self.assertEqual(self.document.pattern_group(name), LEAD)
        # Esc comes back to the cell, and the next blank pattern on the track takes the next number.
        await self.press(Key.ESCAPE)
        self.assertIs(self.app.screen, self.page)
        await self.press(keybindings.ArrangePage.DELETE_CLIP, keybindings.ConfirmDialog.YES, keybindings.ArrangePage.BLANK_PATTERN)
        self.assertEqual(self.app.screen.item, names.MSG_NUMBERED_NAME.format(base=LEAD, number=2))

    async def test_no_patterns_is_explained(self):
        # The clips go first, since a pattern a clip plays can't be deleted.
        for index, scene in enumerate(self.document.song().get_scenes()):
            for track in scene.get_track_names():
                self.document.change_set(self.document.song().get_scene(index).remove_clip_slot, track)
        for name in self.document.get_setlist().get_pattern_names():
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
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_repeat(), defaults.DEFAULT_REPEAT)

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
        self.assertIn(labels_text.MSG_CLIP_CRUMB.format(scene=scene, track=LEAD), self.crumbs_line())

    def clip_slot(self):
        return self.document.clip_slot(index=0, track=LEAD)

    def labels(self):
        return [field.label for field in self.page.fields()]

    def follow_action_text(self):
        return next(field.value() for field in self.page.fields() if field.label == labels_text.MSG_FOLLOW_ACTION_LABEL)

    def patterns(self):
        return self.clip_slot().get_pattern_names()

    def pattern_rows(self):
        return [field.value() for field in self.page.fields() if isinstance(field, PatternRow)]

    async def test_the_patterns_are_a_list_with_an_add_row_even_for_one_pattern(self):
        self.assertEqual(self.pattern_rows(), self.patterns())
        self.assertEqual(len(self.patterns()), ONE_MORE)
        self.assertEqual(self.labels().count(labels_text.MSG_PATTERNS_LABEL), ONE_MORE)
        self.assertEqual([field.value() for field in self.page.fields() if isinstance(field, AddRow)], [marks.MSG_ADD_ROW])
        # A blank line stands between the list's + row and the settings after it.
        lines = [line.strip() for line in self.text().splitlines()]
        add = next(place for place, line in enumerate(lines) if line.endswith(marks.MSG_ADD_ROW) and len(line) <= len(marks.MSG_ADD_ROW) + 2)
        self.assertIn(labels_text.MSG_PATTERNS_LABEL, lines[add - 1])
        self.assertEqual(lines[add + 1], drawing.NOTHING)

    async def test_adding_an_existing_pattern_puts_it_last_and_bksp_takes_one_out_but_never_the_last(self):
        first = self.patterns()
        await self.press(keybindings.ClipPage.ADD_PATTERN)
        self.assertIn(labels_text.MSG_ADD_PATTERN_TITLE, self.text())
        await self.press(Key.ENTER)
        await self.type(OTHER)
        await self.press(Key.ENTER)
        self.assertEqual(self.patterns(), [*first, OTHER])
        self.assertEqual(self.pattern_rows(), [*first, OTHER])
        # The pattern taken out of the list is still a pattern of the set.
        await self.select_field(labels_text.MSG_PATTERNS_LABEL)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertEqual(self.patterns(), [OTHER])
        self.assertTrue(self.document.get_setlist().has_pattern(first[0]))
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertEqual(self.patterns(), [OTHER])
        self.assertIn(errors.ERR_CLIP_NEEDS_A_PATTERN, self.text())

    async def test_a_new_pattern_is_named_for_the_track_made_blank_and_added(self):
        first = self.patterns()
        await self.press(keybindings.ClipPage.ADD_PATTERN, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ENTER)
        self.assertEqual(self.patterns(), [*first, LEAD_1])
        self.assertEqual(self.document.get_setlist().get_pattern(LEAD_1).get_group(), LEAD)
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.patterns(), first)
        self.assertFalse(self.document.get_setlist().has_pattern(LEAD_1))

    async def test_move_carries_a_pattern_along_the_list_as_one_undo_step(self):
        first = self.patterns()[0]
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.PATTERNS, value=[first, OTHER, first])
        self.document.record_edit()
        await self.select_field(labels_text.MSG_PATTERNS_LABEL)
        await self.press(keybindings.ClipPage.MOVE_PATTERN)
        self.assertIn(marks.MSG_MOVING_OPEN + first + marks.MSG_MOVING_CLOSE, self.text())
        await self.press(forward_key(keybindings.ClipPage.CARRY), forward_key(keybindings.ClipPage.CARRY), forward_key(keybindings.ClipPage.CARRY))
        await self.press(keybindings.ClipPage.DROP)
        self.assertEqual(self.patterns(), [OTHER, first, first])
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.patterns(), [first, OTHER, first])

    async def test_pattern_order_steps_through_the_orders_and_stops_at_the_ends(self):
        await self.select_field(labels_text.MSG_PATTERN_ORDER_LABEL)
        self.assertEqual(self.clip_slot().get_pattern_order(), PatternOrder.FORWARD)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.clip_slot().get_pattern_order(), PatternOrder.FORWARD)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.clip_slot().get_pattern_order(), file_format.PATTERN_ORDERS[1])
        for _ in file_format.PATTERN_ORDERS:
            await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.clip_slot().get_pattern_order(), PatternOrder.FIRST_THEN_RANDOM)
        self.assertIn(labels_text.MSG_PATTERN_ORDER_NAMES[PatternOrder.FIRST_THEN_RANDOM], self.text())

    async def test_arrange_counts_the_patterns_after_the_first(self):
        first = self.patterns()[0]
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.PATTERNS, value=[first, OTHER, first])
        self.document.record_edit()
        await self.press(Key.ESCAPE)
        self.assertIn(marks.MSG_CLIP_PATTERNS_COUNTED.format(name=first, more=2), self.text())

    async def test_the_scale_field_gives_the_clip_a_scale_of_its_own_and_takes_it_away(self):
        self.document.add_scale(name=CLIP_SCALE, root=CLIP_SCALE_ROOT, kind=CLIP_SCALE_KIND)
        self.document.record_edit()
        self.assertIsNone(self.clip_slot().get_scale_name())
        await self.select_field(labels_text.MSG_SCALE_LABEL)
        await self.press(Key.ENTER)
        await self.type(CLIP_SCALE)
        await self.press(Key.ENTER)
        self.assertEqual(self.clip_slot().get_scale_name(), CLIP_SCALE)
        await self.press(Key.ENTER)
        for _ in self.document.get_setlist().get_scale_names():
            await self.press(Key.UP)
        await self.press(Key.ENTER)
        self.assertIsNone(self.clip_slot().get_scale_name())

    async def test_advance_shows_the_sets_default_until_the_clip_sets_its_own_and_is_chosen_from_the_three_values(self):
        # No (default) choice; a clip that sets nothing shows the File page's Default follow action, saying it comes from the set.
        self.assertIsNone(self.clip_slot().get_written_follow_action())
        self.assertEqual(self.follow_action_text(), marks.MSG_FROM_SET_SHOWN.format(value=labels_text.MSG_FOLLOW_ACTION_NAMES[FollowAction.WITH_SCENE]))
        self.document.change_set(self.document.get_setlist().set_default_follow_action, FollowAction.OFF)
        self.assertEqual(self.follow_action_text(), marks.MSG_FROM_SET_SHOWN.format(value=labels_text.MSG_FOLLOW_ACTION_NAMES[FollowAction.OFF]))
        self.document.change_set(self.document.get_setlist().set_default_follow_action, FollowAction.WITH_SCENE)
        self.assertIsNone(self.clip_slot().get_written_follow_action())
        await self.select_field(labels_text.MSG_FOLLOW_ACTION_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [labels_text.MSG_FOLLOW_ACTION_NAMES[choice] for choice in file_format.FOLLOW_ACTION_CHOICES])
        await self.press(Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.clip_slot().get_written_follow_action(), FollowAction.OFF)
        self.assertEqual(self.follow_action_text(), labels_text.MSG_FOLLOW_ACTION_NAMES[FollowAction.OFF])
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
        # The page has one pattern, so P works wherever the triangle is, and the crumbs say the way back.
        scene = self.document.song().get_scenes()[0].get_name()
        for label in (labels_text.MSG_PATTERNS_LABEL, labels_text.MSG_REPEAT_LABEL):
            with self.subTest(label=label):
                await self.select_field(label)
                self.assertIn(ui_testing.KEY_SHOWN.format(label=key_name(keybindings.ClipPage.OPEN_PATTERN)) + legends.MSG_LEGEND_WHAT.format(what=legends.MSG_OPEN_PATTERN_WHAT), self.text())
                await self.press(keybindings.ClipPage.OPEN_PATTERN)
                self.assertIsInstance(self.app.screen, PatternEditor)
                self.assertEqual(self.app.screen.item, self.clip_slot().get_pattern_name())
                trail = marks.MSG_CRUMB_SEPARATOR.join([
                    labels_text.Crumb.ARRANGE, labels_text.MSG_CLIP_CRUMB.format(scene=scene, track=LEAD), labels_text.MSG_PATTERN_CRUMB.format(name=self.clip_slot().get_pattern_name()),
                ])
                self.assertIn(drawing.SPACE + trail + drawing.SPACE, self.crumbs_line())
                await self.press(Key.ESCAPE)
                self.assertIs(self.app.screen, self.page)
                self.assertEqual(self.page.field().label, label)

    async def test_the_name_field_names_the_clip_and_the_grid_shows_it(self):
        self.assertEqual(self.labels()[0], labels_text.MSG_NAME_LABEL)
        self.assertIn(marks.MSG_CLIP_NAMED_FOR_PATTERN.format(pattern=TUNE), self.text())
        await self.go_to(labels_text.MSG_NAME_LABEL)
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
        await self.go_to(labels_text.MSG_NAME_LABEL)
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
        self.assertIn(errors.ERR_LOOP_SCENES_INTRO, ' '.join(self.app.screen.messages))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        await self.press(Key.ENTER)
        self.assertFalse(self.clip_slot().loops())

    async def test_chains_are_added_on_their_list_page_and_cleared_from_the_field(self):
        await self.go_to(CHAIN)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GeneratorListPage)
        await self.press(keybindings.GeneratorListPage.ADD)
        await self.pick(listed_generator(setlist=self.document.get_setlist(), name=NAMED))
        await self.press(keybindings.GeneratorListPage.ADD)
        await self.pick(listed_generator(setlist=self.document.get_setlist(), name=NAMED))
        self.assertEqual(self.clip_slot().get_chain_names(), [NAMED, NAMED])
        await self.press(Key.ESCAPE)
        self.assertIn(marks.MSG_CHAIN_JOIN.join([listed_generator(setlist=self.document.get_setlist(), name=NAMED)] * 2), self.text())
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

    async def test_they_are_at_the_bottom_of_the_page(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.set_clip_slot_morph_target(index=0, track=LEAD, pattern=OTHER)
        # Grab track is the last of the fields that shape the notes; only Follow action, which real-time playback alone reads, comes after it, and then the sections of Density, Swell and Articulate, and the Play and Stop buttons.
        fields = self.page.fields()
        first_heading = next(place for place, field in enumerate(fields) if isinstance(field, Heading))
        labels = [field.label for field in fields[:first_heading]]
        self.assertEqual(labels[-2:], [GRAB_TRACK, labels_text.MSG_FOLLOW_ACTION_LABEL])

    async def test_choosing_none_clears(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        await self.go_to(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.app.screen.cursor.set_place(0)
        await self.press(Key.ENTER)
        self.assertIsNone(self.clip_slot().get_grab_track())

    async def test_choosing_a_grab_track(self):
        await self.go_to(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.options, ['(none)', DRUMS])
        self.app.screen.cursor.set_place(1)
        await self.press(Key.ENTER)
        self.assertEqual(self.clip_slot().get_grab_track(), DRUMS)

    async def test_a_circular_grab_is_refused_with_a_message(self):
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        await self.go_to(GRAB_TRACK)
        await self.press(Key.ENTER)
        self.app.screen.cursor.set_place(1)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(CIRCULAR_GRAB, self.text())
        self.assertIn('a circle: lead → drums →', self.text())
        self.assertIn('Remove the grab from another clip in this scene first.', self.text())
        self.assertIsNone(self.clip_slot().get_grab_track())

    def notes_text(self):
        return NEW_LINE.join(line.plain for line in self.page.remarks(self.app.size.width))

    async def test_says_when_the_grab_track_has_no_grab_steps_to_change(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        self.page.draw()
        await self.pilot.pause()
        # The notes stand under the settings, below what a small console shows until the cursor goes down the page.
        self.assertIn(THIS_PATTERN_HAS_NONE_YET, self.notes_text())
        self.document.change_pattern(self.document.pattern(TUNE).set_value, row=Row.GRAB, step=0, value=True)
        self.page.draw()
        await self.pilot.pause()
        self.assertNotIn(THIS_PATTERN_HAS_NONE_YET, self.notes_text())
        render_song(self.document.song())

    async def test_the_grid_marks_them(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        await self.press(Key.ESCAPE)
        self.assertIn(TUNE_G, self.text())

    async def test_a_pattern_in_use_this_way_cannot_be_deleted(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.REPEAT, value=2)
        self.document.set_clip_slot_morph_target(index=0, track=LEAD, pattern=OTHER)
        await self.press(Key.ESCAPE, Key.ESCAPE)
        await self.open_patterns_on(OTHER)
        await self.press(Key.BACKSPACE)
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
        page.cursor.set_place([field.label for field in page.fields()].index(GRAB_TRACK))
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

    async def test_shows_the_length_of_its_longest_clip(self):
        self.assertIn(LENGTH, self.text())
        self.assertIn('0:01', self.text())

    async def test_the_section_is_chosen_from_the_kinds_a_scene_may_be_and_stepped_back_to_none(self):
        self.assertIn(marks.MSG_NONE_SHOWN, next(line for line in self.text().split(NEW_LINE) if labels_text.MSG_SCENE_SECTION_LABEL in line))
        await self.go_to(labels_text.MSG_SCENE_SECTION_LABEL)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.scene().get_section(), file_format.SECTION_KINDS[0])
        await self.press(Key.ENTER)
        # The list is longer than a small console, so its first kinds are looked for.
        for kind in file_format.SECTION_KINDS[:FIRST_WORDS]:
            self.assertIn(kind, self.text())
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.scene().get_section(), file_format.SECTION_KINDS[1])
        await self.press(*[key_of(binding=keybindings.ScenePage.LESS, key=Key.LEFT_BRACKET)] * len(file_format.SECTION_KINDS))
        self.assertIsNone(self.scene().get_section())

    async def test_scale_can_be_set_and_cleared(self):
        await self.go_to(SCALE)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(self.scene().get_scale_name(), setlist.DEFAULT_SCALE)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.scene().get_scale_name())

    async def test_tempo_and_ramp(self):
        await self.go_to(TEMPO)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.scene().get_tempo_setting(), 121)
        # A ramp's section is closed until opened, and a blank part steps from the scene's tempo.
        end = labels_text.MSG_TEMPO_RAMP_LABELS[(RampWay.IN, RampPart.END)]
        self.assertNotIn(end, [field.label for field in self.page.shown_fields()])
        await self.go_to(labels_text.MSG_TEMPO_RAMP_SECTIONS[RampWay.IN])
        await self.press(keybindings.FieldPage.TOGGLE)
        await self.go_to(end)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        # With no bars given there is no ramp yet.
        self.assertIsNone(self.scene().get_tempo_ramp(RampWay.IN))
        self.assertEqual(self.scene().get_tempo_setting(), 121)
        await self.go_to(labels_text.MSG_TEMPO_RAMP_LABELS[(RampWay.IN, RampPart.OVER)])
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.scene().get_tempo_ramp(RampWay.IN), TempoRamp(None, 122, limits.MIN_RAMP_BARS + 1))
        render_song(self.document.song())
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.scene().get_tempo_ramp(RampWay.IN))
        self.assertEqual(self.scene().get_tempo_setting(), 121)

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
        label = labels_text.MSG_RESET_LABEL.format(name=RegisterName.BX)
        await self.go_to(label)
        await self.press(Key.ENTER)
        self.assertEqual(self.scene().get_reset_names(), [RegisterName.BX])
        await self.press(Key.SPACE)
        self.assertEqual(self.scene().get_reset_names(), [])

    async def test_it_can_reset_each_draw_as_it_first_starts(self):
        await self.go_to(labels_text.MSG_RESET_LABEL.format(name=DrawName.CD))
        await self.press(Key.ENTER)
        self.assertEqual(self.scene().get_reset_draw_names(), [DrawName.CD])
        await self.press(Key.SPACE)
        self.assertEqual(self.scene().get_reset_draw_names(), [])


class TestScenesAndClipsEdges(UITest):

    async def scene_page(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)
        return self.app.screen

    async def go_to(self, page, label):
        page.cursor.set_place([field.label for field in page.fields()].index(label))
        page.draw()
        await self.pilot.pause()

    def scene(self):
        return self.document.song().get_scenes()[0]

    async def test_a_scenes_tempo_and_its_ramp_are_set_and_cleared_apart(self):
        self.document.change_set(self.document.song().get_scene(0).set_tempo, 100)
        self.document.change_set(self.document.song().get_scene(0).set_tempo_ramp_setting, way=RampWay.OUT, part=RampPart.END, value=120)
        self.document.change_set(self.document.song().get_scene(0).set_tempo_ramp_setting, way=RampWay.OUT, part=RampPart.OVER, value=limits.MIN_RAMP_BARS)
        page = await self.scene_page()
        await self.go_to(page, TEMPO)
        await self.press(key_of(binding=keybindings.ScenePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual((self.scene().get_tempo_setting(), self.scene().get_tempo_ramp(RampWay.OUT)), (101, TempoRamp(None, 120, limits.MIN_RAMP_BARS)))
        await self.press(Key.BACKSPACE)
        self.assertEqual((self.scene().get_tempo_setting(), self.scene().get_tempo_ramp(RampWay.OUT)), (None, TempoRamp(None, 120, limits.MIN_RAMP_BARS)))

    async def test_choosing_the_songs_scale_clears_the_scenes(self):
        self.document.change_set(self.document.song().get_scene(0).set_scale_name, name=setlist.DEFAULT_SCALE, song=self.document.song())
        page = await self.scene_page()
        await self.go_to(page, SCALE)
        await self.press(Key.ENTER)
        self.app.screen.cursor.set_place(0)
        await self.press(Key.ENTER)
        self.assertIsNone(self.scene().get_scale_name())

    async def clip_page(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.assertIsInstance(self.app.screen, ClipPage)
        return self.app.screen

    async def test_removing_the_last_chain_on_its_list_page_leaves_none(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[NAMED])
        page = await self.clip_page()
        await self.go_to(page, CHAIN)
        await self.press(Key.ENTER)
        await self.press(keybindings.GeneratorListPage.REMOVE)
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
OUT_OF_ORDER_START = fixed_text(errors.ERR_OUT_OF_ORDER)


class TestRegistersPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.REGISTERS)
        self.page = self.app.screen

    def label(self, *, name, what):
        return labels_text.MSG_REGISTER_FIELD_LABEL.format(name=name, what=what)

    def register(self, name):
        return self.document.register(name)

    async def test_it_opens_from_the_main_screen_with_every_register(self):
        self.assertIsInstance(self.page, RegistersPage)
        labels = [field.label for field in self.page.fields()]
        for name in file_format.REGISTER_NAMES:
            for _, what in labels_text.MSG_REGISTER_NUMBER_FIELDS:
                self.assertIn(self.label(name=name, what=what), labels)
            for what in (labels_text.MSG_REGISTER_RESET_BEHAVIOR_FIELD, labels_text.MSG_REGISTER_RESET_EACH_SCENE_FIELD, labels_text.MSG_REGISTER_ALLOWED_INC_MAX_FIELD):
                self.assertIn(self.label(name=name, what=what), labels)

    async def test_it_is_a_grid_the_arrows_move_over_stopping_at_every_edge(self):
        # A row for each register and a column for each setting, the cursor stopping at every edge.
        columns = len(self.page.fields()) // len(file_format.REGISTER_NAMES)
        await self.press(Key.UP, Key.LEFT)
        self.assertEqual(self.page.cursor.get_place(), 0)
        await self.press(Key.DOWN, Key.RIGHT)
        self.assertEqual(self.page.cursor.get_place(), columns + 1)
        await self.press(*[Key.DOWN] * len(file_format.REGISTER_NAMES), *[Key.RIGHT] * columns)
        self.assertEqual(self.page.cursor.get_place(), len(self.page.fields()) - 1)
        self.assertEqual(self.page.field().label, self.label(name=file_format.REGISTER_NAMES[-1], what=labels_text.MSG_REGISTER_RESET_EACH_SCENE_FIELD))
        for heading in labels_text.MSG_REGISTER_COLUMNS:
            self.assertIn(heading, self.text())

    async def test_numbers_change_and_go_back_to_their_defaults(self):
        await self.select_field(self.label(name=RegisterName.BX, what=RegisterSetting.MAXIMUM))
        await self.press(key_of(binding=keybindings.RegistersPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), defaults.DEFAULT_REGISTER_MAXIMUM + 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.register(RegisterName.BX).get_maximum(), defaults.DEFAULT_REGISTER_MAXIMUM)
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
        self.assertEqual(self.register(RegisterName.AX).get_minimum(), defaults.DEFAULT_REGISTER_MINIMUM)
        self.assertIn(OUT_OF_ORDER_START, self.text())

    async def test_reset_behavior_steps_through_its_choices_and_reset_each_scene_toggles(self):
        await self.select_field(self.label(name=RegisterName.CX, what=labels_text.MSG_REGISTER_RESET_BEHAVIOR_FIELD))
        await self.press(key_of(binding=keybindings.RegistersPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.register(RegisterName.CX).get_reset_behavior(), file_format.RESET_BEHAVIORS[1])
        self.assertIn(labels_text.MSG_RESET_BEHAVIOR_NAMES[file_format.RESET_BEHAVIORS[1]], self.text())
        await self.press(key_of(binding=keybindings.RegistersPage.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.register(RegisterName.CX).get_reset_behavior(), file_format.RESET_BEHAVIORS[0])
        self.assertNotIn(Section.REGISTERS, self.document.song().to_data())
        await self.select_field(self.label(name=RegisterName.CX, what=labels_text.MSG_REGISTER_RESET_EACH_SCENE_FIELD))
        await self.press(Key.ENTER)
        self.assertTrue(self.register(RegisterName.CX).resets_each_scene())
        await self.press(Key.ENTER)
        self.assertFalse(self.register(RegisterName.CX).resets_each_scene())

    async def test_a_lower_allowed_inc_max_brings_the_adds_within_it_and_undo_brings_them_back(self):
        add_row = file_format.REGISTER_ADD_ROWS[RegisterName.AX]
        self.document.change_pattern(self.document.pattern(TUNE).set_value, row=add_row, step=0, value=BIG_ADD)
        self.document.change_pattern(self.document.pattern(TUNE).set_value, row=add_row, step=1, value=-BIG_ADD)
        self.document.record_edit()
        await self.select_field(self.label(name=RegisterName.AX, what=labels_text.MSG_REGISTER_ALLOWED_INC_MAX_FIELD))
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
        self.assertEqual(Document.load('x.yml').register(RegisterName.AX).get_maximum(), defaults.DEFAULT_REGISTER_MAXIMUM - 1)
