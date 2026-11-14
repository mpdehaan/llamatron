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

"""Tests internal_tools/record_batch.py, which records a batch video of every example: the pairings, the order, the limit, the mode a new set gets, and stopping at the first take that fails. No take is recorded."""

import contextlib
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'internal_tools'))

from record_batch import MOST_VARIABLE, has_a_video, least_used, mode_for, most_takes, pairings, plan, record_all, recorder  # noqa: E402
from llamatron.composition.setlist import file_stem  # noqa: E402
from llamatron.visualizers.modes import mode_options  # noqa: E402
from llamatron.support.example_sets import example_sets  # noqa: E402

SHORT = 'examples/short.yml'
MIDDLE = 'examples/middle.yml'
LONG = 'examples/long.yml'
LOOPING = 'examples/looping.yml'
LENGTHS = {SHORT: 3.0, MIDDLE: 60.0, LONG: 200.0, LOOPING: None}
PAIRED_MODE = 'plasma'
TWO = '2'
NOT_A_NUMBER = 'two'
SUCCESS = 0
FAILURE = 1
SET_SUFFIX = '.yml'
THE_MODE_OF_MODES = 'cycle'


class TestPairings(unittest.TestCase):

    def test_every_pairing_names_an_example_and_a_mode(self):
        for stem, mode in pairings().items():
            with self.subTest(stem=stem):
                self.assertIn(mode, mode_options())
                self.assertIn(stem, [file_stem(path) for path in example_sets()])

    def test_a_set_with_no_pairing_gets_the_mode_used_least_and_counts_it(self):
        paired = {file_stem(SHORT): PAIRED_MODE}
        first = mode_for(stem=file_stem(MIDDLE), paired=paired)
        self.assertNotEqual(first, PAIRED_MODE)
        self.assertEqual(paired[file_stem(MIDDLE)], first)
        self.assertNotEqual(mode_for(stem=file_stem(LONG), paired=paired), first)
        self.assertNotEqual(least_used({}), THE_MODE_OF_MODES)


class TestPlan(unittest.TestCase):

    def test_the_takes_go_shortest_first_leaving_out_a_set_whose_length_is_unknown(self):
        with contextlib.redirect_stderr(io.StringIO()):
            takes = plan(paths=[LONG, LOOPING, SHORT, MIDDLE], paired={}, most=None, lengths=LENGTHS.get)
        self.assertEqual([path for path, _, _ in takes], [SHORT, MIDDLE, LONG])

    def test_the_limit_keeps_the_shortest(self):
        with contextlib.redirect_stderr(io.StringIO()):
            takes = plan(paths=[LONG, SHORT, MIDDLE], paired={}, most=most_takes({MOST_VARIABLE: TWO}), lengths=LENGTHS.get)
        self.assertEqual([path for path, _, _ in takes], [SHORT, MIDDLE])

    def test_a_set_has_a_video_when_any_take_of_it_is_recorded_whatever_its_mode(self):
        shared = recorder()
        with tempfile.TemporaryDirectory() as folder:
            original = shared.RECORDINGS
            shared.RECORDINGS = folder
            try:
                self.assertFalse(has_a_video(path=SHORT, recorder=shared))
                for video in (os.path.join(folder, file_stem(SHORT) + shared.VIDEO_SUFFIX), shared.batch_video_path(path=SHORT, mode=PAIRED_MODE)):
                    with self.subTest(video=video):
                        with open(video, 'w'):
                            pass
                        self.assertTrue(has_a_video(path=SHORT, recorder=shared))
                        self.assertFalse(has_a_video(path=MIDDLE, recorder=shared))
                        os.unlink(video)
            finally:
                shared.RECORDINGS = original

    def test_a_set_recorded_already_is_left_out_before_the_limit_counts(self):
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            takes = plan(paths=[LONG, SHORT, MIDDLE], paired={}, most=1, lengths=LENGTHS.get, recorded=lambda path, mode: path == SHORT)
        self.assertEqual([path for path, _, _ in takes], [MIDDLE])

    def test_the_limit_is_every_take_unless_set_and_a_whole_number(self):
        self.assertIsNone(most_takes({}))
        with self.assertRaises(ValueError):
            most_takes({MOST_VARIABLE: NOT_A_NUMBER})


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
