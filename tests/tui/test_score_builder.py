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
"""Scores built off the screen's thread (tui/score_builder.py): at once for the tests, in a thread otherwise, a song's problem kept
in place of a score, and a newer request replacing one not yet started."""

import threading
import unittest

from llamatron.composition.song_file_error import SongFileError
from llamatron.tui.score_builder import ScoreBuilder

A_KEY = 'first'
ANOTHER_KEY = 'second'
A_SCORE = 'a score'
ANOTHER_SCORE = 'another score'
PROBLEM = 'a song that cannot be played'
WAIT_SECONDS = 5


def wait_for(*, builder, key):
    """Wait until a request is built, and return what it came to."""
    done = threading.Event()
    for _ in range(WAIT_SECONDS * 100):
        built = builder.built(key)
        if built is not None:
            return built
        done.wait(0.01)
    return None


class TestScoreBuilder(unittest.TestCase):

    def test_at_once_it_builds_in_the_request(self):
        builder = ScoreBuilder(at_once=True)
        builder.request(key=A_KEY, build=lambda earlier: A_SCORE)
        self.assertEqual(builder.built(A_KEY).score, A_SCORE)
        self.assertIsNone(builder.built(ANOTHER_KEY))

    def test_in_a_thread_it_builds_and_keeps_a_problem_in_place_of_a_score(self):
        builder = ScoreBuilder()
        builder.request(key=A_KEY, build=lambda earlier: A_SCORE)
        self.assertEqual(wait_for(builder=builder, key=A_KEY).score, A_SCORE)

        def unplayable(earlier):
            raise SongFileError(PROBLEM)
        builder.request(key=ANOTHER_KEY, build=unplayable)
        self.assertEqual(str(wait_for(builder=builder, key=ANOTHER_KEY).problem), PROBLEM)

    def test_a_newer_request_replaces_one_not_yet_started(self):
        builder = ScoreBuilder()
        started = threading.Event()
        release = threading.Event()
        built = []

        def slow(earlier):
            started.set()
            release.wait(WAIT_SECONDS)
            return A_SCORE
        builder.request(key=A_KEY, build=slow)
        started.wait(WAIT_SECONDS)
        builder.request(key=ANOTHER_KEY, build=lambda earlier: built.append(A_KEY) or A_SCORE)
        builder.request(key=ANOTHER_KEY, build=lambda earlier: ANOTHER_SCORE)
        release.set()
        self.assertEqual(wait_for(builder=builder, key=ANOTHER_KEY).score, ANOTHER_SCORE)
        self.assertEqual(built, [])

    def test_each_build_is_handed_the_last_score_made_and_a_problem_leaves_it(self):
        builder = ScoreBuilder(at_once=True)
        handed = []

        def unplayable(earlier):
            handed.append(earlier)
            raise SongFileError(PROBLEM)
        builder.request(key=A_KEY, build=lambda earlier: handed.append(earlier) or A_SCORE)
        builder.request(key=ANOTHER_KEY, build=unplayable)
        builder.request(key=A_KEY, build=lambda earlier: handed.append(earlier) or ANOTHER_SCORE)
        self.assertEqual(handed, [None, A_SCORE, A_SCORE])


if __name__ == '__main__':
    unittest.main()
