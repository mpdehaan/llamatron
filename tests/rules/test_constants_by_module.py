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

"""The rule that every constant is named through the module that defines it.

A module imports `labels` and writes `labels.MSG_SCALE_LABEL`, or `sound` and `sound.KIND`, never the name alone, so that
no file opens with a wall of names and every use says which module holds the constant. A class or a function keeps its
import. Nothing at all is imported by name from the strings package, from composition's limits and defaults, or from
MIDI's numbers. internal_tools/constants_by_module.py finds what breaks the rule, and rewrites it.
"""

import ast
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
FOLDERS = ('src', 'tests', 'internal_tools')
PYTHON_FILES = '*.py'
FILE_ENCODING = 'utf-8'
STRINGS_PACKAGE = 'llamatron.strings'
# The strings package's own modules import names from each other, which keeps them free of everything else.
STRINGS_FOLDER = ROOT / 'src' / 'llamatron' / 'strings'
CONSTANT_MODULES = ('llamatron.composition.limits', 'llamatron.composition.defaults', 'llamatron.music.midi')
FOUND = '{path}:{line} imports {names} from {module}'
TOOL = ROOT / 'internal_tools' / 'constants_by_module.py'
TOOL_NAME = 'constants_by_module'


def load_tool():
    spec = importlib.util.spec_from_file_location(TOOL_NAME, TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def names_imported(path):
    """Return a line for each import in a file that takes names out of a module of constants."""
    found = []
    tree = ast.parse(path.read_text(encoding=FILE_ENCODING))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if node.module.startswith(STRINGS_PACKAGE + '.') or node.module in CONSTANT_MODULES:
            names = ', '.join(alias.name for alias in node.names)
            found.append(FOUND.format(path=path.relative_to(ROOT).as_posix(), line=node.lineno, names=names, module=node.module))
    return found


class TestConstantsByModule(unittest.TestCase):

    def test_no_module_imports_a_name_from_a_module_of_constants(self):
        found = []
        for folder in FOLDERS:
            for path in sorted((ROOT / folder).rglob(PYTHON_FILES)):
                if STRINGS_FOLDER in path.parents:
                    continue
                found += names_imported(path)
        self.assertEqual(found, [])

    def test_an_import_of_a_name_is_found_and_an_import_of_the_module_is_not(self):
        self.assertTrue(names_imported(STRINGS_FOLDER / 'messages.py'))
        self.assertEqual(names_imported(pathlib.Path(__file__)), [])


if __name__ == '__main__':
    unittest.main()

    def test_no_module_imports_a_constant_by_name_from_any_module_of_the_project(self):
        tool = load_tool()
        project = tool.Project.read()
        found = []
        for name in sorted(project.modules):
            found += tool.find_names_imported(project=project, module=project.modules[name])
        self.assertEqual(found, [])
