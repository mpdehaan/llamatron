# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests Arrange's details view (R): the details under every bar, the marks after a clip's name, the columns and rows growing to fit, the coloured dividers, and every key working as in the usual view."""

import unittest

from llamatron.interface.tracker import keybindings, themes
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Box, Style
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange import arrange_details, arrange_drawing, arrange_page
from llamatron.interface.tracker.screens.arrange.arrange_details import clip_details, detailed_clip_text, details_layout, scene_details, track_details
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.tracker.screens.arrange.clip_page import ClipPage
from llamatron.interface.tracker.screens.generators.chain_editor import ChainEditor
from llamatron.interface.tracker.screens.generators.generator_pages import generator_page_of_kind
from llamatron.interface.tracker.screens.set.groove_editor import GrooveEditor
from llamatron.interface.tracker.screens.set.instrument_editor import InstrumentEditor
from llamatron.interface.tracker.screens.set.scale_page import ScalePage
from llamatron.interface.tracker.screens.shared.generator_names import listed_generator
from llamatron.interface.visualizers import modes
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import ClipSlotSetting, Direction, EuclidPart, FollowAction, RampPart, RampWay, RegisterName, Shape, StrumDirection, StrumPart
from llamatron.user_strings import labels, legends, marks, names
from tests.support import ui_testing
from tests.support.ui_testing import a_song, UITest

FIRST_SCENE = 0
SECOND_SCENE = 1
SOME_REPEATS = 4
OWN_SCALE = 'D Dorian'
OWN_SCALE_ROOT = 'D'
OWN_SCALE_KIND = 'dorian'
SCENE_TEMPO = 132
RAMP_END = 140
RAMP_BARS = 2
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
    return [line.text for line in lines if line.target is None or line.target.kind != arrange_details.ADD_CHAIN]


