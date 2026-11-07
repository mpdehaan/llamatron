#!/usr/bin/env python3
# llamatron: a Python language and framework for producing MIDI clips.
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

"""List imports that a Python file never uses, so they can be removed.

It reads each file's code without running it, and reports every name an import brings in that
the file never mentions again. An import that's there on purpose for other modules to import from
this one, a re-export, is skipped if it's listed in the file's `__all__` or marked with `# noqa`
on its line. Otherwise it only looks at names in the code, so a name used only inside a string
counts as unused.

Run it from the top folder of the project, on the files to check, or with none to check src/,
test/ and tools/:

    .venv/bin/python tools/check_unused_imports.py
    .venv/bin/python tools/check_unused_imports.py src/llamatron/note.py

Each unused import is printed as path:line: name, and it exits with 1 if it found any.
"""

import ast
import glob
import sys

# What to check when no files are named.
EVERY_FILE = ['src/**/*.py', 'test/**/*.py', 'tools/**/*.py']
# A comment that marks an import as there on purpose.
KEEP_MARK = 'noqa'
MODULE_SEPARATOR = '.'
# The list of names a module offers to others, which counts as using them.
EXPORTS = '__all__'
MSG_UNUSED = '{path}:{line}: {name}'
SUCCESS = 0
FAILURE = 1


def unused_imports(path):
    """Return (line, name) for each name a file imports and never uses, in line order."""
    with open(path, encoding='utf-8') as file:
        source = file.read()
    tree = ast.parse(source)
    lines = source.splitlines()
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and KEEP_MARK not in lines[node.lineno - 1]:
            for alias in node.names:
                imported[imported_name(alias)] = node.lineno
    used = names_used(tree) | names_exported(tree)
    return sorted((line, name) for name, line in imported.items() if name not in used)


def imported_name(alias):
    """Return the name an import brings into a file: its `as` name, or the first part of `import a.b`."""
    return (alias.asname or alias.name).split(MODULE_SEPARATOR)[0]


def names_used(tree):
    """Return every plain name a file's code mentions, like `Note` in `Note(...)` or `os` in `os.path`."""
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def names_exported(tree):
    """Return the names a file lists in __all__, if it has one written as a plain list or tuple of strings."""
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == EXPORTS for target in node.targets):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                return {item.value for item in node.value.elts if isinstance(item, ast.Constant)}
    return set()


def files_to_check(named):
    """Return the files named on the command line, or every file under src/, test/ and tools/."""
    if named:
        return named
    return sorted(path for pattern in EVERY_FILE for path in glob.glob(pattern, recursive=True))


def main():
    found = False
    for path in files_to_check(sys.argv[1:]):
        for line, name in unused_imports(path):
            print(MSG_UNUSED.format(path=path, line=line, name=name))
            found = True
    return FAILURE if found else SUCCESS


if __name__ == '__main__':
    sys.exit(main())
