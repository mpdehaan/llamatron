# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""internal_tools/sort_ideas.py, one quick check of its main path: a file out of order is sorted in place. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest

from llamatron.support.safe_yaml import load_safely

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'sort_ideas.py'
MODULE_NAME = 'sort_ideas'
FILE_NAME = 'IDEAS.yml'
HEADER = '# Ideas\n#\n# What the file is.'
# Ideas of the tests' own.
FIRST = 'first'
SECOND = 'second'
PLAIN_TEXT = 'What the idea would mean.'


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_script()


def idea(*, title, priority, text=PLAIN_TEXT):
    return {TOOL.TITLE: title, TOOL.PRIORITY: priority, TOOL.TEXT: text}


def titles(ideas):
    return [each[TOOL.TITLE] for each in ideas]


class SortIdeasTest(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = pathlib.Path(folder.name) / FILE_NAME

    def write(self, ideas):
        self.path.write_text(TOOL.written(header=HEADER, ideas=ideas))

    def read(self):
        return load_safely(self.path.read_text())

    def run_tool(self, *arguments):
        """Run the tool on the test's file and return its exit code, saying nothing."""
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return TOOL.main(argv=list(arguments), paths=[self.path])


class TestSortingAFile(SortIdeasTest):

    def test_a_file_out_of_order_is_sorted_in_place(self):
        self.write([idea(title=SECOND, priority=TOOL.LOW), idea(title=FIRST, priority=TOOL.HIGH)])
        self.assertEqual(self.run_tool(), 0)
        self.assertEqual(titles(self.read()), [FIRST, SECOND])

if __name__ == '__main__':
    unittest.main()
