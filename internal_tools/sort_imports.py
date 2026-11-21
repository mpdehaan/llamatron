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

"""Sort the imports at the top of every Python file into the project's order.

A file's imports come as two groups with one blank line between them: first the system and
third-party libraries, then everything of this project. In each group the lines are in
alphabetical order by the module imported from, the names one line imports are in alphabetical
order too, and two lines that import from one module become one.

    internal_tools/sort_imports.sh            # list the files whose imports are out of order
    internal_tools/sort_imports.sh --write    # rewrite them

Only the run of imports a file opens with is sorted: an import that stands after other code, or
inside a function, stands there for a reason, such as avoiding a circular import or waiting for
a path to be set, and is left where it is. A file with a comment on a line of its own among its
opening imports is left alone and named. internal_tools/check_before_commit.sh runs it with --write to keep the rule.
"""

import argparse
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_PACKAGES = ('llamatron', 'tests')
# Folders whose files are imported by their own names, as the tools and their tests import each other.
TOOLS_FOLDERS = ('internal_tools', 'user_scripts')
FOLDERS = ('src', 'tests', *TOOLS_FOLDERS)
PYTHON_FILES = '*.py'
FILE_ENCODING = 'utf-8'
DOT = '.'
COMMENT = '#'
FROM_IMPORT = 'from {module} import {names}'
PLAIN_IMPORT = 'import {names}'
AS_NAME = '{name} as {other}'
NAME_SEPARATOR = ', '
OUT_OF_ORDER = '{path}: imports out of order'
LEFT_ALONE = '{path}: left alone, a comment stands among its opening imports'
SUMMARY = '{files} files out of order'


def python_files():
    return sorted(path for folder in FOLDERS for path in (ROOT / folder).rglob(PYTHON_FILES))


def tool_modules():
    """Return the names the project's tools are imported by, each a file's own name."""
    return {path.stem for folder in TOOLS_FOLDERS for path in (ROOT / folder).rglob(PYTHON_FILES)}


def written_name(alias):
    return AS_NAME.format(name=alias.name, other=alias.asname) if alias.asname else alias.name


def name_order(alias):
    """Return what a line's names are sorted by: the name without regard to capitals, then as written."""
    return (alias.name.lower(), alias.name, alias.asname or '')


class Line:
    """One import of a file's opening run: the module it imports from, its names, and a comment written after it."""

    __slots__ = ('module', 'aliases', 'is_from', 'comment')

    def __init__(self, *, module, aliases, is_from, comment):
        self.module = module
        self.aliases = aliases
        self.is_from = is_from
        self.comment = comment

    def order(self):
        """Return what a group's lines are sorted by: the module, with `import x` before `from x import`."""
        return (self.module.lower(), self.module, self.is_from, [name_order(alias) for alias in self.aliases])

    def text(self):
        if self.is_from:
            names = NAME_SEPARATOR.join(written_name(alias) for alias in sorted(self.aliases, key=name_order))
            return FROM_IMPORT.format(module=self.module, names=names) + self.comment
        return PLAIN_IMPORT.format(names=NAME_SEPARATOR.join(written_name(alias) for alias in self.aliases)) + self.comment


def is_of_project(*, module, tools):
    top = module.split(DOT)[0]
    return top in PROJECT_PACKAGES or top in tools


def opening_imports(tree):
    """Return the imports a file opens with: every import statement before the first statement that is neither an import nor the docstring."""
    found = []
    for place, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and not getattr(node, 'level', 0):
            found.append(node)
        elif found or not (place == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)):
            break
    return found


def merged(lines):
    """Return a group's lines with those that import from one module made one line, but for a line with a comment after it, which stays its own."""
    by_module = {}
    result = []
    for line in lines:
        if not line.is_from or line.comment:
            result.append(line)
        elif line.module in by_module:
            known = by_module[line.module]
            known.aliases += [alias for alias in line.aliases if (alias.name, alias.asname) not in {(have.name, have.asname) for have in known.aliases}]
        else:
            by_module[line.module] = line
            result.append(line)
    return sorted(result, key=Line.order)


def sorted_source(*, source, tools):
    """Return a file's source with its opening imports sorted, or None for a file left alone because a comment stands among them."""
    tree = ast.parse(source)
    nodes = opening_imports(tree)
    if not nodes:
        return source
    lines = source.split('\n')
    first = nodes[0].lineno - 1
    last = nodes[-1].end_lineno
    covered = {number for node in nodes for number in range(node.lineno - 1, node.end_lineno)}
    for number in range(first, last):
        inside = number in covered and not any(node.lineno - 1 == node.end_lineno - 1 == number for node in nodes)
        if (number not in covered and lines[number].strip()) or (inside and COMMENT in lines[number]):
            return None
    system = []
    project = []
    for node in nodes:
        after = lines[node.end_lineno - 1].encode(FILE_ENCODING)[node.end_col_offset:].decode(FILE_ENCODING)
        if isinstance(node, ast.ImportFrom):
            line = Line(module=node.module, aliases=list(node.names), is_from=True, comment=after)
        else:
            line = Line(module=node.names[0].name, aliases=list(node.names), is_from=False, comment=after)
        (project if is_of_project(module=line.module, tools=tools) else system).append(line)
    groups = [[line.text() for line in merged(group)] for group in (system, project) if group]
    block = groups[0] if len(groups) == 1 else [*groups[0], '', *groups[1]]
    return '\n'.join([*lines[:first], *block, *lines[last:]])


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--write', action='store_true', help='rewrite the files; without it, only list them')
    options = parser.parse_args(arguments)
    tools = tool_modules()
    changed = 0
    for path in python_files():
        source = path.read_text(encoding=FILE_ENCODING)
        result = sorted_source(source=source, tools=tools)
        name = path.relative_to(ROOT).as_posix()
        if result is None:
            print(LEFT_ALONE.format(path=name))
        elif result != source:
            changed += 1
            if options.write:
                path.write_text(result, encoding=FILE_ENCODING)
            else:
                print(OUT_OF_ORDER.format(path=name))
    print(SUMMARY.format(files=changed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
