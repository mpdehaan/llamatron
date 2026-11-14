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

"""The warning when a set opens whose tracks play through instruments that cannot sound here: FluidSynth not installed, or a MIDI port not connected."""

import unittest
from unittest import mock

from llamatron.composition.file_format import FLUIDSYNTH_DEVICE
from llamatron.strings.errors import ERR_DEVICE_WILL_NOT_SOUND, ERR_FLUIDSYNTH_WILL_NOT_SOUND, ERR_SILENT_INSTRUMENTS_TITLE
from llamatron.tui.app import LlamatronApp
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from llamatron.tui.launch import Launch
from llamatron.tui.screens.main_page import MainPage
from llamatron.tui.silent_instruments import silent_instrument_lines
from ui_testing import DRUMS, LEAD, UITest, a_song

FLUID = 'fluid'
KEYS = 'keys'
UNUSED = 'unused'
GONE_PORT = 'IAC Driver Bus 9'
CONNECTED_PORT = 'Analog Four'
SAVED = 'instruments.yml'
PORT_NAMES = 'llamatron.tui.silent_instruments.output_port_names'
INSTALLED = 'llamatron.tui.silent_instruments.fluidsynth_installed'
# Long enough that a launch with a time limit never quits while the test runs.
A_LONG_TIME = 600


def with_instruments(document, *, keys_device=GONE_PORT):
    """Give the lead a FluidSynth instrument and the drums one on a MIDI port, and add an instrument nothing plays through, on a port that has gone."""
    for name, device in ((FLUID, FLUIDSYNTH_DEVICE), (KEYS, keys_device), (UNUSED, GONE_PORT)):
        document.add_instrument(name)
        document.set_instrument_device(name=name, device=device)
    document.set_track_instrument(name=LEAD, instrument=FLUID)
    document.set_track_instrument(name=DRUMS, instrument=KEYS)
    return document


class TestSilentInstrumentLines(unittest.TestCase):

    def setUp(self):
        self.setlist = with_instruments(a_song()).setlist()

    def test_fluidsynth_not_installed_and_a_port_not_connected_are_each_told(self):
        lines = silent_instrument_lines(setlist=self.setlist, installed=False, connected=set())
        self.assertEqual(lines, [ERR_FLUIDSYNTH_WILL_NOT_SOUND, ERR_DEVICE_WILL_NOT_SOUND.format(instrument=KEYS, device=GONE_PORT)])

    def test_an_instrument_no_track_plays_through_is_never_told(self):
        lines = silent_instrument_lines(setlist=self.setlist, installed=False, connected=set())
        self.assertFalse(any(UNUSED in line for line in lines))

    def test_nothing_is_told_when_fluidsynth_is_installed_and_the_port_connected(self):
        self.assertEqual(silent_instrument_lines(setlist=self.setlist, installed=True, connected={GONE_PORT}), [])

    def test_fluidsynth_is_told_once_however_many_instruments_use_it(self):
        document = with_instruments(a_song())
        document.set_instrument_device(name=KEYS, device=FLUIDSYNTH_DEVICE)
        self.assertEqual(silent_instrument_lines(setlist=document.setlist(), installed=False, connected=set()), [ERR_FLUIDSYNTH_WILL_NOT_SOUND])


class SilentInstrumentsTest(UITest):
    """A tracker on a saved set whose instruments cannot sound here: FluidSynth is not installed and no port is connected."""

    def make_app(self):
        self.say_not_installed()
        document = with_instruments(a_song())
        document.save(path=SAVED)
        return LlamatronApp(document=document, launch=self.launch())

    def launch(self):
        return None

    def say_not_installed(self):
        for target, answer in ((INSTALLED, False), (PORT_NAMES, [CONNECTED_PORT])):
            patcher = mock.patch(target, return_value=answer)
            patcher.start()
            self.addCleanup(patcher.stop)

    def assert_told(self, message):
        """Check that the dialog on screen holds the message, read from the dialog, since the page behind shows through between its wrapped lines."""
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(message, self.app.screen.messages)


class TestSilentInstrumentsWhenTheTrackerStarts(SilentInstrumentsTest):

    async def test_the_dialog_tells_each_and_the_set_keeps_its_devices(self):
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(ERR_SILENT_INSTRUMENTS_TITLE, self.text())
        self.assert_told(ERR_FLUIDSYNTH_WILL_NOT_SOUND)
        self.assert_told(ERR_DEVICE_WILL_NOT_SOUND.format(instrument=KEYS, device=GONE_PORT))
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MainPage)
        setlist = self.app.get_document().setlist()
        self.assertEqual(setlist.get_instrument(FLUID).get_device(), FLUIDSYNTH_DEVICE)
        self.assertEqual(setlist.get_instrument(KEYS).get_device(), GONE_PORT)
        self.assertFalse(self.app.get_document().is_dirty())

    async def test_opening_the_set_again_from_the_open_page_tells_it_again(self):
        await self.press(Key.ENTER, Key.CTRL_O)
        rows = [row[0] for row in self.app.screen.rows()]
        self.app.screen.place = rows.index(SAVED)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assert_told(ERR_FLUIDSYNTH_WILL_NOT_SOUND)


class TestNoWarningWhenEverythingSounds(SilentInstrumentsTest):

    def say_not_installed(self):
        for target, answer in ((INSTALLED, True), (PORT_NAMES, [CONNECTED_PORT])):
            patcher = mock.patch(target, return_value=answer)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_app(self):
        self.say_not_installed()
        document = with_instruments(a_song(), keys_device=CONNECTED_PORT)
        document.save(path=SAVED)
        return LlamatronApp(document=document)

    async def test_the_tracker_opens_on_the_main_screen(self):
        self.assertIsInstance(self.app.screen, MainPage)


class TestNoWarningWhenTheTrackerPlaysOnItsOwn(SilentInstrumentsTest):
    """A dialog would stop a tracker launched to play by itself, as the demo recorder launches it."""

    def launch(self):
        return Launch(max_seconds=A_LONG_TIME)

    async def test_no_dialog_is_shown(self):
        self.assertIsInstance(self.app.screen, MainPage)


if __name__ == '__main__':
    unittest.main()
