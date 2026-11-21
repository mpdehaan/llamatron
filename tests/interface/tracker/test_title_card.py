# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests the title on black (interface/tracker/components/title_card.py) on its own, on moments the test chooses, and the start screen in the tracker."""

from rich.color import Color
import string
import unittest
from unittest import mock

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.app import LlamatronApp
from llamatron.interface.tracker.components import scroll_text, title_card
from llamatron.interface.tracker.components.scroll_text import banner, demo_name, scroll_lines, scroll_seconds, scroll_text_for, words_of
from llamatron.interface.tracker.components.title_card import Entrance, Prompt, prompt_level, scan_end, scan_start, scanner_level, title_lines, whole_title_seconds, words_width
from llamatron.interface.tracker.launch import Launch
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.interface.tracker.screens.set.start_screen import StartScreen
from llamatron.interface.tracker.transport import Transport
from llamatron.user_strings import about
from tests.support.ui_testing import UITest

WIDE_SCREEN = (120, 30)
NARROW_SCREEN = (80, 24)
WAVING = 0.5
DURING_SCAN = 4.0
LONG_AFTER = 20.0
STEPS = 200
LONG_LAUNCH_SECONDS = 600.0
# A title's width in columns, a quarter of a sweep, and how many sweeps past the first a load may run on.
TITLE_WIDTH = 60
QUARTER_SWEEP = 0.25
SWEEPS_LATER = 3


def settled():
    """Return a moment after the letters have settled and the scanner has gone."""
    return scan_end() + 0.5


def lines_at(*, elapsed, screen=WIDE_SCREEN, prompt=True, seconds=None):
    width, height = screen
    return title_lines(width=width, height=height, elapsed=elapsed, prompt=Prompt() if prompt else None, seconds=seconds)


def block_rows(lines):
    """Return the numbers of the lines that hold blocks of the word, leaving out the scanner's line."""
    return [number for number, line in enumerate(lines) if about.MSG_BLOCK in line.plain and line.plain.strip(about.MSG_BLOCK) != NO_TEXT]


NO_TEXT = ''


def colours_of(line):
    """Return each run's text colour and background colour, as triplets."""
    return [(span.style.color.get_truecolor(), span.style.bgcolor.get_truecolor()) for span in line.spans]


A_LEARNING_DEMO = 'examples/learning/19_hocket_shanty.yml'
A_LEARNING_DEMO_NAME = 'Hocket Shanty'
A_GENRE_DEMO = 'examples/by_genre/ragtime/entertainer.yml'
A_GENRE_DEMO_NAME = 'Entertainer'
WORDS_WITH_A_NUMBER = 'take-5 blues'
WORDS_WITH_A_NUMBER_AS_WORDS = 'Take 5 Blues'
ONLY_A_NUMBER = 'sets/1999.yml'
ONLY_A_NUMBER_NAME = '1999'
COLON_AND_SPACE = ': '
A_CAPITAL = 'H'
NO_SUCH_LETTER = '~'
SPACE = ' '
A_FEW_COLUMNS = 6
MANY_COLUMNS = 150

