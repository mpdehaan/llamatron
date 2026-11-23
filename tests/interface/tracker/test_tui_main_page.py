# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The main screen: its one block of buttons, their counts, the arrows over them, the file's actions and the header."""

from unittest import mock

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.app import LlamatronApp
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.quit_dialog import QuitDialog
from llamatron.interface.tracker.drawing import Box
from llamatron.interface.tracker.key_table import first_key
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.arrange_page import ArrangePage
from llamatron.interface.tracker.screens.generators.generators_page import GeneratorsPage
from llamatron.interface.tracker.screens.pattern.patterns_page import PatternsPage
from llamatron.interface.tracker.screens.set import main_page
from llamatron.interface.tracker.screens.set.draws_page import DrawsPage
from llamatron.interface.tracker.screens.set.file_page import FilePage
from llamatron.interface.tracker.screens.set.main_page import arrows_between, cell_positions, MainPage, moved
from llamatron.interface.tracker.screens.set.open_page import OpenPage
from llamatron.interface.tracker.screens.set.scales_page import ScalesPage
from llamatron.interface.tracker.screens.set.songs_page import SongsPage
from llamatron.interface.tracker.text import clock
from llamatron.model.file import version
from llamatron.user_strings import labels, legends, marks, messages, names
from tests.support.page_testing import boxed_line
from tests.support.ui_testing import key_name, UITest

# Typed into a prompt that ESC then cancels.
ESCAPED_TITLE = 'never'
# The arrows, in the order the tests list where each takes the cursor.
ARROWS = (Key.UP, Key.DOWN, Key.LEFT, Key.RIGHT)
# Letters the tests press on purpose that aren't keys: two letters no page binds, and a letter typed as
# text into the description. Textual's own name for the Ctrl+Q the tracker no longer binds.
CTRL_Q = 'ctrl+q'
EXIT = 'exit'
# The marks the screen's text puts around anything in reverse video, and what joins a cell's lines.
REVERSED_STARTS = '«'
REVERSED_ENDS = '»'


class TestMainPageStartedWithNoSet(UITest):
    """The tracker started with no set named, opens with the main screen's cursor on Open."""

    def make_app(self):
        return LlamatronApp(document=self.document, cursor_on_open=True)

    async def test_the_cursor_starts_on_open_and_enter_opens_the_open_page(self):
        self.assertIs(self.app.screen.selected().binding, keybindings.MainPage.OPEN_SET_HERE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OpenPage)

