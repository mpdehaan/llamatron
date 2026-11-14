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

"""Quitting: Ctrl+C at once, and Q with its question."""

from unittest import mock

from tests.support.ui_testing import UITest, key_name
from llamatron.tui.drawing import Box
from llamatron.tui.dialogs.dialog import DIALOG_VIEW_SELECTOR
from llamatron.tui.dialogs.quit_dialog import QuitDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.main_page import MainPage
from llamatron.strings.labels import MSG_NOTES_LABEL, MSG_QUIT_BUTTONS
from llamatron.strings.legends import MSG_QUIT_WITHOUT_SAVING_WHAT
from llamatron.tui import keybindings

EXIT = 'exit'


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
        # The console has the room, so the keys under the buttons are on one line: the first key and the last share it.
        first = MSG_QUIT_WITHOUT_SAVING_WHAT
        self.assertTrue(any(key_name(keybindings.QuitDialog.CANCEL) in line and first in line and key_name(keybindings.QuitDialog.SELECT) in line for line in lines[-3:]))
