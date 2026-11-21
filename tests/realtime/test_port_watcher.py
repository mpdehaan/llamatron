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
"""The MIDI ports listed through one thread that lives as long as the process (PortWatcher), the only thread CoreMIDI tells of ports
other programs make later: every listing from any thread is answered by it, the ports are listed once and again only when asked,
an answer always comes even when the listing fails, CoreMIDI lists them on macOS and python-rtmidi elsewhere, and on macOS a port
another program makes later is seen by listing again."""

import subprocess
import sys
import threading
import unittest
from unittest import mock

from llamatron.realtime import coremidi, outputs
from llamatron.realtime.outputs import PortWatcher

A_PORT = 'a port'
ANOTHER_PORT = 'another port'
HAS_LIBRARY = outputs.has_midi_library.__name__
# A port another process makes once the first listing is taken, through a CoreMIDI destination of the tests' own, and how long the
# test looks for it.
LATER_PORT = 'llamatron port made later'
MADE = 'made'
MAKES_A_PORT = f"import time; from tests.realtime.test_coremidi import Destination; Destination({LATER_PORT!r}); print({MADE!r}, flush=True); time.sleep(10)"
LOOKS = 20
LOOK_SECONDS = 0.1


class TestPortWatcher(unittest.TestCase):

    def setUp(self):
        self.threads = []
        self.listings = [[A_PORT], [A_PORT, ANOTHER_PORT]]

    def listed(self):
        """Stand in for listing the ports: note the thread asked, and answer the next listing."""
        self.threads.append(threading.current_thread())
        return self.listings.pop(0)

    def test_every_listing_is_answered_by_one_thread_not_the_askers(self):
        watcher = PortWatcher(listing=self.listed)
        self.assertEqual(watcher.names(), [A_PORT])
        asked_elsewhere = threading.Thread(target=watcher.names_now)
        asked_elsewhere.start()
        asked_elsewhere.join()
        self.assertEqual(len(set(self.threads)), 1)
        self.assertIsNot(self.threads[0], threading.current_thread())

    def test_the_ports_are_listed_once_and_again_only_when_asked(self):
        watcher = PortWatcher(listing=self.listed)
        self.assertEqual(watcher.names(), [A_PORT])
        self.assertEqual(watcher.names(), [A_PORT])
        self.assertEqual(len(self.threads), 1)
        self.assertEqual(watcher.names_now(), [A_PORT, ANOTHER_PORT])
        self.assertEqual(watcher.names(), [A_PORT, ANOTHER_PORT])

    def test_an_answer_comes_even_when_the_listing_fails_and_the_thread_lives_on(self):
        self.listings = [OSError(), [ANOTHER_PORT]]

        def failing_once():
            found = self.listings.pop(0)
            if isinstance(found, Exception):
                raise found
            return found
        watcher = PortWatcher(listing=failing_once)
        self.assertEqual(watcher.names(), [])
        self.assertEqual(watcher.names_now(), [ANOTHER_PORT])

    def test_the_ports_are_listed_through_coremidi_where_it_is_and_python_rtmidi_elsewhere(self):
        with mock.patch.object(coremidi, coremidi.is_available.__name__, return_value=True):
            self.assertIs(outputs.default_listing(), coremidi.destination_names)
        with mock.patch.object(coremidi, coremidi.is_available.__name__, return_value=False), mock.patch.object(outputs, HAS_LIBRARY, return_value=True):
            self.assertIs(outputs.default_listing(), outputs.rtmidi_names)


@unittest.skipUnless(sys.platform == coremidi.MACOS, 'CoreMIDI is on macOS only')
class TestCoreMidiListing(unittest.TestCase):

    def test_a_port_another_program_makes_later_is_seen_by_listing_again(self):
        watcher = PortWatcher(listing=coremidi.destination_names)
        self.assertNotIn(LATER_PORT, watcher.names())
        other = subprocess.Popen([sys.executable, '-c', MAKES_A_PORT], stdout=subprocess.PIPE, text=True)
        self.addCleanup(other.wait)
        self.addCleanup(other.kill)
        self.assertEqual(other.stdout.readline().strip(), MADE)
        for _ in range(LOOKS):
            if LATER_PORT in watcher.names_now():
                return
            threading.Event().wait(LOOK_SECONDS)
        self.fail(LATER_PORT)


if __name__ == '__main__':
    unittest.main()
