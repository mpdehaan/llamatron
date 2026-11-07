# llamatron: a Python language and framework for producing MIDI clips.
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

"""Runs pyflakes over every Python file in src/, test/ and tools/, as part of the test suite.

pyflakes finds unused imports, undefined names, unused variables and names defined twice, without
running the code. The suite fails on any of them, so an import that nothing uses can't be committed.
"""

import io
import os
import unittest
from pathlib import Path

from pyflakes import api, reporter

ROOT = Path(__file__).resolve().parents[1]
# The folders that hold Python: the program, its tests and the tools for working on it.
FOLDERS = ['src', 'test', 'tools']
MSG_PROBLEMS = 'pyflakes found {count} problem(s):\n{problems}'


class TestPyflakes(unittest.TestCase):

    def test_every_python_file_is_clean(self):
        warnings = io.StringIO()
        errors = io.StringIO()
        count = api.checkRecursive([os.path.join(ROOT, folder) for folder in FOLDERS], reporter.Reporter(warnings, errors))
        self.assertEqual(count, 0, MSG_PROBLEMS.format(count=count, problems=warnings.getvalue() + errors.getvalue()))
