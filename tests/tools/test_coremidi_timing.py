# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""internal_tools/coremidi_timing.py, one quick check of its main path: each note is a note on and a note off after zero. A tool fails loudly when it is run, so one check is enough (.claude/rules/TESTING.md)."""

import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'coremidi_timing.py'
MODULE_NAME = 'coremidi_timing'
PORT = 'a port'
ZERO = 10.0


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCoreMidiTiming(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()

    def test_each_note_is_a_note_on_and_a_note_off_after_zero(self):
        events = self.tool.events_of(times=[0.0, 1.0], port=PORT, zero=ZERO)
        self.assertEqual([event.kind for event in events], [self.tool.NOTE_ON, self.tool.NOTE_OFF] * 2)
        self.assertEqual(events[0].seconds, ZERO)
        self.assertEqual(events[1].seconds, ZERO + self.tool.GATE_SECONDS)
        self.assertEqual({event.port for event in events}, {PORT})

if __name__ == '__main__':
    unittest.main()
