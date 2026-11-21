# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Measure the program after a step of the refactoring and add a row to the log, so that the whole can be read end to end.

    internal_tools/refactor_log.sh "the step's name"     # measure, and add a row to .claude/features/REFACTORING_LOG.md
    internal_tools/refactor_log.sh --show                # measure and print the row, changing nothing

A row holds how fast the program is (every example rendered, the function calls that took, the
text UI imported in a new interpreter, the suite's classes run one after another), how large it
is (lines of Python in each top folder of the program, the tests and the tools) and how it is
shaped (classes, the methods of the two largest classes, the files that import ten or more of
the program's modules). The lines counted are every line of every Python file but the license
header that opens each.
"""

import argparse
import ast
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / '.claude' / 'features' / 'REFACTORING_LOG.md'
SOURCE = ROOT / 'src' / 'llamatron'
TESTS = ROOT / 'tests'
TOOLS = ROOT / 'internal_tools'
TEST_TIMES = ROOT / '.test_times.json'
TIME_SCRIPT = ROOT / 'internal_tools' / 'time_renders.py'
PYTHON_FILES = '*.py'
FILE_ENCODING = 'utf-8'
# The license header that opens every file, which is no part of the program.
HEADER_LINES = 3
IMPORT_UI = 'import llamatron.tui.app'
IMPORT_RUNS = 5
TOTAL_ROW = 'every example'
STRINGS_PACKAGE = 'llamatron.user_strings'
PROGRAM_PACKAGE = 'llamatron'
MANY_IMPORTS = 10
LARGEST_CLASSES = ('Document', 'WizardChoices')
MILLISECONDS = 1000
TOP_FILES = '(top)'
# The columns of the log, in order.
STEP = 'step'
RENDER_MS = 'render ms'
RENDER_CALLS = 'render calls'
IMPORT_MS = 'UI import ms'
SUITE_SECONDS = 'suite class seconds'
SOURCE_LINES = 'src lines'
TEST_LINES = 'tests lines'
TOOL_LINES = 'tools lines'
CLASSES = 'classes'
MANY = 'files of 10+ imports'
MOST = 'most imports'
METHODS_OF = '{name} methods'
FOLDER_LINES = '{folder} lines'
ROW = '| {cells} |'
CELL_SEPARATOR = ' | '
RULE_CELL = '---'
LOG_HEADING = """# The Refactoring's Log

A row for each step of the refactoring (`.claude/features/REFACTORING.md`), written by `internal_tools/refactor_log.sh`: how fast
the program is, how large and how shaped, after the step. Every step is committed only with every export byte for byte the same.

"""


def python_files(folder):
    return sorted(folder.rglob(PYTHON_FILES))


def lines_of(path):
    """Return how many lines a Python file has under its license header."""
    return max(len(path.read_text(encoding=FILE_ENCODING).splitlines()) - HEADER_LINES, 0)


def lines_in(folder):
    return sum(lines_of(path) for path in python_files(folder))


def lines_by_folder(folder):
    """Return the lines of Python in each folder straight under a folder, by the folder's name, with the files that lie in the folder itself as one more."""
    found = {}
    for path in python_files(folder):
        parts = path.relative_to(folder).parts
        name = parts[0] if len(parts) > 1 else TOP_FILES
        found[name] = found.get(name, 0) + lines_of(path)
    return dict(sorted(found.items()))


def program_imports(tree):
    """Return the modules of the program a file imports, the strings package left out, since that is text alone."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[0] == PROGRAM_PACKAGE:
            for alias in node.names:
                module = node.module + '.' + alias.name
                is_module = (ROOT / 'src' / pathlib.Path(*module.split('.'))).with_suffix('.py').exists()
                found.add(module if is_module else node.module)
    return {module for module in found if not module.startswith(STRINGS_PACKAGE)}


def shape():
    """Return the program's shape: its classes, the methods of the largest, and how many files import many modules."""
    classes = 0
    methods = dict.fromkeys(LARGEST_CLASSES, 0)
    counts = []
    trees = {path: ast.parse(path.read_text(encoding=FILE_ENCODING)) for path in python_files(SOURCE)}
    by_name = {}
    for tree in trees.values():
        counts.append(len(program_imports(tree)))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes += 1
                by_name[node.name] = node
    for name in LARGEST_CLASSES:
        methods[name] = methods_of(name=name, by_name=by_name)
    return {CLASSES: classes, MANY: sum(1 for count in counts if count >= MANY_IMPORTS), MOST: max(counts),
            **{METHODS_OF.format(name=name): count for name, count in methods.items()}}


def methods_of(*, name, by_name, seen=()):
    """Return how many methods a class has, with those of the program's classes it inherits from."""
    if name not in by_name or name in seen:
        return 0
    node = by_name[name]
    own = sum(1 for part in node.body if isinstance(part, (ast.FunctionDef, ast.AsyncFunctionDef)))
    bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
    return own + sum(methods_of(name=base, by_name=by_name, seen=(*seen, name)) for base in bases)


def render_totals():
    """Return the milliseconds every example takes to render and the function calls that took, from the render timer's last row."""
    output = subprocess.run([sys.executable, str(TIME_SCRIPT)], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for line in output.splitlines():
        if line.startswith(TOTAL_ROW):
            parts = line.split()
            return float(parts[-2]), int(parts[-1])
    return 0.0, 0


def import_milliseconds():
    """Return the best of several times a new interpreter takes to import the text UI."""
    times = []
    for _ in range(IMPORT_RUNS):
        start = time.perf_counter()
        subprocess.run([sys.executable, '-c', IMPORT_UI], cwd=ROOT, check=True)
        times.append(time.perf_counter() - start)
    return min(times) * MILLISECONDS


def suite_seconds():
    """Return the seconds the suite's classes took on its last full run, one after another, or 0 with no run kept."""
    if not TEST_TIMES.exists():
        return 0
    return sum(json.loads(TEST_TIMES.read_text(encoding=FILE_ENCODING)).values())


def measured(step):
    """Return a row of the log: each column's name with its value."""
    render, calls = render_totals()
    row = {STEP: step, RENDER_MS: round(render), RENDER_CALLS: calls, IMPORT_MS: round(import_milliseconds()), SUITE_SECONDS: round(suite_seconds()),
           SOURCE_LINES: lines_in(SOURCE), TEST_LINES: lines_in(TESTS), TOOL_LINES: lines_in(TOOLS)}
    row.update(shape())
    row.update({FOLDER_LINES.format(folder=folder): lines for folder, lines in lines_by_folder(SOURCE).items()})
    return row


def table_line(cells):
    return ROW.format(cells=CELL_SEPARATOR.join(str(cell) for cell in cells))


def with_row(*, text, row):
    """Return the log's text with a row added, the heading and the table's top written when the log is new."""
    if not text:
        text = LOG_HEADING + table_line(row) + '\n' + table_line([RULE_CELL] * len(row)) + '\n'
    return text + table_line(row.values()) + '\n'


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('step', nargs='?', default='', help="the step's name, as the log's row is to say it")
    parser.add_argument('--show', action='store_true', help='print the row and change nothing')
    options = parser.parse_args(arguments)
    row = measured(options.step)
    if options.show or not options.step:
        for name, value in row.items():
            print(name, value)
        return 0
    text = LOG.read_text(encoding=FILE_ENCODING) if LOG.exists() else ''
    LOG.write_text(with_row(text=text, row=row), encoding=FILE_ENCODING)
    print(table_line(row.values()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