class TestDetails(unittest.TestCase):
    """What each clip, scene and track shows in the details view, and only what isn't the default."""

    def setUp(self):
        self.document = a_song()
        self.song = self.document.song()
        self.setlist = self.document.get_setlist()

    def clip_slot(self):
        return self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD)

    def clip_lines(self):
        return own_texts(clip_details(setlist=self.setlist, song=self.song, clip_slot=self.clip_slot()))

    def scene_lines(self, *, index=FIRST_SCENE):
        return own_texts(scene_details(song=self.song, scene=self.song.get_scenes()[index]))

    def track_lines(self, *, name=ui_testing.LEAD):
        return own_texts(track_details(song=self.song, track=self.song.get_track(name)))

    def test_a_plain_clip_scene_and_track_show_nothing(self):
        self.assertEqual(self.clip_lines(), [])
        self.assertEqual(self.scene_lines(), [])
        self.assertEqual(self.track_lines(), [])

    def test_a_chain_shows_its_name_in_parentheses_and_its_generators_under_it_in_order(self):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.CHAINS, value=[ui_testing.NAMED])
        # A cell holds chains, so the details list the chains, chain: name, and a + to add one.
        self.assertEqual(self.clip_lines(), [marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED)])
        self.assertEqual(texts(clip_details(setlist=self.setlist, song=self.song, clip_slot=self.clip_slot()))[1], marks.MSG_DETAILS_ADD_CHAIN)
        # A chain is drawn in the chains' theme colour and a generator in the generators', since a kind has one colour everywhere.
        lines = clip_details(setlist=self.setlist, song=self.song, clip_slot=self.clip_slot())
        self.assertEqual(lines[0].style, themes.text_style(themes.GENERATORS))
        self.assertEqual(lines[1].target.kind, arrange_details.ADD_CHAIN)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_chain_names, names=[ui_testing.NAMED, ui_testing.NAMED], song=self.document.song())
        self.assertEqual(self.scene_lines().count(marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED)), 2)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_chain_names, names=[ui_testing.NAMED], song=self.document.song())
        self.assertEqual(self.track_lines()[0], marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED))

    def test_a_scale_shows_only_where_it_differs_from_the_songs(self):
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_scale_name, name=self.song.get_scale_name(), song=self.document.song())
        self.assertEqual(self.scene_lines(), [])
        self.document.add_scale(name=OWN_SCALE, root=OWN_SCALE_ROOT, kind=OWN_SCALE_KIND)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_scale_name, name=OWN_SCALE, song=self.document.song())
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.SCALE, value=OWN_SCALE)
        self.assertEqual(self.scene_lines(), [marks.MSG_DETAILS_SCALE.format(name=OWN_SCALE)])
        self.assertEqual(self.clip_lines(), [marks.MSG_DETAILS_SCALE.format(name=OWN_SCALE)])

    def test_a_clip_shows_its_grab_its_advance_unless_it_is_the_default_its_strum_and_its_shapes(self):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.FOLLOW_ACTION, value=self.setlist.get_default_follow_action())
        self.assertEqual(self.clip_lines(), [])
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=ui_testing.DRUMS)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.FOLLOW_ACTION, value=FollowAction.NEXT)
        self.document.change_set(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).set_strum_setting, part=StrumPart.DIRECTION, value=StrumDirection.DOWN)
        self.document.change_set(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).set_written, name=ClipSlotSetting.DENSITY_START, value=DENSITY_START)
        self.document.change_set(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).set_written, name=ClipSlotSetting.DENSITY_END, value=DENSITY_END)
        self.assertEqual(self.clip_lines(), [
            marks.MSG_DETAILS_GRAB.format(track=ui_testing.DRUMS), marks.MSG_DETAILS_ADVANCE.format(action=labels.MSG_FOLLOW_ACTION_NAMES[FollowAction.NEXT]),
            marks.MSG_DETAILS_STRUM.format(direction=StrumDirection.DOWN),
            marks.MSG_DETAILS_SHAPE.format(shape=marks.MSG_DETAILS_SHAPE_NAMES[Shape.DENSITY], start=DENSITY_START, end=DENSITY_END),
        ])

    def test_a_scene_shows_its_tempo_or_its_ramp_its_groove_and_its_resets(self):
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_tempo, SCENE_TEMPO)
        self.assertEqual(self.scene_lines(), [marks.MSG_DETAILS_TEMPO.format(tempo=SCENE_TEMPO)])
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_tempo_ramp_setting, way=RampWay.IN, part=RampPart.END, value=RAMP_END)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_tempo_ramp_setting, way=RampWay.IN, part=RampPart.OVER, value=RAMP_BARS)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_groove_choice, choice=False, song=self.document.song())
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_reset, register=RegisterName.AX, on=True)
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_reset, register=RegisterName.DX, on=True)
        self.assertEqual(self.scene_lines(), [
            marks.MSG_DETAILS_TEMPO_RAMPS.format(tempo=SCENE_TEMPO),
            marks.MSG_DETAILS_NO_GROOVE,
            marks.MSG_DETAILS_RESET.format(registers=RegisterName.AX + ', ' + RegisterName.DX),
        ])
        self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_groove_choice, choice=SONG_GROOVE, song=self.document.song())
        self.assertIn(marks.MSG_DETAILS_GROOVE.format(name=SONG_GROOVE), self.scene_lines())

    def test_a_track_shows_its_instrument_transpose_euclid_strum_and_mute(self):
        self.document.add_instrument(INSTRUMENT)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=INSTRUMENT)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_transpose, TRANSPOSE)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_euclid_setting, part=EuclidPart.HITS, value=EUCLID_HITS)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_euclid_setting, part=EuclidPart.STEPS, value=EUCLID_STEPS)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_strum_setting, part=StrumPart.DIRECTION, value=StrumDirection.UP)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_mute, True)
        self.assertEqual(self.track_lines(), [
            marks.MSG_DETAILS_INSTRUMENT.format(name=INSTRUMENT), marks.MSG_DETAILS_TRANSPOSE.format(amount=TRANSPOSE),
            marks.MSG_DETAILS_EUCLID.format(hits=EUCLID_HITS, steps=EUCLID_STEPS), marks.MSG_DETAILS_STRUM.format(direction=StrumDirection.UP), marks.MSG_DETAILS_MUTED,
        ])

    def test_a_clips_name_line_marks_its_loop_and_repeats_and_its_morph_and_direction_are_spelled_out_on_lines(self):
        self.assertEqual(detailed_clip_text(self.clip_slot()), ui_testing.TUNE)
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=SOME_REPEATS)
        self.document.set_clip_slot_morph_target(index=FIRST_SCENE, track=ui_testing.LEAD, pattern=ui_testing.OTHER)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.PENDULUM)
        self.assertEqual(detailed_clip_text(self.clip_slot()), marks.MSG_CLIP_WITH_MARKS.format(name=ui_testing.TUNE, marks=marks.MSG_REPEAT_MARK.format(repeat=SOME_REPEATS)))
        self.assertEqual(self.clip_lines(), [marks.MSG_DETAILS_MORPH.format(pattern=ui_testing.OTHER), marks.MSG_DETAILS_DIRECTION.format(direction=marks.MSG_DETAILS_DIRECTION_NAMES[Direction.PENDULUM])])
        self.assertEqual(detailed_clip_text(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.DRUMS)), marks.MSG_CLIP_WITH_MARKS.format(name=BEAT_NAME(self), marks=marks.MSG_LOOP_MARK))

    def test_every_direction_but_forward_is_spelled_out_and_forward_shows_nothing(self):
        directions = [value for name, value in vars(Direction).items() if name.isupper()]
        self.assertEqual(sorted(marks.MSG_DETAILS_DIRECTION_NAMES), sorted(direction for direction in directions if direction != Direction.FORWARD))
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.FORWARD)
        self.assertEqual(self.clip_lines(), [])

    def test_a_long_detail_is_cut_but_a_clips_name_never_is_and_its_column_widens_to_fit(self):
        self.document.add_chain(LONG_CHAIN)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.CHAINS, value=[LONG_CHAIN])
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.NAME, value=A_LONG_NAME)
        self.assertTrue(all(len(line) <= arrange_details.DETAIL_WIDTH for line in self.clip_lines()))
        layout = details_layout(document=self.document, least_width=arrange_drawing.CELL_WIDTH, name_room=NO_ROOM, detail_room=ROOM, track_name_room=ROOM)
        lead = self.document.track_names().index(ui_testing.LEAD)
        self.assertEqual(layout.track_widths[lead], len(A_LONG_NAME) + NO_ROOM)
        self.assertEqual(layout.track_widths[self.document.track_names().index(ui_testing.DRUMS)], arrange_drawing.CELL_WIDTH)
        self.assertEqual(layout.scene_extra_lines[FIRST_SCENE], 2)
        # The second scene holds nothing but its own stock line and the + that adds a chain.
        self.assertEqual(layout.scene_extra_lines[SECOND_SCENE], 2)


