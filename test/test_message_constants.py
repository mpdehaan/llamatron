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

"""Every ERR_, MSG_ and HELP_ constant lives in the strings package, each in the module for how the text is used, and each is used.

strings/errors.py holds every ERR_ constant, strings/help.py every HELP_ constant, strings/reprs.py the REPR_ text a class
prints itself with, and the package's other modules the MSG_ constants. The package holds all of the program's visible text, so that wording can be read in one place and
a string in a test can't be mistaken for a data key. Nothing else may define a constant with either
prefix outside the package, the modules' own constants all carry their module's prefix (their classes, like What and Crumb, group shared words
without it), a name never repeats its prefix's word (no ERR_ERROR_LINE), and a constant nothing uses is removed. The
modules import only names from the file format, the keys and each other, so that any other module can import them.
"""

import ast
import os
import re
import unittest

import llamatron
from llamatron import strings
from llamatron.strings import errors, help, reprs

SOURCE_FOLDER = os.path.dirname(llamatron.__file__)
TEST_FOLDER = os.path.dirname(os.path.abspath(__file__))
TOOLS_FOLDER = os.path.join(os.path.dirname(TEST_FOLDER), 'internal_tools')
PYTHON_SUFFIX = '.py'
ERROR_PREFIX = 'ERR_'
MESSAGE_PREFIX = 'MSG_'
HELP_PREFIX = 'HELP_'
REPR_PREFIX = 'REPR_'
PREFIXES = (ERROR_PREFIX, MESSAGE_PREFIX, HELP_PREFIX, REPR_PREFIX)
STRINGS_FOLDER = os.path.dirname(strings.__file__)
PACKAGE_FILE = '__init__.py'
# The modules whose constants have a prefix other than MSG_.
OTHER_PREFIXES = {errors.__file__: ERROR_PREFIX, help.__file__: HELP_PREFIX, reprs.__file__: REPR_PREFIX}
# The modules a strings module may import from: the names the file format and the keys define, and the package's own modules.
ALLOWED_IMPORTS = ('llamatron.composition.file_format', 'llamatron.tui.keys', 'llamatron.strings.')
# Names that are allowed to be used by a module's own code alone, since nothing else can see them.
PRIVATE_PREFIX = '_'
# Words a constant's name must not repeat after its prefix, like ERR_ERROR_LINE, MSG_MESSAGE or HELP_HELP_SONG. A message
# about an error belongs in strings/errors.py, so the message words and the error words are redundant in both of those modules.
MESSAGE_WORDS = ('ERR', 'ERROR', 'ERRORS', 'MSG', 'MESSAGE', 'MESSAGES')
REDUNDANT_WORDS = {ERROR_PREFIX: MESSAGE_WORDS, MESSAGE_PREFIX: MESSAGE_WORDS, HELP_PREFIX: ('HELP',), REPR_PREFIX: ('REPR',)}
# A comment at the start of a line that opens a group of constants by naming the module that uses them, and each module path such a comment names.
GROUP_COMMENT = re.compile(r'^# [\w/]+\.py')
MODULE_PATH = re.compile(r'[\w/]+\.py')


def python_files(folder):
    for root, _, names in os.walk(folder):
        for name in names:
            if name.endswith(PYTHON_SUFFIX):
                yield os.path.join(root, name)


def source_of(path):
    with open(path) as file:
        return file.read()


def assigned_names(nodes):
    return [target.id for node in nodes if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)]


def defined_constants(path):
    """Return the names assigned at the top of a module and in its classes."""
    tree = ast.parse(source_of(path))
    names = assigned_names(tree.body)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names += assigned_names(node.body)
    return names


def module_constants(path):
    """Return only the names assigned at the top of a module, outside its classes."""
    return assigned_names(ast.parse(source_of(path)).body)


def string_modules():
    """Return the path of every module of the strings package that holds constants."""
    return sorted(os.path.join(STRINGS_FOLDER, name) for name in os.listdir(STRINGS_FOLDER) if name.endswith(PYTHON_SUFFIX) and name != PACKAGE_FILE)


def own_prefixes():
    """Return each strings module's path with the prefix its constants carry."""
    return {path: OTHER_PREFIXES.get(path, MESSAGE_PREFIX) for path in string_modules()}


OWN_PREFIX = own_prefixes()


def imported_modules(path):
    """Return the modules a source file imports, by their dotted names."""
    tree = ast.parse(source_of(path))
    modules = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
    return modules


def prefixed(names):
    return [name for name in names if name.startswith(PREFIXES)]


class TestMessageConstants(unittest.TestCase):

    def test_only_the_strings_package_defines_prefixed_constants(self):
        for path in python_files(SOURCE_FOLDER):
            if path in OWN_PREFIX:
                continue
            with self.subTest(path=path):
                self.assertEqual(prefixed(defined_constants(path)), [])

    def test_each_module_holds_only_its_own_prefix(self):
        for path, prefix in OWN_PREFIX.items():
            with self.subTest(path=path):
                wrong = [name for name in module_constants(path) if not name.startswith(prefix) and not name.startswith(PRIVATE_PREFIX)]
                self.assertEqual(wrong, [])

    def test_no_name_repeats_its_prefix(self):
        for path, prefix in OWN_PREFIX.items():
            for name in module_constants(path):
                with self.subTest(name=name):
                    words = name[len(prefix):].split(PRIVATE_PREFIX)
                    self.assertFalse(any(word in REDUNDANT_WORDS[prefix] for word in words))

    def test_every_constant_is_used(self):
        others = []
        for folder in (SOURCE_FOLDER, TEST_FOLDER, TOOLS_FOLDER):
            others += [source_of(path) for path in python_files(folder) if path not in OWN_PREFIX]
        everything = '\n'.join(others)
        for path, prefix in OWN_PREFIX.items():
            own = source_of(path)
            for name in defined_constants(path):
                if not name.startswith(prefix):
                    continue
                with self.subTest(name=name):
                    used_elsewhere = re.search(rf'\b{name}\b', everything)
                    used_at_home = len(re.findall(rf'\b{name}\b', own)) > 1
                    self.assertTrue(used_elsewhere or used_at_home)

    def test_every_group_comment_names_a_module_that_exists(self):
        """The constants are grouped under a comment naming the module that uses them, and a module that moved takes its comment with it."""
        for path in string_modules():
            for line in source_of(path).splitlines():
                if not GROUP_COMMENT.match(line):
                    continue
                for module in MODULE_PATH.findall(line):
                    with self.subTest(file=os.path.basename(path), comment=line):
                        self.assertTrue(os.path.exists(os.path.join(SOURCE_FOLDER, module)), module)

    def test_the_string_modules_import_only_names(self):
        """A strings module that imported a module with code of its own could no longer be imported by that module."""
        for path in string_modules():
            for module in imported_modules(path):
                with self.subTest(file=os.path.basename(path), module=module):
                    self.assertTrue(module.startswith(ALLOWED_IMPORTS), module)
