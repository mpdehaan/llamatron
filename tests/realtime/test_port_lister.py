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
"""The MIDI ports listed through one client, made once, so that no launch waits for CoreMIDI to start a client."""

import unittest
from unittest import mock

from llamatron.realtime import outputs
from llamatron.realtime.outputs import PortLister

A_PORT = 'a port'
ANOTHER_PORT = 'another port'


class TestPortLister(unittest.TestCase):

    def test_one_client_lists_the_ports_every_time_and_sees_a_port_added(self):
        library = mock.Mock()
        client = library.MidiOut.return_value
        client.get_ports.side_effect = [[A_PORT], [A_PORT, ANOTHER_PORT]]
        lister = PortLister()
        with mock.patch.object(outputs, outputs.midi_library.__name__, return_value=library), mock.patch.object(outputs, outputs.has_midi_library.__name__, return_value=True):
            self.assertEqual(lister.names(), [A_PORT])
            self.assertEqual(lister.names(), [A_PORT, ANOTHER_PORT])
        library.MidiOut.assert_called_once()

    def test_no_library_lists_no_ports(self):
        with mock.patch.object(outputs, outputs.has_midi_library.__name__, return_value=False):
            self.assertEqual(PortLister().names(), [])


if __name__ == '__main__':
    unittest.main()
