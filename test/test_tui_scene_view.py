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
"""Tests Scene View, the user's design: a scene's notes as written and as played, the chord on each beat, what the scene plays with in the end, and the Inset Window on Arrange that only P closes."""

import unittest

from ui_testing import DRUMS, LEAD, NAMED, UITest, back_key, forward_key
from llamatron.composition.file_format import ChordSymbol, ClipSlotSetting
from llamatron.composition.setlist import Setlist
from llamatron.strings.marks import MSG_SCENE_VIEW_FROM_SCENE, MSG_SCENE_VIEW_FROM_SONG, MSG_SCENE_VIEW_ONE_TAKE, MSG_SCENE_VIEW_PLAYED, MSG_SCENE_VIEW_WRITTEN
from llamatron.support.example_sets import example_sets
from llamatron.tui import keybindings
from llamatron.tui.components.inset_window import BORDER, INSET, PADDING, drawn_over, inside_size
from llamatron.tui.drawing import Box
from llamatron.tui.components.scene_view import MOST_CELLS, OVERLAP_CHARACTER, PLAYED_COLOUR, COOL_COLOURS, WARM_COLOURS, coloured, START_CELLS, WRITTEN_COLOUR, SceneView, track_label
from llamatron.tui.keys import Key
from llamatron.tui.scene_notes import beat_chords, chord_of, chord_texts, effective_values, marked_tracks, scene_notes, written_song
from rich.text import Text

DENSITY = 'edm_density.yml'
HALF_TIME = 4
REGISTERS = '22_registers.yml'
NOT_WEREWOLVES = 'not_werewolves.yml'
F_MAJOR = 'F Major'
C = 0
D = 2
E = 4
F = 5
G = 7
A = 9
B_FLAT = 10
MIDDLE_C = 60
OCTAVE = 12
OWN_SCALE = 'D Dorian'
OWN_SCALE_ROOT = 'D'
OWN_SCALE_KIND = 'dorian'
SCREEN_WIDTH = 60
# The share of a beat a note sounds through, for the chord's weights: all of it, and a passing sixteenth's.
LONG = 1
SHORT = 0.25
SCREEN_HEIGHT = 20
INSIDE_LINE = 'inside'
CLOSING = ' P close '
TITLE = 'a title'
SPACE = ' '
NOTHING = ''
SIXTEENTHS_PER_WHOLE = 16
# Enough passes of the test's half-bar tune to last several bars.
BARS_OF_REPEATS = 8
PURE_GREEN = (0, 255, 0)
PURE_RED = (255, 0, 0)
# Far enough right of the first note, a quarter, to leave it.
SIXTEENTHS_PAST_THE_NOTE = 12


def example(name):
    return Setlist.read_file(next(path for path in example_sets() if path.endswith(name)))


class TestSceneNotes(unittest.TestCase):
    """A scene's notes as played and as written, and which clips read the registers."""

    def test_played_shows_what_the_generators_do_and_written_the_patterns_alone(self):
        song = example(DENSITY).get_songs()[0]
        played = scene_notes(song=song, index=HALF_TIME, written=False)
        written = scene_notes(song=song, index=HALF_TIME, written=True)
        self.assertLess(len(played.notes), len(written.notes))
        self.assertEqual(played.length, written.length)

    def test_the_written_copy_leaves_the_song_as_it_was(self):
        song = example(DENSITY).get_songs()[0]
        before = song.to_data()
        copy = written_song(song)
        self.assertEqual(song.to_data(), before)
        self.assertTrue(all(not scene.get_chain_names() for scene in copy.get_scenes()))
        self.assertTrue(all(not slot.get_chain_names() for scene in copy.get_scenes() for slot in (scene.get_clip_slot(name) for name in copy.get_track_names()) if slot))

    def test_clips_that_read_the_registers_are_marked_in_both_views(self):
        song = example(REGISTERS).get_songs()[0]
        self.assertTrue(marked_tracks(song=song, index=0))
        for written in (False, True):
            notes = scene_notes(song=song, index=0, written=written)
            self.assertTrue(notes.marked_tracks)
            self.assertTrue(any(note.marked for note in notes.notes))


