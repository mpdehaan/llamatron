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
other programs make later: every listing from any thread is answered by it, and an answer always comes, even when the library fails."""

import threading
import unittest
from unittest import mock

from llamatron.realtime import outputs
from llamatron.realtime.outputs import PortWatcher

A_PORT = 'a port'
ANOTHER_PORT = 'another port'
# The library's functions, by name, taken before any test stands in for them.
LIBRARY = outputs.midi_library.__name__
HAS_LIBRARY = outputs.has_midi_library.__name__


class TestPortWatcher(unittest.TestCase):

    def setUp(self):
        self.library = mock.Mock()
        self.threads = []

        def listed():
            self.threads.append(threading.current_thread())
            return [A_PORT]
        self.library.MidiOut.return_value.get_ports.side_effect = listed
        for name, value in ((LIBRARY, self.library), (HAS_LIBRARY, True)):
            patcher = mock.patch.object(outputs, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_every_listing_is_answered_by_one_thread_not_the_askers(self):
        watcher = PortWatcher()
        self.assertEqual(watcher.names(), [A_PORT])
        asked_elsewhere = threading.Thread(target=watcher.names)
        asked_elsewhere.start()
        asked_elsewhere.join()
        self.assertEqual(len(set(self.threads)), 1)
        self.assertIsNot(self.threads[0], threading.current_thread())

    def test_an_answer_comes_even_when_the_library_fails_and_the_thread_lives_on(self):
        watcher = PortWatcher()
        self.library.MidiOut.return_value.get_ports.side_effect = [RuntimeError(), [ANOTHER_PORT]]
        self.assertEqual(watcher.names(), [])
        self.assertEqual(watcher.names(), [ANOTHER_PORT])

    def test_no_library_lists_no_ports(self):
        with mock.patch.object(outputs, HAS_LIBRARY, return_value=False):
            self.assertEqual(PortWatcher().names(), [])


if __name__ == '__main__':
    unittest.main()
