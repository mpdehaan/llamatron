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
"""Every class of the program has a docstring saying what it is: a class is a thing a reader would name, and its docstring is where
it is named."""

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKED_FOLDERS = ('src',)
PYTHON_FILES = '*.py'
UNSAID = '{path}:{line}: class {name} has no docstring saying what it is'


def classes_unsaid(path):
    """Return a line for each class of a file with no docstring."""
    tree = ast.parse(path.read_text(), filename=str(path))
    return [UNSAID.format(path=path.relative_to(ROOT), line=node.lineno, name=node.name) for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None]


def checked_files():
    """Return every Python file the rule holds, in order."""
    return [path for folder in CHECKED_FOLDERS for path in sorted((ROOT / folder).rglob(PYTHON_FILES))]


class TestClassDocstrings(unittest.TestCase):

    def test_every_class_says_what_it_is(self):
        found = [line for path in checked_files() for line in classes_unsaid(path)]
        self.assertEqual(found, [], msg='\n'.join(found))


if __name__ == '__main__':
    unittest.main()
