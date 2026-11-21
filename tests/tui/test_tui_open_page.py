# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Open page."""

import os

from llamatron.tui import keybindings
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.set.file_page import FilePage
from llamatron.tui.screens.set.importing import home_folder
from llamatron.tui.screens.set.open_page import OpenPage
from llamatron.user_strings import labels, marks, names
from tests.support.ui_testing import a_song, UITest

LEAD = 'lead'
DRUMS = 'drums'
FOLDER_OF_SETS = 'sets'
INNER_FOLDER = 'more'
PARENT_FOLDER = '..'
HERE = '.'
SECOND_SONG = 'second'
WRITE_TEXT = 'w'
# A directory the Open page goes into, and the row that goes back up.
SUBFOLDER = 'more songs'


class TestOpenPage(UITest):

    async def test_picks_a_file_and_opens_it(self):
        a_song().save(path='song one.yml')
        await self.press(keybindings.MainPage.FILE, Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.assertIn('song one.yml', rows)
        self.app.screen.cursor.set_place(rows.index('song one.yml'))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, FilePage)
        self.assertEqual(self.app.get_document().get_path(), 'song one.yml')

    async def test_folders_show_with_a_slash_and_enter_goes_into_one_and_back_out(self):
        os.makedirs(os.path.join(FOLDER_OF_SETS, INNER_FOLDER))
        a_song().save(path=os.path.join(FOLDER_OF_SETS, INNER_FOLDER, 'deep song.yml'))
        await self.press(Key.CTRL_O)
        shown = self.text()
        self.assertIn(marks.MSG_FOLDER_ROW.format(name=FOLDER_OF_SETS), shown)
        self.assertIn(marks.MSG_PARENT_ROW, shown)
        for folder in (FOLDER_OF_SETS, INNER_FOLDER):
            rows = [row[0] for row in self.app.screen.rows()]
            self.app.screen.cursor.set_place(rows.index(folder))
            await self.press(Key.ENTER)
        self.assertIn('deep song.yml', [row[0] for row in self.app.screen.rows()])
        self.app.screen.cursor.set_place([row[0] for row in self.app.screen.rows()].index(PARENT_FOLDER))
        await self.press(Key.ENTER)
        self.assertIn(INNER_FOLDER, [row[0] for row in self.app.screen.rows()])

    async def enter(self, name):
        """Press ENTER on the Open page's row of this name."""
        self.app.screen.cursor.set_place([row[0] for row in self.app.screen.rows()].index(name))
        await self.press(Key.ENTER)

    async def test_it_comes_back_to_the_directory_it_last_showed(self):
        # Kept for the session, whether a file was opened there or the page was left with ESC.
        os.makedirs(os.path.join(FOLDER_OF_SETS, INNER_FOLDER))
        a_song().save(path=os.path.join(FOLDER_OF_SETS, 'kept song.yml'))
        await self.press(Key.CTRL_O)
        await self.enter(FOLDER_OF_SETS)
        await self.press(Key.ESCAPE, Key.CTRL_O)
        self.assertIn('kept song.yml', [row[0] for row in self.app.screen.rows()])
        await self.enter('kept song.yml')
        await self.press(Key.CTRL_O)
        self.assertIn('kept song.yml', [row[0] for row in self.app.screen.rows()])
        await self.enter(INNER_FOLDER)
        await self.enter(PARENT_FOLDER)
        await self.press(Key.ESCAPE, Key.CTRL_O)
        self.assertIn('kept song.yml', [row[0] for row in self.app.screen.rows()])

    async def test_a_remembered_directory_that_is_gone_is_forgotten(self):
        os.makedirs(FOLDER_OF_SETS)
        await self.press(Key.CTRL_O)
        await self.enter(FOLDER_OF_SETS)
        await self.press(Key.ESCAPE)
        os.rmdir(FOLDER_OF_SETS)
        await self.press(Key.CTRL_O)
        self.assertEqual(self.app.screen.folder, HERE)

    async def test_the_import_picker_remembers_a_directory_of_its_own(self):
        os.makedirs(FOLDER_OF_SETS)
        await self.press(Key.CTRL_O)
        await self.enter(FOLDER_OF_SETS)
        await self.press(Key.ESCAPE, keybindings.MainPage.IMPORT_HERE)
        self.assertEqual(self.app.screen.folder, home_folder())

    async def test_an_opened_set_starts_on_its_first_song(self):
        two_songs = a_song()
        two_songs.add_song(SECOND_SONG)
        two_songs.save(path='two songs.yml')
        await self.press(Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.cursor.set_place(rows.index('two songs.yml'))
        await self.press(Key.ENTER)
        self.assertEqual(self.app.get_document().get_current_song_name(), names.MSG_DEFAULT_SONG_NAME)
        self.assertEqual(self.app.get_document().song().get_track_names(), [LEAD, DRUMS])
        self.assert_header(set_crumb=labels.MSG_SET_CRUMB.format(file='two songs.yml'), song_crumb=labels.MSG_SONG_CRUMB.format(song=names.MSG_DEFAULT_SONG_NAME))

    async def test_control_o_opens_from_any_page_and_comes_back_to_it(self):
        a_song().save(path='song one.yml')
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, Key.CTRL_O)
        self.assertIsInstance(self.app.screen, OpenPage)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.cursor.set_place(rows.index('song one.yml'))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.get_document().get_path(), 'song one.yml')

    async def test_enter_on_a_directory_goes_into_it_and_lists_its_files(self):
        os.makedirs(SUBFOLDER)
        a_song().save(path=os.path.join(SUBFOLDER, 'inside.yml'))
        await self.press(Key.CTRL_O)
        self.app.screen.folder = os.curdir
        rows = [row[0] for row in self.app.screen.rows_with_plus()]
        self.app.screen.cursor.set_place(rows.index(SUBFOLDER))
        await self.press(Key.ENTER)
        self.assertEqual([row[0] for row in self.app.screen.rows_with_plus()], [PARENT_FOLDER, 'inside.yml'])
        self.app.screen.cursor.set_place(1)
        await self.press(Key.ENTER)
        self.assertEqual(os.path.basename(self.app.get_document().get_path()), 'inside.yml')

    async def test_a_bad_file_is_a_popup_and_keeps_the_song(self):
        with open('bad.yml', WRITE_TEXT) as file:
            file.write('tempo: [')
        before = self.app.get_document()
        await self.press(keybindings.MainPage.FILE, Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.cursor.set_place(rows.index('bad.yml'))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIs(self.app.get_document(), before)
