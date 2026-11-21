# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The map of which test classes run which source files, from the coverage data internal_tools/test_map.sh gathers, and the
classes a set of changed files needs, which internal_tools/test_changed.sh runs.

    internal_tools/test_map.py build              # turn .test_coverage/ into .test_map.json
    internal_tools/test_map.py changed FILE...    # print the classes the files need, one a line, or ALL for the whole suite
"""

import ast
import functools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COVERAGE_FOLDER = ROOT / '.test_coverage'
MAP_FILE = ROOT / '.test_map.json'
SOURCE = 'src/llamatron/'
TESTS = 'tests/'
# The rules about the code's shape, which read every file and so run for any change.
RULE_TESTS = 'tests/rules/'
# What a change outside the source and the tests needs: the folders of tests that read such files, by the folder changed.
FOLDERS_READ = {
    'examples/': ('tests/app/', 'tests/realtime/', 'tests/importers/', 'tests/tools/', 'tests/model/', 'tests/engine/'),
    'docs/': ('tests/rules/', 'tests/tools/'),
    'internal_tools/': ('tests/tools/', 'tests/genres/'),
    'user_scripts/': ('tests/tools/',),
    '.claude/': ('tests/rules/', 'tests/tui/test_tui_help_keys.py'),
}
# Changes that need nothing run: notes only for Claude that no test reads.
NOTHING_NEEDED = ('.claude/QUEUE.md', '.claude/DESIGNS.md', '.claude/IDEAS.yml', '.claude/features/')
EVERYTHING = 'ALL'
# The long sweeps the commit check leaves out, each with the folders of the program whose change brings it back, since a sweep
# tries every example, every subgenre or every page and the map finds that nearly every change ran it: they run before every
# push, and for a change to the sweep's own test file.
MUSIC = ('src/llamatron/model/', 'src/llamatron/engine/', 'src/llamatron/generators/', 'src/llamatron/playback/', 'src/llamatron/exporters/')
SWEEPS = {
    'tests.app.test_every_example.': MUSIC,
    'tests.macro_composer.test_wizard_effect.': (*MUSIC, 'src/llamatron/macro_composer/'),
    'tests.macro_composer.test_wizard_choices.TestWizardFormLengthsOf': (*MUSIC, 'src/llamatron/macro_composer/'),
    'tests.tui.test_tui_help_keys.': ('src/llamatron/tui/', '.claude/'),
}
BUILD = 'build'
CHANGED = 'changed'
PYTHON = '.py'
# The map's two parts: each source file's classes, and every class measured.
FILES = 'files'
CLASSES = 'classes'
# What every test shares, which a change to needs the whole suite.
SHARED_BY_TESTS = ('tests/support/', 'tests/data/', 'tests/__init__.py')


def built_map():
    """Return the map: each source file's test classes, by the file's path from the top folder, and every class measured, from the
    coverage data of every class."""
    from coverage import CoverageData
    by_file = {}
    classes = []
    for data_file in sorted(COVERAGE_FOLDER.iterdir()):
        classes.append(data_file.name)
        data = CoverageData(basename=str(data_file))
        data.read()
        for measured in data.measured_files():
            path = str(pathlib.Path(measured).resolve().relative_to(ROOT))
            # Importing a module runs its top-level lines for every class that imports it; only a line inside a function says the
            # class used the file.
            if set(data.lines(measured) or ()) - import_lines(path):
                by_file.setdefault(path, set()).add(data_file.name)
    return {FILES: {path: sorted(names) for path, names in sorted(by_file.items())}, CLASSES: classes}


@functools.lru_cache(maxsize=None)
def import_lines(path):
    """Return the lines of a source file that run when it is imported: every line of a top-level statement or a class body, and
    each function's header and decorators, but none of a function's body."""
    tree = ast.parse((ROOT / path).read_text())
    lines = set()

    def walk(statements):
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                lines.update(range(min([node.lineno, *[decorator.lineno for decorator in node.decorator_list]]), node.body[0].lineno))
                # A docstring is the first line of a body, which coverage does not count as run.
            elif isinstance(node, ast.ClassDef):
                lines.update(range(min([node.lineno, *[decorator.lineno for decorator in node.decorator_list]]), node.body[0].lineno))
                walk(node.body)
            else:
                lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    walk(tree.body)
    return lines


def prefix_of(path):
    """Return the start of the names of the classes a test folder or a test file holds, like tests.app. or tests.tui.test_tui_wizard."""
    if path.endswith(PYTHON):
        return path[:-len(PYTHON)].replace('/', '.') + '.'
    return path.replace('/', '.')


def classes_in(*, path, every_class):
    return {name for name in every_class if name.startswith(prefix_of(path))}


def needed(*, changed, by_file, every_class):
    """Return the test classes a set of changed files needs, or EVERYTHING when one of them is a file the map can't place."""
    wanted = set()
    for path in changed:
        if path.startswith(NOTHING_NEEDED):
            continue
        if path.startswith(SOURCE):
            if path not in by_file:
                return EVERYTHING
            wanted.update(by_file[path])
        elif path.startswith(SHARED_BY_TESTS):
            return EVERYTHING
        elif path.startswith(TESTS) and path.endswith(PYTHON):
            wanted.update(classes_in(path=path, every_class=every_class))
        else:
            folders = next((reads for folder, reads in FOLDERS_READ.items() if path.startswith(folder)), None)
            if folders is None:
                return EVERYTHING
            for folder in folders:
                wanted.update(classes_in(path=folder, every_class=every_class))
    wanted.update(classes_in(path=RULE_TESTS, every_class=every_class))
    return sorted(name for name in wanted if not is_left_out(name=name, changed=changed))


def is_left_out(*, name, changed):
    """Return whether a class is a long sweep that no change given brings back: none to the folders that bring it back, nor to its
    own test file."""
    for prefix, folders in SWEEPS.items():
        if name.startswith(prefix):
            own = TESTS + prefix.split('.')[1] + '/' + prefix.split('.')[2] + PYTHON
            return not any(path.startswith(folders) or path == own for path in changed)
    return False


def main(arguments):
    if arguments[:1] == [BUILD]:
        MAP_FILE.write_text(json.dumps(built_map(), indent=0))
        return 0
    if arguments[:1] == [CHANGED]:
        if not MAP_FILE.exists():
            print(EVERYTHING)
            return 0
        kept = json.loads(MAP_FILE.read_text())
        found = needed(changed=arguments[1:], by_file=kept[FILES], every_class=kept[CLASSES])
        print(EVERYTHING if found == EVERYTHING else '\n'.join(found))
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
