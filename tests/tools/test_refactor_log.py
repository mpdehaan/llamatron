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

"""internal_tools/refactor_log.py, one quick check of its main path: a new log gets its heading and the tables top and every step adds a row. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import importlib.util
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'refactor_log.py'
MODULE_NAME = 'refactor_log'
FILE_ENCODING = 'utf-8'
BODY_LINES = 4
OTHER_BODY_LINES = 7
A_STEP = 'a step'
ANOTHER_STEP = 'another step'
A_COLUMN = 'lines'


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

    def test_a_new_log_gets_its_heading_and_the_tables_top_and_every_step_adds_a_row(self):
        first = self.tool.with_row(text='', row={self.tool.STEP: A_STEP, A_COLUMN: BODY_LINES})
        self.assertTrue(first.startswith(self.tool.LOG_HEADING))
        second = self.tool.with_row(text=first, row={self.tool.STEP: ANOTHER_STEP, A_COLUMN: OTHER_BODY_LINES})
        rows = second[len(self.tool.LOG_HEADING):].splitlines()
        self.assertEqual(rows, [self.tool.table_line([self.tool.STEP, A_COLUMN]), self.tool.table_line([self.tool.RULE_CELL] * 2),
                                self.tool.table_line([A_STEP, BODY_LINES]), self.tool.table_line([ANOTHER_STEP, OTHER_BODY_LINES])])
