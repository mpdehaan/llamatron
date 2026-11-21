# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Runs pyflakes over every Python file in src/, test/ and internal_tools/, as part of the test suite.

pyflakes finds unused imports, undefined names, unused variables and names defined twice, without
running the code. The suite fails on any of them, so an import that nothing uses can't be committed.
"""

import io
import os
from pathlib import Path
from pyflakes import api, reporter
import unittest

ROOT = Path(__file__).resolve().parents[2]
# The folders that hold Python: the program, its tests and the tools for working on it.
FOLDERS = ['src', 'tests', 'internal_tools']
MSG_PROBLEMS = 'pyflakes found {count} problem(s):\n{problems}'


class TestPyflakes(unittest.TestCase):

    def test_every_python_file_is_clean(self):
        warnings = io.StringIO()
        errors = io.StringIO()
        count = api.checkRecursive([os.path.join(ROOT, folder) for folder in FOLDERS], reporter.Reporter(warnings, errors))
        self.assertEqual(count, 0, MSG_PROBLEMS.format(count=count, problems=warnings.getvalue() + errors.getvalue()))