class TestChords(unittest.TestCase):
    """The chord on each beat, named and numbered in the scene's scale."""

    def test_the_chord_is_the_one_whose_notes_sound_longest_with_passing_notes_allowed_and_its_bass_named(self):
        self.assertEqual(chord_of(weights={C: LONG, E: LONG, G: LONG}, bass=C), (C, ChordSymbol.MAJOR, None))
        self.assertEqual(chord_of(weights={C: LONG, E: LONG, G: LONG}, bass=E), (C, ChordSymbol.MAJOR, E))
        self.assertEqual(chord_of(weights={D: LONG, F: LONG, A: LONG, C: LONG}, bass=D), (D, ChordSymbol.MINOR7, None))
        self.assertEqual(chord_of(weights={C: LONG, E: LONG, G: LONG, D: SHORT, B_FLAT + 1: SHORT}, bass=C)[1], ChordSymbol.MAJOR)
        self.assertIsNone(chord_of(weights={C: LONG}, bass=C))
        self.assertIsNone(chord_of(weights={C: LONG, C + 1: LONG, D: LONG, D + 1: LONG, E: LONG}, bass=C))

    def test_a_chord_is_spelled_and_numbered_as_the_scale_spells_and_numbers_it(self):
        scale = example(NOT_WEREWOLVES).get_named_scale(F_MAJOR)
        self.assertEqual(chord_texts(root=B_FLAT, symbol=ChordSymbol.MAJOR, scale=scale), ('Bb', 'IV'))
        self.assertEqual(chord_texts(root=D, symbol=ChordSymbol.MINOR, scale=scale), ('Dm', 'vi'))
        self.assertEqual(chord_texts(root=C, symbol=ChordSymbol.DOMINANT7, scale=scale), ('C7', 'V'))

    def test_the_verse_of_not_werewolves_hears_its_chords(self):
        song = example(NOT_WEREWOLVES).get_songs()[0]
        names = [chord.name for chord in beat_chords(notes=scene_notes(song=song, index=1, written=True), scale=song.get_named_scale(F_MAJOR))]
        for name in ('Dm', 'F', 'C', 'Bb'):
            self.assertIn(name, names)


class TestEffectiveValues(UITest):
    """What a scene plays with in the end, and where each value comes from."""

    async def test_each_value_says_where_it_comes_from_and_a_clips_own_scale_is_named(self):
        song = self.document.song()
        effective = effective_values(song=song, index=0)
        self.assertEqual((effective.scale_source, effective.tempo_source, effective.groove_source), (MSG_SCENE_VIEW_FROM_SONG,) * 3)
        self.document.add_scale(name=OWN_SCALE, root=OWN_SCALE_ROOT, kind=OWN_SCALE_KIND)
        self.document.set_scene_scale(index=0, name=OWN_SCALE)
        self.document.set_scene_tempo_ramp(index=0, end=140)
        effective = effective_values(song=self.document.song(), index=0)
        self.assertEqual((effective.scale, effective.scale_source, effective.tempo_source), (OWN_SCALE, MSG_SCENE_VIEW_FROM_SCENE, MSG_SCENE_VIEW_FROM_SCENE))
        self.document.set_scene_scale(index=0, name=None)
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.SCALE, value=OWN_SCALE)
        self.assertEqual(effective_values(song=self.document.song(), index=0).clip_scales, {LEAD: OWN_SCALE})


class TestInsetWindow(unittest.TestCase):
    """An Inset Window's border INSET cells in from every edge, and its inside within."""

    def test_the_outline_and_band_sit_inset_and_the_title_and_view_come_one_cell_in(self):
        screen = [Text(SPACE * SCREEN_WIDTH) for _ in range(SCREEN_HEIGHT)]
        inner_width, inner_height = inside_size(width=SCREEN_WIDTH, height=SCREEN_HEIGHT)
        lines = drawn_over(screen=screen, width=SCREEN_WIDTH, height=SCREEN_HEIGHT, title=TITLE, inside=[Text(INSIDE_LINE)] * inner_height,
                           colour=WRITTEN_COLOUR, closing=CLOSING)
        self.assertEqual(lines[INSET - 1].plain[INSET - 1], Box.TOP_LEFT)
        self.assertEqual(lines[SCREEN_HEIGHT - INSET].plain[SCREEN_WIDTH - INSET], Box.BOTTOM_RIGHT)
        self.assertIn(CLOSING, lines[SCREEN_HEIGHT - 1 - INSET].plain)
        title_row = INSET + BORDER + PADDING
        self.assertTrue(lines[title_row].plain[INSET + BORDER + PADDING:].startswith(TITLE))
        self.assertTrue(lines[title_row + 1].plain[INSET + BORDER + PADDING:].startswith(INSIDE_LINE))
        self.assertEqual(lines[0].plain.strip(), NOTHING)


