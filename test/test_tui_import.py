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
"""Importing a MIDI file from the tracker: the main screen's Import cell, the file picker, the import dialog's fields, and the song it adds, undone in one step.

The picker starts in the home directory, which the tests point at a folder of their own holding
one of examples/midi/, so that nothing outside the test's temporary folder is read.
"""

import os
import shutil

import mido
import unittest
from unittest import mock

from ui_testing import UITest
from llamatron.composition.file_format import Section
from llamatron.importers.midi_import import DEFAULT_LONGEST_PATTERN, LONGEST_PATTERN_CHOICES
from llamatron.strings.importing import (
    MSG_IMPORT_AS_TRACKS, MSG_IMPORT_TITLE, MSG_IMPORTED, MSG_IMPORTED_NO_WARNINGS, MSG_IMPORTED_SONG, MSG_IMPORTED_WARNINGS,
)
from llamatron.strings.labels import Crumb, PageName
from llamatron.tui.dialogs.import_dialog import BUTTONS, CANCEL_BUTTON, CHORDS, LONGEST, ImportDialog
from llamatron.tui.dialogs.imported_dialog import ImportedDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.main_page import MainPage, cell_name, cell_opened_by
from llamatron.tui.screens.open_page import OpenPage
from llamatron.tui import keybindings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, 'examples', 'midi', 'pachelbel_canon.mid')
SAMPLE_FILE = os.path.basename(SAMPLE)
SAMPLE_SONG = os.path.splitext(SAMPLE_FILE)[0]
HOME = 'home'
NOT_MIDI = 'not midi.mid'
NOT_MIDI_TEXT = 'this is not a MIDI file'
WRITE_TEXT = 'w'
RENAMED = 'canon'
CONTROL_CHANGE = 'control_change'
# Five CC numbers on one track, one more than a track's lanes, so that the import warns of the one left out.
TAKEN_CCS = (1, 7, 64, 74)
UNTAKEN_CC = 91
WARNED_FILE = 'warned.mid'
DEEPER = 'more midi'
# How much of a warning's start the test looks for, short enough to fit one line of the dialog.
WARNING_SHOWN = 30


