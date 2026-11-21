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


"""internal_tools/coremidi_timing.py's parts that need no MIDI: the grid of sixteenths, its events, and the percentiles of the report. Nothing is sent."""

import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'coremidi_timing.py'
MODULE_NAME = 'coremidi_timing'
SECONDS = 2.0
PORT = 'a port'
ZERO = 10.0
ORDERED = [0.1, 0.2, 0.3, 0.4]
HALF = 50
EVERYTHING = 100


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestCoreMidiTiming(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()

    def test_the_grid_is_sixteenths_at_the_tools_tempo(self):
        times = self.tool.note_times(SECONDS)
        step = self.tool.SECONDS_PER_MINUTE / self.tool.TEMPO / self.tool.SIXTEENTHS_PER_BEAT
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[1], step)
        self.assertEqual(len(times), int(SECONDS / step))

    def test_each_note_is_a_note_on_and_a_note_off_after_zero(self):
        events = self.tool.events_of(times=[0.0, 1.0], port=PORT, zero=ZERO)
        self.assertEqual([event.kind for event in events], [self.tool.NOTE_ON, self.tool.NOTE_OFF] * 2)
        self.assertEqual(events[0].seconds, ZERO)
        self.assertEqual(events[1].seconds, ZERO + self.tool.GATE_SECONDS)
        self.assertEqual({event.port for event in events}, {PORT})

    def test_a_percentile_is_read_from_the_ordered_errors(self):
        self.assertEqual(self.tool.percentile(ordered=ORDERED, percent=HALF), ORDERED[2])
        self.assertEqual(self.tool.percentile(ordered=ORDERED, percent=EVERYTHING), ORDERED[-1])


if __name__ == '__main__':
    unittest.main()