class TestSceneViewOnArrange(UITest):
    """P on a scene's name opens Scene View over Arrange, Tab switches between as written and as played, and only P closes it."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE)
        self.page = self.app.screen

    async def test_p_opens_it_on_a_scenes_name_with_the_written_caption_and_tab_turns_to_played(self):
        await self.press(keybindings.ArrangePage.SCENE_VIEW)
        self.assertIsInstance(self.page.inset, SceneView)
        self.assertIn(MSG_SCENE_VIEW_WRITTEN, self.text())
        self.assertEqual(self.page.inset.border_colour(), WRITTEN_COLOUR)
        self.assertIn(track_label(name=LEAD, place=self.document.track_names().index(LEAD)), self.text())
        await self.press(keybindings.ArrangePage.TO_PLAYED)
        self.assertEqual(self.page.inset.border_colour(), PLAYED_COLOUR)
        self.assertIn(MSG_SCENE_VIEW_PLAYED.format(take=MSG_SCENE_VIEW_ONE_TAKE)[:40], self.text())
        await self.press(keybindings.ArrangePage.TO_WRITTEN)
        self.assertIn(MSG_SCENE_VIEW_WRITTEN, self.text())

    async def test_esc_or_p_closes_it_and_esc_again_leaves_arrange(self):
        # Esc closes the topmost thing, the user's rule, so the first Esc closes Scene View and the second goes back from Arrange.
        await self.press(keybindings.ArrangePage.SCENE_VIEW, Key.ESCAPE)
        self.assertIs(self.app.screen, self.page)
        self.assertIsNone(self.page.inset)
        await self.press(keybindings.ArrangePage.SCENE_VIEW, keybindings.ArrangePage.CLOSE_INSET)
        self.assertIsNone(self.page.inset)
        await self.press(Key.ESCAPE)
        self.assertIsNot(self.app.screen, self.page)

    async def test_the_arrows_move_its_cursor_and_the_line_under_the_roll_names_what_is_there(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[NAMED])
        self.document.record_edit()
        await self.press(keybindings.ArrangePage.SCENE_VIEW)
        before = self.page.inset.under_cursor(notes=self.page.inset.notes())
        self.assertIn(LEAD, before)
        for _ in range(SIXTEENTHS_PAST_THE_NOTE):
            await self.press(Key.RIGHT)
        self.assertNotEqual(self.page.inset.under_cursor(notes=self.page.inset.notes()), before)


    async def test_minus_and_equals_zoom_from_one_to_five_cells_and_pgdn_scrolls_the_sidebar(self):
        await self.press(keybindings.ArrangePage.SCENE_VIEW)
        self.assertEqual(self.page.inset.zoom(), START_CELLS)
        for _ in range(MOST_CELLS):
            await self.press(forward_key(keybindings.ArrangePage.INSET_ZOOM))
        self.assertEqual(self.page.inset.zoom(), MOST_CELLS)
        await self.press(back_key(keybindings.ArrangePage.INSET_ZOOM))
        self.assertEqual(self.page.inset.zoom(), MOST_CELLS - 1)
        await self.press(forward_key(keybindings.ArrangePage.INSET_SCROLL))
        self.assertIsNotNone(self.page.inset)


    async def test_tracks_at_once_show_the_firsts_colour_behind_the_seconds_x_or_their_count(self):
        await self.press(keybindings.ArrangePage.SCENE_VIEW)
        character, style = self.page.inset.overlap([0, 1])
        self.assertEqual(character, OVERLAP_CHARACTER)
        self.assertEqual(style.bgcolor.get_truecolor(), self.page.inset.track_colour(0))
        self.assertEqual(style.color.get_truecolor(), self.page.inset.track_colour(1))
        character, style = self.page.inset.overlap([0, 1, 2])
        self.assertEqual(character, str(3))
        self.assertEqual(style.bgcolor.get_truecolor(), self.page.inset.track_colour(0))


    async def test_drum_tracks_take_warm_colours_and_the_others_cool_ones_green_first(self):
        await self.press(keybindings.ArrangePage.SCENE_VIEW)
        names = self.document.track_names()
        lead = names.index(LEAD)
        drums = names.index(DRUMS)
        self.document.set_track_drum(name=DRUMS, drum=True)
        self.assertEqual(self.page.inset.track_colour(lead), COOL_COLOURS[0])
        self.assertEqual(self.page.inset.track_colour(drums), WARM_COLOURS[0])
        self.assertEqual(COOL_COLOURS[0], PURE_GREEN)
        self.assertEqual(WARM_COLOURS[0], PURE_RED)

    def test_a_group_with_more_tracks_than_its_colours_borrows_the_others_that_are_left(self):
        others = list(range(len(COOL_COLOURS) + 1))
        colours = coloured(drums=[len(others)], others=others)
        self.assertEqual(colours[others[-1]], WARM_COLOURS[0])
        self.assertEqual(colours[len(others)], WARM_COLOURS[1])
        self.assertEqual(len(set(colours.values())), len(colours))

    async def test_tab_jumps_the_cursor_to_the_next_bar_and_shift_tab_back(self):
        self.document.set_clip_slot_repeat(index=0, track=LEAD, repeat=BARS_OF_REPEATS)
        self.document.record_edit()
        await self.press(keybindings.ArrangePage.SCENE_VIEW)
        view = self.page.inset
        bar = int(view.notes().bar * SIXTEENTHS_PER_WHOLE)
        start = view.notes().length * SIXTEENTHS_PER_WHOLE
        await self.press(forward_key(keybindings.ArrangePage.INSET_BARS))
        self.assertEqual(view.cursor_column() % bar, 0)
        moved = view.cursor_column()
        await self.press(back_key(keybindings.ArrangePage.INSET_BARS))
        self.assertLess(view.cursor_column(), moved)
        self.assertLessEqual(moved, start)


if __name__ == '__main__':
    unittest.main()
