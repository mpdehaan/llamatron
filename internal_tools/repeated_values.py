# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""List the strings written out in Python files that repeat a value the program already names: a file's key, a note's name, a scale type, a kind of generator.

Run from the top folder, naming files or folders:

    .venv/bin/python internal_tools/repeated_values.py tests internal_tools      # a count per file, most first
    .venv/bin/python internal_tools/repeated_values.py -v tests/interface/tracker/test_x.py    # each string, its line and the constant that names it

The values are those of the classes of constants in model/schema/file_format.py and of NoteName
in model/values/note.py. Docstrings are left out. Not everything it lists is wrong: a test's own name
for a thing, a track it calls bass, may happen to be a value of the program's too, so it is a
list to read. What it finds in a line of data, a key or a value the program reads, should be
the program's constant.
"""

import ast
import inspect
import os
import sys

from llamatron.model.schema import file_format
from llamatron.model.values import note

VERBOSE_FLAG = '-v'
PYTHON_SUFFIX = '.py'
COUNT_LINE = '{count:5} {path}'
FOUND_LINE = '{path}:{line}: {value!r} is {constant}'
TOTAL_LINE = 'total {total} in {files} files'
CONSTANT_NAME = '{owner}.{name}'
# The modules whose classes of constants name the values looked for.
MODULES_OF_VALUES = (file_format, note)


def named_values():
    """Return every string value the program names in a class of constants, each with the first constant that names it."""
    found = {}
    for module in MODULES_OF_VALUES:
        for owner, constants in inspect.getmembers(module, inspect.isclass):
            if constants.__module__ != module.__name__:
                continue
            for name, value in vars(constants).items():
                if name.isupper() and isinstance(value, str) and value:
                    found.setdefault(value, CONSTANT_NAME.format(owner=owner, name=name))
    return found


def docstrings_of(tree):
    """Return the ids of the nodes that are docstrings."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def repeated_in(*, source, values):
    """Return the strings of some Python source that repeat a named value, each as (its line, the string, the constant that names it), in the order written."""
    tree = ast.parse(source)
    docstrings = docstrings_of(tree)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings and node.value in values:
            found.append((node.lineno, node.value, values[node.value]))
    return sorted(found)


def python_files(paths):
    """Return the Python files named, and those under the folders named, in order."""
    files = []
    for path in paths:
        if os.path.isdir(path):
            for folder, _, names in os.walk(path):
                files += [os.path.join(folder, name) for name in names if name.endswith(PYTHON_SUFFIX)]
        else:
            files.append(path)
    return sorted(files)


def main(arguments):
    verbose = VERBOSE_FLAG in arguments
    values = named_values()
    counts = {}
    for path in python_files([argument for argument in arguments if argument != VERBOSE_FLAG]):
        with open(path) as file:
            found = repeated_in(source=file.read(), values=values)
        if found:
            counts[path] = len(found)
        if verbose:
            for line, value, constant in found:
                print(FOUND_LINE.format(path=path, line=line, value=value, constant=constant))
    if not verbose:
        for path, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            print(COUNT_LINE.format(count=count, path=path))
    print(TOTAL_LINE.format(total=sum(counts.values()), files=len(counts)))


if __name__ == '__main__':
    main(sys.argv[1:])
