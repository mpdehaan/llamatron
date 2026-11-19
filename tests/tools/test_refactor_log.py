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

"""internal_tools/refactor_log.py measures the program's size and shape and keeps a row a step in the refactoring's log."""

import ast
import importlib.util
import pathlib
import tempfile
import textwrap
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'refactor_log.py'
MODULE_NAME = 'refactor_log'
FILE_ENCODING = 'utf-8'
# A program of the tests' own: a file at the top and a file in a folder, each a license header and some lines.
A_FOLDER = 'parts'
BODY_LINES = 4
OTHER_BODY_LINES = 7
A_STEP = 'a step'
ANOTHER_STEP = 'another step'
A_COLUMN = 'lines'
CLASSES_SOURCE = """
    class Base:
        def one(self): pass
        def two(self): pass

    class Largest(Base):
        def three(self): pass
"""
LARGEST = 'Largest'
METHODS_WITH_INHERITED = 3


def load_tool():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRefactorLog(unittest.TestCase):

    def setUp(self):
        self.tool = load_tool()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = pathlib.Path(folder.name)

    def write(self, *, path, lines):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(['# header'] * self.tool.HEADER_LINES + ['pass'] * lines) + '\n', encoding=FILE_ENCODING)

    def test_lines_are_counted_under_the_license_header_and_by_the_folder_straight_under(self):
        self.write(path=self.folder / 'top.py', lines=BODY_LINES)
        self.write(path=self.folder / A_FOLDER / 'deep' / 'part.py', lines=OTHER_BODY_LINES)
        self.assertEqual(self.tool.lines_in(self.folder), BODY_LINES + OTHER_BODY_LINES)
        self.assertEqual(self.tool.lines_by_folder(self.folder), {self.tool.TOP_FILES: BODY_LINES, A_FOLDER: OTHER_BODY_LINES})

    def test_a_classs_methods_are_counted_with_those_it_inherits(self):
        tree = ast.parse(textwrap.dedent(CLASSES_SOURCE))
        by_name = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        self.assertEqual(self.tool.methods_of(name=LARGEST, by_name=by_name), METHODS_WITH_INHERITED)

    def test_a_new_log_gets_its_heading_and_the_tables_top_and_every_step_adds_a_row(self):
        first = self.tool.with_row(text='', row={self.tool.STEP: A_STEP, A_COLUMN: BODY_LINES})
        self.assertTrue(first.startswith(self.tool.LOG_HEADING))
        second = self.tool.with_row(text=first, row={self.tool.STEP: ANOTHER_STEP, A_COLUMN: OTHER_BODY_LINES})
        rows = second[len(self.tool.LOG_HEADING):].splitlines()
        self.assertEqual(rows, [self.tool.table_line([self.tool.STEP, A_COLUMN]), self.tool.table_line([self.tool.RULE_CELL] * 2),
                                self.tool.table_line([A_STEP, BODY_LINES]), self.tool.table_line([ANOTHER_STEP, OTHER_BODY_LINES])])