class TestImportDialog(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        os.makedirs(HOME, exist_ok=True)
        shutil.copy(SAMPLE, HOME)
        patcher = mock.patch('llamatron.tui.screens.importing.home_folder', return_value=os.path.abspath(HOME))
        patcher.start()
        self.addCleanup(patcher.stop)

    async def import_and_close(self):
        """Press Import, and then OK on the dialog that says what was imported."""
        await self.press(keybindings.ImportDialog.IMPORT)
        self.assertIsInstance(self.app.screen, ImportedDialog)
        await self.press(Key.ENTER)

    async def open_the_dialog(self, *, file_name=SAMPLE_FILE):
        await self.press(keybindings.MainPage.IMPORT_HERE)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index(file_name)
        await self.press(Key.ENTER)

    def test_the_main_screen_has_an_import_cell_after_export(self):
        self.assertEqual(cell_opened_by(Key.M), PageName.IMPORT)

    async def test_the_cell_sits_in_the_row_of_actions_after_export(self):
        names = [cell_name(item) for item in self.app.screen.rows()[-1]]
        self.assertEqual(names[names.index(PageName.EXPORT) + 1], PageName.IMPORT)
        self.assertIn(PageName.IMPORT, self.text())

    async def test_m_opens_the_picker_in_the_home_directory_showing_midi_files(self):
        await self.press(keybindings.MainPage.IMPORT_HERE)
        self.assertIsInstance(self.app.screen, OpenPage)
        self.assertEqual(os.path.abspath(self.app.screen.folder), os.path.abspath(HOME))
        self.assertIn(SAMPLE_FILE, [row[0] for row in self.app.screen.rows()])
        self.assertIn(Crumb.IMPORT_MIDI, self.text())

    async def test_enter_on_a_file_asks_how_to_import_it(self):
        await self.open_the_dialog()
        self.assertIsInstance(self.app.screen, ImportDialog)
        self.assertIn(MSG_IMPORT_TITLE, self.text())

    async def test_import_adds_the_song_makes_it_current_and_says_what_it_made(self):
        before = self.document.setlist().get_item_names(Section.PATTERNS)
        await self.open_the_dialog()
        made = self.app.screen.made()
        await self.import_and_close()
        self.assertIsInstance(self.app.screen, MainPage)
        self.assertEqual(self.document.current_song_name(), SAMPLE_SONG)
        self.assertEqual(len(self.document.setlist().get_item_names(Section.PATTERNS)), len(before) + made.patterns)
        self.assertIn(MSG_IMPORTED.format(name=SAMPLE_SONG, tracks=made.tracks, patterns=made.patterns, scenes=made.scenes), self.text())
        self.assertTrue(self.document.is_dirty())

    async def test_one_undo_takes_the_whole_import_away(self):
        songs = self.document.setlist().get_song_names()
        patterns = self.document.setlist().get_item_names(Section.PATTERNS)
        await self.open_the_dialog()
        await self.import_and_close()
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.document.setlist().get_song_names(), songs)
        self.assertEqual(self.document.setlist().get_item_names(Section.PATTERNS), patterns)

    async def test_esc_and_the_cancel_button_add_nothing(self):
        songs = self.document.setlist().get_song_names()
        await self.open_the_dialog()
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, OpenPage)
        await self.press(Key.ENTER)
        self.app.screen.row = BUTTONS
        self.app.screen.button = CANCEL_BUTTON
        await self.press(keybindings.ImportDialog.PRESS)
        self.assertEqual(self.document.setlist().get_song_names(), songs)

    async def test_the_fields_change_what_the_import_makes(self):
        await self.open_the_dialog()
        dialog = self.app.screen
        await self.press(*[Key.DOWN] * LONGEST, keybindings.ImportDialog.MORE)
        self.assertEqual(dialog.choices.longest_pattern, LONGEST_PATTERN_CHOICES[LONGEST_PATTERN_CHOICES.index(DEFAULT_LONGEST_PATTERN) + 1])
        await self.press(*[Key.DOWN] * (CHORDS - LONGEST), keybindings.ImportDialog.TOGGLE)
        self.assertFalse(dialog.choices.chords)
        self.assertIn(MSG_IMPORT_AS_TRACKS, self.text())

    async def test_enter_on_the_song_name_renames_the_song(self):
        await self.open_the_dialog()
        await self.press(keybindings.ImportDialog.RENAME)
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(*[Key.BACKSPACE] * len(SAMPLE_SONG))
        await self.type(RENAMED)
        await self.press(Key.ENTER)
        await self.import_and_close()
        self.assertEqual(self.document.current_song_name(), RENAMED)

    async def test_a_second_import_of_one_file_is_numbered(self):
        await self.open_the_dialog()
        await self.import_and_close()
        await self.open_the_dialog()
        await self.import_and_close()
        self.assertIn(SAMPLE_SONG, self.document.setlist().get_song_names())
        self.assertNotEqual(self.document.current_song_name(), SAMPLE_SONG)

    async def test_after_an_import_a_dialog_says_the_songs_name_and_that_there_were_no_warnings(self):
        await self.open_the_dialog()
        await self.press(keybindings.ImportDialog.IMPORT)
        self.assertIsInstance(self.app.screen, ImportedDialog)
        self.assertIn(MSG_IMPORTED_SONG.format(name=SAMPLE_SONG), self.text())
        self.assertIn(MSG_IMPORTED_NO_WARNINGS, self.text())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_the_dialog_after_an_import_lists_every_warning(self):
        midi = mido.MidiFile(SAMPLE)
        midi.tracks[1].insert(1, mido.Message(CONTROL_CHANGE, control=UNTAKEN_CC, value=1))
        for number in TAKEN_CCS:
            midi.tracks[1].insert(1, mido.Message(CONTROL_CHANGE, control=number, value=1))
        midi.save(os.path.join(HOME, WARNED_FILE))
        await self.open_the_dialog(file_name=WARNED_FILE)
        warnings = self.app.screen.made().warnings
        self.assertTrue(warnings)
        await self.press(keybindings.ImportDialog.IMPORT)
        self.assertIn(MSG_IMPORTED_WARNINGS, self.text())
        self.assertIn(warnings[0][:WARNING_SHOWN], self.text())

    async def test_enter_on_a_directory_goes_into_it_and_imports_from_there(self):
        os.makedirs(os.path.join(HOME, DEEPER))
        shutil.copy(SAMPLE, os.path.join(HOME, DEEPER))
        await self.press(keybindings.MainPage.IMPORT_HERE)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index(DEEPER)
        await self.press(Key.ENTER)
        self.assertEqual(os.path.basename(self.app.screen.folder), DEEPER)
        await self.open_the_picked(SAMPLE_FILE)
        self.assertIsInstance(self.app.screen, ImportDialog)

    async def open_the_picked(self, file_name):
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index(file_name)
        await self.press(Key.ENTER)

    async def test_a_file_that_isnt_midi_is_told_and_the_picker_stays(self):
        with open(os.path.join(HOME, NOT_MIDI), WRITE_TEXT) as file:
            file.write(NOT_MIDI_TEXT)
        await self.open_the_dialog(file_name=NOT_MIDI)
        self.assertIsInstance(self.app.screen, MessageDialog)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, OpenPage)


if __name__ == '__main__':
    unittest.main()
