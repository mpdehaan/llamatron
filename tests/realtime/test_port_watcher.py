# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The MIDI ports listed through one thread that lives as long as the process (PortWatcher), the only thread CoreMIDI tells of ports
other programs make later: every listing from any thread is answered by it, the ports are listed once and again only when asked,
an answer always comes even when the listing fails, CoreMIDI lists them on macOS and python-rtmidi elsewhere, and on macOS a port
another program makes later is seen by listing again."""

import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

from llamatron.realtime.devices import ports
from llamatron.realtime.devices.ports import PortWatcher
from llamatron.realtime.sender_process import coremidi
from tests.support.coremidi_turns import CoreMidiTestCase

A_PORT = 'a port'
ANOTHER_PORT = 'another port'
HAS_LIBRARY = ports.has_midi_library.__name__
# A port another process makes once the first listing is taken, through a CoreMIDI destination of the tests' own, and how long the
# test looks for it. The other process holds the port until its input ends, which happens however the test's process ends, a crash
# included, so that a port is never left behind for the next run to find.
LATER_PORT = 'llamatron port made later'
MADE = 'made'
MAKES_A_PORT = f"import sys; from tests.realtime.test_coremidi import Destination; Destination({LATER_PORT!r}); print({MADE!r}, flush=True); sys.stdin.read()"
# How long the listing may take to show a port another program made: CoreMIDI tells other programs late on a loaded
# machine, as when the suite runs beside itself, by more than ten seconds at times, so the test looks again and again until
# a deadline well inside a class's two minutes.
WAIT_SECONDS = 45
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
            self.assertIs(ports.default_listing(), coremidi.destination_names)
        with mock.patch.object(coremidi, coremidi.is_available.__name__, return_value=False), mock.patch.object(ports, HAS_LIBRARY, return_value=True):
            self.assertIs(ports.default_listing(), ports.rtmidi_names)


@unittest.skipUnless(sys.platform == coremidi.MACOS, 'CoreMIDI is on macOS only')
class TestCoreMidiListing(CoreMidiTestCase):

    def test_a_port_another_program_makes_later_is_seen_by_listing_again(self):
        watcher = PortWatcher(listing=coremidi.destination_names)
        self.assertNotIn(LATER_PORT, watcher.names())
        other = subprocess.Popen([sys.executable, '-c', MAKES_A_PORT], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.addCleanup(other.wait)
        self.addCleanup(other.kill)
        self.assertEqual(other.stdout.readline().strip(), MADE)
        deadline = time.monotonic() + WAIT_SECONDS
        while time.monotonic() < deadline:
            if LATER_PORT in watcher.names_now():
                return
            threading.Event().wait(LOOK_SECONDS)
        self.fail(LATER_PORT)


if __name__ == '__main__':
    unittest.main()
