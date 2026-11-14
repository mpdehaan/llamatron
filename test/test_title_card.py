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

"""Tests the title on black (tui/components/title_card.py) on its own, on moments the test chooses, and the start screen in the tracker."""

import unittest

from llamatron.strings.about import MSG_BLOCK, MSG_SPLASH_ADDRESS, MSG_SPLASH_WORD, MSG_START_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.app import LlamatronApp
from llamatron.tui.components import title_card
from llamatron.tui.components.title_card import (
    ADDRESS_ROW, BLACK, LETTER_ROWS, NARROW, PROMPT_ROW, SCANNER_ROW, WIDE, Entrance, prompt_level, scan_end, scan_start, scanner_level,
    title_lines, whole_title_seconds, words_width,
)
from llamatron.tui.launch import NO_SPLASH, NO_SPLASH_VARIABLE, Launch, start_screen_wanted
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.start_screen import StartScreen
from ui_testing import UITest

WIDE_SCREEN = (120, 30)
NARROW_SCREEN = (80, 24)
WAVING = 0.5
DURING_SCAN = 4.0
LONG_AFTER = 20.0
STEPS = 200
LONG_LAUNCH_SECONDS = 600.0


def settled():
    """Return a moment after the letters have settled and the scanner has gone."""
    return scan_end() + 0.5


def lines_at(*, elapsed, screen=WIDE_SCREEN, prompt=True, seconds=None):
    width, height = screen
    return title_lines(width=width, height=height, elapsed=elapsed, prompt=prompt, seconds=seconds)


def block_rows(lines):
    """Return the numbers of the lines that hold blocks of the word, leaving out the scanner's line."""
    return [number for number, line in enumerate(lines) if MSG_BLOCK in line.plain and line.plain.strip(MSG_BLOCK) != NO_TEXT]


NO_TEXT = ''


def colours_of(line):
    """Return each run's text colour and background colour, as triplets."""
    return [(span.style.color.get_truecolor(), span.style.bgcolor.get_truecolor()) for span in line.spans]


class TestTitleCard(unittest.TestCase):

    def test_everything_is_drawn_on_black_and_every_line_is_as_wide_as_the_screen(self):
        for elapsed in (0.0, WAVING, DURING_SCAN, LONG_AFTER):
            for line in lines_at(elapsed=elapsed):
                self.assertEqual(len(line.plain), WIDE_SCREEN[0])
                self.assertTrue(all(tuple(background) == BLACK for _, background in colours_of(line)))

    def test_the_word_is_twice_as_wide_where_it_fits_and_single_width_where_it_does_not(self):
        for screen, scale in ((WIDE_SCREEN, WIDE), (NARROW_SCREEN, NARROW)):
            with self.subTest(screen=screen):
                lines = lines_at(elapsed=settled(), screen=screen)
                rows = block_rows(lines)
                self.assertEqual(len(rows), LETTER_ROWS)
                first = min(line.plain.index(MSG_BLOCK) for line in (lines[row] for row in rows))
                last = max(len(line.plain.rstrip()) for line in (lines[row] for row in rows))
                self.assertEqual(last - first, words_width(word=MSG_SPLASH_WORD, scale=scale))
                self.assertEqual(first, (screen[0] - words_width(word=MSG_SPLASH_WORD, scale=scale)) // 2)

    def test_the_letters_ride_waves_as_they_come_in_and_settle_onto_five_rows(self):
        self.assertEqual(title_card.ENTRANCE, Entrance.SINE_WAVES)
        self.assertGreater(len(block_rows(lines_at(elapsed=WAVING))), LETTER_ROWS)
        self.assertEqual(len(block_rows(lines_at(elapsed=settled()))), LETTER_ROWS)

    def test_the_scanner_sweeps_right_then_left_between_the_letters_settling_and_its_end(self):
        width = words_width(word=MSG_SPLASH_WORD, scale=WIDE)
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
        address = lines[top + ADDRESS_ROW].plain
        self.assertEqual(address.index(MSG_SPLASH_ADDRESS), (WIDE_SCREEN[0] - len(MSG_SPLASH_ADDRESS)) // 2)
        self.assertEqual(ADDRESS_ROW, SCANNER_ROW + 2)

    def test_the_prompt_waits_for_the_scanner_then_pulses_without_going_dark(self):
        self.assertEqual(prompt_level(scan_end() - 0.01), 0.0)
        top = block_rows(lines_at(elapsed=settled()))[0]
        self.assertNotIn(MSG_START_PROMPT, lines_at(elapsed=DURING_SCAN)[top + PROMPT_ROW].plain)
        self.assertIn(MSG_START_PROMPT, lines_at(elapsed=LONG_AFTER)[top + PROMPT_ROW].plain)
        self.assertEqual(PROMPT_ROW, ADDRESS_ROW + 6)
        pulse = [prompt_level(LONG_AFTER + step / STEPS * 3) for step in range(STEPS)]
        self.assertGreater(min(pulse), 0.0)
        self.assertGreater(max(pulse) - min(pulse), 0.3)
        self.assertFalse(any(MSG_START_PROMPT in line.plain for line in lines_at(elapsed=LONG_AFTER, prompt=False)))

    def test_a_title_shown_for_a_time_fades_to_black_at_its_end(self):
        seconds = whole_title_seconds()
        for line in lines_at(elapsed=seconds, seconds=seconds):
            self.assertTrue(all(tuple(colour) == BLACK for colour, _ in colours_of(line)))
        self.assertTrue(any(tuple(colour) != BLACK for line in lines_at(elapsed=DURING_SCAN, seconds=seconds) for colour, _ in colours_of(line)))


class TestStartScreenWanted(unittest.TestCase):

    def test_the_command_line_wants_it_unless_the_environment_says_not(self):
        self.assertTrue(start_screen_wanted({}))
        self.assertFalse(start_screen_wanted({NO_SPLASH_VARIABLE: NO_SPLASH}))


class TestStartScreen(UITest):
    """The tracker opens on the start screen when the command line asks, and Enter leaves the main screen."""

    def make_app(self):
        return LlamatronApp(document=self.document, start_screen=True)

    async def test_it_shows_over_the_main_screen_until_enter(self):
        self.assertIsInstance(self.app.screen, StartScreen)
        await self.press(keybindings.StartScreen.START)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_other_keys_do_nothing(self):
        await self.press(keybindings.MainPage.QUIT)
        self.assertIsInstance(self.app.screen, StartScreen)


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
