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
"""Tests Arrange's details view (R), the user's design: the details under every bar, the marks after a clip's name, the columns and rows growing to fit, the coloured dividers, and every key working as in the usual view."""

import unittest

from ui_testing import DRUMS, LEAD, NAMED, OTHER, TUNE, UITest, a_song
from llamatron.composition.file_format import ClipSlotSetting, Direction, FollowAction, RegisterName, Shape, StrumDirection, StrumPart, EuclidPart
from llamatron.strings.labels import MSG_FOLLOW_ACTION_NAMES
from llamatron.strings.legends import MSG_HIDE_DETAILS_WHAT, MSG_INTO_DETAILS_WHAT, MSG_SHOW_DETAILS_WHAT
from llamatron.strings.marks import (
    MSG_CLIP_WITH_MARKS, MSG_DETAILS_ADVANCE, MSG_DETAILS_CHAIN, MSG_DETAILS_DIRECTION, MSG_DETAILS_DIRECTION_NAMES, MSG_DETAILS_EUCLID, MSG_DETAILS_GRAB,
    MSG_DETAILS_GROOVE, MSG_DETAILS_INSTRUMENT, MSG_DETAILS_MORPH, MSG_DETAILS_MUTED, MSG_DETAILS_NO_GROOVE, MSG_DETAILS_RESET,
    MSG_DETAILS_SCALE, MSG_DETAILS_SHAPE, MSG_DETAILS_SHAPE_NAMES, MSG_DETAILS_STRUM, MSG_DETAILS_TEMPO, MSG_DETAILS_TEMPO_RAMP, MSG_DETAILS_TRANSPOSE,
    MSG_LOOP_MARK, MSG_REPEAT_MARK,
)
from llamatron.tui import keybindings
from llamatron.tui import themes
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key
from llamatron.tui.screens.arrange_details import ADD_CHAIN, DETAIL_WIDTH, clip_details, detailed_clip_text, details_layout, scene_details, track_details
from llamatron.tui.screens.arrange_drawing import CELL_WIDTH, SCENE_WIDTH
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.instrument_editor import InstrumentEditor
from llamatron.tui.screens.generator_pages import generator_page_of_kind
from llamatron.tui.screens.arrange_page import HEADER_ROW
from llamatron.composition.file_format import GeneratorKind
from llamatron.strings.labels import Crumb, MSG_OPENED_ITEM_CRUMB
from llamatron.strings.marks import MSG_PICKED_CLOSE, MSG_PICKED_OPEN
from llamatron.strings.marks import MSG_DETAILS_ADD_CHAIN, MSG_DETAILS_STOCK
from llamatron.tui.drawing import Style
from llamatron.strings.names import MSG_CHAIN_WORD, MSG_GROOVE_WORD, MSG_INSTRUMENT_WORD, MSG_SCALE_WORD
from llamatron.visualizers.modes import MODES

FIRST_SCENE = 0
SECOND_SCENE = 1
SOME_REPEATS = 4
OWN_SCALE = 'D Dorian'
OWN_SCALE_ROOT = 'D'
OWN_SCALE_KIND = 'dorian'
SCENE_TEMPO = 132
RAMP_END = 140
SONG_GROOVE = 'swing 58'
TRANSPOSE = -7
INSTRUMENT = 'piano'
DENSITY_START = 25
DENSITY_END = 100
EUCLID_HITS = 3
EUCLID_STEPS = 8
A_LONG_NAME = 'a pattern name far longer than any detail is allowed to be'
LONG_CHAIN = 'a chain name far longer than any detail may be'
NO_ROOM = 2
ROOM = 4


def texts(lines):
    return [line.text for line in lines]


def own_texts(lines):
    """Return a cell's lines of details without the + that adds a chain, which every cell has."""
    return [line.text for line in lines if line.target is None or line.target.kind != ADD_CHAIN]


