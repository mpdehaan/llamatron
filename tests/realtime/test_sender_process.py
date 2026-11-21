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
"""The Realtime Sender Process's end of the pipe: when the tracker's end goes away, as when the tracker dies, every note still
sounding is stopped before the process ends, so that nothing is left stuck on a synthesizer."""

import multiprocessing
import threading
import unittest
from unittest import mock

from llamatron.realtime import sender_process
from llamatron.realtime.engine import PlaybackEngine

A_PORT = 'a port'
WAIT_SECONDS = 5


class TestSenderEnds(unittest.TestCase):

    def test_the_sender_stops_every_note_when_the_trackers_end_of_the_pipe_closes(self):
        tracker_end, sender_end = multiprocessing.Pipe()
        with mock.patch.object(PlaybackEngine, PlaybackEngine.close.__name__) as closed:
            sender = threading.Thread(target=sender_process.run_sender, kwargs=dict(connection=sender_end, ports=[A_PORT], recording=True))
            sender.start()
            self.assertEqual(tracker_end.recv(), sender_process.READY)
            tracker_end.close()
            sender.join(timeout=WAIT_SECONDS)
        self.assertFalse(sender.is_alive())
        closed.assert_called_once()


if __name__ == '__main__':
    unittest.main()
