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
"""The diagrams in docs/ARCHITECTURE.md and docs/GETTING_STARTED.md match the code they're generated from.

internal_tools/make_diagrams.py draws the packages and the tracker's screens from the source, so a change
that adds a package, an import between packages or a screen moves a diagram. This runs its check,
which fails until the script is run again, so the pictures in the documents can't go stale.
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'internal_tools' / 'make_diagrams.py'
CHECK_OPTION = '--check'
SUCCESS = 0
SECONDS_ALLOWED = 120


class TestDiagrams(unittest.TestCase):

    def test_the_diagrams_in_the_documents_are_current(self):
        result = subprocess.run([sys.executable, str(SCRIPT), CHECK_OPTION], capture_output=True, text=True, cwd=ROOT, timeout=SECONDS_ALLOWED)
        self.assertEqual(result.returncode, SUCCESS, result.stdout + result.stderr)
