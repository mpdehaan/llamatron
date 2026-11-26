# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""No comprehension holds another comprehension or three loops.

A comprehension that is more than a plain copy, filter or one flattening reads only when its inner layer has a name: the inner
layer becomes a comprehension calling a small function whose name says what it builds (.claude/rules/STYLE.md, "A line whose purpose
isn't obvious gets a name"). Two loops in one comprehension, such as every note of every bar, still read as one thought.
The program holds the rule; the tests and the tools follow once their comprehensions are cleaned up.
"""

import ast
from pathlib import Path
import unittest
from tests import rules

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKED_FOLDERS = ('src',)
PYTHON_FILES = '*.py'
COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
# The most loops one comprehension may hold, inner comprehensions' loops counted with its own.
MOST_LOOPS = 2
NESTED = '{path}:{line}: a comprehension holds another comprehension or more than {most} loops'


def holds_a_comprehension(node):
    """Return whether a comprehension holds another anywhere inside it."""
    return any(isinstance(inner, COMPREHENSIONS) for inner in ast.walk(node) if inner is not node)


def loops_of(node):
    """Return how many loops a comprehension holds, with those of any comprehension inside it."""
    return sum(len(inner.generators) for inner in ast.walk(node) if isinstance(inner, COMPREHENSIONS))


def nested_comprehensions(path):
    """Return a line for each outermost comprehension of a file that holds another comprehension or too many loops."""
    tree = ast.parse(path.read_text(), filename=str(path))
    found = []
    inside = set()
    for node in ast.walk(tree):
        if not isinstance(node, COMPREHENSIONS) or id(node) in inside:
            continue
        if holds_a_comprehension(node) or loops_of(node) > MOST_LOOPS:
            found.append(NESTED.format(path=path.relative_to(ROOT), line=node.lineno, most=MOST_LOOPS))
            inside.update(id(inner) for inner in ast.walk(node))
    return found


def checked_files():
    """Return every Python file the rule holds, in order."""
    return [path for folder in CHECKED_FOLDERS for path in sorted((ROOT / folder).rglob(PYTHON_FILES))]


@unittest.skip(rules.STYLE_WAIVED)
class TestNoNestedComprehensions(unittest.TestCase):

    def test_no_comprehension_holds_another_or_three_loops(self):
        found = [line for path in checked_files() for line in nested_comprehensions(path)]
        self.assertEqual(found, [], msg='\n'.join(found))


if __name__ == '__main__':
    unittest.main()