class TestTitleCard(unittest.TestCase):

    def test_everything_is_drawn_on_black_and_every_line_is_as_wide_as_the_screen(self):
        for elapsed in (0.0, WAVING, DURING_SCAN, LONG_AFTER):
            for line in lines_at(elapsed=elapsed):
                self.assertEqual(len(line.plain), WIDE_SCREEN[0])
                self.assertTrue(all(tuple(background) == title_card.BLACK for _, background in colours_of(line)))

    def test_the_word_is_twice_as_wide_where_it_fits_and_single_width_where_it_does_not(self):
        for screen, scale in ((WIDE_SCREEN, title_card.WIDE), (NARROW_SCREEN, title_card.NARROW)):
            with self.subTest(screen=screen):
                lines = lines_at(elapsed=settled(), screen=screen)
                rows = block_rows(lines)
                self.assertEqual(len(rows), title_card.LETTER_ROWS)
                first = min(line.plain.index(about.MSG_BLOCK) for line in (lines[row] for row in rows))
                last = max(len(line.plain.rstrip()) for line in (lines[row] for row in rows))
                self.assertEqual(last - first, words_width(word=about.MSG_SPLASH_WORD, scale=scale))
                self.assertEqual(first, (screen[0] - words_width(word=about.MSG_SPLASH_WORD, scale=scale)) // 2)

    def test_the_letters_ride_waves_as_they_come_in_and_settle_onto_five_rows(self):
        self.assertEqual(title_card.ENTRANCE, Entrance.SINE_WAVES)
        self.assertGreater(len(block_rows(lines_at(elapsed=WAVING))), title_card.LETTER_ROWS)
        self.assertEqual(len(block_rows(lines_at(elapsed=settled()))), title_card.LETTER_ROWS)

    def test_the_scanner_sweeps_right_then_left_between_the_letters_settling_and_its_end(self):
        width = words_width(word=about.MSG_SPLASH_WORD, scale=title_card.WIDE)
        self.assertEqual(scanner_level(column=width // 2, width=width, elapsed=scan_start() - 0.01), 0.0)
        self.assertEqual(scanner_level(column=width // 2, width=width, elapsed=scan_end()), 0.0)
        quarter = scan_start() + (scan_end() - scan_start()) / 4
        three_quarters = scan_start() + 3 * (scan_end() - scan_start()) / 4
        levels = [scanner_level(column=column, width=width, elapsed=quarter) for column in range(width)]
        self.assertAlmostEqual(max(levels), 1.0, delta=0.05)
        self.assertTrue(all(0.0 <= level <= 1.0 for level in levels))
        # Half way through its going right, and half way through its coming back, the glow is at the same place, wide and shaded.
        back = [scanner_level(column=column, width=width, elapsed=three_quarters) for column in range(width)]
        self.assertEqual(levels.index(max(levels)), back.index(max(back)))
        self.assertGreater(len({round(level, 2) for level in levels if level > 0}), 10)

    def test_the_address_is_two_lines_under_the_scanner_and_centred(self):
        lines = lines_at(elapsed=settled())
        top = block_rows(lines)[0]
        address = lines[top + title_card.ADDRESS_ROW].plain
        self.assertEqual(address.index(about.MSG_SPLASH_ADDRESS), (WIDE_SCREEN[0] - len(about.MSG_SPLASH_ADDRESS)) // 2)
        self.assertEqual(title_card.ADDRESS_ROW, title_card.SCANNER_ROW + 2)

    def test_the_prompt_waits_for_the_scanner_then_pulses_without_going_dark(self):
        self.assertEqual(prompt_level(scan_end() - 0.01), 0.0)
        top = block_rows(lines_at(elapsed=settled()))[0]
        self.assertNotIn(about.MSG_START_PROMPT, lines_at(elapsed=DURING_SCAN)[top + title_card.PROMPT_ROW].plain)
        self.assertIn(about.MSG_START_PROMPT, lines_at(elapsed=LONG_AFTER)[top + title_card.PROMPT_ROW].plain)
        self.assertEqual(title_card.PROMPT_ROW, title_card.ADDRESS_ROW + 6)
        pulse = [prompt_level(LONG_AFTER + step / STEPS * 3) for step in range(STEPS)]
        self.assertGreater(min(pulse), 0.0)
        self.assertGreater(max(pulse) - min(pulse), 0.3)
        self.assertFalse(any(about.MSG_START_PROMPT in line.plain for line in lines_at(elapsed=LONG_AFTER, prompt=False)))

    def test_a_title_shown_for_a_time_fades_to_black_at_its_end(self):
        seconds = whole_title_seconds()
        for line in lines_at(elapsed=seconds, seconds=seconds):
            self.assertTrue(all(tuple(colour) == title_card.BLACK for colour, _ in colours_of(line)))
        self.assertTrue(any(tuple(colour) != title_card.BLACK for line in lines_at(elapsed=DURING_SCAN, seconds=seconds) for colour, _ in colours_of(line)))


class TestScrollText(unittest.TestCase):
    """The demo's name crossing the screen after the title when an example is recorded: DEMO: and the file's name as words, in light orange."""

    def test_a_files_name_loses_its_folder_ending_and_number_and_is_words(self):
        self.assertEqual(demo_name(A_LEARNING_DEMO), A_LEARNING_DEMO_NAME)
        self.assertEqual(demo_name(A_GENRE_DEMO), A_GENRE_DEMO_NAME)
        self.assertEqual(words_of(WORDS_WITH_A_NUMBER), WORDS_WITH_A_NUMBER_AS_WORDS)
        self.assertEqual(scroll_text_for(A_LEARNING_DEMO), about.MSG_DEMO_SCROLL.format(name=A_LEARNING_DEMO_NAME))

    def test_a_name_that_is_only_a_number_keeps_it(self):
        self.assertEqual(demo_name(ONLY_A_NUMBER), ONLY_A_NUMBER_NAME)

    def test_every_letter_and_digit_has_a_shape_of_five_rows_of_five(self):
        for character in string.ascii_uppercase + string.digits + COLON_AND_SPACE:
            with self.subTest(character=character):
                self.assertEqual([len(row) for row in about.MSG_BLOCK_LETTERS[character]], [scroll_text.LETTER_ROWS] * scroll_text.LETTER_ROWS)

    def test_every_letter_is_a_capital_of_one_size(self):
        # The block letters have no lower case, so the words are capitals.
        self.assertEqual(banner(A_CAPITAL), banner(A_CAPITAL.lower()))
        self.assertEqual(len(banner(A_CAPITAL)), scroll_text.BANNER_ROWS)
        self.assertEqual(len(banner(A_CAPITAL)[0]), scroll_text.LETTER_ROWS * scroll_text.BLOCK_COLUMNS)
        self.assertIn(about.MSG_BLOCK, banner(A_CAPITAL)[0])

    def test_a_character_with_no_shape_is_a_space(self):
        self.assertEqual(banner(NO_SUCH_LETTER), banner(SPACE))

    def test_the_words_come_in_at_the_right_cross_and_leave_at_the_left_on_black(self):
        rows = banner(scroll_text_for(A_LEARNING_DEMO))
        seconds = scroll_seconds(text=scroll_text_for(A_LEARNING_DEMO), width=WIDE_SCREEN[0])
        self.assertEqual(self.blocks_at(rows=rows, elapsed=0.0), [])
        early = self.blocks_at(rows=rows, elapsed=A_FEW_COLUMNS / scroll_text.COLUMNS_PER_SECOND)
        self.assertTrue(early)
        self.assertGreaterEqual(min(early), WIDE_SCREEN[0] - A_FEW_COLUMNS)
        later = self.blocks_at(rows=rows, elapsed=MANY_COLUMNS / scroll_text.COLUMNS_PER_SECOND)
        self.assertLess(min(later), min(early))
        self.assertEqual(self.blocks_at(rows=rows, elapsed=seconds), [])

    def test_every_line_is_as_wide_as_the_screen_and_the_words_are_light_orange_alone(self):
        width, height = WIDE_SCREEN
        lines = scroll_lines(rows=banner(scroll_text_for(A_LEARNING_DEMO)), width=width, height=height, elapsed=MANY_COLUMNS / scroll_text.COLUMNS_PER_SECOND)
        self.assertEqual(len(lines), height)
        self.assertEqual({len(line.plain) for line in lines}, {width})
        colours = {span.style.color.triplet for line in lines for span in line.spans if line.plain[span.start] == about.MSG_BLOCK}
        self.assertEqual(colours, {Color.from_rgb(*scroll_text.SCROLL_ORANGE).triplet})
        self.assertTrue(all(span.style.bgcolor.triplet == Color.from_rgb(*title_card.BLACK).triplet for line in lines for span in line.spans))

    def blocks_at(self, *, rows, elapsed):
        """Return the columns that hold a block at a moment, on a wide screen."""
        width, height = WIDE_SCREEN
        lines = scroll_lines(rows=rows, width=width, height=height, elapsed=elapsed)
        return sorted({column for line in lines for column, character in enumerate(line.plain) if character == about.MSG_BLOCK})


class TestScannerWhileLoading(unittest.TestCase):
    """The scanner sweeps at least once, and on while something loads under the title, the prompt coming after the sweep it is in."""

    def test_a_load_done_before_the_first_sweep_ends_leaves_one_sweep(self):
        self.assertEqual(scan_end(loaded_at=scan_start()), scan_end())

    def test_while_loading_the_scanner_never_stops_and_no_prompt_shows(self):
        later = scan_end() + title_card.SCAN_SECONDS * SWEEPS_LATER
        self.assertEqual(prompt_level(later, loaded_at=None), 0.0)
        self.assertGreater(max(scanner_level(column=column, width=TITLE_WIDTH, elapsed=later + QUARTER_SWEEP, loaded_at=None) for column in range(TITLE_WIDTH)), 0.0)

    def test_a_load_done_during_a_later_sweep_ends_the_scanner_with_that_sweep(self):
        loaded = scan_end() + title_card.SCAN_SECONDS / 2
        self.assertEqual(scan_end(loaded_at=loaded), scan_end() + title_card.SCAN_SECONDS)


class TestStartScreen(UITest):
    """The tracker opens on the start screen when the command line asks, Enter waiting until what loads under it is done, and then
    leaving the main screen."""

    # Whether what loads under the title is done as the tracker opens.
    LOADED = True

    def make_app(self):
        self.loaded = self.LOADED
        # The transport's loading under the title is the test's to say done, so that no real FluidSynth or sender starts.
        patcher = mock.patch.object(Transport, Transport.prepare.__name__, return_value=lambda: self.loaded)
        patcher.start()
        self.addCleanup(patcher.stop)
        return LlamatronApp(document=self.document, start_screen=True)

    async def test_it_shows_over_the_main_screen_until_enter(self):
        self.assertIsInstance(self.app.screen, StartScreen)
        await self.press(keybindings.StartScreen.START)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_other_keys_do_nothing(self):
        await self.press(keybindings.MainPage.QUIT)
        self.assertIsInstance(self.app.screen, StartScreen)


class TestStartScreenWhileLoading(TestStartScreen):
    """Enter does nothing while what loads under the title is not done."""

    LOADED = False

    async def test_it_shows_over_the_main_screen_until_enter(self):
        self.loaded = True
        await super().test_it_shows_over_the_main_screen_until_enter()

    async def test_enter_waits_until_what_loads_under_it_is_done(self):
        await self.press(keybindings.StartScreen.START)
        self.assertIsInstance(self.app.screen, StartScreen)
        self.loaded = True
        await self.press(keybindings.StartScreen.START)
        self.assertIsInstance(self.app.screen, MainPage)


class TestNoStartScreenWhenPlayingOnItsOwn(UITest):

    def make_app(self):
        return LlamatronApp(document=self.document, start_screen=True, launch=Launch(max_seconds=LONG_LAUNCH_SECONDS))

    async def test_a_launch_that_is_not_plain_never_shows_it(self):
        self.assertNotIsInstance(self.app.screen, StartScreen)


class TestNoStartScreenByDefault(UITest):

    async def test_the_app_made_without_asking_opens_on_the_main_screen(self):
        self.assertIsInstance(self.app.screen, MainPage)


if __name__ == '__main__':
    unittest.main()
