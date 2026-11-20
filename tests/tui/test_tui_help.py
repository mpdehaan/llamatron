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

"""Every page's help, the F1 dialog and the About dialog."""

from unittest import mock

from llamatron.strings import about, labels, legends, marks
from llamatron.support import version
from llamatron.support.version import build_year
from llamatron.tui import drawing, keybindings
from llamatron.tui.dialogs import about_dialog, dialog as dialog_values
from llamatron.tui.dialogs.about_dialog import AboutDialog
from llamatron.tui.dialogs.help_dialog import HelpDialog
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.pattern.patterns_page import PatternsPage
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.tui.screens.shared import page as page_values
from tests.support.ui_testing import fixed_text, UITest

# The file the export tests save their set as, and where its untitled song's exports then go: beside it, as <set>_<song>.
# The shape of the build date and time, as version.py writes them.
# A quote wider than one line of the About dialog, made of one word repeated.
LONG_QUOTE_WORD = 'rhubarb'
LONG_QUOTE = (LONG_QUOTE_WORD + ' ') * 12
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
TIME_PATTERN = r'^\d{2}:\d{2}$'
# The start of the Patterns page's help, which the F1 dialog's second panel shows and the first doesn't.
HELP_PATTERNS_FIRST_WORDS = 'Every pattern in the set'
DESCRIPTION_KEY = 'd'
MAIN = 'main'
HELP = 'Help'


