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

"""The main screen, the File, Songs, Song and Description pages, loading, exporting, quitting, the keys every page shows, help and the program's look."""

import os
import pathlib
import unittest
from fractions import Fraction
from unittest import mock

from textual.app import App
from textual.screen import Screen

from ui_testing import BEAT, CHROMATIC_SCALE, KEY_SHOWN, UITest, a_song, fixed_text, key_of, key_name
from llamatron.strings.labels import MSG_TEMPO_LABEL
from llamatron.strings.labels import MSG_DEFAULT_DRUM_OCTAVE_LABEL
from llamatron.strings.labels import MSG_DEFAULT_OCTAVE_LABEL
from llamatron.tui.drawing import Box, NOTHING, SELECTED_MARK, SPACE, Style
from llamatron.tui.screens.main_page import CELL_COLUMNS
from llamatron.tui.dialogs import about_dialog
from llamatron.tui.dialogs.about_dialog import EIGHT_BALL_CHANCE, QUOTE_LINES
from llamatron.tui.dialogs.dialog import DIALOG_MARGIN, DIALOG_VIEW_SELECTOR, DIALOG_WIDTH
from llamatron.tui.dialogs.about_dialog import AboutDialog
from llamatron.tui.dialogs.help_dialog import HelpDialog
from llamatron.composition.file_format import (
    NAMED_GENERATORS,
    SongSetting,
    LiveResponsiveness,
    ClipSlotSetting,
    ChordSymbol,
    Direction,
    GeneratorKind,
    FollowAction,
    OctaveLabels,
    PatternSetting,
    Row,
    Section,
    SetlistSetting,
    STEP_SIZE_CHOICES,    TIME_SIGNATURE_CHOICES,
)
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.defaults import DEFAULT_DRUM_OCTAVE, DEFAULT_OCTAVE
from llamatron.composition.setlist import NO_TEXT, new_setlist
from llamatron.composition.defaults import DEFAULT_TIME_SIGNATURE, FIRST_NUMBER
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.tui import app as tui_app
from llamatron.tui.app import LlamatronApp
from llamatron.tui import themes
from llamatron.tui.screens.page import ROOM_FOR_THE_GAP
# A word repeated into a set's crumb too long to share the header's line with the program's name.
LONG_SONG_WORD = 'x'
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.screens.clip_page import ClipPage
from llamatron.tui.screens.scene_page import ScenePage
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.dialogs.chord_dialog import QUALITY_LIST, ChordDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.dialogs.quit_dialog import QuitDialog
from llamatron.tui.screens.page import Page, PROGRAM_NAME
from llamatron.exporters.exports import earlier_export, shown_export_path, EXPORT_LABELS, ExportKind
from llamatron.composition.setlist import DEFAULT_SCALE
from llamatron.tui.document import Document
from llamatron.tui.uses import LOOP_ERRORS_SHOWN
from llamatron.strings.errors import (
    ERR_ADD_A_SCALE_FIRST, ERR_AND_MORE, ERR_CANT_SAVE_TITLE, ERR_LOOP_SCENES_INTRO, ERR_LOOP_SCENES_TITLE, ERR_NAME_IN_USE,
    ERR_TYPED_NOT_A_TIME_SIGNATURE,
)
from llamatron.music.time_signature import MAX_BEATS, MIN_BEATS, UNITS_LISTED
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.arp_editor import ArpEditor
from llamatron.tui.screens.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.chain_editor import ChainEditor
from llamatron.tui.screens.chains_page import ChainsPage
from llamatron.tui.screens.notes_page import NotesPage
from llamatron.tui.screens.file_page import FilePage
from llamatron.tui.screens.generators_page import GeneratorsPage
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.screens.patterns_page import PatternsPage
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.tui.screens.grooves_page import GroovesPage
from llamatron.tui.screens.groove_editor import GrooveEditor
from llamatron.tui.screens.instrument_editor import InstrumentEditor
from llamatron.tui.screens.instruments_page import InstrumentsPage
from llamatron.tui.screens.scales_page import ScalesPage
from llamatron.tui.screens.open_page import PARENT, OpenPage
from llamatron.tui.screens.song_page import SongPage
from llamatron.tui.screens.songs_page import SongsPage
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.tui.screens.pattern_editor import PatternEditor, Reconfigure
from llamatron.support.version import BUILD_DATE, BUILD_TIME, build_year, VERSION
from llamatron.strings.about import (
    MSG_ABOUT_BLOG, MSG_ABOUT_COPYRIGHT, MSG_ABOUT_LICENSE, MSG_ABOUT_MORE, MSG_ABOUT_POWERED, MSG_ABOUT_QUOTES, MSG_ABOUT_VERSION,
    MSG_ABOUT_WEB, MSG_COW, MSG_COW_BUBBLE_TEXT, MSG_EIGHT_BALL, MSG_EIGHT_BALL_ANSWERS, MSG_SITE,
)
from llamatron.composition.song import NO_GENRE
from llamatron.strings.labels import MSG_VISUALIZER_LABEL, MSG_CAPTION_WORDS, MSG_EDITING_CAPTION
from llamatron.strings.labels import (
    MSG_GENRE_LABEL, MSG_LIVE_RESPONSIVENESS_LABEL, MSG_LIVE_RESPONSIVENESS_NAMES, MSG_PREVIEW_INSTRUMENT_LABEL, MSG_PREVIEW_INSTRUMENT_UNSET,
    MSG_SECTION_LABEL, MSG_SECTION_NAMES, Crumb, MSG_ABOUT, MSG_NOTES_BUTTONS, MSG_DESCRIPTION_LABEL, MSG_NOTES_LABEL,
    MSG_EXPORT_CHOICES, MSG_SET_CRUMB, MSG_SONG_CRUMB, MSG_GROOVE_LABEL, MSG_HELP_PANELS, MSG_NAME_LABEL, MSG_NO_FILE_CRUMB, MSG_OCTAVE_LABELS_LABEL, MSG_DEFAULT_FOLLOW_ACTION_LABEL,
    MSG_PROTECTED_LABEL, MSG_QUIT_BUTTONS, MSG_SCALE_LABEL, MSG_SEED_LABEL, MSG_TIME_SIGNATURE_LABEL, MSG_ENTRY_SIZE_LABEL, MSG_TITLE_LABEL,
    PageName,
)
from llamatron.strings.legends import MSG_LEGEND_WHAT, What, MSG_ABOUT_FOOTER_WHAT, KeyName
from llamatron.strings.marks import MSG_PICKER_MARK
from llamatron.strings.marks import (
    MSG_FOLDER_ROW, MSG_PARENT_ROW,
    MSG_SECTION_OPEN_MARK, MSG_NOTE_UNDER_CURSOR, MSG_CRUMB_SEPARATOR, MSG_EXPORTS_AFTER_SAVING, MSG_NOT_SET,
    MSG_ONE_STEP_SHOWN, MSG_UNSAVED_MARK, MSG_UNSAVED_CHANGES_MARK, MSG_SAVED_MARK,
)
from llamatron.strings.messages import (
    MSG_EXPORTED, MSG_FILE_CHANGED_ELSEWHERE_TITLE, MSG_FILE_UNCHANGED, MSG_PROTECTED_TITLE, MSG_QUIT_UNSAVED_NOTE,
    MSG_SAVE_BEFORE_EXPORT_TITLE,
)
from llamatron.strings.names import MSG_NUMBERED_NAME, MSG_DEFAULT_SONG_NAME, MSG_NEW_PATTERN_NAME, MSG_NEW_TRACK_NAME
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key
from llamatron.tui.text import clock, tempo_text
from rendering import render_song

# The file the export tests save their set as, and where its untitled song's exports then go: beside it, as <set>_<song>.
# The shape of the build date and time, as version.py writes them.
# A quote wider than one line of the About dialog, made of one word repeated.
LONG_QUOTE_WORD = 'rhubarb'
A_GENRE = 'Lounge'
# Two instruments a test adds, in the order a picker lists them, and what the first is renamed to.
KEYS_INSTRUMENT = 'keys'
ORGAN_INSTRUMENT = 'organ'
RENAMED_INSTRUMENT = 'piano'
LONG_QUOTE = (LONG_QUOTE_WORD + ' ') * 12
DATE_PATTERN = r'^\d{4}-\d{2}-\d{2}$'
TIME_PATTERN = r'^\d{2}:\d{2}$'
# The start of the Patterns page's help, which the F1 dialog's second panel shows and the first doesn't.
HELP_PATTERNS_FIRST_WORDS = 'Every pattern in the set'
# Typed into a prompt that Esc then cancels.
ESCAPED_TITLE = 'never'
SET_FILE = 'my_set.yml'
# A set file name a test saves to when SET_FILE is taken already, and what its untitled song's Live set is then called.
OTHER_SET_FILE = 'other_set.yml'
OTHER_LIVE_SET = 'other_set_untitled.als'
# A file name the prompt test changes into another by moving the cursor.
FOO_YML = 'foo.yml'
FOO2_YML = 'foo2.yml'
YML_SUFFIX = '.yml'
EXPORT = 'my_set_untitled'
LIVE_SET = EXPORT + '.als'
OTHER_TEMPO = 99
# The export dialog's choices, in the order of MSG_EXPORT_CHOICES.
EXPORT_LIVE = 0
EXPORT_STEMS = 1
EXPORT_MIDI_FILE = 2
EXPORT_CLIPS = 3

# Names the tests give to their own things, and other values they use.
HALF = '1/2'
QUARTER = '1/4'
EIGHTH = '1/8'
DESCRIPTION_KEY = 'd'
TUNE = 'tune'
MAIN = 'main'
FILE = 'file'
SONGS = 'songs'
SONG = 'song'
NOTES_EDITING = 'notes editing'
PATTERN_EDITOR = 'pattern editor'
PATTERN_ROWS = 'pattern rows'
CHAIN_EDITOR = 'chain editor'
GENERATORS = 'generators'
ARRANGE = 'arrange'
ARRANGE_CELL = 'arrange cell'
ARRANGE_TRACK = 'arrange track'
ARRANGE_CORNER = 'arrange corner'
ARRANGE_TRACK_PLUS = 'arrange track plus'
TRACK_EDITOR = 'track editor'
SCENE_ONE = 'one'
SCENE_TWO = 'two'
CLIP = 'clip'
SCENE = 'scene'
SONG_FIELD = 'song field'
FILE_FIELD = 'file field'
PATTERN_ROW = 'pattern row'
LEAD = 'lead'
DRUMS = 'drums'
FIRST_TRACK = MSG_NEW_TRACK_NAME.format(number=1)
OTHER = 'other'
RAIN_ON_THE_BRIDGE = 'Rain on the Bridge'
NOT_AN_INTEGER = 'is not an integer'
OVERWRITE = 'overwrite'
FOLDER_OF_SETS = 'sets'
INNER_FOLDER = 'more'
PARENT_FOLDER = '..'
SECOND_SONG = 'second'
# A time signature the Song page's list doesn't offer, and text that isn't one.
SEVEN_EIGHT = '7/8'
NOT_A_SIGNATURE = '4/5'
# Scenes named for the loop errors dialog, and how many scenes make it say 'and 1 more'.
VERSE = 'verse'
CHORUS = 'chorus'
ONE_MORE_THAN_SHOWN = LOOP_ERRORS_SHOWN + 1
TITLE = 'Title'
AUTHOR = 'Author'
TEMPO = 'Tempo'
SOMEONE = 'Someone'
STEP_SIZE = 'Step size'
WRITE_TEXT = 'w'
# A directory the Open page goes into, and the row that goes back up.
SUBFOLDER = 'more songs'
PARENT_FOLDER = PARENT
KEEP = 'keep'
NO_NOTES_YET = 'No notes yet'
HI_THERE = 'Hi there\n'
HIX_THERE = 'HiX there\n'
HIX_THERE_2 = 'HiX there'
H_2 = 'h\n'
# Letters the tests press on purpose that aren't keys: two letters no page binds, and a letter typed as
# text into the description. Textual's own name for the Ctrl+Q the tracker no longer binds.
CTRL_Q = 'ctrl+q'
UNBOUND_LETTERS = ('j', 'k')
TYPED_LETTER = 'h'
ONETWO = 'onetwo\n'
ONE = 'one\n'
LINE_0 = 'line 0\n'
LINE_2 = 'line 2'
BASS = 'bass'
C_MAJOR = 'C Major'
SIXTEENTH = '1/16'
MINOR_SEVENTH = 'Minor seventh'
SCALE = 'SCALE'
GROOVE_EDITOR = 'GROOVE_EDITOR'
INSTRUMENT_EDITOR = 'INSTRUMENT_EDITOR'
HELP = 'Help'
WHAT_THE_PAGE = 'What the page'
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
# The places of a Yes or No dialog's buttons.
YES_BUTTON = 0
NO_BUTTON = 1


