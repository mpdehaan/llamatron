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

"""Every function and method, in the program, its tests and its tools, takes its arguments by keyword wherever a call passes more than one, or any
optional one: its parameters come after a bare *, so that a call names what it passes and Python refuses
a missing, extra or misspelled argument at the call. Dataclasses are kw_only for the same reason.

The exceptions are Python's own special methods, which Python calls positionally; Rational, whose
arithmetic is the render's hot path and stays positional for speed, and Length and Sound, the
static methods a render calls for every note; methods that Textual or unittest
call with their own positional arguments; forwarders that pass *arguments and **named through; and
functions nested inside another, which are callbacks with a local contract.
"""

import ast
import pathlib
import unittest

import llamatron

ROOT = pathlib.Path(llamatron.__file__).parents[2]
# The program, its tests and its tools all follow the rule.
SOURCE_ROOTS = [ROOT / 'src' / 'llamatron', ROOT / 'test', ROOT / 'internal_tools']
# Classes whose constructor and methods stay positional for speed.
FAST_CLASSES = {'Rational', 'Length', 'Sound'}
# Methods that a library calls with its own positional arguments.
LIBRARY_METHODS = {'on_key', 'on_mount', 'on_resize', 'on_screen_resume', 'compose', 'render', 'check_action'}
LIBRARY_PREFIXES = ('watch_', 'action_')
SELF_NAMES = {'self', 'cls'}
SPECIAL_EDGES = '__'
DATACLASS = 'dataclass'
KW_ONLY = 'kw_only'
PYTHON_SUFFIX = '.py'
ALL_FILES = '**/*.py'
MSG_PLACE = '{path}:{line} {name}({parameters})'
MSG_POSITIONAL = 'these take arguments positionally:\n{places}'
MSG_DATACLASSES = 'these dataclasses are not kw_only:\n{places}'
LIST_SEPARATOR = '\n'


def own_parameters(node):
    """A function's positional parameters, leaving out self or cls."""
    names = [parameter.arg for parameter in node.args.posonlyargs + node.args.args]
    if names and names[0] in SELF_NAMES:
        names = names[1:]
    return names


def should_be_keyword_only(node):
    """Whether a function has enough parameters for the rule to apply: two or more, or any with a default."""
    if node.args.vararg or node.args.kwarg:
        return False
    return len(own_parameters(node)) >= 2 or bool(node.args.defaults)


def is_special(name):
    return name.startswith(SPECIAL_EDGES) and name.endswith(SPECIAL_EDGES)


def is_library_method(name):
    return name in LIBRARY_METHODS or name.startswith(LIBRARY_PREFIXES)


def is_dataclass(node):
    return any(decorator_name(decorator) == DATACLASS for decorator in node.decorator_list)


def decorator_name(decorator):
    return ast.unparse(decorator.func if isinstance(decorator, ast.Call) else decorator)


def is_keyword_only_dataclass(node):
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            for keyword in decorator.keywords:
                if keyword.arg == KW_ONLY and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    return True
    return False


def dataclass_fields(node):
    return [statement for statement in node.body if isinstance(statement, ast.AnnAssign)]


def dataclass_needs_keywords(node):
    fields = dataclass_fields(node)
    return len(fields) >= 2 or any(field.value is not None for field in fields)


def functions_to_check(tree):
    """Every module-level function and every method, with its class name, but not functions nested in them."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            yield None, node
        elif isinstance(node, ast.ClassDef) and node.name not in FAST_CLASSES:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    yield node.name, item


def place_of(*, path, node):
    return MSG_PLACE.format(path=path.relative_to(ROOT), line=node.lineno, name=node.name, parameters=', '.join(own_parameters(node)))


def source_files():
    return [path for root in SOURCE_ROOTS for path in sorted(root.glob(ALL_FILES))]


class TestKeywordOnly(unittest.TestCase):

    def test_every_function_with_two_parameters_or_a_default_takes_them_by_keyword(self):
        positional = []
        for path in source_files():
            tree = ast.parse(path.read_text())
            for class_name, node in functions_to_check(tree):
                if is_special(node.name) or (class_name and is_library_method(node.name)):
                    continue
                if should_be_keyword_only(node):
                    positional.append(place_of(path=path, node=node))
        self.assertEqual(positional, [], MSG_POSITIONAL.format(places=LIST_SEPARATOR.join(positional)))

    def test_every_dataclass_with_two_fields_or_a_default_is_keyword_only(self):
        positional = []
        for path in source_files():
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and is_dataclass(node) and node.name not in FAST_CLASSES:
                    if dataclass_needs_keywords(node) and not is_keyword_only_dataclass(node):
                        positional.append(place_of(path=path, node=node))
        self.assertEqual(positional, [], MSG_DATACLASSES.format(places=LIST_SEPARATOR.join(positional)))

    def test_the_rule_recognizes_the_shapes_it_checks(self):
        tree = ast.parse('def a(x, y): pass\ndef b(x=1): pass\ndef c(x): pass\ndef d(*, x, y): pass\ndef e(*args): pass')
        shapes = {node.name: should_be_keyword_only(node) for node in tree.body}
        self.assertEqual(shapes, {'a': True, 'b': True, 'c': False, 'd': False, 'e': False})


if __name__ == '__main__':
    unittest.main()
