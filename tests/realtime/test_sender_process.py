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
"""The Realtime Sender Process: when the tracker's end of the pipe goes away, as when the tracker dies, every note still sounding
is stopped before the process ends, so that nothing is left stuck on a synthesizer; and as it starts, it freezes what it has made
for the garbage collector, stops collecting on its own, and asks macOS to run it at its most urgent."""

import multiprocessing
import threading
import unittest
from unittest import mock

from llamatron.realtime import sender_process
from llamatron.realtime.engine import PlaybackEngine

A_PORT = 'a port'
WAIT_SECONDS = 5
ANOTHER_SYSTEM = 'linux'


class TestSenderEnds(unittest.TestCase):

    def test_the_sender_stops_every_note_when_the_trackers_end_of_the_pipe_closes(self):
        tracker_end, sender_end = multiprocessing.Pipe()
        # The process's own settings for garbage and urgency would reach the whole test run in a thread, so they are left out here.
        with mock.patch.object(PlaybackEngine, PlaybackEngine.close.__name__) as closed, \
                mock.patch.object(sender_process, sender_process.hold_garbage_back.__name__), mock.patch.object(sender_process, sender_process.ask_to_be_urgent.__name__):
            sender = threading.Thread(target=sender_process.run_sender, kwargs=dict(connection=sender_end, ports=[A_PORT], recording=True))
            sender.start()
            self.assertEqual(tracker_end.recv(), sender_process.READY)
            tracker_end.close()
            sender.join(timeout=WAIT_SECONDS)
        self.assertFalse(sender.is_alive())
        closed.assert_called_once()



class TestSenderStarts(unittest.TestCase):

    def test_the_sender_freezes_what_it_made_and_stops_collecting_on_its_own(self):
        with mock.patch.object(sender_process, 'gc') as garbage:
            sender_process.hold_garbage_back()
        garbage.freeze.assert_called_once()
        garbage.disable.assert_called_once()

    def test_on_macos_the_sender_asks_for_the_most_urgent_quality_of_service(self):
        with mock.patch.object(sender_process.sys, 'platform', sender_process.DARWIN), mock.patch.object(sender_process.ctypes, 'CDLL') as library:
            sender_process.ask_to_be_urgent()
        library.return_value.pthread_set_qos_class_self_np.assert_called_once_with(sender_process.QOS_CLASS_USER_INTERACTIVE, 0)

    def test_elsewhere_the_sender_asks_nothing(self):
        with mock.patch.object(sender_process.sys, 'platform', ANOTHER_SYSTEM), mock.patch.object(sender_process.ctypes, 'CDLL') as library:
            sender_process.ask_to_be_urgent()
        library.assert_not_called()


if __name__ == '__main__':
    unittest.main()