def boxed_line(text):
    """Return the selected cell of the main screen's grid, its key and name between the sides of its double-lined box, the only such box."""
    lines = [line for line in text.splitlines() if line.count(Box.DOUBLE_BAR) >= 2 and '«' in line]
    assert len(lines) == 1, text
    line = lines[0]
    return line[line.index(Box.DOUBLE_BAR):line.rindex(Box.DOUBLE_BAR) + 1]



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
        # Arrange's row first, with the Real Time switch, then the pages four to a row, then the Set File page with the actions, and the footer ends with help and about.
        lines = text.splitlines()
        self.assertLess(next(number for number, line in enumerate(lines) if '« A »' in line), next(number for number, line in enumerate(lines) if '« P »' in line))
        self.assertEqual(sum(1 for line in lines if '« F »' in line), 1)
        self.assertEqual(next(line for line in lines if '« P »' in line).count('«'), CELL_COLUMNS)
        self.assertIn('« Q »', next(line for line in lines if '« F »' in line))
        self.assertIn('« F1 »', lines[-1])
        self.assertTrue(lines[-1].rstrip().endswith(MSG_ABOUT_FOOTER_WHAT))

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
        await self.press(Key.DOWN)
        self.assertIn(f'{counts[first_key(keybindings.MainPage.SONGS)]} {Box.DOUBLE_BAR}', boxed_line(self.text()))
        await self.press(keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD, Key.ESCAPE, Key.ESCAPE)
        self.assertEqual(page.count(next(item for item in page.menu_items() if item.binding is keybindings.MainPage.GROOVES)), 1)

    async def test_the_arrows_move_the_box_over_the_grid_and_it_stays_while_a_page_is_open(self):
        # The grid, the user's layout: Arrange and Real Time; Songs, Scales, Patterns, Grooves; Generators, Chains, Instruments,
        # Registers; Set File, Save, Open, Export, Import, Quit. The cursor starts on Arrange.
        self.assertIn(PageName.ARRANGE, boxed_line(self.text()))
        await self.press(Key.RIGHT)
        self.assertIn(PageName.REAL_TIME, boxed_line(self.text()))
        # Down keeps the column where the row has one: Scales, then Chains, then Save.
        await self.press(Key.DOWN)
        self.assertIn(PageName.SCALES, boxed_line(self.text()))
        await self.press(Key.DOWN)
        self.assertIn(PageName.CHAINS, boxed_line(self.text()))
        await self.press(Key.DOWN)
        self.assertIn(PageName.SAVE, boxed_line(self.text()))
        await self.press(*[Key.RIGHT] * len(self.app.screen.rows()[-1]))
        self.assertIn(PageName.QUIT, boxed_line(self.text()))
        # Up from the sixth column lands on the row above's last cell, Registers, and Up again keeps that column: Grooves.
        await self.press(Key.UP)
        self.assertIn(PageName.REGISTERS, boxed_line(self.text()))
        await self.press(Key.UP)
        self.assertIn(PageName.GROOVES, boxed_line(self.text()))
        # Left steps back along the rows.
        await self.press(Key.LEFT, Key.LEFT)
        self.assertIn(PageName.SCALES, boxed_line(self.text()))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ScalesPage)
        await self.press(Key.ESCAPE)
        self.assertIn(PageName.SCALES, boxed_line(self.text()))
        await self.press(Key.LEFT, Key.LEFT)
        self.assertIn(PageName.REAL_TIME, boxed_line(self.text()))
        # No arrow goes past an edge: Up from the top row, Left from the first cell, Right from the last, or Down from the file's row.
        await self.press(Key.UP, Key.LEFT, Key.LEFT)
        self.assertIn(PageName.ARRANGE, boxed_line(self.text()))
        await self.press(*[Key.DOWN] * len(self.app.screen.rows()))
        self.assertIn(PageName.FILE, boxed_line(self.text()))
        await self.press(*[Key.RIGHT] * len(self.app.screen.menu_items()))
        self.assertIn(PageName.QUIT, boxed_line(self.text()))
        await self.press(Key.DOWN)
        self.assertIn(PageName.QUIT, boxed_line(self.text()))

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

    async def test_descriptions_start_with_a_capital_letter_and_only_the_selected_cells_is_shown(self):
        for about in MainPage.ABOUT.values():
            self.assertTrue(about[0].isupper(), about)
        self.assertIn(MSG_ABOUT[PageName.ARRANGE], self.text())
        self.assertNotIn(MSG_ABOUT[PageName.SCALES], self.text())
        await self.press(Key.RIGHT, Key.DOWN)
        self.assertIn(MSG_ABOUT[PageName.SCALES], self.text())
        self.assertNotIn(MSG_ABOUT[PageName.ARRANGE], self.text())


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

class TestRealKeys(UITest):
    """Presses keys the slow way, through the same path that a terminal's keys take."""

    async def test_keys_arrive_with_the_names_the_screens_expect(self):
        await self.pilot.press(first_key(keybindings.MainPage.PATTERNS).upper())
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.pilot.press(Key.ENTER)
        editor = self.app.screen
        self.assertIsInstance(editor, PatternEditor)
        # The roll comes first, with the cursor on the first note's row: Space a row up places the second degree, then Tab reaches the rows and their digits.
        await self.pilot.press(Key.RIGHT, Key.UP, Key.SPACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=1), 2)
        await self.pilot.press(first_key(keybindings.PatternEditor.TO_EDITOR), '5')
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=1), 5)
        # PgDn reaches the first section's heading, and Down from Degree reaches Gate, in the Timing section, which is open at the start; placing the note left it blank, one step.
        await self.pilot.press(Key.PAGE_DOWN)
        self.assertEqual(editor.row_name(), RowSection.BASICS)
        names = [row.name for row in editor.rows_view.reachable()]
        self.assertIn(Row.GATE, names)
        await self.pilot.press(*[Key.DOWN] * (names.index(Row.GATE) - names.index(editor.row_name())), key_of(binding=keybindings.GateRow.MORE, key=Key.PLUS))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.GATE, step=1), QUARTER)
        await self.pilot.press(key_of(binding=keybindings.GateRow.LESS, key=Key.MINUS))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.GATE, step=1), EIGHTH)
        await self.pilot.press(Key.DOWN, Key.SPACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DOT, step=1), DESCRIPTION_KEY)
        # Up to #/b, in the Basics section above.
        await self.pilot.press(*[Key.UP] * (names.index(Row.DOT) - names.index(Row.ACCIDENTAL)), Key.SPACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.ACCIDENTAL, step=1), '#')
        await self.pilot.press(Key.BACKSPACE)
        self.assertIsNone(self.document.step_value(name=TUNE, row=Row.ACCIDENTAL, step=1))
        await self.pilot.press(Key.ESCAPE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        await self.pilot.press(first_key(keybindings.MainPage.PATTERNS))
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.pilot.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_the_plain_keys_that_move_scenes_and_tracks_arrive_from_a_terminal(self):
        # Textual's own key handling delivers M and the arrows, which need no modifier a terminal might keep.
        await self.pilot.press(first_key(keybindings.MainPage.ARRANGE), first_key(keybindings.ArrangePage.MOVE_SCENE), Key.DOWN, Key.ENTER)
        self.assertEqual([scene.get_name() for scene in self.document.song().get_scenes()], [SCENE_TWO, SCENE_ONE])
        await self.pilot.press(Key.UP, Key.UP)
        while self.app.screen.track() != LEAD:
            await self.pilot.press(Key.LEFT)
        await self.pilot.press(first_key(keybindings.ArrangePage.MOVE_TRACK), Key.RIGHT, Key.ENTER)
        self.assertEqual(self.document.song().get_track_names(), [DRUMS, LEAD])
        await self.pilot.press(first_key(keybindings.ArrangePage.MOVE_TRACK), Key.LEFT, Key.ENTER)
        self.assertEqual(self.document.song().get_track_names(), [LEAD, DRUMS])

    async def test_q_asks_too(self):
        self.document.changed()
        await self.pilot.press(first_key(keybindings.MainPage.QUIT))
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, QuitDialog)

    async def test_the_global_control_and_function_keys_work_from_a_terminal(self):
        # A terminal sends a control key with an unprintable character and a function key with none,
        # so these can only be matched by name: a shortcut through the test helper once hid that.
        await self.pilot.press(first_key(keybindings.MainPage.PATTERNS), Key.CTRL_S)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, PromptDialog)
        # Exports need a saved set, so the set is saved before X is tried.
        self.document.save(path=SET_FILE)
        await self.pilot.press(Key.ESCAPE, Key.CTRL_X)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, MSG_EXPORT_CHOICES)
        await self.pilot.press(Key.ESCAPE, Key.F1)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, HelpDialog)


class EveryKeyIsShownTests:
    """The checks of every page's keys, run by two classes that each walk half of the pages, so that the walk is split between two processes."""

    async def visit(self):
        raise NotImplementedError

    async def test_every_key_in_the_table_is_on_screen_or_in_the_help_dialog(self):
        async for where in self.visit():
            page = self.app.screen
            text = self.text()
            for item in page.shown_keys():
                with self.subTest(where=where, label=item.shown_label()):
                    self.assertIn(f'« {item.shown_label()} »', text)
            if not any(item.binding is keybindings.Page.HELP for item in page.key_table()):
                continue
            await self.press(keybindings.Page.HELP)
            self.assertIsInstance(self.app.screen, HelpDialog, where)
            text = self.text()
            for item in page.key_table():
                # F1 is the one key its own dialog doesn't list, by the user's choice of 2026-11-09: whoever reads the dialog pressed it.
                if item.binding is keybindings.Page.HELP:
                    continue
                with self.subTest(where=where, label=item.shown_label()):
                    self.assertIn(f'« {item.shown_label()} »', text)
            # The dialog fits: its bottom edge is on the screen, on both panels.
            self.assertIn('┗', text, where)
            await self.press(Key.TAB)
            self.assertIn('┗', self.text(), where)
            await self.press(Key.ESCAPE)
            self.assertIs(self.app.screen, page, where)

    async def test_a_key_that_is_not_shown_does_nothing(self):
        await self.press(keybindings.MainPage.PATTERNS)
        before = self.text()
        await self.press(*UNBOUND_LETTERS, Key.F5)
        self.assertEqual(self.text(), before)

    async def test_no_key_table_is_empty(self):
        async for where in self.visit():
            with self.subTest(where=where):
                self.assertTrue(self.app.screen.keys())

    async def test_every_legend_starts_with_esc_and_a_hidden_key_is_listed_only_by_f1(self):
        async for where in self.visit():
            page = self.app.screen
            # The main screen has nowhere to go back to, and a dialog's legend is its own.
            if isinstance(page, (Dialog, MainPage)):
                continue
            with self.subTest(where=where):
                self.assertEqual(page.shown_keys()[0].keys, (Key.ESCAPE,))
                hidden = [item for item in page.keys() if not item.shown]
                for item in hidden:
                    self.assertNotIn(f'« {item.shown_label()} »', self.text(), item.shown_label())
                self.assertEqual([item for item in page.shown_keys() if not item.shown], [])


