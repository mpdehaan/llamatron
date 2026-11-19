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

"""The rule that every file's opening imports are sorted: the libraries, a blank line, then the project's, each group by module, each line's names in order.

internal_tools/sort_imports.py says what the order is and rewrites a file that is out of it; these tests hold the tool to
the rule on small sources and hold every file of the project to the tool.
"""

import ast
import importlib.util
import pathlib
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / 'internal_tools' / 'sort_imports.py'
TOOL_NAME = 'sort_imports'
FILE_ENCODING = 'utf-8'
# A tool's name of the tests' own, imported by its file's name as the project's tools are.
A_TOOL = 'a_tool'


def load_tool():
    spec = importlib.util.spec_from_file_location(TOOL_NAME, TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestImportOrder(unittest.TestCase):

    def setUp(self):
        self.tool = load_tool()

    def check(self, *, source, expected):
        result = self.tool.sorted_source(source=textwrap.dedent(source).lstrip('\n'), tools={A_TOOL})
        self.assertEqual(result, textwrap.dedent(expected).lstrip('\n'))

    def test_every_file_of_the_project_has_its_opening_imports_in_order(self):
        tools = self.tool.tool_modules()
        found = []
        for path in self.tool.python_files():
            source = path.read_text(encoding=FILE_ENCODING)
            if self.tool.sorted_source(source=source, tools=tools) not in (source, None):
                found.append(self.tool.OUT_OF_ORDER.format(path=path.relative_to(ROOT).as_posix()))
        self.assertEqual(found, [])

    def test_every_file_with_imports_at_its_top_level_opens_with_some_so_that_none_is_passed_over(self):
        # A second string under the docstring once hid a file's imports from the sort.
        found = []
        for path in self.tool.python_files():
            tree = ast.parse(path.read_text(encoding=FILE_ENCODING))
            if not self.tool.opening_imports(tree) and any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body):
                found.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(found, [])

    def test_the_libraries_come_first_then_the_project_each_by_module_with_names_in_order_and_one_line_a_module(self):
        self.check(source="""
            \"\"\"A module.\"\"\"

            from llamatron.music.sound import Sound
            import sys
            from llamatron.music import sound as sound_values
            import a_tool
            from tests.support import ui_testing
            from llamatron.music import note, midi
            from dataclasses import field, dataclass
            import ast

            VALUE = 1
        """, expected="""
            \"\"\"A module.\"\"\"

            import ast
            from dataclasses import dataclass, field
            import sys

            import a_tool
            from llamatron.music import midi, note, sound as sound_values
            from llamatron.music.sound import Sound
            from tests.support import ui_testing

            VALUE = 1
        """)

    def test_an_import_after_other_code_stays_where_it_is(self):
        source = """
            import sys

            sys.path.insert(0, '.')
            import zebra
            import ast
        """
        self.check(source=source, expected=source)

    def test_a_comment_after_an_import_stays_on_its_line_and_a_comment_on_a_line_of_its_own_leaves_the_file_alone(self):
        self.check(source="""
            import sys  # first
            import ast
        """, expected="""
            import ast
            import sys  # first
        """)
        alone = textwrap.dedent("""
            import sys
            # Why the next import is here.
            import ast
        """).lstrip('\n')
        self.assertIsNone(self.tool.sorted_source(source=alone, tools={A_TOOL}))
