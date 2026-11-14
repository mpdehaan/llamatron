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

"""internal_tools/sort_ideas.py keeps the ideas files sorted by priority, 1 first, without undoing the order within a priority."""

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
CHECK = '--check'
HEADER = '# Ideas\n#\n# What the file is.'
# Ideas of the tests' own.
FIRST = 'first'
SECOND = 'second'
THIRD = 'third'
UNRANKED_IDEA = 'never ranked'
# A title and a text that YAML would read wrongly were they not written with care: a colon, quotes, a list mark, a blank line.
AWKWARD_TITLE = 'A "quoted" title: with a colon'
AWKWARD_TEXT = 'One line: with a colon.\n\n- a list mark\n  an indented line\n### A heading'
PLAIN_TEXT = 'What the idea would mean.'
NOT_A_NUMBER = 'high'


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


class TestPriorities(unittest.TestCase):
    """The user's words as numbers: 1 is the highest."""

    def test_high_is_one_medium_five_low_ten_and_unranked_under_them_all(self):
        self.assertEqual((TOOL.HIGH, TOOL.MEDIUM, TOOL.LOW), (1, 5, 10))
        self.assertGreater(TOOL.UNRANKED, TOOL.LOW)

    def test_the_lowest_number_comes_first(self):
        ideas = [idea(title=THIRD, priority=TOOL.LOW), idea(title=UNRANKED_IDEA, priority=TOOL.UNRANKED), idea(title=FIRST, priority=TOOL.HIGH), idea(title=SECOND, priority=TOOL.MEDIUM)]
        self.assertEqual(titles(TOOL.in_order(ideas)), [FIRST, SECOND, THIRD, UNRANKED_IDEA])

    def test_ideas_of_one_priority_keep_the_order_they_have(self):
        ideas = [idea(title=THIRD, priority=TOOL.MEDIUM), idea(title=FIRST, priority=TOOL.MEDIUM), idea(title=SECOND, priority=TOOL.HIGH)]
        self.assertEqual(titles(TOOL.in_order(ideas)), [SECOND, THIRD, FIRST])


class TestSortingAFile(SortIdeasTest):

    def test_a_file_out_of_order_is_sorted_in_place(self):
        self.write([idea(title=SECOND, priority=TOOL.LOW), idea(title=FIRST, priority=TOOL.HIGH)])
        self.assertEqual(self.run_tool(), 0)
        self.assertEqual(titles(self.read()), [FIRST, SECOND])

    def test_a_file_in_order_is_left_as_it_is(self):
        self.write([idea(title=FIRST, priority=TOOL.HIGH), idea(title=SECOND, priority=TOOL.LOW)])
        before = self.path.read_text()
        self.assertEqual(self.run_tool(), 0)
        self.assertEqual(self.path.read_text(), before)

    def test_the_header_is_kept(self):
        self.write([idea(title=SECOND, priority=TOOL.LOW), idea(title=FIRST, priority=TOOL.HIGH)])
        self.run_tool()
        self.assertTrue(self.path.read_text().startswith(HEADER))

    def test_a_title_and_a_text_read_back_as_written(self):
        self.write([idea(title=SECOND, priority=TOOL.LOW), idea(title=AWKWARD_TITLE, priority=TOOL.HIGH, text=AWKWARD_TEXT)])
        self.run_tool()
        first = self.read()[0]
        self.assertEqual(first[TOOL.TITLE], AWKWARD_TITLE)
        self.assertEqual(first[TOOL.TEXT].rstrip(), AWKWARD_TEXT)

    def test_sorting_twice_changes_nothing_more(self):
        self.write([idea(title=SECOND, priority=TOOL.LOW), idea(title=FIRST, priority=TOOL.HIGH)])
        self.run_tool()
        once = self.path.read_text()
        self.run_tool()
        self.assertEqual(self.path.read_text(), once)


class TestChecking(SortIdeasTest):

    def test_check_fails_on_a_file_out_of_order_and_changes_nothing(self):
        self.write([idea(title=SECOND, priority=TOOL.LOW), idea(title=FIRST, priority=TOOL.HIGH)])
        before = self.path.read_text()
        self.assertEqual(self.run_tool(CHECK), 1)
        self.assertEqual(self.path.read_text(), before)

    def test_check_passes_on_a_file_in_order(self):
        self.write([idea(title=FIRST, priority=TOOL.HIGH), idea(title=SECOND, priority=TOOL.LOW)])
        self.assertEqual(self.run_tool(CHECK), 0)

    def test_a_priority_that_is_not_a_number_is_refused_and_the_file_left_alone(self):
        self.write([idea(title=FIRST, priority=NOT_A_NUMBER)])
        before = self.path.read_text()
        self.assertEqual(self.run_tool(), 1)
        self.assertEqual(self.path.read_text(), before)


class TestTheIdeasFiles(unittest.TestCase):
    """The repository's own ideas files are lists of ideas. Their order isn't held here: the user edits priorities by hand, and
    Claude sorts the files when it finds them out of order, so a hand edit never fails the suite."""

    def test_each_is_a_list_of_ideas(self):
        for path in TOOL.IDEAS_FILES:
            with self.subTest(path=path):
                text = path.read_text()
                self.assertTrue(TOOL.ideas_of(text=text, path=path))


if __name__ == '__main__':
    unittest.main()