class TestEveryKeyIsShownOnTheSetPages(EveryKeyIsShownTests, UITest):
    """The main screen, File, Description, Songs, Song, Patterns and the pattern editor."""

    async def visit(self):
        yield MAIN
        await self.press(keybindings.MainPage.FILE)
        yield FILE
        for _ in range(5):
            await self.press(Key.DOWN)
            yield FILE_FIELD
        await self.select_field(MSG_NOTES_LABEL)
        await self.press(Key.ENTER)
        yield NOTES_EDITING
        await self.press(Key.ESCAPE)
        yield SetlistSetting.NOTES
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS)
        yield SONGS
        await self.press(Key.ENTER)
        yield SONG
        for _ in range(2):
            await self.press(Key.DOWN)
            yield SONG_FIELD
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS)
        yield Section.PATTERNS
        await self.press(Key.ENTER)
        yield PATTERN_EDITOR
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        yield PATTERN_ROWS
        for _ in range(8):
            await self.press(Key.DOWN)
            yield PATTERN_ROW


class TestEveryKeyIsShownOnTheSongPages(EveryKeyIsShownTests, UITest):
    """Chains, Generators, Scales, Grooves, Arrange and the pages under them."""

    async def visit(self):
        await self.press(keybindings.MainPage.CHAINS)
        yield Section.CHAINS
        await self.press(Key.ENTER)
        yield CHAIN_EDITOR
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GENERATORS)
        yield GENERATORS
        await self.press(Key.ENTER)
        yield GeneratorKind.ARP
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SCALES)
        yield Section.SCALES
        await self.press(Key.ENTER)
        yield SCALE
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GROOVES)
        yield Section.GROOVES
        await self.press(Key.ENTER)
        yield GROOVE_EDITOR
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.INSTRUMENTS, keybindings.InstrumentsPage.ADD)
        yield INSTRUMENT_EDITOR
        await self.press(Key.ESCAPE)
        yield Section.INSTRUMENTS
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.ARRANGE)
        yield ARRANGE
        # The instrument added above turned Real Time on, so the corner over the scene names is there, and Up from the first scene's name reaches it.
        await self.press(Key.UP)
        yield ARRANGE_CORNER
        await self.press(Key.RIGHT)
        yield ARRANGE_TRACK
        await self.press(Key.RIGHT, Key.RIGHT)
        yield ARRANGE_TRACK_PLUS
        await self.press(Key.ENTER, Key.LEFT, Key.LEFT, Key.ENTER)
        yield TRACK_EDITOR
        await self.press(Key.ESCAPE, Key.DOWN, Key.RIGHT)
        yield ARRANGE_CELL
        await self.press(Key.ENTER)
        yield CLIP
        await self.press(Key.ESCAPE, Key.LEFT, Key.ENTER)
        yield SCENE


class TestEveryKeyIsShownOnTheSetPagesOnAUsualConsole(TestEveryKeyIsShownOnTheSetPages):
    SIZE = (80, 24)


class TestEveryKeyIsShownOnTheSongPagesOnAUsualConsole(TestEveryKeyIsShownOnTheSongPages):
    SIZE = (80, 24)

    async def test_a_long_line_cannot_push_the_keys_off_the_screen(self):
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=DRUMS)
        self.document.set_clip_slot_setting(index=0, track=LEAD, setting=ClipSlotSetting.DIRECTION, value=Direction.EITHERWAY)
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.LOOP, value=None)
        self.document.set_clip_slot_setting(index=0, track=DRUMS, setting=ClipSlotSetting.PATTERN, value=OTHER)
        await self.press(keybindings.MainPage.ARRANGE, Key.RIGHT, Key.ENTER)
        self.assertIn('« Esc »', self.text())
        self.assertEqual(self.text().count('\n'), 23)


