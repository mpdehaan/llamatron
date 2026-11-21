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

"""internal_tools/loudness_steps.py, one quick check of its main path: the step into a chorus is said as written and as made. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'loudness_steps.py'
MODULE_NAME = 'loudness_steps_report'
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_SEED = 11


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

if __name__ == '__main__':
    unittest.main()