class TestDetails(unittest.TestCase):
    """What each clip, scene and track shows in the details view, and only what isn't the default."""

    def setUp(self):
        self.document = a_song()
        self.song = self.document.song()
        self.setlist = self.document.setlist()

    def clip_slot(self):
        return self.document.clip_slot(index=FIRST_SCENE, track=LEAD)

    def clip_lines(self):
        return own_texts(clip_details(setlist=self.setlist, song=self.song, clip_slot=self.clip_slot()))

    def scene_lines(self, *, index=FIRST_SCENE):
        return own_texts(scene_details(song=self.song, scene=self.song.get_scenes()[index]))

    def track_lines(self, *, name=LEAD):
        return own_texts(track_details(song=self.song, track=self.song.get_track(name)))

    def test_a_plain_clip_scene_and_track_show_nothing(self):
        self.assertEqual(self.clip_lines(), [])
        self.assertEqual(self.scene_lines(), [])
        self.assertEqual(self.track_lines(), [])

    def test_a_chain_shows_its_name_in_parentheses_and_its_generators_under_it_in_order(self):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[NAMED])
        # A cell holds chains, so the details list the chains, chain: name, and a + to add one, the user's design.
        self.assertEqual(self.clip_lines(), [MSG_DETAILS_CHAIN.format(name=NAMED)])
        self.assertEqual(texts(clip_details(setlist=self.setlist, song=self.song, clip_slot=self.clip_slot()))[1], MSG_DETAILS_ADD_CHAIN)
        # A chain is drawn in the chains' theme colour and a generator in the generators', the user's rule that a kind has one colour everywhere.
        lines = clip_details(setlist=self.setlist, song=self.song, clip_slot=self.clip_slot())
        self.assertEqual(lines[0].style, themes.text_style(themes.CHAINS))
        self.assertEqual(lines[1].target.kind, ADD_CHAIN)
        self.document.set_scene_chains(index=FIRST_SCENE, names=[NAMED, NAMED])
        self.assertEqual(self.scene_lines().count(MSG_DETAILS_CHAIN.format(name=NAMED)), 2)
        self.document.set_track_chains(name=LEAD, names=[NAMED])
        self.assertEqual(self.track_lines()[0], MSG_DETAILS_CHAIN.format(name=NAMED))

    def test_a_scale_shows_only_where_it_differs_from_the_songs(self):
        self.document.set_scene_scale(index=FIRST_SCENE, name=self.song.get_scale_name())
        self.assertEqual(self.scene_lines(), [])
        self.document.add_scale(name=OWN_SCALE, root=OWN_SCALE_ROOT, kind=OWN_SCALE_KIND)
        self.document.set_scene_scale(index=FIRST_SCENE, name=OWN_SCALE)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.SCALE, value=OWN_SCALE)
        self.assertEqual(self.scene_lines(), [MSG_DETAILS_SCALE.format(name=OWN_SCALE)])
        self.assertEqual(self.clip_lines(), [MSG_DETAILS_SCALE.format(name=OWN_SCALE)])

    def test_a_clip_shows_its_grab_its_advance_unless_it_is_the_default_its_strum_and_its_shapes(self):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.FOLLOW_ACTION, value=self.setlist.get_default_follow_action())
        self.assertEqual(self.clip_lines(), [])
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.FOLLOW_ACTION, value=FollowAction.NEXT)
        self.document.set_clip_strum_setting(index=FIRST_SCENE, track=LEAD, part=StrumPart.DIRECTION, value=StrumDirection.DOWN)
        self.document.set_clip_shape_setting(index=FIRST_SCENE, track=LEAD, name=ClipSlotSetting.DENSITY_START, value=DENSITY_START)
        self.document.set_clip_shape_setting(index=FIRST_SCENE, track=LEAD, name=ClipSlotSetting.DENSITY_END, value=DENSITY_END)
        self.assertEqual(self.clip_lines(), [
            MSG_DETAILS_GRAB.format(track=DRUMS), MSG_DETAILS_ADVANCE.format(action=MSG_FOLLOW_ACTION_NAMES[FollowAction.NEXT]),
            MSG_DETAILS_STRUM.format(direction=StrumDirection.DOWN),
            MSG_DETAILS_SHAPE.format(shape=MSG_DETAILS_SHAPE_NAMES[Shape.DENSITY], start=DENSITY_START, end=DENSITY_END),
        ])

    def test_a_scene_shows_its_tempo_or_its_ramp_its_groove_and_its_resets(self):
        self.document.set_scene_tempo(index=FIRST_SCENE, tempo=SCENE_TEMPO)
        self.assertEqual(self.scene_lines(), [MSG_DETAILS_TEMPO.format(tempo=SCENE_TEMPO)])
        self.document.set_scene_tempo_ramp(index=FIRST_SCENE, end=RAMP_END)
        self.document.set_scene_groove(index=FIRST_SCENE, choice=False)
        self.document.set_reset(index=FIRST_SCENE, register=RegisterName.AX, on=True)
        self.document.set_reset(index=FIRST_SCENE, register=RegisterName.DX, on=True)
        self.assertEqual(self.scene_lines(), [
            MSG_DETAILS_TEMPO_RAMP.format(start=SCENE_TEMPO, end=RAMP_END), MSG_DETAILS_NO_GROOVE,
            MSG_DETAILS_RESET.format(registers=RegisterName.AX + ', ' + RegisterName.DX),
        ])
        self.document.set_scene_groove(index=FIRST_SCENE, choice=SONG_GROOVE)
        self.assertIn(MSG_DETAILS_GROOVE.format(name=SONG_GROOVE), self.scene_lines())

    def test_a_track_shows_its_instrument_transpose_euclid_strum_and_mute(self):
        self.document.add_instrument(INSTRUMENT)
        self.document.set_track_instrument(name=LEAD, instrument=INSTRUMENT)
        self.document.set_track_transpose(name=LEAD, transpose=TRANSPOSE)
        self.document.set_track_euclid_setting(name=LEAD, part=EuclidPart.HITS, value=EUCLID_HITS)
        self.document.set_track_euclid_setting(name=LEAD, part=EuclidPart.STEPS, value=EUCLID_STEPS)
        self.document.set_track_strum_setting(name=LEAD, part=StrumPart.DIRECTION, value=StrumDirection.UP)
        self.document.set_track_mute(name=LEAD, muted=True)
        self.assertEqual(self.track_lines(), [
            MSG_DETAILS_INSTRUMENT.format(name=INSTRUMENT), MSG_DETAILS_TRANSPOSE.format(amount=TRANSPOSE),
            MSG_DETAILS_EUCLID.format(hits=EUCLID_HITS, steps=EUCLID_STEPS), MSG_DETAILS_STRUM.format(direction=StrumDirection.UP), MSG_DETAILS_MUTED,
        ])

    def test_a_clips_name_line_marks_its_loop_and_repeats_and_its_morph_and_direction_are_spelled_out_on_lines(self):
        self.assertEqual(detailed_clip_text(self.clip_slot()), TUNE)
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=LEAD, repeat=SOME_REPEATS)
        self.document.set_clip_slot_morph_target(index=FIRST_SCENE, track=LEAD, pattern=OTHER)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.PENDULUM)
        self.assertEqual(detailed_clip_text(self.clip_slot()), MSG_CLIP_WITH_MARKS.format(name=TUNE, marks=MSG_REPEAT_MARK.format(repeat=SOME_REPEATS)))
        self.assertEqual(self.clip_lines(), [MSG_DETAILS_MORPH.format(pattern=OTHER), MSG_DETAILS_DIRECTION.format(direction=MSG_DETAILS_DIRECTION_NAMES[Direction.PENDULUM])])
        self.assertEqual(detailed_clip_text(self.document.clip_slot(index=FIRST_SCENE, track=DRUMS)), MSG_CLIP_WITH_MARKS.format(name=BEAT_NAME(self), marks=MSG_LOOP_MARK))

    def test_every_direction_but_forward_is_spelled_out_and_forward_shows_nothing(self):
        directions = [value for name, value in vars(Direction).items() if name.isupper()]
        self.assertEqual(sorted(MSG_DETAILS_DIRECTION_NAMES), sorted(direction for direction in directions if direction != Direction.FORWARD))
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.FORWARD)
        self.assertEqual(self.clip_lines(), [])

    def test_a_long_detail_is_cut_but_a_clips_name_never_is_and_its_column_widens_to_fit(self):
        self.document.add_chain(LONG_CHAIN)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[LONG_CHAIN])
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.NAME, value=A_LONG_NAME)
        self.assertTrue(all(len(line) <= DETAIL_WIDTH for line in self.clip_lines()))
        layout = details_layout(document=self.document, least_width=CELL_WIDTH, name_room=NO_ROOM, detail_room=ROOM, track_name_room=ROOM)
        lead = self.document.track_names().index(LEAD)
        self.assertEqual(layout.track_widths[lead], len(A_LONG_NAME) + NO_ROOM)
        self.assertEqual(layout.track_widths[self.document.track_names().index(DRUMS)], CELL_WIDTH)
        self.assertEqual(layout.scene_extra_lines[FIRST_SCENE], 2)
        # The second scene holds nothing but its own stock line and the + that adds a chain.
        self.assertEqual(layout.scene_extra_lines[SECOND_SCENE], 2)


