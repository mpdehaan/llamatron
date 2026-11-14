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

"""The Open page."""

import os

from tests.support.ui_testing import UITest, a_song
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.file_page import FilePage
from llamatron.tui.screens.set.open_page import OpenPage
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.strings.labels import MSG_SET_CRUMB, MSG_SONG_CRUMB
from llamatron.strings.marks import MSG_FOLDER_ROW, MSG_PARENT_ROW
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME
from llamatron.tui import keybindings

LEAD = 'lead'
DRUMS = 'drums'
FOLDER_OF_SETS = 'sets'
INNER_FOLDER = 'more'
PARENT_FOLDER = '..'
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
