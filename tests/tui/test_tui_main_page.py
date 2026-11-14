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

"""The main screen: its two layouts, its cells and counts, the arrows over them, the file's actions and the header."""

from unittest import mock

from tests.support.ui_testing import UITest, key_name
from llamatron.tui.drawing import Box, NOTHING, SPACE
from llamatron.tui.screens.main_page import arrows_between, cell_positions, COLUMNS, moved
from llamatron.strings.marks import MSG_MAIN_CLOCK, MSG_MAIN_MAP_CLIP, MSG_MAIN_MAP_CUT, MSG_MAIN_MAP_EMPTY, MSG_MAIN_MORE_TRACKS, MSG_REAL_TIME_OFF_MARK
from llamatron.composition.file_format import NAMED_GENERATORS
from llamatron.tui.app import LlamatronApp
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.quit_dialog import QuitDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.chains_page import ChainsPage
from llamatron.tui.screens.file_page import FilePage
from llamatron.tui.screens.generators_page import GeneratorsPage
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.tui.screens.scales_page import ScalesPage
from llamatron.tui.screens.open_page import OpenPage
from llamatron.tui.screens.songs_page import SongsPage
from llamatron.support.version import VERSION
from llamatron.strings.labels import Crumb, MSG_ABOUT, MSG_SET_CRUMB, MSG_SONG_CRUMB, MSG_NO_FILE_CRUMB, MSG_QUIT_BUTTONS, MSG_TITLE_LABEL, PageName
from llamatron.strings.legends import MSG_ABOUT_FOOTER_WHAT
from llamatron.strings.marks import MSG_CRUMB_SEPARATOR, MSG_UNSAVED_MARK, MSG_UNSAVED_CHANGES_MARK, MSG_SAVED_MARK
from llamatron.strings.messages import MSG_QUIT_UNSAVED_NOTE, MSG_SAVE_BEFORE_EXPORT_TITLE
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from llamatron.tui.text import clock
from tests.support.page_testing import boxed_line

# Typed into a prompt that ESC then cancels.
ESCAPED_TITLE = 'never'
# Tracks and scenes added to outgrow the main screen's map of the song.
EXTRA_TRACK = 'extra {number}'
EXTRA_SCENE = 'more {number}'
# Letters the tests press on purpose that aren't keys: two letters no page binds, and a letter typed as
# text into the description. Textual's own name for the Ctrl+Q the tracker no longer binds.
CTRL_Q = 'ctrl+q'
EXIT = 'exit'
# The marks the screen's text puts around anything in reverse video, and what joins a cell's lines.
REVERSED_STARTS = '«'
REVERSED_ENDS = '»'


class TestMainPageStartedWithNoSet(UITest):
    """The tracker started with no set named, the user's ask, opens with the main screen's cursor on Open."""

    def make_app(self):
        return LlamatronApp(document=self.document, cursor_on_open=True)

    async def test_the_cursor_starts_on_open_and_enter_opens_the_open_page(self):
        self.assertIs(self.app.screen.selected().binding, keybindings.MainPage.OPEN_SET_HERE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OpenPage)