class TestFilePage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.FILE)

    async def test_save_and_open_buttons_come_after_a_blank_line_and_do_what_their_keys_do(self):
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels[-2:], [PageName.SAVE, PageName.OPEN])
        self.assert_buttons_come_last_after_a_blank_line()
        await self.select_field(PageName.SAVE)
        self.assertIn(key_name(keybindings.Page.SAVE), self.text())
        self.assertIn(key_name(keybindings.Page.OPEN_SET), self.text())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ESCAPE)
        await self.select_field(PageName.OPEN)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OpenPage)

    async def test_the_loose_settings_come_alphabetically_and_title_and_author_start_blank(self):
        # The user's order: the loose settings alphabetically, then the Notes & Octaves and Visualizers sections.
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels[:6], [AUTHOR, MSG_DEFAULT_FOLLOW_ACTION_LABEL, MSG_DESCRIPTION_LABEL, MSG_NOTES_LABEL, MSG_PROTECTED_LABEL, TITLE])
        self.assertEqual(self.document.setlist().get_title(), NO_TEXT)
        await self.select_field(TITLE)
        await self.press(Key.ENTER)
        await self.type('Rain on the Bridge')
        await self.press(Key.ENTER)
        await self.select_field(AUTHOR)
        await self.press(Key.ENTER)
        await self.type('Someone')
        await self.press(Key.ENTER)
        setlist = self.document.setlist()
        self.assertEqual((setlist.get_title(), setlist.get_author()), (RAIN_ON_THE_BRIDGE, SOMEONE))
        self.document.save(path='song.yml')
        with open('song.yml') as file:
            self.assertTrue(file.read().startswith(f'version: {VERSION}\ntitle: Rain on the Bridge\nauthor: Someone\n'))
        self.assertEqual(Document.load('song.yml').setlist().get_title(), RAIN_ON_THE_BRIDGE)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.document.setlist().get_author(), NO_TEXT)

    async def test_step_size_offers_only_the_allowed_values(self):
        await self.select_field(STEP_SIZE)
        await self.press(key_of(binding=keybindings.FilePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.setlist().get_step_size(), Fraction(1, 8))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, STEP_SIZE_CHOICES)

    async def test_the_notes_say_where_the_file_and_the_exports_are(self):
        text = self.text()
        self.assertIn('not saved yet', text)
        self.assertIn(MSG_EXPORTS_AFTER_SAVING, text)
        self.assertIn(MSG_NOT_SET, text)
        self.document.save(path=SET_FILE)
        await self.press(Key.ESCAPE, keybindings.MainPage.FILE)
        self.assertIn(EXPORT, self.text())

    async def test_the_prompt_cursor_moves_with_the_arrows_and_types_and_erases_where_it_is(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type(FOO_YML)
        # Back over .yml, type the 2, erase the o before it and type it again: foo.yml becomes foo2.yml.
        await self.press(*([Key.LEFT] * len(YML_SUFFIX)))
        await self.type('2')
        await self.press(Key.BACKSPACE, Key.BACKSPACE)
        self.assertEqual(self.app.screen.value, 'fo.yml')
        await self.type('o2')
        self.assertEqual(self.app.screen.value, FOO2_YML)
        # Moving past either end stops there, and erasing at the start erases nothing.
        await self.press(*([Key.RIGHT] * (len(FOO2_YML) + 1)))
        self.assertEqual(self.app.screen.cursor(), len(FOO2_YML))
        await self.press(*([Key.LEFT] * (len(FOO2_YML) + 1)))
        self.assertEqual(self.app.screen.cursor(), 0)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.app.screen.value, FOO2_YML)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.get_path(), FOO2_YML)

    async def test_save_as_then_save(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type('tune')
        await self.press(Key.ENTER)
        self.assertTrue(os.path.exists('tune.yml'))
        self.assertEqual(self.document.get_path(), 'tune.yml')
        self.assertFalse(self.document.is_dirty())
        await self.select_field(STEP_SIZE)
        await self.press(key_of(binding=keybindings.FilePage.MORE, key=Key.RIGHT_BRACKET))
        self.assertTrue(self.document.is_dirty())
        with open('tune.yml') as file:
            before = file.read()
        await self.press(Key.CTRL_S)
        with open('tune.yml') as file:
            self.assertNotEqual(file.read(), before)
        self.assertFalse(self.document.is_dirty())

    async def test_a_protected_set_offers_a_copy_and_the_file_page_turns_protection_off(self):
        self.assertFalse(self.document.setlist().is_protected())
        await self.select_field(MSG_PROTECTED_LABEL)
        self.assertIn(KEY_SHOWN.format(label=KeyName.SPACE_ENTER), self.text())
        await self.press(Key.ENTER)
        self.assertTrue(self.document.setlist().is_protected())
        # Space toggles too, like Enter.
        await self.press(Key.SPACE)
        self.assertFalse(self.document.setlist().is_protected())
        await self.press(Key.SPACE)
        self.assertTrue(self.document.setlist().is_protected())
        self.document.save(path='demo.yml')
        self.document.set_tempo(OTHER_TEMPO)
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(MSG_PROTECTED_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = 'copy.yml'
        await self.press(Key.ENTER)
        self.assertNotEqual(Document.load('demo.yml').song().get_tempo(), OTHER_TEMPO)
        self.assertEqual(Document.load('copy.yml').song().get_tempo(), OTHER_TEMPO)
        self.assertFalse(Document.load('copy.yml').setlist().is_protected())
        self.assertEqual(self.document.get_path(), 'copy.yml')
        self.assertFalse(self.document.is_dirty())
        # Saying no leaves everything as it was. Protecting a set is kept by saving it to a new file.
        self.document.set_protected(True)
        self.document.save(path='second.yml')
        self.document.set_tempo(OTHER_TEMPO + 1)
        await self.press(Key.CTRL_S, keybindings.ConfirmDialog.NO)
        self.assertTrue(self.document.is_dirty())
        self.assertEqual(Document.load('second.yml').song().get_tempo(), OTHER_TEMPO)
        # Turning protection off on the File page lets Ctrl+S write the file again.
        await self.select_field(MSG_PROTECTED_LABEL)
        await self.press(Key.ENTER, Key.CTRL_S)
        self.assertFalse(self.document.is_dirty())
        self.assertEqual(Document.load('second.yml').song().get_tempo(), OTHER_TEMPO + 1)

    async def test_saving_a_protected_set_under_its_own_name_is_refused_in_a_dialog(self):
        self.document.set_protected(True)
        self.document.save(path='demo.yml')
        # Unchanged, a protected set still gets the dialog rather than the status line.
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(MSG_PROTECTED_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        before = os.stat('demo.yml').st_mtime_ns
        await self.press(keybindings.FilePage.SAVE_AS)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertEqual(self.app.screen.value, 'demo.yml')
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(MSG_PROTECTED_TITLE, self.text())
        await self.press(Key.ENTER)
        self.assertEqual(os.stat('demo.yml').st_mtime_ns, before)
        self.assertEqual(self.document.get_path(), 'demo.yml')

    async def test_saving_an_unchanged_set_writes_nothing_and_says_so(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'tune.yml'
        await self.press(Key.ENTER)
        before = os.stat('tune.yml').st_mtime_ns
        self.document.changed()
        await self.press(Key.CTRL_S)
        self.assertEqual(os.stat('tune.yml').st_mtime_ns, before)
        self.assertIn(MSG_FILE_UNCHANGED.format(path='tune.yml'), self.text())
        self.assertFalse(self.document.is_dirty())

    async def test_saving_over_a_file_changed_elsewhere_asks_first(self):
        await self.press(keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'tune.yml'
        await self.press(Key.ENTER)
        other = Document.load('tune.yml')
        other.set_tempo(OTHER_TEMPO)
        other.save()
        await self.select_field(STEP_SIZE)
        await self.press(keybindings.FilePage.MORE)
        self.assertTrue(self.document.is_dirty())
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(MSG_FILE_CHANGED_ELSEWHERE_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(Document.load('tune.yml').song().get_tempo(), OTHER_TEMPO)
        await self.press(Key.CTRL_S, keybindings.ConfirmDialog.YES)
        self.assertNotEqual(Document.load('tune.yml').song().get_tempo(), OTHER_TEMPO)
        self.assertFalse(self.document.is_dirty())

    async def test_save_works_from_any_page(self):
        await self.press(Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER, Key.CTRL_S)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type('tune')
        await self.press(Key.ENTER)
        self.assertTrue(os.path.exists('tune.yml'))
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_save_as_asks_before_replacing_another_file(self):
        with open('taken.yml', WRITE_TEXT) as file:
            file.write(KEEP)
        await self.press(keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'taken.yml'
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        with open('taken.yml') as file:
            self.assertEqual(file.read(), KEEP)

    async def test_new_asks_if_there_are_unsaved_changes(self):
        self.document.changed()
        await self.press(keybindings.FilePage.NEW)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.app.get_document().song().get_pattern_names(), [MSG_NEW_PATTERN_NAME.format(number=FIRST_NUMBER)])
        self.assertEqual(self.app.get_document().song().get_scale_name(), DEFAULT_SCALE)
        self.assertEqual(self.app.get_document().song_names(), [MSG_DEFAULT_SONG_NAME])


class TestSongPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        # Enter on the Songs page opens the current song's settings, starting on Name.
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)

    async def test_it_holds_the_song_settings_and_names_the_song(self):
        self.assertIsInstance(self.app.screen, SongPage)
        labels = [field.label for field in self.app.screen.fields()]
        self.assertEqual(labels, [MSG_NAME_LABEL, TEMPO, MSG_TIME_SIGNATURE_LABEL, MSG_ENTRY_SIZE_LABEL, MSG_SCALE_LABEL, MSG_SEED_LABEL, MSG_GROOVE_LABEL, MSG_GENRE_LABEL, MSG_LIVE_RESPONSIVENESS_LABEL, MSG_PREVIEW_INSTRUMENT_LABEL, MSG_VISUALIZER_LABEL, PageName.EXPORT])
        self.assertIn(MSG_DEFAULT_SONG_NAME, self.text())
        self.assert_buttons_come_last_after_a_blank_line()

    async def test_the_preview_instrument_is_one_of_the_sets_and_follows_a_rename_and_bksp_clears_it(self):
        song = self.document.song()
        self.assertIsNone(song.get_preview_instrument_name())
        self.assertIn(MSG_PREVIEW_INSTRUMENT_UNSET, self.text())
        self.document.add_instrument(ORGAN_INSTRUMENT)
        self.document.add_instrument(KEYS_INSTRUMENT)
        await self.select_field(MSG_PREVIEW_INSTRUMENT_LABEL)
        # ] steps through the instruments by name and stops at the last, and [ goes back to none and stops there.
        await self.press(keybindings.SongPage.MORE)
        self.assertEqual(song.get_preview_instrument_name(), KEYS_INSTRUMENT)
        await self.press(keybindings.SongPage.MORE, keybindings.SongPage.MORE)
        self.assertEqual(song.get_preview_instrument_name(), ORGAN_INSTRUMENT)
        await self.press(*[keybindings.SongPage.LESS] * 3)
        self.assertIsNone(song.get_preview_instrument_name())
        # Enter picks from the list, where the pattern's own track comes first.
        await self.press(Key.ENTER)
        self.assertIn(MSG_PREVIEW_INSTRUMENT_UNSET, str(self.app.screen.query_one(DIALOG_VIEW_SELECTOR).render()))
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(song.get_preview_instrument_name(), KEYS_INSTRUMENT)
        # The song is a use of the instrument, and a rename is followed.
        self.assertTrue(self.document.uses(section=Section.INSTRUMENTS, name=KEYS_INSTRUMENT))
        self.document.rename_named(section=Section.INSTRUMENTS, old=KEYS_INSTRUMENT, new=RENAMED_INSTRUMENT)
        self.assertEqual(song.get_preview_instrument_name(), RENAMED_INSTRUMENT)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(song.get_preview_instrument_name())

    async def test_the_genre_is_typed_and_bksp_clears_it(self):
        await self.select_field(MSG_GENRE_LABEL)
        await self.press(Key.ENTER)
        await self.type(A_GENRE)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_genre(), A_GENRE)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertEqual(self.document.song().get_genre(), NO_GENRE)

    async def test_live_response_steps_through_its_three_choices_from_next_bar(self):
        await self.select_field(MSG_LIVE_RESPONSIVENESS_LABEL)
        self.assertEqual(self.document.song().get_live_responsiveness(), LiveResponsiveness.NEXT_BAR)
        self.assertIn(MSG_LIVE_RESPONSIVENESS_NAMES[LiveResponsiveness.NEXT_BAR], self.text())
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.document.song().get_live_responsiveness(), LiveResponsiveness.CLIP_RESTART)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.document.song().get_live_responsiveness(), LiveResponsiveness.ASAP)
        self.assertEqual(self.document.song().to_data()[SongSetting.LIVE_RESPONSIVENESS], LiveResponsiveness.ASAP)

    async def test_enter_on_the_name_renames_the_song_and_the_crumb_follows(self):
        await self.press(Key.ENTER)
        self.app.screen.value = SECOND_SONG
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [SECOND_SONG])
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)
        self.assertEqual(self.app.screen.crumbs, (Crumb.SONGS, SECOND_SONG))
        self.assertTrue(self.document.is_dirty())

    async def test_a_name_another_song_has_is_refused(self):
        self.document.add_song(SECOND_SONG)
        self.document.select_song(MSG_DEFAULT_SONG_NAME)
        await self.press(Key.ENTER)
        self.app.screen.value = SECOND_SONG
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, SECOND_SONG])
        self.assertIn(ERR_NAME_IN_USE.format(name=SECOND_SONG), self.text())

    async def test_the_export_row_asks_which_kind_like_control_x(self):
        self.document.save(path=SET_FILE)
        await self.select_field(PageName.EXPORT)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, MSG_EXPORT_CHOICES)
        self.assertIn(MSG_DEFAULT_SONG_NAME, self.text())

    async def test_the_time_signature_steps_through_common_ones_and_enter_types_any(self):
        await self.select_field(MSG_TIME_SIGNATURE_LABEL)
        self.assertEqual(self.document.song().get_time_signature().to_text(), DEFAULT_TIME_SIGNATURE)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.song().get_time_signature().to_text(), TIME_SIGNATURE_CHOICES[TIME_SIGNATURE_CHOICES.index(DEFAULT_TIME_SIGNATURE) + 1])
        await self.press(Key.LEFT, Key.LEFT)
        self.assertEqual(self.document.song().get_time_signature().to_text(), TIME_SIGNATURE_CHOICES[TIME_SIGNATURE_CHOICES.index(DEFAULT_TIME_SIGNATURE) - 1])
        await self.press(Key.ENTER)
        self.app.screen.value = SEVEN_EIGHT
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_time_signature().to_text(), SEVEN_EIGHT)
        self.assertIn(SEVEN_EIGHT, self.text())
        self.assertTrue(self.document.is_dirty())

    async def test_the_entry_size_steps_through_the_step_sizes_and_backspace_means_one_step(self):
        await self.select_field(MSG_ENTRY_SIZE_LABEL)
        self.assertIsNone(self.document.song().get_entry_size())
        self.assertIn(MSG_ONE_STEP_SHOWN, self.text())
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.song().get_written_entry_size(), STEP_SIZE_CHOICES[0])
        await self.press(Key.LEFT)
        self.assertIsNone(self.document.song().get_written_entry_size())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [MSG_ONE_STEP_SHOWN, *STEP_SIZE_CHOICES])
        await self.press(Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.song().get_written_entry_size(), STEP_SIZE_CHOICES[2])
        self.assertIn(STEP_SIZE_CHOICES[2], self.text())
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_written_entry_size())
        self.assertTrue(self.document.is_dirty())

    async def test_a_time_signature_that_is_not_one_is_refused(self):
        await self.select_field(MSG_TIME_SIGNATURE_LABEL)
        await self.press(Key.ENTER)
        self.app.screen.value = NOT_A_SIGNATURE
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_time_signature().to_text(), DEFAULT_TIME_SIGNATURE)
        self.assertIn(ERR_TYPED_NOT_A_TIME_SIGNATURE.format(text=NOT_A_SIGNATURE, lowest=MIN_BEATS, highest=MAX_BEATS, units=UNITS_LISTED), self.text())

    async def test_plus_and_minus_change_the_tempo(self):
        await self.select_field(TEMPO)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.PLUS), key_of(binding=keybindings.SongPage.MORE, key=Key.PLUS), key_of(binding=keybindings.SongPage.LESS, key=Key.MINUS))
        self.assertEqual(self.document.song().get_tempo(), 121)
        self.assertTrue(self.document.is_dirty())

    async def test_the_brackets_change_the_tempo_and_the_legend_names_the_arrows_alone(self):
        """A setting's legend says the arrows, with [ and ] and the older + and - working beside them, the user's choice of 2026-11-09."""
        await self.select_field(TEMPO)
        before = self.document.song().get_tempo()
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET), key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET), key_of(binding=keybindings.SongPage.LESS, key=Key.LEFT_BRACKET))
        self.assertEqual(self.document.song().get_tempo(), before + 1)
        await self.press(Key.RIGHT, Key.LEFT, Key.LEFT)
        self.assertEqual(self.document.song().get_tempo(), before)
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.FieldPage.MORE)) + MSG_LEGEND_WHAT.format(what=What.MORE), self.text())
        self.assertIn(KEY_SHOWN.format(label=key_name(keybindings.FieldPage.LESS)) + MSG_LEGEND_WHAT.format(what=What.LESS), self.text())
        # The legend names [ dec and ] inc, as everywhere a value steps, and Left and Right do the same off the legend.
        self.assertEqual((KeyName.RIGHT_BRACKET, KeyName.LEFT_BRACKET), (key_name(keybindings.FieldPage.MORE), key_name(keybindings.FieldPage.LESS)))

    async def test_typing_a_tempo(self):
        await self.select_field(TEMPO)
        await self.press(Key.ENTER, Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        await self.type('90')
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_tempo(), 90)

    async def test_nonsense_is_refused(self):
        await self.select_field(TEMPO)
        await self.press(Key.ENTER, Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        await self.type('xx')
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_tempo(), 120)
        self.assertIn(NOT_AN_INTEGER, self.text())

    async def test_seed_starts_as_none_and_counts_from_zero_when_set(self):
        self.assertIsNone(self.document.song().get_seed())
        await self.select_field(MSG_SEED_LABEL)
        await self.press(key_of(binding=keybindings.SongPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.document.song().get_seed(), 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_seed())

    async def test_scale_can_be_none(self):
        await self.select_field(MSG_SCALE_LABEL)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.document.song().get_scale_name())


class TestSongsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.SONGS)

    def names(self):
        return [row[0] for row in self.app.screen.rows()]

    async def test_lists_the_songs_with_the_current_one_marked(self):
        self.assertIsInstance(self.app.screen, SongsPage)
        self.assertEqual(self.names(), [MSG_DEFAULT_SONG_NAME])
        self.assertIn('●', self.text())

    async def test_adding_a_song_makes_it_current_and_the_header_says_so(self):
        await self.press(keybindings.SongsPage.ADD)
        await self.type(SECOND_SONG)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, SECOND_SONG])
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)
        self.assertEqual(self.document.song().get_track_names(), [FIRST_TRACK])
        await self.press(Key.ESCAPE, keybindings.MainPage.PATTERNS)
        self.assertIn(MSG_SONG_CRUMB.format(song=SECOND_SONG), self.song_line())

    async def test_space_makes_a_song_current_and_enter_opens_its_settings(self):
        self.document.add_song(SECOND_SONG)
        self.document.select_song(MSG_DEFAULT_SONG_NAME)
        await self.press(Key.DOWN, Key.SPACE)
        self.assertEqual(self.document.current_song_name(), SECOND_SONG)
        await self.press(Key.UP, Key.ENTER)
        self.assertIsInstance(self.app.screen, SongPage)
        self.assertEqual(self.document.current_song_name(), MSG_DEFAULT_SONG_NAME)

    async def test_copying_and_renaming(self):
        await self.press(keybindings.SongsPage.COPY)
        self.assertEqual(len(self.document.song_names()), 2)
        copy = self.document.song_names()[1]
        self.assertEqual(self.document.setlist().get_song(copy).get_track_names(), [LEAD, DRUMS])
        await self.press(keybindings.SongsPage.RENAME)
        self.app.screen.value = SECOND_SONG
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME, SECOND_SONG])

    async def test_the_last_song_cannot_be_deleted(self):
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME])
        self.assertIn('at least one song', self.text())

    async def test_deleting_the_current_song_moves_to_another(self):
        self.document.add_song(SECOND_SONG)
        await self.press(Key.DOWN, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertEqual(self.document.song_names(), [MSG_DEFAULT_SONG_NAME])
        self.assertEqual(self.document.current_song_name(), MSG_DEFAULT_SONG_NAME)

    async def test_songs_share_the_patterns_and_have_their_own_tracks(self):
        self.document.add_song(SECOND_SONG)
        self.assertEqual(self.document.song().get_pattern_names(), [TUNE, BEAT, OTHER])
        self.assertEqual(self.document.song().get_track_names(), [FIRST_TRACK])
        self.document.select_song(MSG_DEFAULT_SONG_NAME)
        self.assertEqual(self.document.song().get_track_names(), [LEAD, DRUMS])


class TestExporting(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.save(path=SET_FILE)

    async def export(self, choice):
        """Press X, pick a kind of export, and check the status line says where it went."""
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, MSG_EXPORT_CHOICES)
        await self.press(*([Key.DOWN] * choice), Key.ENTER)
        self.assertNotIsInstance(self.app.screen, MessageDialog)
        self.assertIn(fixed_text(MSG_EXPORTED), self.text())

    async def test_the_live_set_is_first_and_says_where_it_went_on_the_status_line(self):
        await self.press(Key.CTRL_X, Key.ENTER)
        self.assertNotIsInstance(self.app.screen, MessageDialog)
        self.assertIn(MSG_EXPORTED.format(name=EXPORT_LABELS[ExportKind.ABLETON], path=LIVE_SET), self.text())
        self.assertTrue(os.path.exists(LIVE_SET))

    async def test_an_unsaved_set_is_saved_first_and_then_exported(self):
        self.app.set_document(Document())
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(MSG_SAVE_BEFORE_EXPORT_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = ''
        await self.type(OTHER_SET_FILE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, MSG_EXPORT_CHOICES)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertIn(OTHER_LIVE_SET, self.text())
        self.assertTrue(os.path.exists(OTHER_LIVE_SET))

    async def test_declining_to_save_exports_nothing(self):
        self.app.set_document(Document())
        await self.press(Key.CTRL_X, keybindings.ConfirmDialog.NO)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertEqual(os.listdir(self.folder), [SET_FILE])

    async def test_writing_over_a_live_set_asks_only_the_first_time(self):
        await self.export(EXPORT_LIVE)
        await self.press(Key.CTRL_X, Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(OVERWRITE, self.text().lower())
        self.assertIn(LIVE_SET, self.text())
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertIn(fixed_text(MSG_EXPORTED), self.text())
        await self.export(EXPORT_LIVE)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_midi_exports_never_ask(self):
        await self.export(EXPORT_MIDI_FILE)
        await self.export(EXPORT_MIDI_FILE)
        self.assertTrue(os.path.exists(shown_export_path(kind=ExportKind.MIDI_FILE, directory=self.folder, name=EXPORT)))

    async def test_stems_and_clips_too(self):
        await self.export(EXPORT_STEMS)
        self.assertTrue(earlier_export(kind=ExportKind.STEMS, directory=self.folder, name=EXPORT))
        await self.export(EXPORT_CLIPS)
        self.assertTrue(earlier_export(kind=ExportKind.CLIP_TREE, directory=self.folder, name=EXPORT))
        self.assertEqual(earlier_export(kind=ExportKind.MIDI_FILE, directory=self.folder, name=EXPORT), [])

    async def test_x_can_be_cancelled_and_works_from_any_page(self):
        await self.press(Key.CTRL_X, Key.ESCAPE)
        self.assertEqual(os.listdir(self.folder), [SET_FILE])
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_exports_the_current_song_under_its_own_name(self):
        self.document.add_song(SECOND_SONG)
        self.document.add_track(LEAD)
        self.document.add_scene(index=0, name=VERSE)
        self.document.add_clip_slot(index=0, track=LEAD, pattern=TUNE)
        await self.export(EXPORT_LIVE)
        self.assertTrue(os.path.exists(f'my_set_{SECOND_SONG}.als'))
        self.assertFalse(os.path.exists(LIVE_SET))

    async def test_changes_do_not_export_or_save_by_themselves(self):
        tempo = self.document.song().get_tempo()
        with open(SET_FILE) as file:
            saved = file.read()
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(TEMPO)
        await self.press(keybindings.SongPage.MORE, keybindings.SongPage.MORE)
        self.assertGreater(self.document.song().get_tempo(), tempo)
        self.assertTrue(self.document.is_dirty())
        self.assertEqual(os.listdir(self.folder), [SET_FILE])
        with open(SET_FILE) as file:
            self.assertEqual(file.read(), saved)

    def loop_every_clip_in_scene(self, *, index, name):
        """Name a scene and set its one clip to loop, so that the scene would never end."""
        self.document.set_scene_name(index=index, name=name)
        self.document.set_clip_slot_setting(index=index, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)

    def dialog_words(self):
        """Return the dialog's own text as one line of words, since the page behind it shows through beside it."""
        return ' '.join(str(self.app.screen.query_one('#dialog-view').render()).replace('┃', ' ').split())

    async def test_every_clip_looping_is_a_popup_at_export_that_names_the_scenes(self):
        self.loop_every_clip_in_scene(index=0, name=VERSE)
        self.document.add_scene(index=1, name=CHORUS)
        self.document.add_clip_slot(index=1, track=LEAD, pattern=TUNE)
        self.loop_every_clip_in_scene(index=1, name=CHORUS)
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, MessageDialog)
        words = self.dialog_words()
        self.assertIn(ERR_LOOP_SCENES_TITLE, words)
        self.assertIn(ERR_LOOP_SCENES_INTRO, words)
        self.assertIn(VERSE, words)
        self.assertIn(CHORUS, words)
        self.assertNotIn(ERR_AND_MORE.format(count=1), words)
        await self.press(Key.ENTER)
        self.assertFalse(os.path.exists(LIVE_SET))

    async def test_the_loop_errors_dialog_lists_ten_scenes_and_counts_the_rest(self):
        for index in range(ONE_MORE_THAN_SHOWN):
            if index:
                self.document.add_scene(index=index, name=MSG_NUMBERED_NAME.format(base=VERSE, number=index))
                self.document.add_clip_slot(index=index, track=LEAD, pattern=TUNE)
            self.loop_every_clip_in_scene(index=index, name=MSG_NUMBERED_NAME.format(base=VERSE, number=index))
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, MessageDialog)
        words = self.dialog_words()
        self.assertIn(MSG_NUMBERED_NAME.format(base=VERSE, number=LOOP_ERRORS_SHOWN - 1), words)
        self.assertNotIn(MSG_NUMBERED_NAME.format(base=VERSE, number=LOOP_ERRORS_SHOWN), words)
        self.assertIn(ERR_AND_MORE.format(count=1), words)


class TestFilePageEdges(UITest):

    async def test_saving_a_new_set_asks_for_a_name_and_an_empty_one_does_nothing(self):
        await self.press(Key.CTRL_S)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = '  '
        await self.press(Key.ENTER)
        self.assertIsNone(self.document.get_path())

    async def test_quitting_can_save_first_and_asks_where(self):
        self.document.changed()
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(keybindings.MainPage.QUIT, keybindings.QuitDialog.SAVE)
            self.assertIsInstance(self.app.screen, PromptDialog)
            self.app.screen.value = 'tune.yml'
            await self.press(Key.ENTER)
            self.assertTrue(os.path.exists('tune.yml'))
            leave.assert_called_once()

    async def test_a_save_that_fails_is_explained(self):
        os.mkdir('taken.yml')
        await self.press(keybindings.MainPage.FILE, keybindings.FilePage.SAVE_AS)
        self.app.screen.value = 'taken.yml'
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(ERR_CANT_SAVE_TITLE, self.text())

    async def test_new_and_load_ask_first_with_unsaved_changes(self):
        self.document.changed()
        await self.press(keybindings.MainPage.FILE, keybindings.FilePage.NEW)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(Key.ESCAPE, Key.CTRL_O)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertIsInstance(self.app.screen, OpenPage)

    async def test_choosing_a_scale_needs_one_first(self):
        self.document.set_scale_name(None)
        for name in self.document.song().get_scale_names():
            self.document.delete_named(section=Section.SCALES, name=name)
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_SCALE_LABEL)
        await self.press(Key.ENTER)
        self.assertIn(ERR_ADD_A_SCALE_FIRST, self.text())


class TestNotesPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_NOTES_LABEL)
        await self.press(Key.ENTER)

    async def save(self):
        """Press Save under the text: Tab reaches the buttons, Save is the first, and Enter presses it."""
        await self.press(Key.TAB)
        self.assertTrue(self.app.screen.on_buttons)
        await self.press(Key.ENTER)
        self.assertFalse(self.app.screen.editing)

    async def test_enter_on_the_notes_field_opens_it_editing_and_esc_twice_comes_back(self):
        self.assertIsInstance(self.app.screen, NotesPage)
        self.assertTrue(self.app.screen.editing)
        await self.press(Key.ESCAPE)
        self.assertFalse(self.app.screen.editing)
        self.assertIn(NO_NOTES_YET, self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertIn(MSG_NOT_SET, self.text())

    async def test_esc_and_the_cancel_button_throw_the_typing_away_and_save_keeps_it(self):
        await self.type(ONE)
        await self.press(Key.ESCAPE)
        self.assertFalse(self.app.screen.editing)
        self.assertFalse(self.document.setlist().has_notes())
        await self.press(keybindings.NotesPage.EDIT)
        await self.type(ONE)
        # Tab reaches the buttons, Right moves to Cancel, and Tab again goes back to the text, where letters type again.
        await self.press(Key.TAB)
        self.assertIn(SELECTED_MARK + KEY_SHOWN.format(label=MSG_NOTES_BUTTONS[0]), self.text())
        await self.press(Key.RIGHT)
        self.assertIn(SELECTED_MARK + KEY_SHOWN.format(label=MSG_NOTES_BUTTONS[1]), self.text())
        await self.press(Key.TAB)
        self.assertFalse(self.app.screen.on_buttons)
        await self.type(ONE)
        # The buttons remember that Cancel was chosen, so Tab and Enter press it.
        await self.press(Key.TAB)
        self.assertIn(SELECTED_MARK + KEY_SHOWN.format(label=MSG_NOTES_BUTTONS[1]), self.text())
        await self.press(Key.ENTER)
        self.assertFalse(self.app.screen.editing)
        self.assertFalse(self.document.setlist().has_notes())
        await self.press(keybindings.NotesPage.EDIT)
        await self.type(ONE)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), ONE)

    async def test_a_protected_sets_notes_can_only_be_read(self):
        await self.press(Key.ESCAPE, Key.ESCAPE)
        self.document.set_protected(True)
        self.document.set_notes(ONE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, NotesPage)
        self.assertFalse(self.app.screen.editing)
        self.assertNotIn(first_key(keybindings.NotesPage.EDIT), [name for item in self.app.screen.keys() for name in item.keys])
        await self.press(keybindings.NotesPage.EDIT, Key.BACKSPACE)
        self.assertFalse(self.app.screen.editing)
        self.assertEqual(self.document.setlist().get_notes(), ONE)
        self.assertIsInstance(self.app.screen, NotesPage)

    async def test_typing_new_lines_and_erasing(self):
        # What's typed reaches the set when Save is pressed, not letter by letter, so that undo takes it back as one edit.
        await self.type('Hi there')
        await self.press(Key.ENTER)
        await self.type('ok')
        self.assertFalse(self.document.setlist().has_notes())
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), 'Hi there\nok\n')
        await self.press(keybindings.NotesPage.EDIT, Key.BACKSPACE, Key.BACKSPACE, Key.BACKSPACE)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), HI_THERE)
        # Six steps left from the end of 'Hi there' is just after 'Hi'.
        await self.press(keybindings.NotesPage.EDIT, *[Key.LEFT] * 6)
        await self.type('X')
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), HIX_THERE)
        self.assertFalse(self.app.screen.editing)
        self.assertIn(HIX_THERE_2, self.text())
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertIn(HIX_THERE_2, self.text())

    async def test_letters_are_text_while_editing_and_f1_helps_while_reading(self):
        await self.press(TYPED_LETTER)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), H_2)
        await self.press(Key.F1)
        self.assertIsInstance(self.app.screen, HelpDialog)

    async def test_erasing_at_the_start_of_a_line_joins_it_to_the_one_before(self):
        await self.press(Key.ESCAPE)
        self.document.set_notes('one\ntwo\n')
        await self.press(keybindings.NotesPage.EDIT, Key.UP, Key.DOWN)
        self.app.screen.column = 0
        await self.press(Key.BACKSPACE)
        await self.save()
        self.assertEqual(self.document.setlist().get_notes(), ONETWO)

    async def test_clearing_asks_first_while_reading(self):
        await self.press(Key.ESCAPE)
        self.document.set_notes(ONE)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.YES)
        self.assertFalse(self.document.setlist().has_notes())

    async def test_long_notes_scroll(self):
        await self.press(Key.ESCAPE)
        self.document.set_notes(''.join(f'line {n}\n' for n in range(100)))
        await self.press(Key.DOWN, Key.DOWN)
        self.assertNotIn(LINE_0, self.text().replace(' ', ''))
        self.assertIn(LINE_2, self.text())


class TestQuitNow(UITest):
    """Ctrl+C quits at once from any page or dialog, the user's ask, through the app's exit, which closes FluidSynth and the MIDI sender."""

    async def quitting_after(self, *keys):
        with mock.patch.object(self.app, 'exit') as exited:
            await self.press(*keys, keybindings.Page.QUIT_NOW)
        return exited

    async def test_ctrl_c_quits_from_a_page(self):
        exited = await self.quitting_after(keybindings.MainPage.PATTERNS)
        exited.assert_called_once()

    async def test_ctrl_c_quits_from_a_dialog(self):
        exited = await self.quitting_after(keybindings.Page.HELP)
        exited.assert_called_once()

    async def test_ctrl_c_quits_while_the_notes_are_being_edited(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_NOTES_LABEL)
        exited = await self.quitting_after(Key.ENTER)
        exited.assert_called_once()


class TestOpenPage(UITest):

    async def test_picks_a_file_and_opens_it(self):
        a_song().save(path='song one.yml')
        await self.press(keybindings.MainPage.FILE, Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.assertIn('song one.yml', rows)
        self.app.screen.place = rows.index('song one.yml')
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertEqual(self.app.get_document().get_path(), 'song one.yml')

    async def test_folders_show_with_a_slash_and_enter_goes_into_one_and_back_out(self):
        os.makedirs(os.path.join(FOLDER_OF_SETS, INNER_FOLDER))
        a_song().save(path=os.path.join(FOLDER_OF_SETS, INNER_FOLDER, 'deep song.yml'))
        await self.press(Key.CTRL_O)
        shown = self.text()
        self.assertIn(MSG_FOLDER_ROW.format(name=FOLDER_OF_SETS), shown)
        self.assertIn(MSG_PARENT_ROW, shown)
        for folder in (FOLDER_OF_SETS, INNER_FOLDER):
            rows = [row[0] for row in self.app.screen.rows()]
            self.app.screen.place = rows.index(folder)
            await self.press(Key.ENTER)
        self.assertIn('deep song.yml', [row[0] for row in self.app.screen.rows()])
        self.app.screen.place = [row[0] for row in self.app.screen.rows()].index(PARENT_FOLDER)
        await self.press(Key.ENTER)
        self.assertIn(INNER_FOLDER, [row[0] for row in self.app.screen.rows()])

    async def test_an_opened_set_starts_on_its_first_song(self):
        two_songs = a_song()
        two_songs.add_song(SECOND_SONG)
        two_songs.save(path='two songs.yml')
        await self.press(Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index('two songs.yml')
        await self.press(Key.ENTER)
        self.assertEqual(self.app.get_document().current_song_name(), MSG_DEFAULT_SONG_NAME)
        self.assertEqual(self.app.get_document().song().get_track_names(), [LEAD, DRUMS])
        self.assert_header(set_crumb=MSG_SET_CRUMB.format(file='two songs.yml'), song_crumb=MSG_SONG_CRUMB.format(song=MSG_DEFAULT_SONG_NAME))

    async def test_control_o_opens_from_any_page_and_comes_back_to_it(self):
        a_song().save(path='song one.yml')
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, Key.CTRL_O)
        self.assertIsInstance(self.app.screen, OpenPage)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index('song one.yml')
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.get_document().get_path(), 'song one.yml')

    async def test_enter_on_a_directory_goes_into_it_and_lists_its_files(self):
        os.makedirs(SUBFOLDER)
        a_song().save(path=os.path.join(SUBFOLDER, 'inside.yml'))
        await self.press(Key.CTRL_O)
        self.app.screen.folder = os.curdir
        rows = [row[0] for row in self.app.screen.rows_with_plus()]
        self.app.screen.place = rows.index(SUBFOLDER)
        await self.press(Key.ENTER)
        self.assertEqual([row[0] for row in self.app.screen.rows_with_plus()], [PARENT_FOLDER, 'inside.yml'])
        self.app.screen.place = 1
        await self.press(Key.ENTER)
        self.assertEqual(os.path.basename(self.app.get_document().get_path()), 'inside.yml')

    async def test_a_bad_file_is_a_popup_and_keeps_the_song(self):
        with open('bad.yml', WRITE_TEXT) as file:
            file.write('tempo: [')
        before = self.app.get_document()
        await self.press(keybindings.MainPage.FILE, Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index('bad.yml')
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIs(self.app.get_document(), before)


class TestPlusRow(UITest):
    """Every list has a + at the bottom, where Enter does the same as pressing +."""

    async def test_every_list_has_one(self):
        for keys, page in [
            ([keybindings.MainPage.PATTERNS], PatternsPage), ([keybindings.MainPage.CHAINS], ChainsPage), ([keybindings.MainPage.SCALES], ScalesPage), ([keybindings.MainPage.GROOVES], GroovesPage),
            ([keybindings.MainPage.INSTRUMENTS], InstrumentsPage),
        ]:
            await self.press(*keys)
            self.assertIsInstance(self.app.screen, page)
            self.assertEqual(self.app.screen.rows_with_plus()[-1][0], None, page)
            await self.press(Key.ESCAPE)

    async def test_down_past_the_last_row_goes_to_it_and_up_from_the_top_stays_there(self):
        names = self.document.song().get_pattern_names()
        await self.press(keybindings.MainPage.PATTERNS, Key.UP)
        self.assertEqual(self.app.screen.current(), names[0])
        await self.press(*[Key.DOWN] * len(names))
        self.assertIsNone(self.app.screen.current())
        # Down on the + row stays there too.
        await self.press(Key.DOWN)
        self.assertIsNone(self.app.screen.current())

    async def test_an_empty_list_starts_on_it(self):
        self.empty_the_arrangement()
        for name in self.document.song().get_pattern_names():
            self.document.delete_named(section=Section.PATTERNS, name=name)
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)

    async def test_backspace_and_copy_do_nothing_on_it(self):
        names = self.document.song().get_pattern_names()
        await self.press(keybindings.MainPage.PATTERNS, *[Key.DOWN] * len(names), Key.BACKSPACE, keybindings.PatternsPage.COPY, keybindings.PatternsPage.MOVE)
        self.assertEqual(self.document.song().get_pattern_names(), names)
        self.assertIsInstance(self.app.screen, PatternsPage)

    async def test_lists_that_cannot_add_have_none(self):
        await self.press(keybindings.MainPage.OPEN_SET_HERE)
        self.assertEqual(len(self.app.screen.rows_with_plus()), len(self.app.screen.remembered_rows()))

    async def test_arrange_has_one_for_scenes(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.DOWN, Key.DOWN)
        self.assertTrue(self.app.screen.on_plus_row())
        self.assertNotIn('« Bksp »', self.text())
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.song().get_scenes()), 3)
        self.assertEqual(self.app.screen.row, 2)
        self.assertEqual(self.document.song().get_scenes()[2].get_track_names(), [])

    async def test_arrange_with_no_scenes_starts_on_it(self):
        self.empty_the_arrangement()
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.assertEqual(len(self.document.song().get_scenes()), 1)


