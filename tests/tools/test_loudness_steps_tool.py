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

"""internal_tools/loudness_steps.py says how big the step in loudness is into the first chorus of what the song wizard makes."""

import contextlib
import importlib.util
import io
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'loudness_steps.py'
MODULE_NAME = 'loudness_steps_report'
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_SUBGENRE_WITHOUT_A_CHORUS = 'rock and roll'
NOT_A_GENRE = 'polka'
A_SEED = 11
NO_FAILURE = 0
A_FAILURE = 1


def tool():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestLoudnessSteps(unittest.TestCase):

    def test_the_step_into_a_chorus_is_said_as_written_and_as_made(self):
        before, written, made = tool().chorus_step(genre=A_GENRE, subgenre=A_SUBGENRE, seed=A_SEED)
        self.assertTrue(before)
        self.assertLess(made, written)

    def test_a_song_with_no_chorus_has_no_step(self):
        self.assertIsNone(tool().chorus_step(genre=A_GENRE, subgenre=A_SUBGENRE_WITHOUT_A_CHORUS, seed=A_SEED))

    def test_a_genre_is_reported_a_line_for_each_subgenre_with_a_chorus(self):
        module = tool()
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.assertEqual(module.main(arguments=[A_GENRE]), NO_FAILURE)
        lines = printed.getvalue().splitlines()
        self.assertTrue(any(A_SUBGENRE in line for line in lines))
        self.assertFalse(any(A_SUBGENRE_WITHOUT_A_CHORUS in line for line in lines))

    def test_a_genre_that_does_not_exist_is_refused(self):
        refused = io.StringIO()
        with contextlib.redirect_stderr(refused):
            self.assertEqual(tool().main(arguments=[NOT_A_GENRE]), A_FAILURE)
        self.assertIn(NOT_A_GENRE, refused.getvalue())


if __name__ == '__main__':
    unittest.main()