class TestMainPage(UITest):

    async def test_the_header_keeps_the_crumbs_left_llamatron_centred_and_the_set_and_song_right(self):
        # The user's design: the crumbs, which change with every page, in the left corner of the first line, llamatron centred, and the
        # set and its song as one block at the right, just left of the save mark and the length.
        unsaved = MSG_SET_CRUMB.format(file=MSG_NO_FILE_CRUMB)
        song = MSG_SONG_CRUMB.format(song=MSG_DEFAULT_SONG_NAME)
        self.assert_header(set_crumb=unsaved, song_crumb=song)
        self.assertTrue(self.crumbs_line().startswith(SPACE + Crumb.MAIN_SCREEN + SPACE))
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assert_header(set_crumb=unsaved, song_crumb=song)
        self.assertTrue(self.crumbs_line().startswith(SPACE + Crumb.PATTERNS + MSG_CRUMB_SEPARATOR))
        # The rule, or on a page with a theme its stripe, which is drawn in the theme's colour behind the page's caption.
        self.assertNotIn(Box.RULE * 3, self.text().splitlines()[2])
        # The version is left to the About dialog, and the length sits at the right of the song's line.
        self.assertNotIn(VERSION, self.title_line())
        self.assertTrue(self.song_line().rstrip().endswith(clock(self.app.screen.duration())))
        self.assertNotIn(clock(self.app.screen.duration()), self.title_line())
        # A set with no file yet is unsaved, saving makes it saved, a change gives it unsaved changes, and saving again makes it saved.
        self.assertTrue(self.title_line().rstrip().endswith(MSG_UNSAVED_MARK))
        self.document.save(path='songs/tune.yml')
        await self.press(Key.ESCAPE)
        self.assert_header(set_crumb=MSG_SET_CRUMB.format(file='tune.yml'), song_crumb=song)
        self.assertTrue(self.title_line().rstrip().endswith(MSG_SAVED_MARK))
        # The main screen draws again when a page closes over it, so each change is looked at from a page.
        self.document.changed()
        await self.press(keybindings.MainPage.PATTERNS, Key.ESCAPE)
        self.assertTrue(self.title_line().rstrip().endswith(MSG_UNSAVED_CHANGES_MARK))
        self.document.save(path='songs/tune.yml')
        await self.press(keybindings.MainPage.PATTERNS, Key.ESCAPE)
        self.assertTrue(self.title_line().rstrip().endswith(MSG_SAVED_MARK))

    async def test_o_opens_and_x_exports_on_the_main_screen_without_ctrl_and_the_cells_show_the_letters(self):
        # The user's choice of 2026-11-09, to save a keystroke: the main screen's letters are its own. Ctrl+O and Ctrl+X still work.
        text = self.text()
        self.assertIn(f'« {key_name(keybindings.MainPage.OPEN_SET_HERE)} » {PageName.OPEN}', text)
        self.assertIn(f'« {key_name(keybindings.MainPage.EXPORT_HERE)} » {PageName.EXPORT}', text)
        self.assertIn(f'« {key_name(keybindings.MainPage.SAVE)} » {PageName.SAVE}', text)
        self.assertNotIn(f'« {key_name(keybindings.MainPage.OPEN_SET)} »', text)
        await self.press(keybindings.MainPage.OPEN_SET_HERE)
        self.assertIsInstance(self.app.screen, OpenPage)
        await self.press(Key.ESCAPE, Key.CTRL_O)
        self.assertIsInstance(self.app.screen, OpenPage)
        await self.press(Key.ESCAPE, keybindings.MainPage.EXPORT_HERE)
        # An unsaved set asks to be saved before an export.
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(MSG_SAVE_BEFORE_EXPORT_TITLE, self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_the_keys_that_work_everywhere_come_first_in_every_table_and_stay_out_of_every_footer(self):
        for keys in [[keybindings.MainPage.PATTERNS], [Key.ENTER], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.ARRANGE]]:
            await self.press(*keys)
            page = type(self.app.screen).__name__
            everywhere = keybindings.Page.EVERYWHERE
            handled = [item.binding for item in self.app.screen.key_table()]
            self.assertEqual(handled[:len(everywhere)], everywhere, page)
            shown = [item.binding for item in self.app.screen.shown_keys()]
            self.assertEqual([binding for binding in shown if binding in everywhere], [], page)
            self.assertNotIn('« Ctrl+S »', self.text(), page)
            self.assertNotIn('« F1 »', self.text(), page)

    async def test_each_key_opens_its_page(self):
        for name, page in [(keybindings.MainPage.FILE, FilePage), (keybindings.MainPage.SONGS, SongsPage), (keybindings.MainPage.PATTERNS, PatternsPage), (keybindings.MainPage.CHAINS, ChainsPage), (keybindings.MainPage.GENERATORS, GeneratorsPage), (keybindings.MainPage.SCALES, ScalesPage), (keybindings.MainPage.ARRANGE, ArrangePage)]:
            await self.press(name)
            self.assertIsInstance(self.app.screen, page)
            await self.press(Key.ESCAPE)
            self.assertIsInstance(self.app.screen, MainPage)

    async def test_upper_and_lower_case_are_the_same(self):
        await self.press(first_key(keybindings.MainPage.PATTERNS).upper())
        self.assertIsInstance(self.app.screen, PatternsPage)

    async def test_tab_never_quits(self):
        await self.press(Key.ESCAPE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertTrue(self.app.is_running)

    async def test_quit_asks_only_with_unsaved_changes_and_enter_quits_without_saving(self):
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(keybindings.MainPage.QUIT)
            leave.assert_called_once()
        self.document.changed()
        await self.press(keybindings.MainPage.QUIT)
        self.assertIsInstance(self.app.screen, QuitDialog)
        for button in MSG_QUIT_BUTTONS:
            self.assertIn(button, self.text())
        self.assertIn(MSG_QUIT_UNSAVED_NOTE, self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertTrue(self.app.is_running)
        await self.press(keybindings.MainPage.QUIT, Key.ENTER)
        self.assertIsNotNone(self.app._exit)

    async def test_q_quits_from_the_main_screen_alone_and_ctrl_q_does_nothing(self):
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(keybindings.MainPage.PATTERNS, keybindings.MainPage.QUIT)
            self.assertIsInstance(self.app.screen, PatternsPage)
            await self.pilot.press(CTRL_Q)
            await self.pilot.pause()
            self.assertIsInstance(self.app.screen, PatternsPage)
            leave.assert_not_called()
            await self.press(Key.ESCAPE, keybindings.MainPage.QUIT)
            leave.assert_called_once()

    async def test_shows_the_length_of_the_song(self):
        self.assertIn('0:01', self.text())

    async def test_esc_goes_back_like_tab_and_cancels_a_dialog(self):
        await self.press(keybindings.MainPage.SONGS)
        self.assertIsInstance(self.app.screen, SongsPage)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_TITLE_LABEL)
        await self.press(Key.ENTER)
        await self.type(ESCAPED_TITLE)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertFalse(self.document.setlist().get_title())
        self.assertFalse(self.document.is_dirty())

    async def test_a_tall_console_has_the_smart_fit_layout_arrange_at_the_left_and_two_narrow_columns_at_the_right(self):
        # The user's design: Arrange down all the height at the left; at the right the Real Time switch across both columns, the
        # pages in pairs, and the file's actions in one box, three rows of two.
        page = self.app.screen
        self.assertTrue(page.smart_fit)
        lines = self.text().splitlines()
        line_of = {key_name(item.binding): next(number for number, line in enumerate(lines) if f'« {item.shown_label()} »' in line) for item in page.menu_items()}
        keys = keybindings.MainPage
        self.assertEqual(line_of[key_name(keys.ARRANGE)], line_of[key_name(keys.REAL_TIME)])
        for left, right in ((keys.SONGS, keys.PATTERNS), (keys.SCALES, keys.GENERATORS), (keys.GROOVES, keys.CHAINS), (keys.INSTRUMENTS, keys.REGISTERS), (keys.FILE, keys.EXPORT_HERE), (keys.SAVE, keys.IMPORT_HERE), (keys.OPEN_SET_HERE, keys.QUIT)):
            with self.subTest(left=left):
                self.assertEqual(line_of[key_name(left)], line_of[key_name(right)])
                self.assertGreater(line_of[key_name(left)], line_of[key_name(keys.REAL_TIME)])
        self.assertEqual(line_of[key_name(keys.SAVE)], line_of[key_name(keys.FILE)] + 1)
        self.assertEqual(line_of[key_name(keys.OPEN_SET_HERE)], line_of[key_name(keys.SAVE)] + 1)
        # Arrange's box runs down to the line above the status line, and every line is as wide as the console.
        bottoms = [number for number, line in enumerate(lines) if line.startswith(Box.DOUBLE_BOTTOM_LEFT)]
        self.assertEqual(bottoms, [len(lines) - 4])
        self.assertLessEqual(max(len(line.replace(REVERSED_STARTS, NOTHING).replace(REVERSED_ENDS, NOTHING).rstrip()) for line in lines), self.SIZE[0])
        # The two columns at the right are as narrow as their cells, so Arrange has more than a third of the width.
        self.assertGreater(page.smart_arrange_width(self.SIZE[0]), self.SIZE[0] // COLUMNS)

    async def test_in_the_smart_fit_layout_every_arrow_moves_by_the_geometry_drawn_and_stops_at_every_edge(self):
        keys = keybindings.MainPage
        moves = {
            keys.ARRANGE: (keys.ARRANGE, keys.ARRANGE, keys.ARRANGE, keys.REAL_TIME),
            keys.REAL_TIME: (keys.REAL_TIME, keys.SONGS, keys.ARRANGE, keys.REAL_TIME),
            keys.SONGS: (keys.REAL_TIME, keys.SCALES, keys.ARRANGE, keys.PATTERNS),
            keys.SCALES: (keys.SONGS, keys.GROOVES, keys.ARRANGE, keys.GENERATORS),
            keys.GROOVES: (keys.SCALES, keys.INSTRUMENTS, keys.ARRANGE, keys.CHAINS),
            keys.INSTRUMENTS: (keys.GROOVES, keys.FILE, keys.ARRANGE, keys.REGISTERS),
            keys.PATTERNS: (keys.REAL_TIME, keys.GENERATORS, keys.SONGS, keys.PATTERNS),
            keys.GENERATORS: (keys.PATTERNS, keys.CHAINS, keys.SCALES, keys.GENERATORS),
            keys.CHAINS: (keys.GENERATORS, keys.REGISTERS, keys.GROOVES, keys.CHAINS),
            keys.REGISTERS: (keys.CHAINS, keys.EXPORT_HERE, keys.INSTRUMENTS, keys.REGISTERS),
            keys.FILE: (keys.INSTRUMENTS, keys.SAVE, keys.ARRANGE, keys.EXPORT_HERE),
            keys.SAVE: (keys.FILE, keys.OPEN_SET_HERE, keys.ARRANGE, keys.IMPORT_HERE),
            keys.OPEN_SET_HERE: (keys.SAVE, keys.OPEN_SET_HERE, keys.ARRANGE, keys.QUIT),
            keys.EXPORT_HERE: (keys.REGISTERS, keys.IMPORT_HERE, keys.FILE, keys.EXPORT_HERE),
            keys.IMPORT_HERE: (keys.EXPORT_HERE, keys.QUIT, keys.SAVE, keys.IMPORT_HERE),
            keys.QUIT: (keys.IMPORT_HERE, keys.QUIT, keys.OPEN_SET_HERE, keys.QUIT),
        }
        page = self.app.screen
        self.assertEqual(len(moves), len(page.menu_items()))
        for start, ends in moves.items():
            for arrow, end in zip((Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT), ends):
                with self.subTest(start=start, arrow=arrow):
                    page.select(start)
                    await self.press(arrow)
                    self.assertIs(page.selected().binding, end)

    async def test_in_the_smart_fit_layout_an_arrow_back_returns_to_the_cell_the_cursor_came_from(self):
        keys = keybindings.MainPage
        page = self.app.screen
        # Right from Arrange goes back to the cell at the right the cursor came from.
        for beside in (keys.SONGS, keys.GROOVES, keys.FILE, keys.OPEN_SET_HERE):
            with self.subTest(beside=beside):
                page.select(beside)
                await self.press(Key.LEFT)
                self.assertIs(page.selected().binding, keys.ARRANGE)
                await self.press(Key.RIGHT)
                self.assertIs(page.selected().binding, beside)
        # The Real Time switch is across both columns: Down from it goes back to the column the cursor came up from.
        page.select(keys.PATTERNS)
        await self.press(Key.UP)
        self.assertIs(page.selected().binding, keys.REAL_TIME)
        await self.press(Key.DOWN)
        self.assertIs(page.selected().binding, keys.PATTERNS)
        # The cursor stays on its cell while a page is open over the main screen, and the selected action is reversed in the bar.
        page.select(keys.CHAINS)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainsPage)
        await self.press(Key.ESCAPE)
        self.assertIs(page.selected().binding, keys.CHAINS)
        page.select(keys.QUIT)
        await self.press(Key.UP)
        self.assertIn(f'{PageName.IMPORT} {REVERSED_ENDS}', self.text())

    async def test_the_fewest_arrows_reach_every_cell_from_every_cell_in_both_layouts(self):
        # What the video tutorial walks by: the arrows found are pressed, one layout after the other, and reach the cell.
        page = self.app.screen
        for rows in (page.grid_rows(), page.smart_fit_rows()):
            cells = list({id(item.binding): item.binding for row in rows for item in row}.values())
            for start in cells:
                for end in cells:
                    position = cell_positions(rows=rows, binding=start)[0]
                    arrows = arrows_between(rows=rows, position=position, binding=end)
                    self.assertIsNotNone(arrows, (start, end))
                    self.assertLess(len(arrows), len(rows) + COLUMNS)
                    for arrow in arrows:
                        position = moved(rows=rows, position=position, key=arrow)
                    self.assertIs(rows[position[0]][position[1]].binding, end)
        # On the screen, the arrows to a cell are the ones a person would press.
        self.assertEqual(page.arrows_to(keybindings.MainPage.PATTERNS), [Key.RIGHT, Key.DOWN, Key.RIGHT])
        self.assertEqual(page.arrows_to(keybindings.MainPage.ARRANGE), [])

    async def test_the_map_of_the_song_has_a_line_for_each_track_and_a_block_for_each_scene_with_a_clip(self):
        # The user's design: a track's light, hollow while nothing sounds and always while Real Time is off, its name, then a
        # block where the track has a clip in a scene and a dot where it has none.
        song = self.document.song()
        scenes = range(len(song.get_scenes()))
        for track in song.get_track_names():
            blocks = NOTHING.join(MSG_MAIN_MAP_EMPTY if self.document.clip_slot(index=index, track=track) is None else MSG_MAIN_MAP_CLIP for index in scenes)
            line = next(line for line in self.text().splitlines() if f'{MSG_REAL_TIME_OFF_MARK} {track}' in line)
            self.assertIn(blocks, line)
        self.assertIn(MSG_MAIN_MAP_CLIP, self.text())
        self.assertNotIn(MSG_MAIN_CLOCK.format(at=NOTHING).strip(), boxed_line(self.text()))
        # More tracks than the cell has lines: the first ones, and how many more there are.
        page = self.app.screen
        for number in range(self.SIZE[1]):
            self.document.add_track(EXTRA_TRACK.format(number=number))
        page.draw()
        await self.pilot.pause()
        shown = sum(1 for line in boxed_line(self.text()).splitlines() if MSG_REAL_TIME_OFF_MARK in line)
        tracks = len(self.document.song().get_track_names())
        self.assertLess(shown, tracks)
        self.assertIn(MSG_MAIN_MORE_TRACKS.format(count=tracks - shown), boxed_line(self.text()))
        # More scenes than the line has room for: the first ones, and a mark that the line was cut.
        self.assertNotIn(MSG_MAIN_MAP_CUT, boxed_line(self.text()))
        for number in range(self.SIZE[0]):
            self.document.add_scene(index=len(self.document.song().get_scenes()), name=EXTRA_SCENE.format(number=number))
        page.draw()
        await self.pilot.pause()
        self.assertIn(MSG_MAIN_MAP_CUT, boxed_line(self.text()))
        self.assertLessEqual(max(len(line) for line in boxed_line(self.text()).splitlines()), self.SIZE[0])


class TestMainPageOnAUsualConsole(UITest):
    """The main screen on a console of 80 by 24, too short for the smart fit layout: the grid of three columns."""

    SIZE = (80, 24)

    async def test_a_usual_console_keeps_the_grid_of_three_columns(self):
        self.assertFalse(self.app.screen.smart_fit)
        # With the Real Time switch off, every track has a light, a hollow circle (the user's design).
        for track in self.document.song().get_track_names():
            self.assertIn(f'{MSG_REAL_TIME_OFF_MARK} {track}', boxed_line(self.text()))
        self.assertNotIn(MSG_MAIN_MAP_CLIP, self.text())

    async def test_opens_on_the_main_screen_with_a_cell_for_every_page_and_the_file_actions_and_help_in_the_footer(self):
        self.assertIsInstance(self.app.screen, MainPage)
        text = self.text()
        for binding in keybindings.MainPage.PAGES:
            self.assertIn(f'« {key_name(binding)} »', text)
        for item in [*self.app.screen.menu_items(), *self.app.screen.shown_keys()]:
            self.assertIn(f'« {item.shown_label()} »', text)
        self.assertIn('« Ctrl+S »', text)
        # Undo and Redo have no cell, since they're Ctrl+Z and Ctrl+Y on every page, and F1 lists them.
        self.assertNotIn('« Ctrl+Z »', text)
        self.assertNotIn(PageName.UNDO, text)
        # Arrange first, with a column of pages beside it, three cells to a line, then the bar: File/Global with Save and Open, over Export, Import and Quit.
        lines = text.splitlines()
        self.assertEqual(next(number for number, line in enumerate(lines) if '« A »' in line), next(number for number, line in enumerate(lines) if '« P »' in line))
        self.assertEqual(sum(1 for line in lines if '« F »' in line), 1)
        self.assertEqual(next(line for line in lines if '« P »' in line).count('«'), COLUMNS)
        self.assertIn('« O »', next(line for line in lines if '« F »' in line))
        self.assertIn('« Q »', next(line for line in lines if '« X »' in line))
        self.assertIn(PageName.FILE, text)
        self.assertIn('« F1 »', lines[-1])
        self.assertTrue(lines[-1].rstrip().endswith(MSG_ABOUT_FOOTER_WHAT))

    async def test_each_cell_counts_what_its_page_lists_with_a_space_before_the_border(self):
        page = self.app.screen
        setlist = self.document.setlist()
        counts = {item.keys[0]: page.count(item) for item in page.menu_items()}
        self.assertEqual(counts[first_key(keybindings.MainPage.SONGS)], len(self.document.song_names()))
        self.assertEqual(counts[first_key(keybindings.MainPage.PATTERNS)], len(setlist.get_pattern_names()))
        self.assertEqual(counts[first_key(keybindings.MainPage.CHAINS)], len(setlist.get_chain_names()))
        self.assertEqual(counts[first_key(keybindings.MainPage.SCALES)], len(setlist.get_scale_names()))
        # The set's own grooves, never the factory ones, which every set has.
        self.assertEqual(counts[first_key(keybindings.MainPage.GROOVES)], 0)
        self.assertEqual(counts[first_key(keybindings.MainPage.GENERATORS)], sum(len(setlist.get_generator_names(kind)) for kind in NAMED_GENERATORS))
        for binding in (keybindings.MainPage.FILE, keybindings.MainPage.REGISTERS, keybindings.MainPage.ARRANGE, keybindings.MainPage.SAVE, keybindings.MainPage.OPEN_SET_HERE, keybindings.MainPage.EXPORT_HERE, keybindings.MainPage.QUIT):
            self.assertIsNone(counts[first_key(binding)], binding)
        # The count sits one space in from the box's edge, on the selected cell as on the others.
        await self.press(Key.RIGHT)
        self.assertIn(f'{counts[first_key(keybindings.MainPage.SONGS)]} {Box.DOUBLE_BAR}', boxed_line(self.text()))
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD, Key.ESCAPE, Key.ESCAPE)
        self.assertEqual(page.count(next(item for item in page.menu_items() if item.binding is keybindings.MainPage.GROOVES)), 1)

    async def test_the_arrows_move_the_box_over_the_grid_and_it_stays_while_a_page_is_open(self):
        # The cursor starts on Arrange, and Right from it goes to the top cell beside it, Songs.
        self.assertIn(PageName.ARRANGE, boxed_line(self.text()))
        await self.press(Key.RIGHT)
        self.assertIn(PageName.SONGS, boxed_line(self.text()))
        await self.press(Key.RIGHT)
        self.assertIn(PageName.PATTERNS, boxed_line(self.text()))
        await self.press(Key.DOWN, Key.DOWN)
        self.assertIn(PageName.CHAINS, boxed_line(self.text()))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChainsPage)
        await self.press(Key.ESCAPE)
        self.assertIn(PageName.CHAINS, boxed_line(self.text()))

    async def test_every_arrow_moves_by_the_geometry_drawn_and_stops_at_every_edge(self):
        # The user's layout and rule: from each cell, where Up, Down, Left and Right go, the cell itself where the arrow stops at an edge.
        keys = keybindings.MainPage
        moves = {
            keys.ARRANGE: (keys.ARRANGE, keys.REAL_TIME, keys.ARRANGE, keys.SONGS),
            keys.REAL_TIME: (keys.ARRANGE, keys.FILE, keys.REAL_TIME, keys.INSTRUMENTS),
            keys.SONGS: (keys.SONGS, keys.SCALES, keys.ARRANGE, keys.PATTERNS),
            keys.SCALES: (keys.SONGS, keys.GROOVES, keys.ARRANGE, keys.GENERATORS),
            keys.GROOVES: (keys.SCALES, keys.INSTRUMENTS, keys.ARRANGE, keys.CHAINS),
            keys.INSTRUMENTS: (keys.GROOVES, keys.SAVE, keys.REAL_TIME, keys.REGISTERS),
            keys.PATTERNS: (keys.PATTERNS, keys.GENERATORS, keys.SONGS, keys.PATTERNS),
            keys.GENERATORS: (keys.PATTERNS, keys.CHAINS, keys.SCALES, keys.GENERATORS),
            keys.CHAINS: (keys.GENERATORS, keys.REGISTERS, keys.GROOVES, keys.CHAINS),
            keys.REGISTERS: (keys.CHAINS, keys.OPEN_SET_HERE, keys.INSTRUMENTS, keys.REGISTERS),
            keys.FILE: (keys.REAL_TIME, keys.EXPORT_HERE, keys.FILE, keys.SAVE),
            keys.SAVE: (keys.INSTRUMENTS, keys.IMPORT_HERE, keys.FILE, keys.OPEN_SET_HERE),
            keys.OPEN_SET_HERE: (keys.REGISTERS, keys.QUIT, keys.SAVE, keys.OPEN_SET_HERE),
            keys.EXPORT_HERE: (keys.FILE, keys.EXPORT_HERE, keys.EXPORT_HERE, keys.IMPORT_HERE),
            keys.IMPORT_HERE: (keys.SAVE, keys.IMPORT_HERE, keys.EXPORT_HERE, keys.QUIT),
            keys.QUIT: (keys.OPEN_SET_HERE, keys.QUIT, keys.IMPORT_HERE, keys.QUIT),
        }
        page = self.app.screen
        self.assertEqual(len(moves), len(page.menu_items()))
        for start, ends in moves.items():
            for arrow, end in zip((Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT), ends):
                with self.subTest(start=start, arrow=arrow):
                    page.select(start)
                    await self.press(arrow)
                    self.assertIs(page.selected().binding, end)

    async def test_right_from_arrange_goes_back_to_the_cell_the_cursor_came_from(self):
        keys = keybindings.MainPage
        page = self.app.screen
        for beside in (keys.SONGS, keys.SCALES, keys.GROOVES):
            with self.subTest(beside=beside):
                page.select(beside)
                await self.press(Key.LEFT)
                self.assertIs(page.selected().binding, keys.ARRANGE)
                await self.press(Key.RIGHT)
                self.assertIs(page.selected().binding, beside)
        # Reached from below, Arrange forgets the side: Right goes to the top cell.
        page.select(keys.GROOVES)
        await self.press(Key.LEFT, Key.DOWN, Key.UP, Key.RIGHT)
        self.assertIs(page.selected().binding, keys.SONGS)

    async def test_the_selected_action_of_the_bar_is_reversed_in_the_bars_double_lined_box(self):
        page = self.app.screen
        page.select(keybindings.MainPage.OPEN_SET_HERE)
        await self.press(Key.DOWN)
        self.assertIn(PageName.QUIT, boxed_line(self.text()))
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)
        # A column's keys end at one place, so that Import is in line with Save under the longer key.
        lines = self.text().splitlines()
        save = next(line for line in lines if PageName.SAVE in line)
        imported = next(line for line in lines if PageName.IMPORT in line)
        self.assertEqual(save.index(PageName.SAVE), imported.index(PageName.IMPORT))

    async def test_descriptions_start_with_a_capital_letter_and_only_the_selected_cells_is_shown(self):
        for about in MainPage.ABOUT.values():
            self.assertTrue(about[0].isupper(), about)
        self.assertIn(MSG_ABOUT[PageName.ARRANGE], self.text())
        self.assertNotIn(MSG_ABOUT[PageName.SCALES], self.text())
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertIn(MSG_ABOUT[PageName.SCALES], self.text())
        self.assertNotIn(MSG_ABOUT[PageName.ARRANGE], self.text())