class TestSettingArrows(UITest):

    async def test_left_and_right_do_the_same_as_minus_and_plus(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(TEMPO)
        await self.press(Key.RIGHT, Key.RIGHT, Key.LEFT)
        self.assertEqual(self.document.song().get_tempo(), 121)

    async def test_on_every_song_setting_with_a_value_to_step(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(MSG_SCALE_LABEL)
        await self.press(Key.LEFT)
        self.assertIsNone(self.document.song().get_scale_name())
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_scale_name(), C_MAJOR)
        await self.press(Key.DOWN, Key.RIGHT)
        self.assertEqual(self.document.song().get_seed(), 1)

    async def test_on_every_set_setting_with_a_value_to_step(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(STEP_SIZE)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_step_size(), Fraction(1, 8))
        await self.select_field(MSG_DEFAULT_OCTAVE_LABEL)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.song().get_default_octave(), DEFAULT_OCTAVE - 1)
        await self.select_field(MSG_DEFAULT_DRUM_OCTAVE_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_default_drum_octave(), DEFAULT_DRUM_OCTAVE + 1)
        await self.select_field(MSG_OCTAVE_LABELS_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_octave_labels(), OctaveLabels.LLAMATRON)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.song().get_octave_labels(), OctaveLabels.LIVE)

    async def test_default_follow_action_is_chosen_from_a_list_and_written_only_when_set(self):
        # Real-time playback alone reads it (the user's design of 2026-11-09), and a set that never sets it writes nothing, so the demos stay as they are.
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_DEFAULT_FOLLOW_ACTION_LABEL)
        self.assertEqual(self.document.setlist().get_default_follow_action(), FollowAction.WITH_SCENE)
        self.assertNotIn(SetlistSetting.DEFAULT_FOLLOW_ACTION, self.document.setlist().to_data())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.setlist().get_default_follow_action(), FollowAction.NEXT)
        self.assertEqual(self.document.setlist().to_data()[SetlistSetting.DEFAULT_FOLLOW_ACTION], FollowAction.NEXT)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.setlist().get_default_follow_action(), FollowAction.OFF)

    async def test_octave_labels_are_chosen_from_a_list(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_OCTAVE_LABELS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.song().get_octave_labels(), OctaveLabels.LLAMATRON)


class TestLookAndNewKeys(UITest):

    async def test_the_title_is_plain_text_and_nothing_sits_between_the_rule_and_the_cells(self):
        # The user dropped the set-and-song line and the song summary on 2026-11-09: the crumbs say the first and the cells count the set's things.
        lines = self.text().splitlines()
        self.assertIn(SPACE + PROGRAM_NAME + SPACE, lines[0])
        self.assertNotIn(MSG_SITE, self.text())
        self.assertNotIn('█', self.text())
        self.assertNotIn(tempo_text(self.document.song().get_tempo()), self.text())
        first_cell = next(number for number, line in enumerate(lines) if '┌' in line)
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
        self.assertEqual(dialog.part, QUALITY_LIST)
        self.assertIsNone(dialog.choice().quality)
        dialog.places[QUALITY_LIST] = dialog.qualities.index(ChordSymbol.MINOR7)
        await self.press(Key.ENTER)
        self.assertEqual(self.value(Row.CHORD), ChordSymbol.MINOR7)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.choice().quality, ChordSymbol.MINOR7)
        self.assertIn(MINOR_SEVENTH.lower(), self.dialog_text())
        self.app.screen.places[QUALITY_LIST] = self.app.screen.qualities.index(ChordSymbol.SCALE_TRIAD)
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
        self.document.add_scale(name=CHROMATIC_SCALE, root=NoteName.C, kind=scale_type_name(ScaleType.CHROMATIC))
        self.document.set_scale_name(CHROMATIC_SCALE)
        self.document.changed()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR, '1', '2')
        self.assertEqual(self.value(Row.DEGREE), 12)


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
            self.assertIn(MSG_HELP_PANELS[1], text)
            self.assertIn('┏', text)
            self.assertIn('┗', text)
            self.assertIn(f'« {KeyName.ENTER_ESCAPE} »', text)
        await self.press(Key.ENTER)
        self.assertIs(self.app.screen, page, where)

    async def test_every_page_has_help_that_fits(self):
        await self.assert_help_fits(MAIN)
        for keys in [
            [keybindings.MainPage.FILE], [DESCRIPTION_KEY], [Key.ESCAPE, Key.CTRL_O], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS], [Key.ENTER], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS], [Key.ENTER],
            [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.ARRANGE, Key.UP, Key.ENTER],
            [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.CHAINS], [Key.ENTER], [Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GENERATORS], [Key.ENTER],
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
        self.assertIn(MSG_NOTE_UNDER_CURSOR, text)
        self.assertIn('Step 1:', text)
        self.assertIn('« Esc »', text)
        await self.press(keybindings.PatternEditor.TO_EDITOR)
        text = self.text()
        # The gauge, its number and the octave are pinned, and the first section's heading and at least one of its rows show under them.
        self.assertIn('│ Degree', text)
        self.assertIn('│ Octave', text)
        self.assertIn(Box.BAR + SPACE + MSG_SECTION_LABEL.format(mark=MSG_SECTION_OPEN_MARK, name=MSG_SECTION_NAMES[RowSection.BASICS]), text)
        self.assertIn('│ #/b', text)
        self.assertIn('Step 1:', text)
        self.assertIn('« Esc »', text)


class TestArrowsAndTheMark(UITest):
    """The cursor shows itself as a triangle on every page with rows, and the arrows and Enter get around without a letter."""

    def marked_line(self):
        """Return the one line of the page with the mark on it."""
        lines = [line for line in self.text().splitlines() if SELECTED_MARK in line]
        self.assertEqual(len(lines), 1, self.text())
        return lines[0]

    def marked_dialog_line(self):
        """Return the one line inside the open dialog with the mark on it; the page beneath can show its own."""
        lines = [line.split('┃')[1] for line in self.text().splitlines() if line.count('┃') >= 2 and SELECTED_MARK in line.split('┃')[1]]
        self.assertEqual(len(lines), 1, self.text())
        return lines[0]

    async def test_the_main_screen_boxes_every_cell_and_the_selected_one_double_in_place_of_the_mark(self):
        self.assertNotIn(SELECTED_MARK, self.text())
        self.assertIn(PageName.ARRANGE, boxed_line(self.text()))
        # Every cell has a box, and the selected one's is double-lined, the only such box; a cell's name starts one space after the key.
        self.assertEqual(self.text().count(Box.TOP_LEFT), len(self.app.screen.menu_items()) - 1)
        self.assertEqual(self.text().count(Box.DOUBLE_TOP_LEFT), 1)
        await self.press(Key.DOWN)
        self.assertIn(f'« {key_name(keybindings.MainPage.SONGS)} » {PageName.SONGS}', boxed_line(self.text()))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, SongsPage)
        await self.press(Key.ESCAPE)
        self.assertIn(PageName.SONGS, boxed_line(self.text()))

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
        await self.press(*[Key.DOWN] * len(self.app.screen.rows()), *[Key.RIGHT] * len(self.app.screen.rows()[-1]))
        self.assertIn(PageName.QUIT, boxed_line(self.text()))
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(Key.ENTER)
            leave.assert_called_once()


    async def test_a_list_page_marks_the_selected_row_without_reverse_video(self):
        await self.press(keybindings.MainPage.PATTERNS)
        self.assertIn(TUNE, self.marked_line())
        self.assertNotIn('«', self.marked_line())
        await self.press(Key.DOWN)
        self.assertIn(BEAT, self.marked_line())

    async def test_a_settings_page_marks_the_selected_field_and_reverses_only_a_selected_button(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(MSG_TITLE_LABEL)
        line = self.marked_line()
        self.assertIn(MSG_TITLE_LABEL, line)
        self.assertNotIn('«', line)
        # The buttons are a row of boxes, the selected one double-lined, as the dialogs' are.
        await self.select_field(PageName.SAVE)
        line = next(line for line in self.text().splitlines() if PageName.SAVE in line and key_name(keybindings.Page.SAVE) in line)
        self.assertLess(line.index(Box.DOUBLE_BAR), line.index(PageName.SAVE))
        await self.select_field(MSG_TITLE_LABEL)
        unselected = next(line for line in self.text().splitlines() if PageName.SAVE in line and key_name(keybindings.Page.SAVE) in line)
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
        # The buttons are boxed, the selected one double-lined, the user's design: its box's side comes just before its key.
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
        names = self.document.song().get_pattern_names()
        await self.press(keybindings.MainPage.PATTERNS, Key.UP)
        self.assertEqual(self.app.screen.current(), names[0])
        await self.press(*[Key.DOWN] * (len(names) + 1))
        self.assertIsNone(self.app.screen.current())
        await self.press(Key.ESCAPE, keybindings.MainPage.SONGS, Key.ENTER, Key.UP)
        self.assertEqual(self.app.screen.place, 0)
        last = len(self.app.screen.fields()) - 1
        await self.press(*[Key.DOWN] * (last + 1))
        self.assertEqual(self.app.screen.place, last)
        await self.select_field(MSG_SCALE_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.UP)
        self.assertEqual(self.app.screen.place, 0)
        count = len(self.app.screen.matches())
        await self.press(*[Key.DOWN] * count)
        self.assertEqual(self.app.screen.place, count - 1)
        await self.press(Key.ESCAPE, Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        editor = self.app.screen
        await self.press(Key.LEFT, Key.UP)
        self.assertEqual((editor.step, editor.rows_view.row), (0, 0))
        await self.press(*[Key.RIGHT] * editor.steps(), *[Key.DOWN] * len(editor.rows_view.reachable()))
        self.assertEqual((editor.step, editor.rows_view.row), (editor.steps() - 1, len(editor.rows_view.reachable()) - 1))
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.GROOVES, keybindings.GroovesPage.ADD, Key.LEFT)
        self.assertEqual(self.app.screen.step, 0)
        await self.press(*[Key.RIGHT] * len(self.app.screen.cells()))
        self.assertEqual(self.app.screen.step, len(self.app.screen.cells()) - 1)


class TestHelpDialog(UITest):
    SIZE = (80, 24)

    async def test_f1_lists_the_everywhere_keys_then_the_pages_own_in_two_columns_and_tab_turns_to_the_text(self):
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.HELP)
        dialog = self.app.screen
        self.assertIsInstance(dialog, HelpDialog)
        text = self.text()
        self.assertIn(MSG_HELP_PANELS[0], text)
        # The dialog's own lines are between its side bars; the page shows through either side of them.
        lines = [line.split('┃')[1] for line in text.splitlines() if line.count('┃') >= 2]
        lines = [line for line in lines if '»' in line]
        # Seven everywhere keys fill two columns downwards over four lines, F1 left out of its own dialog, Silence last in the first column so that Undo still sits above Redo in the second, as the user asked on 2026-11-09.
        self.assertIn('« Ctrl+S »', lines[0])
        self.assertIn('« Ctrl+Z »', lines[0])
        self.assertIn('« Ctrl+Y »', lines[1])
        self.assertIn('« F3 »', lines[2])
        self.assertIn('« Ctrl+T »', lines[3])
        self.assertNotIn('« F1 »', text)
        # The page's own keys start with Esc, the back key, and then the arrows.
        self.assertIn('« Esc »', lines[4])
        self.assertIn('« ↑↓ »', lines[5])
        self.assertIn(f'« {KeyName.TAB_ARROWS} »', text)
        self.assertNotIn(HELP_PATTERNS_FIRST_WORDS, text)
        await self.press(Key.TAB)
        self.assertIn(MSG_HELP_PANELS[1], self.text())
        self.assertIn(HELP_PATTERNS_FIRST_WORDS, self.text())
        await self.press(Key.RIGHT)
        self.assertIn(MSG_HELP_PANELS[0], self.text())
        await self.press(Key.LEFT)
        self.assertIn(MSG_HELP_PANELS[1], self.text())
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
            self.assertIn(MSG_COW_BUBBLE_TEXT.format(text=PROGRAM_NAME), text)
            self.assertIn(MSG_COW[-1].strip(), text)
            self.assertIn(MSG_ABOUT_VERSION.format(version=VERSION, date=BUILD_DATE, time=BUILD_TIME), text)
            self.assertIn(MSG_ABOUT_WEB, text)
            self.assertIn(MSG_ABOUT_BLOG, text)
            self.assertIn(MSG_ABOUT_MORE.format(site=MSG_SITE), text)
            self.assertIn(MSG_ABOUT_POWERED, text)
            self.assertIn(MSG_ABOUT_LICENSE, text)
            self.assertIn(MSG_ABOUT_COPYRIGHT.format(year=build_year()), text)
            self.assertIn(self.app.screen.quote, text)
            self.assertTrue(self.app.screen.quote in MSG_ABOUT_QUOTES or self.app.screen.quote.startswith(fixed_text(MSG_EIGHT_BALL)))
            self.assertIn('┗', text)
            await self.press(Key.ESCAPE)
            self.assertNotIsInstance(self.app.screen, AboutDialog)

    async def test_the_quote_is_the_eight_balls_answer_when_the_roll_falls_under_its_chance(self):
        with mock.patch.object(about_dialog.random, 'random', return_value=EIGHT_BALL_CHANCE / 2), mock.patch.object(about_dialog.random, 'choice', side_effect=lambda options: options[-1]):
            await self.press(keybindings.MainPage.ABOUT)
        self.assertEqual(self.app.screen.quote, MSG_EIGHT_BALL.format(answer=MSG_EIGHT_BALL_ANSWERS[-1]))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)

    def dialog_lines(self):
        return [line for line in self.text().splitlines() if Box.HEAVY_BAR in line]

    async def test_a_long_quote_wraps_onto_more_lines_in_place_of_the_blank_ones_and_the_box_stays_whole(self):
        with mock.patch.object(about_dialog, 'random_quote', return_value=LONG_QUOTE):
            await self.press(keybindings.MainPage.ABOUT)
        inner = DIALOG_WIDTH - DIALOG_MARGIN
        self.assertTrue(all(len(line.plain) <= inner for line in self.app.screen.lines(inner)))
        self.assertEqual(len(self.app.screen.quote_lines(inner)), 2)
        self.assertEqual(sum(LONG_QUOTE_WORD in line for line in self.dialog_lines()), 2)
        self.assertIn(Box.HEAVY_BOTTOM_LEFT, self.text())
        await self.press(Key.ENTER)

    async def test_a_one_line_quote_has_a_blank_line_above_and_below_it(self):
        await self.press(keybindings.MainPage.ABOUT)
        quote = self.app.screen.quote_lines(DIALOG_WIDTH - DIALOG_MARGIN)
        self.assertEqual(len(quote), 1)
        lines = [line.plain for line in self.app.screen.lines(DIALOG_WIDTH - DIALOG_MARGIN)]
        at = lines.index(quote[0])
        self.assertEqual((lines[at - 1], lines[at + 1]), (NOTHING, NOTHING))
        self.assertIn(Box.HEAVY_BOTTOM_LEFT, self.text())
        await self.press(Key.ENTER)

    async def test_a_quote_longer_than_four_lines_is_cut_there(self):
        with mock.patch.object(about_dialog, 'random_quote', return_value=LONG_QUOTE * 4):
            await self.press(keybindings.MainPage.ABOUT)
        self.assertEqual(len(self.app.screen.quote_lines(DIALOG_WIDTH - DIALOG_MARGIN)), QUOTE_LINES)
        self.assertEqual(sum(LONG_QUOTE_WORD in line for line in self.dialog_lines()), QUOTE_LINES)
        await self.press(Key.ENTER)

    async def test_every_quote_keeps_the_dialog_on_a_usual_console(self):
        for quote in MSG_ABOUT_QUOTES:
            with mock.patch.object(about_dialog, 'random_quote', return_value=quote):
                await self.press(keybindings.MainPage.ABOUT)
            self.assertIn(Box.HEAVY_BOTTOM_LEFT, self.text(), quote)
            await self.press(Key.ENTER)

    async def test_the_quote_is_one_of_the_quotes_when_the_roll_falls_over_the_eight_balls_chance(self):
        with mock.patch.object(about_dialog.random, 'random', return_value=EIGHT_BALL_CHANCE + (1 - EIGHT_BALL_CHANCE) / 2):
            await self.press(keybindings.MainPage.ABOUT)
        self.assertIn(self.app.screen.quote, MSG_ABOUT_QUOTES)
        self.assertNotIn(fixed_text(MSG_EIGHT_BALL), self.app.screen.quote)
        await self.press(Key.ENTER)

    async def test_the_build_date_is_a_date_and_the_year_comes_from_it(self):
        self.assertRegex(BUILD_DATE, DATE_PATTERN)
        self.assertRegex(BUILD_TIME, TIME_PATTERN)
        self.assertEqual(build_year(), BUILD_DATE[:len(build_year())])


