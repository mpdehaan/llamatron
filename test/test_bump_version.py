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

"""internal_tools/bump_version.py raises the version for a commit that changes the program, and tells internal_tools/check_before_commit.sh when a commit lacks its bump."""

import datetime
import importlib.util
import pathlib
import unittest

from llamatron.support import version

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'bump_version.py'
MODULE_NAME = 'bump_version'
# A moment to build at, and how the version module writes its date and time.
NOW = datetime.datetime(2031, 2, 3, 4, 5)
NOW_DATE = '2031-02-03'
NOW_TIME = '04:05'
A_SOURCE_FILE = 'src/llamatron/tui/keys.py'
A_TEST_FILE = 'test/test_note.py'
A_DOCUMENT = 'GUIDE.md'
A_TEMPLATE_IN_SOURCE = 'src/llamatron/templates/live12.als'
# What `git diff --cached --unified=0` shows of the version module when a commit bumps it, and when it only moves the build time.
BUMP_DIFF = "-VERSION = '1.0.1'\n+VERSION = '1.0.2'\n"
TIME_ONLY_DIFF = "-BUILD_TIME = '01:00'\n+BUILD_TIME = '02:00'\n"
NO_DIFF = ''
VERSION_LINE = "VERSION = '{version}'"
NO_VERSION_TEXT = "BUILD_DATE = '2031-01-01'\nBUILD_TIME = '00:00'\n"


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestBumpVersion(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.text = pathlib.Path(version.__file__).read_text()

    def test_a_bump_raises_the_last_number_and_sets_the_build_date_and_time(self):
        first, second, last = version.version_numbers(version.VERSION)
        text = self.tool.bumped(text=self.text, now=NOW)
        self.assertEqual(self.tool.version_in(text), version.VERSION_SEPARATOR.join(str(number) for number in (first, second, last + 1)))
        self.assertIn(self.tool.BUILD_DATE_LINE.format(date=NOW_DATE), text)
        self.assertIn(self.tool.BUILD_TIME_LINE.format(time=NOW_TIME), text)
        # Nothing else in the module changes.
        self.assertEqual(len(text.splitlines()), len(self.text.splitlines()))

    def test_a_bump_counts_in_whole_numbers_never_decimals(self):
        text = self.text.replace(VERSION_LINE.format(version=version.VERSION), VERSION_LINE.format(version='1.0.9'))
        self.assertEqual(self.tool.version_in(self.tool.bumped(text=text, now=NOW)), '1.0.10')

    def test_a_bump_that_cannot_find_its_line_stops_rather_than_changing_nothing(self):
        with self.assertRaises(ValueError):
            self.tool.bumped(text=NO_VERSION_TEXT, now=NOW)
        twice = self.text + VERSION_LINE.format(version=version.VERSION) + '\n'
        with self.assertRaises(ValueError):
            self.tool.bumped(text=twice, now=NOW)

    def test_a_commit_that_changes_the_programs_python_needs_a_bump(self):
        self.assertTrue(self.tool.is_missing_a_bump(staged_paths=[A_SOURCE_FILE], version_diff=NO_DIFF))
        self.assertTrue(self.tool.is_missing_a_bump(staged_paths=[A_DOCUMENT, A_SOURCE_FILE], version_diff=TIME_ONLY_DIFF))
        self.assertFalse(self.tool.is_missing_a_bump(staged_paths=[A_SOURCE_FILE], version_diff=BUMP_DIFF))

    def test_a_commit_of_tests_documents_or_other_files_needs_none(self):
        for path in (A_TEST_FILE, A_DOCUMENT, A_TEMPLATE_IN_SOURCE):
            with self.subTest(path=path):
                self.assertFalse(self.tool.is_missing_a_bump(staged_paths=[path], version_diff=NO_DIFF))
        self.assertFalse(self.tool.is_missing_a_bump(staged_paths=[], version_diff=NO_DIFF))
