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

"""internal_tools/record_batch.py, one quick check of its main path: each take is a batch video through FluidSynth and the first failure stops the rest. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'internal_tools'))

from record_batch import record_all  # noqa: E402

SHORT = 'examples/short.yml'
MIDDLE = 'examples/middle.yml'
LONG = 'examples/long.yml'
PAIRED_MODE = 'plasma'
SUCCESS = 0
FAILURE = 1


class TestRecordAll(unittest.TestCase):

    def test_each_take_is_a_batch_video_through_fluidsynth_and_the_first_failure_stops_the_rest(self):
        asked = []

        def record(**named):
            asked.append(named)
            return FAILURE if named['path'] == MIDDLE else SUCCESS
        takes = [(SHORT, PAIRED_MODE, 3.0), (MIDDLE, PAIRED_MODE, 60.0), (LONG, PAIRED_MODE, 200.0)]
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            code = record_all(takes=takes, record=record, driver=None, max_seconds=None, audio_device=None, fluidsynth_output=None, window_id=None)
        self.assertEqual(code, FAILURE)
        self.assertEqual([named['path'] for named in asked], [SHORT, MIDDLE])
        self.assertTrue(all(named['batch'] and named['fluidsynth'] and named['go'] for named in asked))
        self.assertEqual(asked[0]['visualizer'], PAIRED_MODE)


if __name__ == '__main__':
    unittest.main()