class TestQuitting(UITest):

    async def test_quitting_asks_and_then_quits(self):
        self.document.changed()
        with mock.patch.object(self.app, EXIT) as leave:
            await self.press(keybindings.MainPage.QUIT)
            self.assertIsInstance(self.app.screen, QuitDialog)
            await self.press(Key.ESCAPE)
            leave.assert_not_called()
            self.assertIsInstance(self.app.screen, MainPage)
            await self.press(keybindings.MainPage.QUIT, keybindings.QuitDialog.QUIT)
            leave.assert_called_once()


    async def test_the_quit_dialogs_buttons_are_inside_its_box(self):
        self.document.changed()
        await self.press(keybindings.MainPage.QUIT)
        lines = str(self.app.screen.query_one(DIALOG_VIEW_SELECTOR).render()).splitlines()
        # The box is as wide as its three buttons need: every line is the box's width and ends at its side.
        self.assertEqual({len(line) for line in lines}, {len(lines[0])})
        for line in lines[1:-1]:
            self.assertEqual((line[0], line[-1]), (Box.HEAVY_BAR, Box.HEAVY_BAR))
        for label in MSG_QUIT_BUTTONS:
            self.assertTrue(any(label in line for line in lines), label)
        self.assertLessEqual(len(lines[0]), self.app.size.width)


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
        pages = [
            Page, ListPage, FieldPage, MainPage, FilePage, OpenPage, SongsPage, SongPage, PatternsPage, TrackEditor, ChainsPage,
            ChainEditor, GeneratorsPage, ArpEditor, AutoRatchetEditor,
            ScalesPage, ScalePage, GroovesPage, GrooveEditor, InstrumentsPage, InstrumentEditor, ArrangePage, ScenePage,
            ClipPage, PatternEditor, Dialog, MessageDialog, ConfirmDialog, PromptDialog, ChoiceDialog,
        ]
        for page in pages:
            for name, value in vars(page).items():
                if callable(value) and not name.startswith('_') and name not in ours:
                    with self.subTest(page=page.__name__, name=name):
                        self.assertFalse(hasattr(Screen, name))


class TestTitleInTheMiddle(UITest):
    """The header's first line keeps the set and its song in the left corner and the save mark in the right, the program's name centred between, the user's design."""

    async def test_the_name_is_centred_and_gives_way_to_a_long_set_and_song(self):
        self.assert_title(set_crumb=self.app.screen.set_crumb())
        page = self.app.screen
        long_crumb = LONG_SONG_WORD * page.size.width
        line = page.header_line(width=page.size.width, left=long_crumb, names=NOTHING, names_start=page.size.width - 1, mark=MSG_UNSAVED_MARK, centre=PROGRAM_NAME).plain
        self.assertNotIn(PROGRAM_NAME, line)
        self.assertTrue(line.rstrip().endswith(MSG_UNSAVED_MARK))
    """Each kind of page has a theme colour, the user's design, drawn as a stripe under the header in place of its rule; the main screen and Arrange keep the rule."""

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
        self.assertEqual(page.has_room_for_the_gap(), page.size.height >= ROOM_FOR_THE_GAP)


class TestCaptionsAndNames(UITest):
    """The theme's stripe carries the page's caption, and a page that starts with Name leaves a blank line under it, the user's design."""

    async def test_a_list_says_its_name_and_an_editor_says_what_it_edits(self):
        await self.press(keybindings.MainPage.PATTERNS)
        self.assertEqual(self.app.screen.caption(), Crumb.PATTERNS)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.caption(), MSG_EDITING_CAPTION.format(what=MSG_CAPTION_WORDS[Section.PATTERNS].upper(), name=self.app.screen.item))
        self.assertIn(self.app.screen.caption(), self.text().splitlines()[2])

    async def test_a_blank_line_follows_name(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        lines = [line.plain for line in self.app.screen.body(width=self.SIZE[0], height=self.SIZE[1])]
        name_line = next(place for place, line in enumerate(lines) if MSG_NAME_LABEL in line)
        self.assertEqual(lines[name_line + 1].strip(), NOTHING)


class TestFunctionKeys(UITest):
    """F2 renames, as on Windows, and F3 opens About, the user's choice; N still renames, since a stock Mac needs fn for F2."""

    async def test_f2_renames_on_a_list_and_on_a_page_with_a_name_and_f3_opens_about(self):
        await self.press(keybindings.MainPage.PATTERNS)
        await self.pilot.press(Key.F2)
        await self.settle()
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS, Key.ENTER, Key.DOWN, Key.DOWN)
        await self.pilot.press(Key.F2)
        await self.settle()
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ESCAPE)
        await self.pilot.press(Key.F3)
        await self.settle()
        self.assertIsInstance(self.app.screen, AboutDialog)


class TestPickerMark(UITest):
    """A settings field whose Enter opens a list shows a dim mark after its value, the user's choice; a typed one shows none."""

    async def test_scale_shows_the_mark_and_tempo_does_not(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        lines = self.text().splitlines()
        self.assertTrue(next(line for line in lines if MSG_SCALE_LABEL in line).rstrip().endswith(MSG_PICKER_MARK))
        self.assertNotIn(MSG_PICKER_MARK, next(line for line in lines if MSG_TEMPO_LABEL in line))


class TestButtonRowOnASettingsPage(UITest):
    """A settings page's buttons are one row under its settings: Down from the last setting reaches the first, Left and Right
    move along them, Up from any goes back to the last setting, and Down on them stays, the user's design."""

    async def test_the_arrows_reach_and_leave_the_buttons(self):
        await self.press(keybindings.MainPage.FILE)
        page = self.app.screen
        first_button = page.first_button_place()
        await self.press(*[Key.DOWN] * len(page.shown_fields()))
        self.assertEqual(page.place, first_button)
        await self.press(Key.DOWN, Key.RIGHT)
        self.assertEqual(page.place, first_button + 1)
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(page.place, len(page.shown_fields()) - 1)
        await self.press(Key.UP)
        self.assertEqual(page.place, first_button - 1)
