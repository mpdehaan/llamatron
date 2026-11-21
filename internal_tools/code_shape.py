# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Find what breaks the rules of a function's shape in the program: a body too long, blocks too deep, too many parameters, a reach
into another object's private names, a catch of every error, type checks that choose what to do, and a file or a class too big.

tests/rules/shape_exceptions.py lists what broke a rule when the rule was made, a list that only shrinks, and the few places a rule
allows with a reason; tests/rules/test_code_shape.py fails for anything else, and for a listed place that no longer breaks its
rule until `internal_tools/code_shape.sh --prune` takes it off.

    internal_tools/code_shape.sh            every place that breaks a rule, each marked allowed, with a reason, new or gone
    internal_tools/code_shape.sh --prune    take the places that are gone off the lists
"""

import argparse
import ast
import importlib.util
import pathlib
import pprint
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'src' / 'llamatron'
EXCEPTIONS_FILE = ROOT / 'tests' / 'rules' / 'shape_exceptions.py'
FILE_ENCODING = 'utf-8'
PYTHON_FILES = '*.py'
# The rules, by the names their lists are kept under.
LONG = 'long'
DEEP = 'deep'
DEEPEST = 'deepest'
PARAMETERS = 'parameters'
PRIVATE = 'private'
CATCHES = 'catches'
TYPE_CHECKS = 'type checks'
BIG_FILES = 'big files'
BIG_CLASSES = 'big classes'
RULES = (LONG, DEEP, DEEPEST, PARAMETERS, PRIVATE, CATCHES, TYPE_CHECKS, BIG_FILES, BIG_CLASSES)
# The limits: a body's lines without its docstring, blocks inside blocks, and parameters but self or cls.
MOST_LINES = 30
MOST_DEPTH = 3
# A depth past MOST_DEPTH that a function may reach where it reads better, with a reason; nothing goes deeper.
DEEPEST_ALLOWED = 4
MOST_PARAMETERS = 5
MOST_TYPE_CHECKS = 1
# The most lines of code a file or a class may hold, blank lines and comments left out.
MOST_CODE_LINES = 300
# The files that are lists by nature, the set file's names, the program's text and the key bindings, which no split would make clearer.
LIST_FILES = ('model/vocabulary/file_format.py', 'tui/keybindings.py')
LIST_FOLDERS = ('user_strings',)
COMMENT = '#'
BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
OWN_NAMES = ('self', 'cls')
# A named tuple's own methods start with an underscore and are its public face.
NAMED_TUPLE_METHODS = ('_replace', '_asdict', '_fields', '_make')
EVERY_ERROR = ('Exception', 'BaseException')
SLOTS = '__slots__'
# The built-in types that checking data read from a file or typed by a person asks after, which is not the program's objects.
BUILT_IN_TYPES = ('bool', 'int', 'float', 'str', 'list', 'tuple', 'dict', 'set', 'frozenset', 'bytes', 'Fraction', 'Rational')
PLACE = '{path}:{name}'
REACH = '{place}: {owner}.{name}'
SHOWN = '{rule}: {place} ({state})'
SUMMARY = '{rule}: {count} listed, {new} new, {gone} gone'
NEW = 'new'
ALLOWED_STATE = 'listed'
REASON_STATE = 'with a reason'
GONE = 'gone'
EXCEPTIONS_START = '\nALLOWED = '
EXCEPTIONS_REASONS = '\n\nWITH_REASON = '


def is_elif(*, parent, child):
    """Return whether an if is its parent's elif, which stands level with the if rather than inside it: an elif starts where its
    if does, and an if inside an else is indented."""
    return isinstance(parent, ast.If) and isinstance(child, ast.If) and parent.orelse == [child] and child.col_offset == parent.col_offset


def code_lines(lines):
    """Return how many of some lines are code: not blank and not a comment."""
    return sum(1 for line in lines if line.strip() and not line.strip().startswith(COMMENT))


def is_a_list_file(path):
    """Return whether a file of the program is a list by nature, which the rule of a file's size leaves alone."""
    return path in LIST_FILES or path.split('/')[0] in LIST_FOLDERS


def own_depth(node, *, depth=0):
    """Return how deep blocks nest inside a function, not counting the functions and classes defined inside it, an elif level
    with its if."""
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, SCOPES):
            continue
        deeper = isinstance(child, BLOCKS) and not is_elif(parent=node, child=child)
        deepest = max(deepest, own_depth(child, depth=depth + 1 if deeper else depth))
    return deepest


def body_lines(function):
    """Return how many lines a function's body takes, its docstring left out."""
    body = function.body[1:] if ast.get_docstring(function) is not None else function.body
    return body[-1].end_lineno - body[0].lineno + 1 if body else 0


def parameter_count(function):
    """Return how many parameters a function names, self or cls left out, and *arguments and **named, which pass things on."""
    arguments = function.args
    named = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    return len([argument for argument in named if argument.arg not in OWN_NAMES])


def names_a_class_of_its_own(node):
    """Return whether an isinstance asks after a class of the program's own, rather than a built-in type such as int, which
    checking data read from a file or typed by a person asks after."""
    asked = node.args[1] if len(node.args) > 1 else None
    kinds = asked.elts if isinstance(asked, ast.Tuple) else [asked]
    return any(not (isinstance(kind, ast.Name) and kind.id in BUILT_IN_TYPES) for kind in kinds)


def type_checks(function):
    """Return how many times a function asks whether an object is of a class of the program's own with isinstance."""
    count = 0
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == isinstance.__name__ and names_a_class_of_its_own(node):
            count += 1
    return count


def is_private_reach(node):
    """Return whether an attribute reaches into another object's private name: an underscore name of anything but self or cls."""
    name = node.attr
    if not name.startswith('_') or name.startswith('__') or name in NAMED_TUPLE_METHODS:
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in OWN_NAMES)