def BEAT_NAME(test):
    return test.document.clip_slot(index=FIRST_SCENE, track=DRUMS).get_display_name()


class TestArrangeDetailsView(UITest):
    """R on Arrange shows the details view and hides it again, every key working in it as in the usual view."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[NAMED])
        self.document.record_edit()
        await self.press(keybindings.MainPage.ARRANGE)
        self.page = self.app.screen
        self.assertIsInstance(self.page, ArrangePage)

    def drawn(self):
        width, height = self.SIZE
        return [line.plain for line in self.page.drawing.body(width=width, height=height)]

    def legend(self):
        return [binding.what for binding in self.page.shown_keys()]

    async def test_r_shows_the_details_and_r_again_hides_them(self):
        self.assertIn(MSG_SHOW_DETAILS_WHAT, self.legend())
        self.assertNotIn(MSG_DETAILS_CHAIN.format(name=NAMED), self.text())
        usual = self.drawn()
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        self.assertTrue(self.page.shows_details())
        self.assertIn(MSG_HIDE_DETAILS_WHAT, self.legend())
        self.assertIn(MSG_DETAILS_CHAIN.format(name=NAMED), self.text())
        self.assertIn(MSG_DETAILS_CHAIN.format(name=NAMED), self.text())
        await self.press(keybindings.ArrangePage.HIDE_DETAILS)
        self.assertFalse(self.page.shows_details())
        self.assertEqual(self.drawn(), usual)

    async def test_the_details_view_draws_a_double_divider_after_the_scenes_and_one_between_the_tracks(self):
        self.assertTrue(all(line[SCENE_WIDTH] != Box.DOUBLE_BAR for line in self.drawn()))
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        lines = self.drawn()
        self.assertTrue(any(line[SCENE_WIDTH] == Box.DOUBLE_BAR for line in lines))
        self.assertTrue(any(line[SCENE_WIDTH] == Box.DOUBLE_CROSS for line in lines))
        divider = self.page.drawing.cell_column(1)
        self.assertTrue(any(line[divider] == Box.BAR for line in lines))

    async def test_every_row_grows_by_its_tallest_cells_details_and_a_cell_with_none_says_stock(self):
        usual = len(self.drawn())
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        chained = len(clip_details(setlist=self.document.setlist(), song=self.document.song(), clip_slot=self.document.clip_slot(index=FIRST_SCENE, track=LEAD)))
        # The header's track names and the second scene have no details of their own, so each grows by stock's line and the + line.
        self.assertEqual(len(self.drawn()), usual + 2 + chained + 2)
        self.assertIn(MSG_DETAILS_STOCK, self.text())

    async def test_the_cursor_reaches_every_cell_and_its_box_is_always_drawn(self):
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        width, height = self.SIZE
        rows = len(self.document.song().get_scenes())
        columns = len(self.document.track_names())
        for row in range(rows):
            for column in range(columns + 1):
                with self.subTest(row=row, column=column):
                    self.page.row = row
                    self.page.column = column
                    self.page.clamp()
                    first, last = self.page.drawing.visible_tracks(width)
                    shown = self.page.drawing.visible_scenes(height)
                    self.assertIsNotNone(self.page.drawing.frame_place(shown=shown, first=first, last=last))
        for _ in range(rows + columns + 2):
            await self.press(Key.DOWN)
            await self.press(Key.RIGHT)
        self.assertTrue(self.page.on_plus_row())

    async def test_enter_on_a_clip_opens_its_page_as_in_the_usual_view_and_the_view_is_kept(self):
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        await self.press(Key.RIGHT)
        await self.press(keybindings.ArrangePage.EDIT_CLIP)
        self.assertIsInstance(self.app.screen, ClipPage)
        await self.press(keybindings.Page.BACK)
        self.assertTrue(self.app.screen.shows_details())

    async def test_the_visualizer_hides_the_details_and_they_come_back_after_it(self):
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        self.page.show_visualizer(MODES[0])
        self.assertFalse(self.page.shows_details())
        self.page.hide_visualizer()
        self.assertTrue(self.page.shows_details())


class TestPickingDetails(UITest):
    """Tab inside a cell of the details view picks a line naming something, shown in brackets, and Enter opens its page with Arrange's crumbs first."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_scale(name=OWN_SCALE, root=OWN_SCALE_ROOT, kind=OWN_SCALE_KIND)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[NAMED])
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.SCALE, value=OWN_SCALE)
        self.document.record_edit()
        await self.press(keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SHOW_DETAILS)
        self.page = self.app.screen
        self.page.row = FIRST_SCENE
        self.page.column = self.document.track_names().index(LEAD) + 1
        await self.press(Key.RIGHT, Key.LEFT)

    def legend(self):
        return [binding.what for binding in self.page.shown_keys()]

    def picked_text(self):
        return self.page.drawing.details_at_cursor()[self.page.picked_line()].text

    async def test_tab_on_a_cell_with_no_details_locks_into_it_showing_stock_and_an_empty_slot_has_no_tab(self):
        self.assertIn(MSG_INTO_DETAILS_WHAT, self.legend())
        await self.press(keybindings.ArrangePage.HIDE_DETAILS, Key.LEFT)
        self.assertEqual(texts(self.page.drawing.details_at_cursor()), [MSG_DETAILS_STOCK, MSG_DETAILS_ADD_CHAIN])
        self.assertEqual(self.page.pickable(), [1])
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertTrue(self.page.picking())
        self.assertEqual(self.picked_text(), MSG_DETAILS_ADD_CHAIN)
        self.assertIn(MSG_DETAILS_STOCK, self.text())
        await self.press(keybindings.ArrangePage.OUT_OF_DETAILS, Key.DOWN, Key.RIGHT)
        self.assertIsNone(self.document.clip_slot(index=self.page.row, track=self.page.track()))
        self.assertNotIn(MSG_INTO_DETAILS_WHAT, self.legend())

    async def test_a_locked_cells_box_is_green(self):
        width, height = self.SIZE

        def styles():
            return {span.style for line in self.page.drawing.body(width=width, height=height) for span in line.spans}
        self.assertNotIn(Style.DETAILS_LOCKED, styles())
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertIn(Style.DETAILS_LOCKED, styles())

    async def test_esc_while_locked_leaves_the_cell_and_r_closes_every_detail_and_leaves_the_cell(self):
        # Esc closes the topmost thing, the user's rule: the lock first, staying on Arrange.
        await self.press(keybindings.ArrangePage.INTO_DETAILS, Key.ESCAPE)
        self.assertFalse(self.page.picking())
        self.assertIs(self.app.screen, self.page)
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertTrue(self.page.picking())
        await self.press(keybindings.ArrangePage.CLOSE_DETAILS)
        self.assertFalse(self.page.picking())
        self.assertFalse(self.page.shows_details())
        await self.press(keybindings.ArrangePage.INTO_DETAILS, keybindings.ArrangePage.CLOSE_DETAILS)
        self.assertFalse(self.page.picking())
        self.assertIsNone(self.page.opened_cell)

    async def test_tab_picks_the_first_line_in_brackets_and_the_arrows_stop_at_either_end(self):
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertEqual(self.picked_text(), MSG_DETAILS_CHAIN.format(name=NAMED))
        self.assertIn(MSG_PICKED_OPEN + MSG_DETAILS_CHAIN.format(name=NAMED) + MSG_PICKED_CLOSE, self.text())
        await self.press(Key.UP)
        self.assertEqual(self.picked_text(), MSG_DETAILS_CHAIN.format(name=NAMED))
        for _ in range(len(self.page.pickable()) + 2):
            await self.press(Key.DOWN)
        self.assertEqual(self.picked_text(), MSG_DETAILS_SCALE.format(name=OWN_SCALE))
        self.assertEqual(self.page.row, FIRST_SCENE)

    async def test_tab_or_esc_leaves_the_cell_and_left_and_right_do_nothing_meanwhile(self):
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        place = (self.page.row, self.page.column)
        await self.press(Key.LEFT, Key.RIGHT)
        self.assertTrue(self.page.picking())
        self.assertEqual((self.page.row, self.page.column), place)
        await self.press(keybindings.ArrangePage.OUT_OF_DETAILS)
        self.assertFalse(self.page.picking())
        await self.press(keybindings.ArrangePage.INTO_DETAILS, Key.ESCAPE)
        self.assertFalse(self.page.picking())
        self.assertIs(self.app.screen, self.page)

    async def test_in_the_usual_view_tab_opens_the_cell_alone_growing_its_row_and_column_and_tab_again_closes_it(self):
        await self.press(keybindings.ArrangePage.HIDE_DETAILS)
        width, height = self.SIZE
        usual = [line.plain for line in self.page.drawing.body(width=width, height=height)]
        drums = self.document.track_names().index(DRUMS)
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertTrue(self.page.picking())
        self.assertFalse(self.page.shows_details())
        opened = [line.plain for line in self.page.drawing.body(width=width, height=height)]
        lines = clip_details(setlist=self.document.setlist(), song=self.document.song(), clip_slot=self.document.clip_slot(index=FIRST_SCENE, track=LEAD))
        self.assertEqual(len(opened), len(usual) + len(lines))
        self.assertIn(MSG_DETAILS_CHAIN.format(name=NAMED), self.text())
        self.assertGreater(self.page.drawing.track_width(self.document.track_names().index(LEAD)), CELL_WIDTH)
        self.assertEqual(self.page.drawing.track_width(drums), CELL_WIDTH)
        self.assertTrue(all(line[SCENE_WIDTH] != Box.DOUBLE_BAR for line in opened if len(line) > SCENE_WIDTH))
        await self.press(keybindings.ArrangePage.OUT_OF_DETAILS)
        self.assertEqual([line.plain for line in self.page.drawing.body(width=width, height=height)], usual)

    async def test_enter_opens_a_chains_a_generators_and_a_scales_page_with_arranges_crumbs_first(self):
        for downs, page, word, name in (
            (0, ChainEditor, MSG_CHAIN_WORD, NAMED), (2, ScalePage, MSG_SCALE_WORD, OWN_SCALE),
        ):
            with self.subTest(page=page.__name__):
                await self.press(keybindings.ArrangePage.INTO_DETAILS)
                for _ in range(downs):
                    await self.press(Key.DOWN)
                await self.press(keybindings.ArrangePage.OPEN_DETAIL)
                self.assertIsInstance(self.app.screen, page)
                self.assertEqual(self.app.screen.crumb_trail(), (Crumb.ARRANGE, MSG_OPENED_ITEM_CRUMB.format(word=word, name=name)))
                await self.press(Key.ESCAPE)
                self.assertIs(self.app.screen, self.page)
                self.assertTrue(self.page.picking())
                await self.press(keybindings.ArrangePage.OUT_OF_DETAILS)

    async def test_on_a_tracks_name_enter_opens_its_instruments_and_its_grooves_page(self):
        self.document.add_instrument(INSTRUMENT)
        self.document.set_track_instrument(name=LEAD, instrument=INSTRUMENT)
        self.document.set_track_groove(name=LEAD, choice=SONG_GROOVE)
        self.document.record_edit()
        self.page.row = HEADER_ROW
        await self.press(Key.RIGHT, Key.LEFT)
        for downs, page, word, name in ((1, InstrumentEditor, MSG_INSTRUMENT_WORD, INSTRUMENT), (2, GrooveEditor, MSG_GROOVE_WORD, SONG_GROOVE)):
            with self.subTest(page=page.__name__):
                await self.press(keybindings.ArrangePage.INTO_DETAILS)
                for _ in range(downs):
                    await self.press(Key.DOWN)
                await self.press(keybindings.ArrangePage.OPEN_DETAIL)
                self.assertIsInstance(self.app.screen, page)
                self.assertEqual(self.app.screen.crumb_trail(), (Crumb.ARRANGE, MSG_OPENED_ITEM_CRUMB.format(word=word, name=name)))
                await self.press(Key.ESCAPE, keybindings.ArrangePage.OUT_OF_DETAILS)

    def test_every_kind_of_generator_has_a_page_with_an_editor(self):
        for kind in [value for name, value in vars(GeneratorKind).items() if name.isupper()]:
            with self.subTest(kind=kind):
                self.assertIsNotNone(generator_page_of_kind(kind).EDITOR)

    async def test_a_pick_stays_within_the_lines_left_after_an_edit_takes_some_away(self):
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        for _ in range(2):
            await self.press(Key.DOWN)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=LEAD, setting=ClipSlotSetting.SCALE, value=None)
        self.document.record_edit()
        self.assertEqual(self.picked_text(), MSG_DETAILS_ADD_CHAIN)

    async def test_plus_adds_a_chain_to_the_cell_alone_and_backspace_takes_one_out(self):
        # The user's design: Enter on + picks one of the set's chains for this cell, and Bksp on a chain: line removes it from this cell.
        await self.press(keybindings.ArrangePage.INTO_DETAILS, Key.DOWN)
        self.assertEqual(self.picked_text(), MSG_DETAILS_ADD_CHAIN)
        await self.press(keybindings.ArrangePage.ADD_CHAIN)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(NAMED)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=LEAD).get_chain_names(), [NAMED, NAMED])
        await self.press(Key.UP, keybindings.ArrangePage.REMOVE_CHAIN)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=LEAD).get_chain_names(), [NAMED])
        self.assertIn(NAMED, self.document.song().get_chain_names())

if __name__ == '__main__':
    unittest.main()
