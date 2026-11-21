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

"""The tracker's look: the selected row's mark and the boxes, the header and the theme's stripe, captions, and the rules of the design."""

from fractions import Fraction
import pathlib
from textual.app import App
from textual.screen import Screen
import unittest
from unittest import mock

from llamatron.composition.file_format import ChordSymbol, PatternSetting, Row, Section
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.setlist import new_setlist
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.strings import about, labels, marks
from llamatron.tui import app as tui_app, drawing, keybindings, themes
from llamatron.tui.app import LlamatronApp
from llamatron.tui.dialogs import chord_dialog
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.chord_dialog import ChordDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.document import Document
from llamatron.tui.drawing import Box, Style
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import Reconfigure
from llamatron.tui.screens.set import main_page
from llamatron.tui.screens.set.file_page import FilePage
from llamatron.tui.screens.set.songs_page import SongsPage
from llamatron.tui.screens.shared import page as page_values
from tests.support import ui_testing
from tests.support.page_testing import boxed_line
from tests.support.rendering import render_song
from tests.support.ui_testing import key_name, UITest

# A word repeated into a set's crumb too long to share the header's line with the program's name.
LONG_SONG_WORD = 'x'
TUNE = 'tune'
SIXTEENTH = '1/16'
MINOR_SEVENTH = 'Minor seventh'
EXIT = 'exit'
# Every Python file of the tracker, which the design tests read.
TRACKER_FILES = '**/*.py'
COMPOSE = 'compose'
ON_MOUNT = 'on_mount'
ON_KEY = 'on_key'
ON_RESIZE = 'on_resize'
ON_SCREEN_RESUME = 'on_screen_resume'
RED = 'red'
GREEN = 'green'
BLUE = 'blue'
YELLOW = 'yellow'
CYAN = 'cyan'
MAGENTA = 'magenta'
WHITE = 'white'
BLACK = 'black'
TOOLTIP = 'tooltip'
FILE_ENCODING = 'utf-8'
LINE_SEPARATOR = '\n'
# What a title in block letters would be drawn with.
BLOCK_LETTER = '█'
# The places of a Yes or No dialog's buttons.
YES_BUTTON = 0
NO_BUTTON = 1

# Where every class of llamatron's lives.
OUR_PACKAGE = 'llamatron.'