def own_private_names(node):
    """Return the private names a class has of its own: its slots, what its methods set on self, and its methods, which its own
    methods may read on another instance of it, as an __eq__ reads the other's."""
    names = {child.name for child in node.body if isinstance(child, FUNCTIONS)}
    for child in ast.walk(node):
        if isinstance(child, ast.Assign) and any(isinstance(target, ast.Name) and target.id == SLOTS for target in child.targets):
            names.update(element.value for element in ast.walk(child.value) if isinstance(element, ast.Constant) and isinstance(element.value, str))
        if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id in OWN_NAMES:
            names.add(child.attr)
    return {name for name in names if name.startswith('_')}


def catches_every_error(handler):
    """Return whether an except catches every error: bare, or Exception or BaseException."""
    return handler.type is None or getattr(handler.type, 'id', None) in EVERY_ERROR


class ShapeFinder(ast.NodeVisitor):
    """Walks one file, noting each function by its qualified name, and what of it breaks a rule."""

    def __init__(self, *, path, lines):
        self.path = path
        self.lines = lines
        self.names = []
        # The private names of each class the walk is inside, which its own methods may read on another instance of it.
        self.own = []
        self.found = {rule: [] for rule in RULES}

    def place(self):
        return PLACE.format(path=self.path, name='.'.join(self.names) or '<module>')

    def visit_ClassDef(self, node):
        self.names.append(node.name)
        if not is_a_list_file(self.path) and code_lines(self.lines[node.lineno - 1:node.end_lineno]) > MOST_CODE_LINES:
            self.found[BIG_CLASSES].append(self.place())
        self.own.append(own_private_names(node))
        self.generic_visit(node)
        self.own.pop()
        self.names.pop()

    def visit_FunctionDef(self, node):
        self.names.append(node.name)
        place = self.place()
        depth = own_depth(node)
        if body_lines(node) > MOST_LINES:
            self.found[LONG].append(place)
        if depth > DEEPEST_ALLOWED:
            self.found[DEEPEST].append(place)
        elif depth > MOST_DEPTH:
            self.found[DEEP].append(place)
        if parameter_count(node) > MOST_PARAMETERS:
            self.found[PARAMETERS].append(place)
        if type_checks(node) > MOST_TYPE_CHECKS:
            self.found[TYPE_CHECKS].append(place)
        self.generic_visit(node)
        self.names.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Attribute(self, node):
        if is_private_reach(node) and not (self.own and node.attr in self.own[-1]):
            reach = REACH.format(place=self.place(), owner=ast.unparse(node.value), name=node.attr)
            if reach not in self.found[PRIVATE]:
                self.found[PRIVATE].append(reach)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if catches_every_error(node):
            self.found[CATCHES].append(self.place())
        self.generic_visit(node)


def breaks():
    """Return, for each rule, every place in the program that breaks it, in file order."""
    found = {rule: [] for rule in RULES}
    for path in sorted(SOURCE.rglob(PYTHON_FILES)):
        text = path.read_text(encoding=FILE_ENCODING)
        name = str(path.relative_to(SOURCE))
        finder = ShapeFinder(path=name, lines=text.splitlines())
        finder.visit(ast.parse(text, filename=str(path)))
        if not is_a_list_file(name) and code_lines(finder.lines) > MOST_CODE_LINES:
            finder.found[BIG_FILES].append(name)
        for rule in RULES:
            found[rule] += [place for place in finder.found[rule] if place not in found[rule]]
    return found


def exceptions():
    """Return the lists of tests/rules/shape_exceptions.py: what broke each rule when it was made, and what a rule allows with a reason."""
    spec = importlib.util.spec_from_file_location(EXCEPTIONS_FILE.stem, EXCEPTIONS_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ALLOWED, module.WITH_REASON


def exceptions_text(*, header, allowed, with_reason):
    """Return the exceptions file's text: its header and docstring as they are, then the lists."""
    return header + EXCEPTIONS_START + pprint.pformat(allowed, width=200, sort_dicts=False) + EXCEPTIONS_REASONS + pprint.pformat(with_reason, width=200, sort_dicts=False) + '\n'


def pruned(*, found, allowed):
    """Return the lists with the places that no longer break their rules taken off: a list only ever loses rows."""
    return {rule: tuple(place for place in allowed.get(rule, ()) if place in found[rule]) for rule in RULES}


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--prune', action='store_true', help='take the places that are gone off the lists')
    parser.add_argument('--quiet', action='store_true', help='print only the summary')
    options = parser.parse_args(arguments)
    found = breaks()
    allowed, with_reason = exceptions()
    for rule in RULES:
        listed = allowed.get(rule, ())
        reasoned = with_reason.get(rule, {})
        new = [place for place in found[rule] if place not in listed and place not in reasoned]
        gone = [place for place in listed if place not in found[rule]]
        if not options.quiet:
            for place in found[rule]:
                state = NEW if place in new else REASON_STATE if place in reasoned else ALLOWED_STATE
                print(SHOWN.format(rule=rule, place=place, state=state))
            for place in gone:
                print(SHOWN.format(rule=rule, place=place, state=GONE))
        print(SUMMARY.format(rule=rule, count=len(found[rule]) - len(new), new=len(new), gone=len(gone)))
    if options.prune:
        text = EXCEPTIONS_FILE.read_text(encoding=FILE_ENCODING)
        header = text[:text.index(EXCEPTIONS_START)]
        EXCEPTIONS_FILE.write_text(exceptions_text(header=header, allowed=pruned(found=found, allowed=allowed), with_reason=with_reason), encoding=FILE_ENCODING)
    return 0


if __name__ == '__main__':
    sys.exit(main())
