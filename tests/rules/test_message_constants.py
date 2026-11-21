# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every ERR_, MSG_ and HELP_ constant lives in the strings package, each in the module for how the text is used, and each is used.

A generator plugin is the one exception: its own words live in its folder, in strings.py, so that a plugin written elsewhere
touches no other file, and that module may hold constants of any prefix. user_strings/errors.py holds every ERR_ constant, user_strings/help.py every HELP_ constant, user_strings/reprs.py the REPR_ text a class
prints itself with, and the package's other modules the MSG_ constants. The package holds all of the program's visible text, so that wording can be read in one place and
a string in a test can't be mistaken for a data key. Nothing else may define a constant with either
prefix outside the package, no module defines a name twice, since the second would quietly replace the first, and a constant
nothing uses is removed. The
modules import only names from the file format, the keys and each other, so that any other module can import them.
"""

import ast
import collections
import os
import pathlib
import re
import unittest

import llamatron
from llamatron import user_strings
from llamatron.engine import generators as generator_package
from llamatron.model.schema import defaults, limits
from llamatron.user_strings import errors, help, reprs

SOURCE_FOLDER = os.path.dirname(llamatron.__file__)
TEST_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_FOLDER = os.path.join(os.path.dirname(TEST_FOLDER), 'internal_tools')
PYTHON_SUFFIX = '.py'
# A word of a source file, which a constant's name is one of, and how often a constant nothing uses is named in its own module.
WORD = re.compile(r'\w+')
DEFINED_ONLY = 1
FILE_ENCODING = 'utf-8'
ERROR_PREFIX = 'ERR_'
MESSAGE_PREFIX = 'MSG_'
HELP_PREFIX = 'HELP_'
REPR_PREFIX = 'REPR_'
PREFIXES = (ERROR_PREFIX, MESSAGE_PREFIX, HELP_PREFIX, REPR_PREFIX)
STRINGS_FOLDER = os.path.dirname(user_strings.__file__)
PACKAGE_FILE = '__init__.py'
# Where the generator plugins are, and the module of each that holds its own words.
PLUGINS_FOLDER = os.path.dirname(generator_package.__file__)
PLUGIN_STRINGS = '*/strings.py'
# The modules whose constants have a prefix other than MSG_.
OTHER_PREFIXES = {errors.__file__: ERROR_PREFIX, help.__file__: HELP_PREFIX, reprs.__file__: REPR_PREFIX}
# The modules a strings module may import from: the names the file format and the keys define, and the package's own modules.
ALLOWED_IMPORTS = ('llamatron.model.schema.file_format', 'llamatron.tui.keys', 'llamatron.user_strings')
# Names that are allowed to be used by a module's own code alone, since nothing else can see them.
PRIVATE_PREFIX = '_'
# Words a constant's name must not repeat after its prefix, like ERR_ERROR_LINE, MSG_MESSAGE or HELP_HELP_SONG. A message
# about an error belongs in user_strings/errors.py, so the message words and the error words are redundant in both of those modules.
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


def plugin_string_modules():
    """Return the path of every generator plugin's strings module."""
    return sorted(str(path) for path in pathlib.Path(PLUGINS_FOLDER).glob(PLUGIN_STRINGS))


def own_prefixes():
    """Return each strings module's path with the prefix its constants carry, any prefix for a plugin's own words."""
    return {**{path: OTHER_PREFIXES.get(path, MESSAGE_PREFIX) for path in string_modules()}, **{path: PREFIXES for path in plugin_string_modules()}}


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


def defined_twice(path):
    """Return the names a module assigns at its top level more than once, in order."""
    with open(path, encoding=FILE_ENCODING) as source:
        tree = ast.parse(source.read())
    seen = set()
    twice = []
    for node in tree.body:
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)] if isinstance(node, ast.Assign) else []
        twice += [target for target in targets if target in seen]
        seen.update(targets)
    return twice


class TestMessageConstants(unittest.TestCase):

    def test_only_the_strings_package_defines_prefixed_constants(self):
        for path in python_files(SOURCE_FOLDER):
            if path in OWN_PREFIX:
                continue
            with self.subTest(path=path):
                self.assertEqual(prefixed(defined_constants(path)), [])

    def test_no_module_of_the_strings_package_defines_a_name_twice(self):
        """A second definition silently replaces the first, so that whatever used the first shows the second's text."""
        paths = [os.path.join(STRINGS_FOLDER, name) for name in sorted(os.listdir(STRINGS_FOLDER)) if name.endswith(PYTHON_SUFFIX)]
        self.assertEqual([(os.path.basename(path), name) for path in paths for name in defined_twice(path)], [])

    def test_no_module_of_limits_or_defaults_defines_a_name_twice(self):
        """A second limit of one name silently replaces the first, which once held a track's accent to a shape's range."""
        for module in (limits, defaults):
            with self.subTest(module=module.__name__):
                self.assertEqual(defined_twice(module.__file__), [])

    def test_every_constant_is_used(self):
        # Every word of every other file is gathered once, and each constant looked up among them: a search of the whole
        # program for each of several thousand names took twenty seconds.
        used_elsewhere = set()
        for folder in (SOURCE_FOLDER, TEST_FOLDER, TOOLS_FOLDER):
            for path in python_files(folder):
                if path not in OWN_PREFIX:
                    used_elsewhere.update(WORD.findall(source_of(path)))
        unused = []
        for path, prefix in OWN_PREFIX.items():
            times_at_home = collections.Counter(WORD.findall(source_of(path)))
            for name in defined_constants(path):
                if name.startswith(prefix) and name not in used_elsewhere and times_at_home[name] <= DEFINED_ONLY:
                    unused.append(name)
        self.assertEqual(unused, [])

    def test_the_string_modules_import_only_names(self):
        """A strings module that imported a module with code of its own could no longer be imported by that module."""
        for path in string_modules() + plugin_string_modules():
            for module in imported_modules(path):
                with self.subTest(file=os.path.basename(path), module=module):
                    self.assertTrue(module.startswith(ALLOWED_IMPORTS), module)