class TestHelp(UITest):
    """Help has to work on every page, and to fit a console of the usual size."""

    SIZE = (80, 24)

    async def assert_help_fits(self, where):
        page = self.app.screen
        self.assertTrue(page.HELP, where)
        await self.press(Key.F1, Key.TAB)
        self.assertIsInstance(self.app.screen, HelpDialog, where)
        text = self.text()
        with self.subTest(where=where):
            self.assertIn(HELP, text)
            self.assertIn(labels.MSG_HELP_PANELS[1], text)
            self.assertIn('┏', text)
            self.assertIn('┗', text)
            self.assertIn(f'« {legends.KeyName.ENTER_ESCAPE} »', text)
        await self.press(Key.ENTER)
        self.assertIs(self.app.screen, page, where)

    async def test_every_page_has_help_that_fits(self):
        await self.assert_help_fits(MAIN)
        for keys in [
            [keybindings.MainPage.FILE], [DESCRIPTION_KEY], [Key.ESCAPE, Key.CTRL_O], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS], [Key.ENTER], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS], [Key.ENTER],
            [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER],
            [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GENERATORS], [Key.ENTER],
            [Key.ESCAPE, Key.DOWN, Key.ENTER],
            [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SCALES], [Key.ENTER], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GROOVES], [Key.ENTER], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD], [Key.ESCAPE], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.ARRANGE], [Key.RIGHT, Key.ENTER],
            [Key.ESCAPE, Key.LEFT, Key.ENTER],
        ]:
            await self.press(*keys)
            await self.assert_help_fits(type(self.app.screen).__name__)

    async def test_f1_is_shown_on_the_main_screen_alone_and_opens_the_help_on_every_page(self):
        self.assertIn('« F1 »', self.text())
        await self.press(keybindings.MainPage.PATTERNS)
        self.assertNotIn('« F1 »', self.text())
        await self.press(Key.F1)
        self.assertIsInstance(self.app.screen, HelpDialog)

    async def test_the_pattern_editor_fits_too(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        text = self.text()
        # The piano roll comes first, with the cursor's row and the description on screen.
        self.assertIn(marks.MSG_NOTE_UNDER_CURSOR, text)
        self.assertIn('Step 1:', text)
        self.assertIn('« ESC »', text)
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        text = self.text()
        # The gauge, its number and the octave are pinned, and the first section's heading and at least one of its rows show under them.
        self.assertIn('│ Degree', text)
        self.assertIn('│ Octave', text)
        self.assertIn(Box.BAR + drawing.SPACE + labels.MSG_SECTION_LABEL.format(mark=marks.MSG_SECTION_OPEN_MARK, name=labels.MSG_SECTION_NAMES[RowSection.BASICS]), text)
        self.assertIn('│ #/b', text)
        self.assertIn('Step 1:', text)
        self.assertIn('« ESC »', text)


class TestHelpDialog(UITest):
    SIZE = (80, 24)

    async def test_f1_lists_the_everywhere_keys_then_the_pages_own_in_two_columns_and_tab_turns_to_the_text(self):
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.HELP)
        dialog = self.app.screen
        self.assertIsInstance(dialog, HelpDialog)
        text = self.text()
        self.assertIn(labels.MSG_HELP_PANELS[0], text)
        # The dialog's own lines are between its side bars; the page shows through either side of them.
        lines = [line.split('┃')[1] for line in text.splitlines() if line.count('┃') >= 2]
        lines = [line for line in lines if '»' in line]
        # Seven everywhere keys fill two columns downwards over four lines, F1 left out of its own dialog, Silence last in the first column so that Undo still sits above Redo in the second.
        self.assertIn('« Ctrl+S »', lines[0])
        self.assertIn('« Ctrl+Z »', lines[0])
        self.assertIn('« Ctrl+Y »', lines[1])
        self.assertIn('« F3 »', lines[2])
        self.assertIn('« Ctrl+T »', lines[3])
        # The wizard's F5 ends the first column, under Silence, so that Undo still starts the second.
        self.assertIn('« F5 »', lines[4])
        self.assertNotIn('« F1 »', text)
        # The page's own keys start with ESC, the back key, and then the arrows.
        self.assertIn('« ESC »', lines[5])
        self.assertIn('« ↑↓ »', lines[6])
        self.assertIn(f'« {legends.KeyName.TAB_ARROWS} »', text)
        self.assertNotIn(HELP_PATTERNS_FIRST_WORDS, text)
        await self.press(Key.TAB)
        self.assertIn(labels.MSG_HELP_PANELS[1], self.text())
        self.assertIn(HELP_PATTERNS_FIRST_WORDS, self.text())
        await self.press(Key.RIGHT)
        self.assertIn(labels.MSG_HELP_PANELS[0], self.text())
        await self.press(Key.LEFT)
        self.assertIn(labels.MSG_HELP_PANELS[1], self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.press(keybindings.PatternsPage.HELP, Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternsPage)
        # F1 closes the dialog it opened, so pressing it twice is a glance at the keys.
        await self.press(keybindings.PatternsPage.HELP)
        self.assertIsInstance(self.app.screen, HelpDialog)
        await self.press(keybindings.PatternsPage.HELP)
        self.assertIsInstance(self.app.screen, PatternsPage)

    async def test_the_pattern_editors_keys_fit_the_dialog_on_a_usual_console(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.HELP)
        text = self.text()
        self.assertIn('┗', text)
        for item in self.app.screen.own:
            self.assertIn(f'« {item.shown_label()} »', text)


class TestAboutDialog(UITest):
    SIZE = (80, 24)

    async def test_f2_shows_the_cow_the_version_the_links_a_quote_and_the_license_on_every_page(self):
        for keys in [[keybindings.Page.ABOUT], [keybindings.MainPage.PATTERNS, keybindings.Page.ABOUT]]:
            await self.press(*keys)
            self.assertIsInstance(self.app.screen, AboutDialog)
            text = self.text()
            self.assertIn(about.MSG_COW_BUBBLE_TEXT.format(text=page_values.PROGRAM_NAME), text)
            self.assertIn(about.MSG_COW[-1].strip(), text)
            self.assertIn(about.MSG_ABOUT_VERSION.format(version=version.VERSION, date=version.BUILD_DATE, time=version.BUILD_TIME), text)
            self.assertIn(about.MSG_ABOUT_WEB, text)
            self.assertIn(about.MSG_ABOUT_BLOG, text)
            self.assertIn(about.MSG_ABOUT_MORE.format(site=about.MSG_SITE), text)
            self.assertIn(about.MSG_ABOUT_POWERED, text)
            self.assertIn(about.MSG_ABOUT_LICENSE, text)
            self.assertIn(about.MSG_ABOUT_COPYRIGHT.format(year=build_year()), text)
            self.assertIn(self.app.screen.quote, text)
            self.assertTrue(self.app.screen.quote in about.MSG_ABOUT_QUOTES or self.app.screen.quote.startswith(fixed_text(about.MSG_EIGHT_BALL)))
            self.assertIn('┗', text)
            await self.press(Key.ESCAPE)
            self.assertNotIsInstance(self.app.screen, AboutDialog)

    async def test_the_quote_is_the_eight_balls_answer_when_the_roll_falls_under_its_chance(self):
        with mock.patch.object(about_dialog.random, 'random', return_value=about_dialog.EIGHT_BALL_CHANCE / 2), mock.patch.object(about_dialog.random, 'choice', side_effect=lambda options: options[-1]):
            await self.press(keybindings.MainPage.ABOUT)
        self.assertEqual(self.app.screen.quote, about.MSG_EIGHT_BALL.format(answer=about.MSG_EIGHT_BALL_ANSWERS[-1]))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)

    def dialog_lines(self):
        return [line for line in self.text().splitlines() if Box.HEAVY_BAR in line]

    async def test_a_long_quote_wraps_onto_more_lines_in_place_of_the_blank_ones_and_the_box_stays_whole(self):
        with mock.patch.object(about_dialog, 'random_quote', return_value=LONG_QUOTE):
            await self.press(keybindings.MainPage.ABOUT)
        inner = dialog_values.DIALOG_WIDTH - dialog_values.DIALOG_MARGIN
        self.assertTrue(all(len(line.plain) <= inner for line in self.app.screen.lines(inner)))
        self.assertEqual(len(self.app.screen.quote_lines(inner)), 2)
        self.assertEqual(sum(LONG_QUOTE_WORD in line for line in self.dialog_lines()), 2)
        self.assertIn(Box.HEAVY_BOTTOM_LEFT, self.text())
        await self.press(Key.ENTER)

    async def test_a_one_line_quote_has_a_blank_line_above_and_below_it(self):
        await self.press(keybindings.MainPage.ABOUT)
        quote = self.app.screen.quote_lines(dialog_values.DIALOG_WIDTH - dialog_values.DIALOG_MARGIN)
        self.assertEqual(len(quote), 1)
        lines = [line.plain for line in self.app.screen.lines(dialog_values.DIALOG_WIDTH - dialog_values.DIALOG_MARGIN)]
        at = lines.index(quote[0])
        self.assertEqual((lines[at - 1], lines[at + 1]), (drawing.NOTHING, drawing.NOTHING))
        self.assertIn(Box.HEAVY_BOTTOM_LEFT, self.text())
        await self.press(Key.ENTER)

    async def test_a_quote_longer_than_four_lines_is_cut_there(self):
        with mock.patch.object(about_dialog, 'random_quote', return_value=LONG_QUOTE * 4):
            await self.press(keybindings.MainPage.ABOUT)
        self.assertEqual(len(self.app.screen.quote_lines(dialog_values.DIALOG_WIDTH - dialog_values.DIALOG_MARGIN)), about_dialog.QUOTE_LINES)
        self.assertEqual(sum(LONG_QUOTE_WORD in line for line in self.dialog_lines()), about_dialog.QUOTE_LINES)
        await self.press(Key.ENTER)

    async def test_every_quote_keeps_the_dialog_on_a_usual_console(self):
        for quote in about.MSG_ABOUT_QUOTES:
            with mock.patch.object(about_dialog, 'random_quote', return_value=quote):
                await self.press(keybindings.MainPage.ABOUT)
            self.assertIn(Box.HEAVY_BOTTOM_LEFT, self.text(), quote)
            await self.press(Key.ENTER)

    async def test_the_quote_is_one_of_the_quotes_when_the_roll_falls_over_the_eight_balls_chance(self):
        with mock.patch.object(about_dialog.random, 'random', return_value=about_dialog.EIGHT_BALL_CHANCE + (1 - about_dialog.EIGHT_BALL_CHANCE) / 2):
            await self.press(keybindings.MainPage.ABOUT)
        self.assertIn(self.app.screen.quote, about.MSG_ABOUT_QUOTES)
        self.assertNotIn(fixed_text(about.MSG_EIGHT_BALL), self.app.screen.quote)
        await self.press(Key.ENTER)

    async def test_the_build_date_is_a_date_and_the_year_comes_from_it(self):
        self.assertRegex(version.BUILD_DATE, DATE_PATTERN)
        self.assertRegex(version.BUILD_TIME, TIME_PATTERN)
        self.assertEqual(build_year(), version.BUILD_DATE[:len(build_year())])