class TestLookAndNewKeys(UITest):

    async def test_the_title_is_plain_text_and_nothing_sits_between_the_rule_and_the_cells(self):
        # No set-and-song line: the crumbs say the first and the cells count the set's things.
        lines = self.text().splitlines()
        self.assertIn(drawing.SPACE + page_values.PROGRAM_NAME + drawing.SPACE, lines[0])
        self.assertNotIn(about.MSG_SITE, self.text())
        # No title drawn in block letters over the cells.
        self.assertNotIn(BLOCK_LETTER, LINE_SEPARATOR.join(lines[:lines.index(next(line for line in lines if labels.PageName.ARRANGE in line))]))
        first_cell = next(number for number, line in enumerate(lines) if line.startswith((Box.TOP_LEFT, Box.DOUBLE_TOP_LEFT)))
        self.assertTrue(all(not line.strip() for line in lines[self.app.screen.header_lines():first_cell]))


    async def test_new_sets_default_to_sixteenth_note_steps(self):
        self.assertEqual(new_setlist()[PatternSetting.STEP_SIZE], SIXTEENTH)
        document = Document()
        document.add_pattern(name=TUNE, steps=2)
        self.assertEqual(document.lengths().pattern_length(TUNE), Fraction(1, 8))

    async def go_to_row(self, name):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        editor = self.app.screen
        section = editor.rows_view.section_of(name)
        if section is not None and not editor.rows_view.section_is_open(section):
            # PgDn reaches the section's heading, which every pattern shows, and Space opens it.
            self.assertIn(section, [row.name for row in editor.rows_view.reachable()])
            while editor.row_name() != section:
                await self.press(Key.PAGE_DOWN)
            await self.press(Key.SPACE)
        names = [row.name for row in editor.rows_view.reachable()]
        self.assertIn(name, names)
        await self.press(*[Key.DOWN] * (names.index(name) - names.index(editor.row_name())))

    def value(self, row):
        return self.document.step_value(name=TUNE, row=row, step=self.app.screen.step)

    async def test_enter_on_a_chord_cell_opens_the_chord_dialog_on_its_qualities(self):
        await self.go_to_row(Row.CHORD)
        await self.press(Key.ENTER)
        dialog = self.app.screen
        self.assertIsInstance(dialog, ChordDialog)
        self.assertEqual(dialog.part, chord_dialog.QUALITY_LIST)
        self.assertIsNone(dialog.choice().quality)
        dialog.places[chord_dialog.QUALITY_LIST] = dialog.qualities.index(ChordSymbol.MINOR7)
        await self.press(Key.ENTER)
        self.assertEqual(self.value(Row.CHORD), ChordSymbol.MINOR7)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.choice().quality, ChordSymbol.MINOR7)
        self.assertIn(MINOR_SEVENTH.lower(), self.dialog_text())
        self.app.screen.places[chord_dialog.QUALITY_LIST] = self.app.screen.qualities.index(ChordSymbol.SCALE_TRIAD)
        await self.press(Key.ENTER)
        self.assertEqual(self.value(Row.CHORD), 3)
        render_song(self.document.song())

    def dialog_text(self):
        return str(self.app.screen.query_one('#dialog-view').render())

    async def test_the_chord_dialog_fits_the_console(self):
        await self.go_to_row(Row.CHORD)
        await self.press(Key.ENTER)
        text = self.dialog_text()
        # On this console; the smallest console is held by TestChordDialogOnASmallConsole.
        self.assertLessEqual(len(text.splitlines()), self.app.size.height)
        self.assertLessEqual(max(len(line) for line in text.splitlines()), self.app.size.width)

    async def test_typing_numbers_into_ratchet(self):
        await self.go_to_row(Row.RATCHET)
        await self.press('4')
        self.assertEqual(self.value(Row.RATCHET), 4)
        await self.press(Key.RIGHT, Key.LEFT, '1', '2')
        self.assertEqual(self.value(Row.RATCHET), 12)

    async def test_too_big_a_number_starts_again(self):
        await self.go_to_row(Row.RATCHET)
        await self.press('1', '6', '3')
        self.assertEqual(self.value(Row.RATCHET), 3)

    async def test_typing_velocity_with_several_digits(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press('1', '0', '0')
        self.assertEqual(self.value(Row.VELOCITY), 100)
        await self.press(Key.RIGHT, Key.LEFT, '6', '4')
        self.assertEqual(self.value(Row.VELOCITY), 64)
        await self.press(keybindings.NumberRow.MORE)
        await self.press('9')
        self.assertEqual(self.value(Row.VELOCITY), 9)

    async def test_zero_is_refused_where_it_is_out_of_range(self):
        await self.go_to_row(Row.VELOCITY)
        await self.press('5', Key.RIGHT, Key.LEFT, '0')
        self.assertEqual(self.value(Row.VELOCITY), 5)

    async def test_typing_probability(self):
        await self.go_to_row(Row.PROBABILITY)
        await self.press('0')
        self.assertEqual(self.value(Row.PROBABILITY), 0)
        await self.press('1', '0', '0')
        self.assertEqual(self.value(Row.PROBABILITY), 100)

    async def test_typing_does_not_move_the_cursor(self):
        await self.go_to_row(Row.VELOCITY)
        before = (self.app.screen.step, self.app.screen.rows_view.row)
        await self.press('1', '0')
        self.assertEqual((self.app.screen.step, self.app.screen.rows_view.row), before)

    async def test_a_scale_with_more_than_nine_notes_takes_two_digits(self):
        self.document.add_scale(name=ui_testing.CHROMATIC_SCALE, root=NoteName.C, kind=scale_type_name(ScaleType.CHROMATIC))
        self.document.change(self.document.song().set_scale_name, ui_testing.CHROMATIC_SCALE)
        self.document.changed()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, '1', '2')
        self.assertEqual(self.value(Row.DEGREE), 12)