class TestMainPage(UITest):

    async def test_the_header_keeps_the_crumbs_left_llamatron_centred_and_the_set_and_song_right(self):
        # The crumbs, which change with every page, in the left corner of the first line, llamatron centred, and the
        # set and its song as one block at the right, just left of the save mark and the length.
        unsaved = labels.MSG_SET_CRUMB.format(file=labels.MSG_NO_FILE_CRUMB)
        song = labels.MSG_SONG_CRUMB.format(song=names.MSG_DEFAULT_SONG_NAME)
        self.assert_header(set_crumb=unsaved, song_crumb=song)
        self.assertTrue(self.crumbs_line().startswith(drawing.SPACE + labels.Crumb.MAIN_SCREEN + drawing.SPACE))
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assert_header(set_crumb=unsaved, song_crumb=song)
        self.assertTrue(self.crumbs_line().startswith(drawing.SPACE + labels.Crumb.PATTERNS + marks.MSG_CRUMB_SEPARATOR))
        # The rule, or on a page with a theme its stripe, which is drawn in the theme's colour behind the page's caption.
        self.assertNotIn(Box.RULE * 3, self.text().splitlines()[2])
        # The version is left to the About dialog, and the length sits at the right of the song's line.
        self.assertNotIn(version.VERSION, self.title_line())
        self.assertTrue(self.song_line().rstrip().endswith(clock(self.app.screen.duration())))
        self.assertNotIn(clock(self.app.screen.duration()), self.title_line())
        # A set with no file yet is unsaved, saving makes it saved, a change gives it unsaved changes, and saving again makes it saved.
        self.assertTrue(self.title_line().rstrip().endswith(marks.MSG_UNSAVED_MARK))
        self.document.save(path='songs/tune.yml')
        await self.press(Key.ESCAPE)
        self.assert_header(set_crumb=labels.MSG_SET_CRUMB.format(file='tune.yml'), song_crumb=song)
        self.assertTrue(self.title_line().rstrip().endswith(marks.MSG_SAVED_MARK))
        # The main screen draws again when a page closes over it, so each change is looked at from a page.
        self.document.changed()
        await self.press(keybindings.MainPage.PATTERNS, Key.ESCAPE)
        self.assertTrue(self.title_line().rstrip().endswith(marks.MSG_UNSAVED_CHANGES_MARK))
        self.document.save(path='songs/tune.yml')
        await self.press(keybindings.MainPage.PATTERNS, Key.ESCAPE)
        self.assertTrue(self.title_line().rstrip().endswith(marks.MSG_SAVED_MARK))

    async def test_o_opens_and_x_exports_on_the_main_screen_without_ctrl_and_the_cells_show_the_letters(self):
        # To save a keystroke: the main screen's letters are its own. Ctrl+O and Ctrl+X still work.
        text = self.text()
        # In the bar a column's names start at one place, so Open stands clear of its key by the room Save's longer key takes.
        open_line = next(line for line in text.splitlines() if labels.PageName.OPEN in line)
        self.assertIn(f'« {key_name(keybindings.MainPage.OPEN_SET_HERE)} »', open_line)
        self.assertIn(f'« {key_name(keybindings.MainPage.EXPORT_HERE)} » {labels.PageName.EXPORT}', text)
        self.assertIn(f'« {key_name(keybindings.MainPage.SAVE)} » {labels.PageName.SAVE}', text)
        self.assertNotIn(f'« {key_name(keybindings.MainPage.OPEN_SET)} »', text)
        await self.press(keybindings.MainPage.OPEN_SET_HERE)
        self.assertIsInstance(self.app.screen, OpenPage)
        await self.press(Key.ESCAPE, Key.CTRL_O)
        self.assertIsInstance(self.app.screen, OpenPage)
        await self.press(Key.ESCAPE, keybindings.MainPage.EXPORT_HERE)
        # An unsaved set asks to be saved before an export.
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_SAVE_BEFORE_EXPORT_TITLE, self.text())
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
        for name, page in [(keybindings.MainPage.FILE, FilePage), (keybindings.MainPage.SONGS, SongsPage), (keybindings.MainPage.PATTERNS, PatternsPage), (keybindings.MainPage.GENERATORS, GeneratorsPage), (keybindings.MainPage.SCALES, ScalesPage), (keybindings.MainPage.ARRANGE, ArrangePage)]:
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
        for button in labels.MSG_QUIT_BUTTONS:
            self.assertIn(button, self.text())
        self.assertIn(messages.MSG_QUIT_UNSAVED_NOTE, self.text())
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
        await self.select_field(labels.MSG_TITLE_LABEL)
        await self.press(Key.ENTER)
        await self.type(ESCAPED_TITLE)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertFalse(self.document.get_setlist().get_title())
        self.assertFalse(self.document.is_dirty())

    async def test_a_large_console_shows_the_same_block_of_buttons_at_the_top_left_never_stretched(self):
        # The buttons are the size they are on an 80 by 24 console, however large the window.
        lines = [line.replace(REVERSED_STARTS + drawing.SPACE, drawing.NOTHING).replace(drawing.SPACE + REVERSED_ENDS, drawing.NOTHING).rstrip() for line in self.text().splitlines()]
        boxed = [line for line in lines if line.startswith((Box.TOP_LEFT, Box.DOUBLE_TOP_LEFT, Box.BOTTOM_LEFT, Box.DOUBLE_BOTTOM_LEFT))]
        self.assertTrue(boxed)
        self.assertEqual({len(line) for line in boxed}, {main_page.GRID_WIDTH})
        self.assertLess(main_page.GRID_WIDTH, self.SIZE[0])
        self.assertEqual(sum(self.app.screen.column_widths()) + main_page.COLUMNS - 1, main_page.GRID_WIDTH)

    async def test_the_fewest_arrows_reach_every_cell_from_every_cell(self):
        # What the video tutorial walks by: the arrows found are pressed and reach the cell.
        page = self.app.screen
        rows = page.rows()
        cells = list({id(item.binding): item.binding for row in rows for item in row if item is not main_page.EMPTY_CELL}.values())
        for start in cells:
            for end in cells:
                position = cell_positions(rows=rows, binding=start)[0]
                arrows = arrows_between(rows=rows, position=position, binding=end)
                self.assertIsNotNone(arrows, (start, end))
                self.assertLess(len(arrows), len(rows) + main_page.COLUMNS)
                for arrow in arrows:
                    position = moved(rows=rows, position=position, key=arrow)
                self.assertIs(rows[position[0]][position[1]].binding, end)
        # On the screen, the arrows to a cell are the ones a person would press.
        self.assertEqual(page.arrows_to(keybindings.MainPage.WIZARD), [Key.DOWN, Key.RIGHT])
        self.assertEqual(page.arrows_to(keybindings.MainPage.ARRANGE), [])