def BEAT_NAME(test):
    return test.document.clip_slot(index=FIRST_SCENE, track=ui_testing.DRUMS).get_display_name()


class TestArrangeDetailsView(UITest):
    """R on Arrange shows the details view and hides it again, every key working in it as in the usual view."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.CHAINS, value=[ui_testing.NAMED])
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
        self.assertIn(legends.MSG_SHOW_DETAILS_WHAT, self.legend())
        self.assertNotIn(marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED), self.text())
        usual = self.drawn()
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        self.assertTrue(self.page.shows_details())
        self.assertIn(legends.MSG_HIDE_DETAILS_WHAT, self.legend())
        self.assertIn(marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED), self.text())
        self.assertIn(marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED), self.text())
        await self.press(keybindings.ArrangePage.HIDE_DETAILS)
        self.assertFalse(self.page.shows_details())
        self.assertEqual(self.drawn(), usual)

    async def test_the_details_view_draws_a_double_divider_after_the_scenes_and_one_between_the_tracks(self):
        self.assertTrue(all(line[arrange_drawing.SCENE_WIDTH] != Box.DOUBLE_BAR for line in self.drawn()))
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        lines = self.drawn()
        self.assertTrue(any(line[arrange_drawing.SCENE_WIDTH] == Box.DOUBLE_BAR for line in lines))
        self.assertTrue(any(line[arrange_drawing.SCENE_WIDTH] == Box.DOUBLE_CROSS for line in lines))
        divider = self.page.drawing.cell_column(1)
        self.assertTrue(any(line[divider] == Box.BAR for line in lines))

    async def test_every_row_grows_by_its_tallest_cells_details_and_a_cell_with_none_says_stock(self):
        usual = len(self.drawn())
        await self.press(keybindings.ArrangePage.SHOW_DETAILS)
        chained = len(clip_details(setlist=self.document.get_setlist(), song=self.document.song(), clip_slot=self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD)))
        # The header's track names and the second scene have no details of their own, so each grows by stock's line and the + line.
        self.assertEqual(len(self.drawn()), usual + 2 + chained + 2)
        self.assertIn(marks.MSG_DETAILS_STOCK, self.text())

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
        self.page.show_visualizer(modes.MODES[0])
        self.assertFalse(self.page.shows_details())
        self.page.hide_visualizer()
        self.assertTrue(self.page.shows_details())


class TestPickingDetails(UITest):
    """Tab inside a cell of the details view picks a line naming something, shown in brackets, and Enter opens its page with Arrange's crumbs first."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_scale(name=OWN_SCALE, root=OWN_SCALE_ROOT, kind=OWN_SCALE_KIND)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.CHAINS, value=[ui_testing.NAMED])
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.SCALE, value=OWN_SCALE)
        self.document.record_edit()
        await self.press(keybindings.MainPage.ARRANGE, keybindings.ArrangePage.SHOW_DETAILS)
        self.page = self.app.screen
        self.page.row = FIRST_SCENE
        self.page.column = self.document.track_names().index(ui_testing.LEAD) + 1
        await self.press(Key.RIGHT, Key.LEFT)

    def legend(self):
        return [binding.what for binding in self.page.shown_keys()]

    def picked_text(self):
        return self.page.drawing.details_at_cursor()[self.page.picked_line()].text

    async def test_tab_on_a_cell_with_no_details_locks_into_it_showing_stock_and_an_empty_slot_has_no_tab(self):
        self.assertIn(legends.MSG_INTO_DETAILS_WHAT, self.legend())
        await self.press(keybindings.ArrangePage.HIDE_DETAILS, Key.LEFT)
        self.assertEqual(texts(self.page.drawing.details_at_cursor()), [marks.MSG_DETAILS_STOCK, marks.MSG_DETAILS_ADD_CHAIN])
        self.assertEqual(self.page.pickable(), [1])
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertTrue(self.page.picking())
        self.assertEqual(self.picked_text(), marks.MSG_DETAILS_ADD_CHAIN)
        self.assertIn(marks.MSG_DETAILS_STOCK, self.text())
        await self.press(keybindings.ArrangePage.OUT_OF_DETAILS, Key.DOWN, Key.RIGHT)
        self.assertIsNone(self.document.clip_slot(index=self.page.row, track=self.page.track()))
        self.assertNotIn(legends.MSG_INTO_DETAILS_WHAT, self.legend())

    async def test_a_locked_cells_box_is_green(self):
        width, height = self.SIZE

        def styles():
            return {span.style for line in self.page.drawing.body(width=width, height=height) for span in line.spans}
        self.assertNotIn(Style.DETAILS_LOCKED, styles())
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertIn(Style.DETAILS_LOCKED, styles())

    async def test_esc_while_locked_leaves_the_cell_and_r_closes_every_detail_and_leaves_the_cell(self):
        # Esc closes the topmost thing: the lock first, staying on Arrange.
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
        self.assertEqual(self.picked_text(), marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED))
        self.assertIn(marks.MSG_PICKED_OPEN + marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED) + marks.MSG_PICKED_CLOSE, self.text())
        await self.press(Key.UP)
        self.assertEqual(self.picked_text(), marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED))
        for _ in range(len(self.page.pickable()) + 2):
            await self.press(Key.DOWN)
        self.assertEqual(self.picked_text(), marks.MSG_DETAILS_SCALE.format(name=OWN_SCALE))
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
        drums = self.document.track_names().index(ui_testing.DRUMS)
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        self.assertTrue(self.page.picking())
        self.assertFalse(self.page.shows_details())
        opened = [line.plain for line in self.page.drawing.body(width=width, height=height)]
        lines = clip_details(setlist=self.document.get_setlist(), song=self.document.song(), clip_slot=self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD))
        self.assertEqual(len(opened), len(usual) + len(lines))
        self.assertIn(marks.MSG_DETAILS_CHAIN.format(name=ui_testing.NAMED), self.text())
        self.assertGreater(self.page.drawing.track_width(self.document.track_names().index(ui_testing.LEAD)), arrange_drawing.CELL_WIDTH)
        self.assertEqual(self.page.drawing.track_width(drums), arrange_drawing.CELL_WIDTH)
        self.assertTrue(all(line[arrange_drawing.SCENE_WIDTH] != Box.DOUBLE_BAR for line in opened if len(line) > arrange_drawing.SCENE_WIDTH))
        await self.press(keybindings.ArrangePage.OUT_OF_DETAILS)
        self.assertEqual([line.plain for line in self.page.drawing.body(width=width, height=height)], usual)

    async def test_enter_opens_a_chains_a_generators_and_a_scales_page_with_arranges_crumbs_first(self):
        for downs, page, word, name in (
            (0, ChainEditor, names.MSG_CHAIN_WORD, ui_testing.NAMED), (2, ScalePage, names.MSG_SCALE_WORD, OWN_SCALE),
        ):
            with self.subTest(page=page.__name__):
                await self.press(keybindings.ArrangePage.INTO_DETAILS)
                for _ in range(downs):
                    await self.press(Key.DOWN)
                await self.press(keybindings.ArrangePage.OPEN_DETAIL)
                self.assertIsInstance(self.app.screen, page)
                self.assertEqual(self.app.screen.crumb_trail(), (labels.Crumb.ARRANGE, labels.MSG_OPENED_ITEM_CRUMB.format(word=word, name=name)))
                await self.press(Key.ESCAPE)
                self.assertIs(self.app.screen, self.page)
                self.assertTrue(self.page.picking())
                await self.press(keybindings.ArrangePage.OUT_OF_DETAILS)

    async def test_on_a_tracks_name_enter_opens_its_instruments_and_its_grooves_page(self):
        self.document.add_instrument(INSTRUMENT)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=INSTRUMENT)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_groove_choice, choice=SONG_GROOVE, song=self.document.song())
        self.document.record_edit()
        self.page.row = arrange_page.HEADER_ROW
        await self.press(Key.RIGHT, Key.LEFT)
        for downs, page, word, name in ((1, InstrumentEditor, names.MSG_INSTRUMENT_WORD, INSTRUMENT), (2, GrooveEditor, names.MSG_GROOVE_WORD, SONG_GROOVE)):
            with self.subTest(page=page.__name__):
                await self.press(keybindings.ArrangePage.INTO_DETAILS)
                for _ in range(downs):
                    await self.press(Key.DOWN)
                await self.press(keybindings.ArrangePage.OPEN_DETAIL)
                self.assertIsInstance(self.app.screen, page)
                self.assertEqual(self.app.screen.crumb_trail(), (labels.Crumb.ARRANGE, labels.MSG_OPENED_ITEM_CRUMB.format(word=word, name=name)))
                await self.press(Key.ESCAPE, keybindings.ArrangePage.OUT_OF_DETAILS)

    def test_every_kind_of_generator_has_a_page_with_an_editor(self):
        for kind in list(generator_plugins.plugins()):
            with self.subTest(kind=kind):
                self.assertIsNotNone(generator_page_of_kind(kind).EDITOR)

    async def test_a_pick_stays_within_the_lines_left_after_an_edit_takes_some_away(self):
        await self.press(keybindings.ArrangePage.INTO_DETAILS)
        for _ in range(2):
            await self.press(Key.DOWN)
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.SCALE, value=None)
        self.document.record_edit()
        self.assertEqual(self.picked_text(), marks.MSG_DETAILS_ADD_CHAIN)

    async def test_plus_adds_a_chain_to_the_cell_alone_and_backspace_takes_one_out(self):
        # Enter on + picks one of the set's chains for this cell, and Bksp on a chain: line removes it from this cell.
        await self.press(keybindings.ArrangePage.INTO_DETAILS, Key.DOWN)
        self.assertEqual(self.picked_text(), marks.MSG_DETAILS_ADD_CHAIN)
        await self.press(keybindings.ArrangePage.ADD_CHAIN)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(listed_generator(setlist=self.document.get_setlist(), name=ui_testing.NAMED))
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).get_chain_names(), [ui_testing.NAMED, ui_testing.NAMED])
        await self.press(Key.UP, keybindings.ArrangePage.REMOVE_CHAIN)
        self.assertEqual(self.document.clip_slot(index=FIRST_SCENE, track=ui_testing.LEAD).get_chain_names(), [ui_testing.NAMED])
        self.assertIn(ui_testing.NAMED, self.document.song().get_setlist().get_chain_names())

if __name__ == '__main__':
    unittest.main()
