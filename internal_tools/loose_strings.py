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


"""List the string literals inside functions and classes of Python files, which the style rules say should be named constants.

Run from the top folder, naming files or folders:

    .venv/bin/python internal_tools/loose_strings.py test            # a count per file
    .venv/bin/python internal_tools/loose_strings.py -v test/test_x.py   # the strings themselves, most common first

Docstrings, blank strings, long text and strings at the top level of a module (which are the
constants' own values) are left out. Not everything it lists is wrong: a test's own data, like
the notes of a tune, can stay literal, so it's a list to read, not a rule to enforce.
"""

import ast
import collections
import os
import sys

VERBOSE_FLAG = '-v'
LONGEST_INTERESTING = 60
MOST_SHOWN = 12
PYTHON_SUFFIX = '.py'
COUNT_LINE = '{count:4} {path}'
DETAIL_LINE = '{path}: {count} -> {details}'
TOTAL_LINE = 'total {total}'
DETAIL = '{value!r}x{count}'
DETAIL_SEPARATOR = ', '


def docstring_ids(tree):
    """Return the ids of the Constant nodes that are docstrings."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


SLOTS = '__slots__'


def is_constant_definition(node):
    """A plain NAME = value line, which is a constant's own definition rather than a loose use."""
    return isinstance(node, ast.Assign) and all(isinstance(target, ast.Name) for target in node.targets)


def is_slots(node):
    return isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == SLOTS for target in node.targets)


def code_to_check(top):
    """The statements of a class or function whose strings should be constants: not constant definitions or __slots__."""
    if isinstance(top, ast.ClassDef):
        return [statement for statement in top.body if not (is_constant_definition(statement) or is_slots(statement))]
    return [statement for statement in top.body if not is_slots(statement)]


def loose_strings(path):
    """Return (line, value) for each string literal inside a function or class of a file."""
    with open(path) as file:
        tree = ast.parse(file.read())
    docstrings = docstring_ids(tree)
    found = []
    for top in tree.body:
        if not isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in [leaf for statement in code_to_check(top) for leaf in ast.walk(statement)]:
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                if node.value.strip() and len(node.value) <= LONGEST_INTERESTING:
                    found.append((node.lineno, node.value))
    return found


def python_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for folder, _, names in os.walk(path):
                for name in sorted(names):
                    if name.endswith(PYTHON_SUFFIX):
                        yield os.path.join(folder, name)
        else:
            yield path


def main():
    verbose = VERBOSE_FLAG in sys.argv
    paths = [argument for argument in sys.argv[1:] if argument != VERBOSE_FLAG]
    total = 0
    for path in sorted(python_files(paths)):
        found = loose_strings(path)
        total += len(found)
        if not found:
            continue
        if verbose:
            counts = collections.Counter(value for _, value in found)
            details = DETAIL_SEPARATOR.join(DETAIL.format(value=value, count=count) for value, count in counts.most_common(MOST_SHOWN))
            print(DETAIL_LINE.format(path=path, count=len(found), details=details))
        else:
            print(COUNT_LINE.format(count=len(found), path=path))
    print(TOTAL_LINE.format(total=total))


if __name__ == '__main__':
    main()
