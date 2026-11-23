# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The turns the test classes that open CoreMIDI take, so that one such class runs at a time however many classes the suite runs
side by side: CoreMIDI's server refused clients, and a listing read a destination another class had just taken away, when several
ran at once under load."""

import fcntl
import pathlib
import tempfile
import unittest

# One file for every checkout and run on the machine, since CoreMIDI's server is the machine's.
TURN_FILE = 'llamatron_coremidi_turn'


class CoreMidiTestCase(unittest.TestCase):
    """A test class that opens CoreMIDI: it waits for its turn before its first test and gives the turn up after its last."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        turn = open(pathlib.Path(tempfile.gettempdir()) / TURN_FILE, 'w')
        fcntl.flock(turn, fcntl.LOCK_EX)
        cls.addClassCleanup(turn.close)
