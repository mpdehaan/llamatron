# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The diagrams in docs/ARCHITECTURE.md and docs/GETTING_STARTED.md match the code they're generated from.

internal_tools/make_diagrams.py draws the packages and the tracker's screens from the source, so a change
that adds a package, an import between packages or a screen moves a diagram. This runs its check,
which fails until the script is run again, so the pictures in the documents can't go stale.
"""

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'internal_tools' / 'make_diagrams.py'
CHECK_OPTION = '--check'
SUCCESS = 0
SECONDS_ALLOWED = 120


class TestDiagrams(unittest.TestCase):

    def test_the_diagrams_in_the_documents_are_current(self):
        result = subprocess.run([sys.executable, str(SCRIPT), CHECK_OPTION], capture_output=True, text=True, cwd=ROOT, timeout=SECONDS_ALLOWED)
        self.assertEqual(result.returncode, SUCCESS, result.stdout + result.stderr)