class TestArrowsAndTheMark(UITest):
    """The cursor shows itself as a triangle on every page with rows, and the arrows and ENTER get around without a letter."""

    def marked_line(self):
        """Return the one line of the page with the mark on it."""
        lines = [line for line in self.text().splitlines() if drawing.SELECTED_MARK in line]
        self.assertEqual(len(lines), 1, self.text())
        return lines[0]

    def marked_dialog_line(self):
        """Return the one line inside the open dialog with the mark on it; the page beneath can show its own."""
        lines = [line.split('┃')[1] for line in self.text().splitlines() if line.count('┃') >= 2 and drawing.SELECTED_MARK in line.split('┃')[1]]
        self.assertEqual(len(lines), 1, self.text())
        return lines[0]

    async def test_the_main_screen_boxes_every_cell_and_the_selected_one_double_in_place_of_the_mark(self):
        self.assertNotIn(drawing.SELECTED_MARK, self.text())
        self.assertIn(labels.PageName.ARRANGE, boxed_line(self.text()))
        # Every cell has a box, and the selected one's is double-lined, the only such box; a cell's name starts one space after the key.
        # The bar's six actions share one box, and Arrange's, selected, is the double one.
        self.assertEqual(self.text().count(Box.TOP_LEFT), len(self.app.screen.menu_items()) - main_page.BAR_ROWS * main_page.COLUMNS)
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)
        await self.press(*self.app.screen.arrows_to(keybindings.MainPage.SONGS))
        self.assertIn(f'« {key_name(keybindings.MainPage.SONGS)} » {labels.PageName.SONGS}', boxed_line(self.text()))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, SongsPage)
        await self.press(Key.ESCAPE)
        self.assertIn(labels.PageName.SONGS, boxed_line(self.text()))

    async def test_each_pages_cell_is_boxed_in_its_theme_toned_to_one_brightness(self):
        page = self.app.screen
        patterns = next(item for item in page.menu_items() if item.binding is keybindings.MainPage.PATTERNS)
        arrange = next(item for item in page.menu_items() if item.binding is keybindings.MainPage.ARRANGE)
        self.assertEqual(page.edge_style(patterns).color.get_truecolor(), themes.balanced(themes.PATTERNS))
        self.assertEqual(page.edge_style(arrange), Style.DIM)
        brightness = {round(themes.luminance(themes.balanced(colour)), 2) for colour in (themes.SONGS, themes.PATTERNS, themes.GROOVES, themes.REGISTERS)}
        self.assertEqual(len(brightness), 1)

    async def test_enter_on_the_quit_cell_quits(self):
        # The Quit cell is the last of the actions.
        await self.press(*self.app.screen.arrows_to(keybindings.MainPage.QUIT))
        self.assertIn(labels.PageName.QUIT, boxed_line(self.text()))
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(Key.ENTER)
            leave.assert_called_once()


    async def test_a_list_page_marks_the_selected_row_without_reverse_video(self):
        await self.press(keybindings.MainPage.PATTERNS)
        self.assertIn(TUNE, self.marked_line())
        self.assertNotIn('«', self.marked_line())
        await self.press(Key.DOWN)
        self.assertIn(labels.MSG_NEW_PATTERN_BUTTON, self.marked_line())

    async def test_a_settings_page_marks_the_selected_field_and_reverses_only_a_selected_button(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(labels.MSG_TITLE_LABEL)
        line = self.marked_line()
        self.assertIn(labels.MSG_TITLE_LABEL, line)
        self.assertNotIn('«', line)
        # The buttons are a row of boxes, the selected one double-lined, as the dialogs' are.
        await self.select_field(labels.PageName.SAVE)
        line = next(line for line in self.text().splitlines() if labels.PageName.SAVE in line and key_name(keybindings.Page.SAVE) in line)
        self.assertLess(line.index(Box.DOUBLE_BAR), line.index(labels.PageName.SAVE))
        await self.select_field(labels.MSG_TITLE_LABEL)
        unselected = next(line for line in self.text().splitlines() if labels.PageName.SAVE in line and key_name(keybindings.Page.SAVE) in line)
        self.assertNotIn(Box.DOUBLE_BAR, unselected)

    async def test_a_picker_marks_the_highlighted_option(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        await self.reconfigure(Reconfigure.LOAD_OVER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        options = self.app.screen.options
        self.assertIn(options[0], self.marked_dialog_line())
        self.assertNotIn('«', self.marked_dialog_line())
        await self.press(Key.DOWN)
        self.assertIn(options[1], self.marked_dialog_line())
        await self.press(Key.ESCAPE)

    async def test_yes_and_no_are_buttons_that_the_arrows_move_between_and_enter_presses(self):
        self.document.changed()
        await self.press(keybindings.MainPage.FILE, keybindings.FilePage.NEW)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        # The buttons are boxed, the selected one double-lined: its box's side comes just before its key.
        self.assertEqual(self.app.screen.choice, YES_BUTTON)
        self.assertIn(Box.DOUBLE_BAR, self.text())
        await self.press(Key.RIGHT)
        self.assertEqual(self.app.screen.choice, NO_BUTTON)
        await self.press(Key.ENTER)
        # No: the set is kept.
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertTrue(self.document.is_dirty())
        await self.press(keybindings.FilePage.NEW, Key.RIGHT, Key.RIGHT, Key.LEFT, Key.LEFT, Key.ENTER)
        # Right from No stays on No and Left from Yes stays on Yes, since no cursor goes round: Yes is pressed, and the set is replaced.
        self.assertFalse(self.app.get_document().is_dirty())

    async def test_no_cursor_goes_round_from_one_end_to_the_other(self):
        """Up on the first row and Down on the last stay put on a list page, a settings page and a picker, and so do Left and Right in the pattern editor and the one-row editors (.claude/UX.md)."""
        names = self.document.get_setlist().get_scale_names()
        await self.press(keybindings.MainPage.SCALES, Key.UP)
        self.assertEqual(self.app.screen.current(), names[0])
        await self.press(*[Key.DOWN] * (len(names) + 1))
        self.assertIsNone(self.app.screen.current())
        await self.press(Key.ESCAPE, keybindings.MainPage.SONGS, Key.ENTER, Key.UP)
        self.assertEqual(self.app.screen.cursor.get_place(), 0)
        last = len(self.app.screen.fields()) - 1
        await self.press(*[Key.DOWN] * (last + 1))
        self.assertEqual(self.app.screen.cursor.get_place(), last)
        await self.select_field(labels.MSG_SCALE_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.UP)
        self.assertEqual(self.app.screen.cursor.get_place(), 0)
        count = len(self.app.screen.matches())
        await self.press(*[Key.DOWN] * count)
        self.assertEqual(self.app.screen.cursor.get_place(), count - 1)
        await self.press(Key.ESCAPE, Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        editor = self.app.screen
        await self.press(Key.LEFT, Key.UP)
        self.assertEqual((editor.step, editor.rows_view.row), (0, 0))
        await self.press(*[Key.RIGHT] * editor.step_count(), *[Key.DOWN] * len(editor.rows_view.reachable()))
        self.assertEqual((editor.step, editor.rows_view.row), (editor.step_count() - 1, len(editor.rows_view.reachable()) - 1))
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD, Key.LEFT)
        self.assertEqual(self.app.screen.step, 0)
        await self.press(*[Key.RIGHT] * len(self.app.screen.cells()))
        self.assertEqual(self.app.screen.step, len(self.app.screen.cells()) - 1)


def tracker_sources():
    """Return (path, source) for every Python file of the tracker."""
    folder = pathlib.Path(tui_app.__file__).parent
    return [(path, path.read_text(encoding=FILE_ENCODING)) for path in sorted(folder.glob(TRACKER_FILES))]


class TestDesign(unittest.TestCase):

    def test_there_are_no_tooltips(self):
        for path, text in tracker_sources():
            with self.subTest(path=path):
                self.assertNotIn(TOOLTIP, text)

    def test_the_command_palette_is_off(self):
        self.assertFalse(LlamatronApp.ENABLE_COMMAND_PALETTE)
        self.assertTrue(issubclass(LlamatronApp, App))

    def test_the_program_uses_terminal_colors_only(self):
        for path, text in tracker_sources():
            for color in [RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE, BLACK, '#']:
                with self.subTest(path=path, color=color):
                    self.assertNotIn(f"style='{color}", text)

    def test_no_screen_replaces_a_method_that_textual_needs(self):
        # Naming a method remove or render here stops screens from closing or drawing.
        ours = {COMPOSE, ON_MOUNT, ON_KEY, ON_RESIZE, ON_SCREEN_RESUME}
        for page in screens_of_ours():
            for name, value in vars(page).items():
                if callable(value) and not name.startswith('_') and name not in ours:
                    with self.subTest(page=page.__name__, name=name):
                        self.assertFalse(hasattr(Screen, name))


class TestTitleInTheMiddle(UITest):
    """The header's first line keeps the set and its song in the left corner and the save mark in the right, the program's name centred between."""

    async def test_the_name_is_centred_and_gives_way_to_a_long_set_and_song(self):
        self.assert_title(set_crumb=self.app.screen.set_crumb())
        page = self.app.screen
        long_crumb = LONG_SONG_WORD * page.size.width
        line = page.header_line(width=page.size.width, left=long_crumb, names=drawing.NOTHING, names_start=page.size.width - 1, mark=marks.MSG_UNSAVED_MARK, centre=page_values.PROGRAM_NAME).plain
        self.assertNotIn(page_values.PROGRAM_NAME, line)
        self.assertTrue(line.rstrip().endswith(marks.MSG_UNSAVED_MARK))
    """Each kind of page has a theme colour, drawn as a stripe under the header in place of its rule; the main screen and Arrange keep the rule."""

    async def test_a_page_and_its_list_share_a_colour_the_main_screen_is_white_and_arrange_has_none(self):
        self.assertEqual(self.app.screen.theme(), themes.MAIN_SCREEN)
        await self.press(keybindings.MainPage.ARRANGE)
        self.assertIsNone(self.app.screen.theme())
        await self.press(Key.ESCAPE, keybindings.MainPage.PATTERNS)
        listed = self.app.screen.theme()
        self.assertEqual(listed, themes.PATTERNS)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.theme(), listed)

    async def test_the_stripe_takes_the_rules_place_and_a_blank_line_follows_only_where_there_is_room(self):
        await self.press(keybindings.MainPage.PATTERNS)
        page = self.app.screen
        lines = page.header(page.size.width)
        self.assertEqual(lines[2].plain.strip(), page.caption())
        self.assertEqual(len(lines), page.header_lines())
        self.assertEqual(page.has_room_for_the_gap(), page.size.height >= page_values.ROOM_FOR_THE_GAP)


class TestCaptionsAndNames(UITest):
    """The theme's stripe carries the page's caption, and a page that starts with Name leaves a blank line under it."""

    async def test_a_list_says_its_name_and_an_editor_says_what_it_edits(self):
        await self.press(keybindings.MainPage.PATTERNS)
        self.assertEqual(self.app.screen.caption(), labels.Crumb.PATTERNS)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.caption(), labels.MSG_EDITING_CAPTION.format(what=labels.MSG_CAPTION_WORDS[Section.PATTERNS].upper(), name=self.app.screen.item))
        self.assertIn(self.app.screen.caption(), self.text().splitlines()[2])

    async def test_a_blank_line_follows_name(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        lines = [line.plain for line in self.app.screen.body(width=self.SIZE[0], height=self.SIZE[1])]
        name_line = next(place for place, line in enumerate(lines) if labels.MSG_NAME_LABEL in line)
        self.assertEqual(lines[name_line + 1].strip(), drawing.NOTHING)


def screens_of_ours():
    """Return every screen class of llamatron's, every page and dialog, found from Textual's Screen once every page is imported."""
    ui_testing.leaf_pages()
    found = []
    waiting = [Screen]
    while waiting:
        for kind in waiting.pop().__subclasses__():
            waiting.append(kind)
            if kind.__module__.startswith(OUR_PACKAGE):
                found.append(kind)
    return found
