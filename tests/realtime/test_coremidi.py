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



"""The CoreMIDI port (realtime/coremidi.py) on macOS, through a destination of the test's own that nothing else listens to, so
nothing is heard: events handed ahead arrive at their moments, a flush takes back what is still to come, and a name that is no
destination is refused in the program's words, and no flush ever reaches the destination as a system reset; and elsewhere, CoreMIDI is not there to use."""

import sys
import threading
import time
import unittest
from unittest import mock

from llamatron.realtime import coremidi, outputs, timeline
from llamatron.realtime.coremidi import CoreMidiOutput
from llamatron.strings import errors

DESTINATION = 'llamatron test destination'
NO_SUCH_DESTINATION = 'no such destination for llamatron'
ANOTHER_SYSTEM = 'linux'
CHANNEL = 15
LOWEST_NOTE = 1
QUIETEST = 1
# Three notes handed together, the first a little ahead, the rest a little apart.
FIRST_AHEAD_SECONDS = 0.05
APART_SECONDS = 0.03
NOTES = 3
# How far from its moment a note may arrive while the suite loads the machine: CoreMIDI measured within a tenth of a millisecond.
ALLOWED_SECONDS = 0.003
# A note handed far enough ahead for a flush to take it back, and how long the test waits to be sure it never comes.
FAR_AHEAD_SECONDS = 0.2
WAIT_SECONDS = 0.4


def note_on():
    return [timeline.NOTE_ON | CHANNEL, LOWEST_NOTE, QUIETEST]


class TestElsewhere(unittest.TestCase):

    def tearDown(self):
        coremidi.is_available.cache_clear()

    def test_coremidi_is_not_there_to_use_on_another_system(self):
        coremidi.is_available.cache_clear()
        with mock.patch.object(coremidi.sys, 'platform', ANOTHER_SYSTEM):
            self.assertFalse(coremidi.is_available())


@unittest.skipUnless(sys.platform == coremidi.MACOS and outputs.has_midi_library(), 'CoreMIDI is on macOS only')
class TestCoreMidiOutput(unittest.TestCase):

    def setUp(self):
        import rtmidi
        self.arrived = []
        self.listener = rtmidi.MidiIn()
        self.listener.open_virtual_port(DESTINATION)
        self.listener.set_callback(lambda message, data: self.arrived.append((time.perf_counter(), message[0])))
        self.addCleanup(self.listener.close_port)
        self.output = CoreMidiOutput(name=DESTINATION)
        self.addCleanup(self.output.close)

    def test_coremidi_is_there_to_use_on_macos(self):
        self.assertTrue(coremidi.is_available())

    def test_notes_handed_ahead_arrive_at_their_moments(self):
        first = time.perf_counter() + FIRST_AHEAD_SECONDS
        moments = [first + place * APART_SECONDS for place in range(NOTES)]
        for moment in moments:
            self.output.send_at(data=note_on(), at=moment)
        threading.Event().wait(FIRST_AHEAD_SECONDS + NOTES * APART_SECONDS + FIRST_AHEAD_SECONDS)
        self.assertEqual([message for _at, message in self.arrived], [note_on()] * NOTES)
        worst = max(abs(at - moment) for (at, _message), moment in zip(self.arrived, moments))
        self.assertLess(worst, ALLOWED_SECONDS)

    def test_a_flush_takes_back_what_is_still_to_come_sends_no_system_reset_and_what_is_sent_at_once_still_arrives(self):
        """CoreMIDI's own flush reached a destination another program made as a byte 0xFF, a system reset, which FluidSynth obeys."""
        self.output.send_at(data=note_on(), at=time.perf_counter() + FAR_AHEAD_SECONDS)
        self.output.flush()
        self.output.send(note_on())
        threading.Event().wait(WAIT_SECONDS)
        self.assertEqual([message for _at, message in self.arrived], [note_on()])

    def test_a_name_that_is_no_destination_is_refused_in_the_programs_words(self):
        with self.assertRaises(ValueError) as caught:
            CoreMidiOutput(name=NO_SUCH_DESTINATION)
        self.assertEqual(str(caught.exception), errors.ERR_NO_SUCH_MIDI_PORT.format(name=NO_SUCH_DESTINATION))


if __name__ == '__main__':
    unittest.main()