class TestMainPageOnAUsualConsole(UITest):
    """The main screen on a console of 80 by 24, which the block of buttons fills from edge to edge."""

    SIZE = (80, 24)

    async def test_the_screen_is_named_once_and_the_stripe_carries_no_caption(self):
        # The crumbs name the main screen, so the theme's stripe under the header says nothing.
        self.assertEqual(self.text().count(labels.Crumb.MAIN_SCREEN), 1)
        self.assertEqual(self.app.screen.caption(), drawing.NOTHING)

    async def test_the_status_line_stays_empty_until_something_is_refused_or_said(self):
        # No description of the selected button: the line is for refusals and warnings here.
        page = self.app.screen
        self.assertEqual(page.resting_status(), drawing.NOTHING)
        lines = self.text().splitlines()
        self.assertFalse(lines[-3].strip())
        await self.press(Key.DOWN, Key.RIGHT)
        self.assertFalse(self.text().splitlines()[-3].strip())

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
        self.assertNotIn(labels.PageName.UNDO, text)
        # Arrange alone on a bar across the top, then three buttons to a line, a blank line, and the bar:
        # Open, Import and File/Global over Save, Export and Quit.
        lines = text.splitlines()
        arrange = next(number for number, line in enumerate(lines) if '« A »' in line)
        self.assertEqual(lines[arrange].count('«'), 1)
        self.assertLess(arrange, next(number for number, line in enumerate(lines) if '« S »' in line))
        self.assertEqual(sum(1 for line in lines if '« F »' in line), 1)
        for row in ('« S »', '« G »', '« I »'):
            self.assertEqual(next(line for line in lines if row in line).count('«'), main_page.COLUMNS)
        # Songs, the Wizard and Patterns; Scales, Generators and Draws; Grooves, Instruments and the Real Time switch.
        self.assertIn('« W »', next(line for line in lines if '« S »' in line))
        self.assertIn('« P »', next(line for line in lines if '« S »' in line))
        self.assertIn('« Z »', next(line for line in lines if '« G »' in line))
        self.assertIn('« D »', next(line for line in lines if '« G »' in line))
        self.assertIn('« V »', next(line for line in lines if '« I »' in line))
        self.assertIn('« T »', next(line for line in lines if '« I »' in line))
        opens = next(number for number, line in enumerate(lines) if '« O »' in line)
        self.assertIn('« L »', lines[opens])
        self.assertIn('« F »', lines[opens])
        self.assertIn('« Ctrl+S »', lines[opens + 1])
        self.assertIn('« Q »', lines[opens + 1])
        self.assertIn('« X »', lines[opens + 1])
        # One blank line between the buttons and the bar of the file's actions.
        self.assertFalse(lines[opens - 2].strip())
        self.assertTrue(lines[opens - 3].startswith(Box.BOTTOM_LEFT))
        self.assertIn(labels.PageName.FILE, text)
        self.assertIn('« F1 »', lines[-1])
        self.assertTrue(lines[-1].rstrip().endswith(legends.MSG_ABOUT_FOOTER_WHAT))

    async def test_each_cell_counts_what_its_page_lists_with_a_space_before_the_border(self):
        page = self.app.screen
        setlist = self.document.get_setlist()
        counts = {item.keys[0]: page.count(item) for item in page.menu_items()}
        self.assertEqual(counts[first_key(keybindings.MainPage.SONGS)], len(self.document.song_names()))
        self.assertEqual(counts[first_key(keybindings.MainPage.PATTERNS)], len(setlist.get_pattern_names()))
        self.assertEqual(counts[first_key(keybindings.MainPage.SCALES)], len(setlist.get_scale_names()))
        # The set's own grooves, never the factory ones, which every set has.
        self.assertEqual(counts[first_key(keybindings.MainPage.GROOVES)], 0)
        self.assertEqual(counts[first_key(keybindings.MainPage.GENERATORS)], len(setlist.every_generator_name()))
        for binding in (keybindings.MainPage.FILE, keybindings.MainPage.WIZARD, keybindings.MainPage.DRAWS, keybindings.MainPage.ARRANGE, keybindings.MainPage.SAVE, keybindings.MainPage.OPEN_SET_HERE, keybindings.MainPage.EXPORT_HERE, keybindings.MainPage.QUIT):
            self.assertIsNone(counts[first_key(binding)], binding)
        # The count sits one space in from the box's edge, on the selected cell as on the others.
        await self.press(Key.DOWN)
        self.assertIn(f'{counts[first_key(keybindings.MainPage.SONGS)]} {Box.DOUBLE_BAR}', boxed_line(self.text()))
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD, Key.ESCAPE, Key.ESCAPE)
        self.assertEqual(page.count(next(item for item in page.menu_items() if item.binding is keybindings.MainPage.GROOVES)), 1)

    async def test_the_arrows_move_the_box_over_the_grid_and_it_stays_while_a_page_is_open(self):
        # The cursor starts on Arrange, and Down from it goes to the first button under it, Songs.
        self.assertIn(labels.PageName.ARRANGE, boxed_line(self.text()))
        await self.press(Key.DOWN)
        self.assertIn(labels.PageName.SONGS, boxed_line(self.text()))
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertIn(labels.PageName.PATTERNS, boxed_line(self.text()))
        # Down from Patterns is Draws, and Down again the Real Time switch; Draws opens and the box stays on it.
        await self.press(Key.DOWN)
        self.assertIn(labels.PageName.DRAWS, boxed_line(self.text()))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, DrawsPage)
        await self.press(Key.ESCAPE)
        self.assertIn(labels.PageName.DRAWS, boxed_line(self.text()))
        await self.press(Key.DOWN)
        self.assertIn(labels.PageName.REAL_TIME, boxed_line(self.text()))

    async def test_every_arrow_moves_by_the_geometry_drawn_and_stops_at_every_edge(self):
        # From each cell, where Up, Down, Left and Right go, the cell itself where the arrow stops at an edge.
        keys = keybindings.MainPage
        moves = {
            keys.ARRANGE: (keys.ARRANGE, keys.SONGS, keys.ARRANGE, keys.ARRANGE),
            keys.SONGS: (keys.ARRANGE, keys.SCALES, keys.SONGS, keys.WIZARD),
            keys.WIZARD: (keys.ARRANGE, keys.GENERATORS, keys.SONGS, keys.PATTERNS),
            keys.PATTERNS: (keys.ARRANGE, keys.DRAWS, keys.WIZARD, keys.PATTERNS),
            keys.SCALES: (keys.SONGS, keys.GROOVES, keys.SCALES, keys.GENERATORS),
            keys.GENERATORS: (keys.WIZARD, keys.INSTRUMENTS, keys.SCALES, keys.DRAWS),
            keys.DRAWS: (keys.PATTERNS, keys.REAL_TIME, keys.GENERATORS, keys.DRAWS),
            keys.GROOVES: (keys.SCALES, keys.OPEN_SET_HERE, keys.GROOVES, keys.INSTRUMENTS),
            keys.INSTRUMENTS: (keys.GENERATORS, keys.IMPORT_HERE, keys.GROOVES, keys.REAL_TIME),
            keys.REAL_TIME: (keys.DRAWS, keys.FILE, keys.INSTRUMENTS, keys.REAL_TIME),
            keys.OPEN_SET_HERE: (keys.GROOVES, keys.SAVE, keys.OPEN_SET_HERE, keys.IMPORT_HERE),
            keys.IMPORT_HERE: (keys.INSTRUMENTS, keys.EXPORT_HERE, keys.OPEN_SET_HERE, keys.FILE),
            keys.FILE: (keys.REAL_TIME, keys.QUIT, keys.IMPORT_HERE, keys.FILE),
            keys.SAVE: (keys.OPEN_SET_HERE, keys.SAVE, keys.SAVE, keys.EXPORT_HERE),
            keys.EXPORT_HERE: (keys.IMPORT_HERE, keys.EXPORT_HERE, keys.SAVE, keys.QUIT),
            keys.QUIT: (keys.FILE, keys.QUIT, keys.EXPORT_HERE, keys.QUIT),
        }
        page = self.app.screen
        self.assertEqual(len(moves), len(page.menu_items()))
        for start, ends in moves.items():
            for arrow, end in zip(ARROWS, ends):
                with self.subTest(start=start, arrow=arrow):
                    page.select(start)
                    await self.press(arrow)
                    self.assertIs(page.selected().binding, end)

    async def test_down_from_arrange_goes_back_to_the_button_the_cursor_came_from(self):
        keys = keybindings.MainPage
        page = self.app.screen
        for under in (keys.SONGS, keys.WIZARD):
            with self.subTest(under=under):
                page.select(under)
                await self.press(Key.UP)
                self.assertIs(page.selected().binding, keys.ARRANGE)
                await self.press(Key.DOWN)
                self.assertIs(page.selected().binding, under)
        # Arrange is one button across the three columns: Left and Right stay on it, and the column it was reached from is kept.
        page.select(keys.WIZARD)
        await self.press(Key.UP, Key.LEFT, Key.RIGHT, Key.DOWN)
        self.assertIs(page.selected().binding, keys.WIZARD)

    async def test_the_selected_action_of_the_bar_is_reversed_in_the_bars_double_lined_box(self):
        page = self.app.screen
        page.select(keybindings.MainPage.FILE)
        await self.press(Key.DOWN)
        self.assertIn(labels.PageName.QUIT, boxed_line(self.text()))
        self.assertIn(f'{labels.PageName.QUIT} {REVERSED_ENDS}', self.text())
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)

    async def test_in_the_bar_a_columns_keys_sit_under_the_buttons_keys_and_its_names_start_at_one_place(self):
        # Open is directly above Save though Save's key is longer, and both keys start where Songs' key does.
        lines = self.text().splitlines()
        save = next(line for line in lines if labels.PageName.SAVE in line)
        opened = next(line for line in lines if labels.PageName.OPEN in line)
        songs = next(line for line in lines if labels.PageName.SONGS in line)
        self.assertEqual(save.index(REVERSED_STARTS), opened.index(REVERSED_STARTS))
        self.assertEqual(save.index(REVERSED_STARTS), songs.index(REVERSED_STARTS))
        plain = [line.replace(REVERSED_STARTS + drawing.SPACE, drawing.NOTHING).replace(drawing.SPACE + REVERSED_ENDS, drawing.NOTHING) for line in (save, opened)]
        self.assertEqual(plain[0].index(labels.PageName.SAVE), plain[1].index(labels.PageName.OPEN))
        self.assertEqual(plain[0].index(labels.PageName.EXPORT), plain[1].index(labels.PageName.IMPORT))
        self.assertEqual(plain[0].index(labels.PageName.QUIT), plain[1].index(labels.PageName.FILE))
