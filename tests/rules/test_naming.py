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

"""Only composition/naming.py numbers a name, so that every name the tracker makes follows the one rule (.claude/UX.md, "Names the tracker makes")."""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / 'src' / 'llamatron'
PYTHON_FILES = '*.py'
# The module that makes every name, and the module that defines the constants it numbers with.
NAMING_MODULE = SOURCE / 'composition' / 'naming.py'
STRINGS_MODULE = SOURCE / 'strings' / 'names.py'
# What a numbered name is made with, which nothing else may import.
NUMBERING_CONSTANTS = ('MSG_NUMBERED_NAME', 'MSG_NUMBER_JOINT')
MSG_NUMBERS_NAMES = 'these number a name themselves and should call composition/naming.py: {places}'
PLACE = '{path} imports {name}'
LIST_SEPARATOR = ', '


def imported_names(path):
    """Return every name a module imports from another."""
    tree = ast.parse(path.read_text())
    return [alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names]


def numbering_imports():
    """Return each place in the program, outside the naming module, that imports what a name is numbered with."""
    places = []
    for path in sorted(SOURCE.rglob(PYTHON_FILES)):
        if path in (NAMING_MODULE, STRINGS_MODULE):
            continue
        for name in imported_names(path):
            if name in NUMBERING_CONSTANTS:
                places.append(PLACE.format(path=path.relative_to(ROOT), name=name))
    return places


class TestOnlyTheNamingModuleNumbersNames(unittest.TestCase):

    def test_nothing_else_imports_what_a_name_is_numbered_with(self):
        places = numbering_imports()
        self.assertEqual(places, [], MSG_NUMBERS_NAMES.format(places=LIST_SEPARATOR.join(places)))

    def test_the_naming_module_imports_it(self):
        for name in NUMBERING_CONSTANTS:
            self.assertIn(name, imported_names(NAMING_MODULE))


if __name__ == '__main__':
    unittest.main()
