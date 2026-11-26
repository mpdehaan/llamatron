# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later



"""The CoreMIDI port (realtime/sender_process/coremidi.py) on macOS, through a destination of the test's own that nothing else listens to, so
nothing is heard: events handed ahead arrive at their moments, a flush takes back what is still to come, and a name that is no
destination is refused in the program's words, a destination taken away as it is read is passed over, and no flush ever reaches the destination as a system reset; and elsewhere, CoreMIDI is not there to use."""

import ctypes
import sys
import threading
import time
import unittest
from unittest import mock

from llamatron.realtime.render_process import timeline
from llamatron.realtime.sender_process import coremidi
from llamatron.realtime.sender_process.coremidi import CoreMidiOutput
from llamatron.user_strings import errors
from tests.support.coremidi_turns import CoreMidiTestCase

DESTINATION = 'llamatron test destination'
NO_SUCH_DESTINATION = 'no such destination for llamatron'
GONE_DESTINATION = 'a destination taken away for llamatron'
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
# Where a packet list's first packet starts, and where a packet's length and bytes start, in CoreMIDI's MIDIPacketList.
FIRST_PACKET = 4
PACKET_LENGTH = 8
PACKET_DATA = 10
PACKET_ALIGNMENT = 4
READ_PROC = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


class Destination:
    """A CoreMIDI destination of the test's own, made in the process's one client, so that the suite makes no second client, which
    under load the MIDI server once refused; it keeps each message it receives with the clock's reading."""

    __slots__ = ('arrived', '_read', '_endpoint')

    def __init__(self, name):
        self.arrived = []
        core = coremidi.core_midi()
        def received(packets, _read_context, _source_context):
            moment = time.perf_counter()
            self.arrived.extend((moment, message) for message in messages_in(packets))
        # Kept, so that the callback CoreMIDI calls lives as long as the destination.
        self._read = READ_PROC(received)
        self._endpoint = ctypes.c_uint32()
        coremidi.checked(call=name, status=core.midi.MIDIDestinationCreate(core.client, core.text(name), self._read, None, ctypes.byref(self._endpoint)))

    def get_endpoint(self):
        return self._endpoint

    def close(self):
        coremidi.core_midi().midi.MIDIEndpointDispose(self._endpoint)


def messages_in(packets):
    """Return the bytes of each packet of a CoreMIDI packet list, read at its address."""
    messages = []
    place = packets + FIRST_PACKET
    for _ in range(ctypes.c_uint32.from_address(packets).value):
        length = ctypes.c_uint16.from_address(place + PACKET_LENGTH).value
        messages.append(list(ctypes.string_at(place + PACKET_DATA, length)))
        place = (place + PACKET_DATA + length + PACKET_ALIGNMENT - 1) & ~(PACKET_ALIGNMENT - 1)
    return messages


def note_on():
    return [timeline.NOTE_ON | CHANNEL, LOWEST_NOTE, QUIETEST]


class TestElsewhere(unittest.TestCase):

    def tearDown(self):
        coremidi.is_available.cache_clear()

    def test_coremidi_is_not_there_to_use_on_another_system(self):
        coremidi.is_available.cache_clear()
        with mock.patch.object(coremidi.sys, 'platform', ANOTHER_SYSTEM):
            self.assertFalse(coremidi.is_available())


@unittest.skipUnless(sys.platform == coremidi.MACOS, 'CoreMIDI is on macOS only')
class TestCoreMidiOutput(CoreMidiTestCase):

    def setUp(self):
        self.destination = Destination(DESTINATION)
        self.addCleanup(self.destination.close)
        self.arrived = self.destination.arrived
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

    def test_a_destination_taken_away_before_its_names_are_read_has_none_and_is_not_listed(self):
        gone = Destination(GONE_DESTINATION)
        endpoint = gone.get_endpoint()
        gone.close()
        self.assertIsNone(coremidi.core_midi().names_of(endpoint))
        self.assertNotIn(GONE_DESTINATION, coremidi.destination_names())


if __name__ == '__main__':
    unittest.main()
