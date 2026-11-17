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

"""No function or method carries a type hint, on a parameter or on what it returns.

Python works every hint out when a module is imported, so hints on every function would slow
the program's start. A class that needs its fields declared, a dataclass or a named tuple, still
declares them in its body, which is not a hint on a function and is allowed.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKED_FOLDERS = ('src', 'tests', 'internal_tools')
PYTHON_FILES = '*.py'
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
HINTED = '{path}:{line}: {name} has a type hint'
LAMBDA_NAME = 'lambda'


def parameters_of(function):
    """Return every parameter a function declares, of every kind."""
    arguments = function.args
    extras = [argument for argument in (arguments.vararg, arguments.kwarg) if argument is not None]
    return [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, *extras]


def is_hinted(function):
    """Return whether a function hints a parameter or what it returns."""
    if getattr(function, 'returns', None) is not None:
        return True
    return any(parameter.annotation is not None for parameter in parameters_of(function))


def hinted_functions(path):
    """Return a line for each function of a file that carries a type hint."""
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        HINTED.format(path=path.relative_to(ROOT), line=node.lineno, name=getattr(node, 'name', LAMBDA_NAME))
        for node in ast.walk(tree) if isinstance(node, FUNCTIONS) and is_hinted(node)
    ]


class TestNoTypeHints(unittest.TestCase):

    def test_no_function_has_a_type_hint(self):
        found = []
        for folder in CHECKED_FOLDERS:
            for path in sorted((ROOT / folder).rglob(PYTHON_FILES)):
                found += hinted_functions(path)
        self.assertEqual(found, [])

    def test_a_hint_is_found(self):
        hinted = ast.parse('def double(number: int) -> int:\n    return number * 2\n').body[0]
        plain = ast.parse('def double(number):\n    return number * 2\n').body[0]
        self.assertTrue(is_hinted(hinted))
        self.assertFalse(is_hinted(plain))
