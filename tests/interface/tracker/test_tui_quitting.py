# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Quitting: Ctrl+C at once, Q with its question, and a crash, whose traceback is printed as plain text."""

import os
import subprocess
import sys
import unittest
from unittest import mock

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs import dialog
from llamatron.interface.tracker.dialogs.quit_dialog import QuitDialog
from llamatron.interface.tracker.drawing import Box
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.user_strings import labels, legends
from tests.support.ui_testing import key_name, UITest

EXIT = 'exit'
# A tracker that raises an error nothing catches once it is open, run headless in a process of its own.
CRASH_MESSAGE = 'a crash on purpose'
CRASHING_TRACKER = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'crashing_tracker.py')
# What a coloured or boxed traceback holds and a plain one never does: an escape code, and the corner of Rich's box.
ESCAPE = '\x1b'
BOX_CORNER = '╭'


class TestQuitNow(UITest):
    """Ctrl+C quits at once from any page or dialog, through the app's exit, which closes FluidSynth and the MIDI sender."""

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
        await self.select_field(labels.MSG_NOTES_LABEL)
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
        lines = str(self.app.screen.query_one(dialog.DIALOG_VIEW_SELECTOR).render()).splitlines()
        # The box is as wide as its three buttons need: every line is the box's width and ends at its side.
        self.assertEqual({len(line) for line in lines}, {len(lines[0])})
        for line in lines[1:-1]:
            self.assertEqual((line[0], line[-1]), (Box.HEAVY_BAR, Box.HEAVY_BAR))
        for label in labels.MSG_QUIT_BUTTONS:
            self.assertTrue(any(label in line for line in lines), label)
        self.assertLessEqual(len(lines[0]), self.app.size.width)
        # The console has the room, so the keys under the buttons are on one line: the first key and the last share it.
        first = legends.MSG_QUIT_WITHOUT_SAVING_WHAT
        self.assertTrue(any(key_name(keybindings.QuitDialog.CANCEL) in line and first in line and key_name(keybindings.QuitDialog.SELECT) in line for line in lines[-3:]))


class TestACrash(unittest.TestCase):
    """An error nothing catches closes the tracker with Python's own plain traceback, which reads well when saved to a file."""

    def test_the_traceback_is_plain_text_with_no_colour_box_or_locals(self):
        ran = subprocess.run([sys.executable, CRASHING_TRACKER, CRASH_MESSAGE], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(ran.returncode, 0)
        self.assertIn(CRASH_MESSAGE, ran.stderr)
        self.assertTrue(ran.stderr.splitlines()[0].startswith('Traceback'))
        self.assertNotIn(ESCAPE, ran.stderr)
        self.assertNotIn(BOX_CORNER, ran.stderr)
