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
"""Real time got ready under the start screen (Transport.prepare): FluidSynth started where it is installed and the Realtime Sender
Process opened on every port, in the background, the function returned saying when it is done, and a sender started after the
tracker began to quit closed rather than left behind."""

import threading
import unittest
from unittest import mock

from llamatron.realtime import fluidsynth as fluidsynth_values
from llamatron.tui import transport as transport_values
from llamatron.tui.transport import Transport

PORTS = ['IAC Driver Bus 1', fluidsynth_values.FLUIDSYNTH_PORT]
WAIT_SECONDS = 5
# The transport's listing of the ports, by name, taken before any test stands in for it.
PORT_LISTING = transport_values.output_port_names.__name__


class Sender:
    """A stand-in for the Realtime Sender Process that notes being started and closed."""

    __slots__ = ('ports', 'started', 'closed')

    def __init__(self, ports):
        self.ports = ports
        self.started = False
        self.closed = False

    def start(self, *, at=None):
        self.started = True

    def stop_all(self):
        pass

    def close(self):
        self.closed = True


class TestPrepare(unittest.TestCase):

    def setUp(self):
        self.senders = []
        self.fluidsynth = mock.Mock()
        patcher = mock.patch.object(transport_values, PORT_LISTING, return_value=PORTS)
        patcher.start()
        self.addCleanup(patcher.stop)

    def made_sender(self, ports):
        sender = Sender(ports)
        self.senders.append(sender)
        return sender

    def transport(self, *, installed=True):
        return Transport(document_holder=mock.Mock(), make_sender=self.made_sender, fluidsynth=self.fluidsynth, fluidsynth_installed=lambda: installed)

    def wait_until(self, ready):
        done = threading.Event()
        for _ in range(WAIT_SECONDS * 100):
            if ready():
                return
            done.wait(0.01)
        self.fail()

    def test_fluidsynth_starts_and_the_sender_opens_every_port_before_it_says_done(self):
        transport = self.transport()
        self.wait_until(transport.prepare())
        # The sender is started on FluidSynth's port too, which asks FluidSynth again, answered at once as it already runs.
        self.fluidsynth.ensure_running.assert_called()
        self.assertEqual(self.senders[0].ports, sorted(PORTS))
        self.assertTrue(self.senders[0].started)

    def test_fluidsynth_not_installed_is_left_alone(self):
        transport = self.transport(installed=False)
        # With no FluidSynth, no port of FluidSynth's is listed.
        with mock.patch.object(transport_values, PORT_LISTING, return_value=PORTS[:1]):
            self.wait_until(transport.prepare())
        self.fluidsynth.ensure_running.assert_not_called()

    def test_a_sender_started_after_quitting_began_is_closed(self):
        transport = self.transport()
        gate = threading.Event()
        self.fluidsynth.ensure_running.side_effect = lambda: gate.wait(WAIT_SECONDS)
        ready = transport.prepare()
        transport.close()
        gate.set()
        self.wait_until(ready)
        self.assertTrue(self.senders[0].closed)


if __name__ == '__main__':
    unittest.main()
