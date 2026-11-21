# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Realtime Sender Process: when the tracker's end of the pipe goes away, as when the tracker dies, every note still sounding
is stopped before the process ends, so that nothing is left stuck on a synthesizer; and as it starts, it freezes what it has made
for the garbage collector, stops collecting on its own, and asks macOS to run it at its most urgent."""

import multiprocessing
import threading
import unittest
from unittest import mock

from llamatron.realtime import coremidi, sender_process, timeline
from llamatron.realtime.engine import PlaybackEngine
from llamatron.realtime.scheduled_engine import ScheduledPlaybackEngine
from llamatron.realtime.timeline import Playing, Tag
from llamatron.support.rational import Rational

A_PORT = 'a port'
WAIT_SECONDS = 5
ANOTHER_SYSTEM = 'linux'
ANOTHER_PORT = 'another port'
A_TAG = Tag(0, 'lead', 1)
ANOTHER_TAG = Tag(0, 'bass', 2)
TAG_NUMBER = 7
A_TIME = 1.25
CHANNEL = 2
NUMBER = 60
VELOCITY = 100


class TestSenderEnds(unittest.TestCase):

    def test_the_sender_stops_every_note_when_the_trackers_end_of_the_pipe_closes(self):
        for driver in (sender_process.IMMEDIATE, sender_process.TIMESTAMPED):
            with self.subTest(driver=driver):
                self.check_the_sender_stops_when_the_pipe_closes(driver)

    def check_the_sender_stops_when_the_pipe_closes(self, driver):
        tracker_end, sender_end = multiprocessing.Pipe()
        # The process's own settings for garbage and urgency would reach the whole test run in a thread, so they are left out here.
        with mock.patch.object(PlaybackEngine, PlaybackEngine.close.__name__) as closed, \
                mock.patch.object(sender_process, sender_process.hold_garbage_back.__name__), mock.patch.object(sender_process, sender_process.ask_to_be_urgent.__name__):
            sender = threading.Thread(target=sender_process.run_sender, kwargs=dict(connection=sender_end, ports=[A_PORT], recording=True, driver=driver))
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



class TestDrivers(unittest.TestCase):
    """The driver chosen once as the sender starts: timestamped where CoreMIDI is, immediate elsewhere, each with its engine."""

    def test_the_timestamped_driver_is_the_default_where_coremidi_is(self):
        with mock.patch.object(coremidi, coremidi.is_available.__name__, return_value=True):
            self.assertEqual(sender_process.default_driver(), sender_process.TIMESTAMPED)

    def test_the_immediate_driver_is_the_default_elsewhere(self):
        with mock.patch.object(coremidi, coremidi.is_available.__name__, return_value=False):
            self.assertEqual(sender_process.default_driver(), sender_process.IMMEDIATE)

    def test_each_driver_sends_through_its_own_engine_and_records_what_it_would_send(self):
        timestamped = sender_process.engine_for(driver=sender_process.TIMESTAMPED, ports=[A_PORT], recording=True)
        immediate = sender_process.engine_for(driver=sender_process.IMMEDIATE, ports=[A_PORT], recording=True)
        self.assertIsInstance(timestamped, ScheduledPlaybackEngine)
        self.assertNotIsInstance(immediate, ScheduledPlaybackEngine)
        self.assertEqual(timestamped.recordings(), {A_PORT: []})
        self.assertEqual(immediate.recordings(), {A_PORT: []})


class TestRecords(unittest.TestCase):
    """Events cross the pipe as slim records, version first, every field the engine needs carried exactly."""

    def test_records_carry_each_events_time_place_bytes_and_tag(self):
        ports = [A_PORT, ANOTHER_PORT]
        places = {name: place for place, name in enumerate(ports)}
        tags = {A_TAG: TAG_NUMBER}
        events = [Playing(Rational(0), A_TIME, ANOTHER_PORT, CHANNEL, timeline.NOTE_ON, NUMBER, VELOCITY, A_TAG),
                  Playing(Rational(0), A_TIME, A_PORT, CHANNEL, timeline.PROGRAM_CHANGE, NUMBER, None, A_TAG)]
        records = sender_process.records_of(events=events, place_of_port=places.__getitem__, number_of_tag=tags.__getitem__)
        self.assertEqual(records[0], sender_process.RECORDS_VERSION)
        read = sender_process.events_of(records=records, ports=ports)
        self.assertEqual([(event.seconds, event.port, event.tag) for event in read], [(A_TIME, ANOTHER_PORT, TAG_NUMBER), (A_TIME, A_PORT, TAG_NUMBER)])
        self.assertEqual([event.data() for event in read], [event.data() for event in events])

    def test_a_plays_tag_keeps_its_number_from_sending_to_forgetting(self):
        sender = sender_process.RealtimeMIDISenderProcess(ports=[A_PORT])
        first = sender.tag_number(A_TAG)
        self.assertEqual(sender.tag_number(ANOTHER_TAG), first + 1)
        self.assertEqual(sender.tag_number(A_TAG), first)


if __name__ == '__main__':
    unittest.main()
