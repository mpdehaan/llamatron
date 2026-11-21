# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Name every constant through the module that defines it: `from package import module`, then `module.NAME`.

A file that reads `from llamatron.music.sound import KIND, Sound` and then `sound[KIND]` is
rewritten to read `from llamatron.music import sound` beside `from llamatron.music.sound import
Sound`, and `sound.KIND`. A constant is a name in capitals that its module assigns; a class or a
function keeps its import, whatever its name. A constant one module imports and another takes
from there is named through the module that defines it. Where the module's name is already a
name of the file, or a built-in, the module is imported as `<module>_values`.

    internal_tools/constants_by_module.sh                  # list what would change
    internal_tools/constants_by_module.sh --write          # rewrite the files
    internal_tools/constants_by_module.sh --write --from llamatron.music llamatron.support   # only constants those packages define

Nothing is rewritten by matching text: each file's syntax tree says where every import and
every use is. internal_tools/check_before_commit.sh runs it with --write to keep the rule.
"""

import argparse
import ast
import builtins
import keyword
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_FOLDER = 'src'
TESTS_FOLDER = 'tests'
TOOLS_FOLDERS = ('internal_tools', 'user_scripts')
PYTHON_FILES = '*.py'
PACKAGE_FILE = '__init__'
FILE_ENCODING = 'utf-8'
DOT = '.'
# The strings package's modules import names from each other, which keeps them free of everything else.
STRINGS_PACKAGE = 'llamatron.strings'
# What a module is imported as where its own name is taken in the file.
OTHER_NAME = '{name}_values'
FROM_IMPORT = '{indent}from {package} import {names}'
PLAIN_IMPORT = '{indent}import {names}'
AS_NAME = '{name} as {other}'
NAME_SEPARATOR = ', '
THROUGH_MODULE = '{module}.{name}'
FOUND = '{path}:{line} imports {names} from {module}'
SKIPPED = '{path}:{line} is left alone: {why}'
WHY_ASSIGNED = '{name} is also assigned in the file'
WHY_COMMENT = 'a comment stands inside the import'
SUMMARY = '{names} names in {files} files'
CALLABLE = 'callable'
CONSTANT = 'constant'


def is_constant_name(name):
    """Return whether a name is written as a constant: in capitals, with a letter."""
    return name == name.upper() and any(character.isalpha() for character in name)


def module_name_of(path):
    """Return the name a file is imported by: a dotted name under src/ and tests/, the file's own name for a tool."""
    parts = path.relative_to(ROOT).with_suffix('').parts
    if parts[0] == SOURCE_FOLDER:
        parts = parts[1:]
    elif parts[0] != TESTS_FOLDER:
        parts = parts[-1:]
    if parts[-1] == PACKAGE_FILE:
        parts = parts[:-1]
    return DOT.join(parts)


def python_files():
    return sorted(path for folder in (SOURCE_FOLDER, TESTS_FOLDER, *TOOLS_FOLDERS) for path in (ROOT / folder).rglob(PYTHON_FILES))


class Module:
    """One file of the project: what it defines at its top level, as a constant or as a class or function, and what it imports by name."""

    __slots__ = ('name', 'path', 'source', 'tree', 'defined', 'imported')

    def __init__(self, *, name, path, source):
        self.name = name
        self.path = path
        self.source = source
        self.tree = ast.parse(source)
        self.defined = {}
        self.imported = {}
        self._read(self.tree.body)

    def _read(self, statements):
        """Note what a run of top-level statements defines and imports, going into the branches of an if or a try."""
        for node in statements:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                self.defined[node.name] = CALLABLE
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name):
                            self.defined.setdefault(name.id, CONSTANT)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                for alias in node.names:
                    self.imported[alias.asname or alias.name] = (node.module, alias.name)
            elif isinstance(node, (ast.If, ast.Try, ast.With)):
                for branch in ('body', 'orelse', 'finalbody'):
                    self._read(getattr(node, branch, []))
                for handler in getattr(node, 'handlers', []):
                    self._read(handler.body)


class Project:
    """Every module of the project by the name it is imported by, and where each imported name is defined."""

    __slots__ = ('modules',)

    def __init__(self, modules):
        self.modules = {module.name: module for module in modules}

    @staticmethod
    def read():
        return Project([Module(name=module_name_of(path), path=path, source=path.read_text(encoding=FILE_ENCODING)) for path in python_files()])

    def origin(self, *, module, name):
        """Return the module that defines a name another imports from a module, whether it is a constant, and what that module calls it, which differs where an import on the way renamed it: (module name, kind, name), or None for a module outside the project."""
        seen = set()
        while module in self.modules and (module, name) not in seen:
            seen.add((module, name))
            found = self.modules[module]
            if name in found.defined:
                return module, found.defined[name], name
            if name not in found.imported:
                return module, CONSTANT, name
            module, name = found.imported[name]
        return (module, CONSTANT, name) if module in self.modules else None


class Move:
    """One constant a file imports by name: where its import stands, what the file calls it, and the module and name it is defined by."""

    __slots__ = ('node', 'local', 'module', 'name')

    def __init__(self, *, node, local, module, name):
        self.node = node
        self.local = local
        self.module = module
        self.name = name


def is_in_strings(name):
    return name == STRINGS_PACKAGE or name.startswith(STRINGS_PACKAGE + DOT)


def moves_of(*, module, project, prefixes=None):
    """Return the constants a module imports by name that are to be named through their modules, as Moves, in the order they are imported.

    The strings package's own modules are left alone. prefixes, when given, keeps only the
    constants defined by modules of those names or under them.
    """
    if is_in_strings(module.name):
        return []
    moves = []
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.ImportFrom) or not node.module or node.level:
            continue
        for alias in node.names:
            if not is_constant_name(alias.name):
                continue
            origin = project.origin(module=node.module, name=alias.name)
            if origin is None or origin[1] == CALLABLE:
                continue
            if prefixes and not any(origin[0] == prefix or origin[0].startswith(prefix + DOT) for prefix in prefixes):
                continue
            moves.append(Move(node=node, local=alias.asname or alias.name, module=origin[0], name=origin[2]))
    return moves


def find_names_imported(*, project, module):
    """Return a line for each import in a module that takes a constant out of a module of the project by name, which the rule's test reads."""
    lines = {}
    for move in moves_of(module=module, project=project):
        lines.setdefault((move.node.lineno, move.node.module), []).append(move.name)
    path = module.path.relative_to(ROOT).as_posix()
    return [FOUND.format(path=path, line=line, names=NAME_SEPARATOR.join(names), module=name) for (line, name), names in sorted(lines.items())]


def module_aliases(tree):
    """Return the modules a file imports whole, by the name the file calls each."""
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                aliases[alias.asname or alias.name] = (node.module + DOT + alias.name, node)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname or DOT not in alias.name:
                    aliases[alias.asname or alias.name] = (alias.name, node)
    return aliases


def passed_on(*, module, project, prefixes=None):
    """Return each use of `module.NAME` where the module only imports the constant from another: (the use, the import that brought the module in, the module that defines the constant, its name there).

    Such a use stops working once the module in between names the constant through its own module.
    """
    if is_in_strings(module.name):
        return []
    aliases = module_aliases(module.tree)
    rebound = bound_names_but_imports(module.tree)
    found = []
    for node in ast.walk(module.tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and isinstance(node.ctx, ast.Load)):
            continue
        if node.value.id not in aliases or node.value.id in rebound or not is_constant_name(node.attr):
            continue
        through, statement = aliases[node.value.id]
        if through not in project.modules or node.attr in project.modules[through].defined:
            continue
        origin = project.origin(module=through, name=node.attr)
        if origin is None or origin[1] == CALLABLE or origin[0] == through:
            continue
        if prefixes and not any(origin[0] == prefix or origin[0].startswith(prefix + DOT) for prefix in prefixes):
            continue
        found.append((node, statement, origin[0], origin[2]))
    return found


def bound_names_but_imports(tree):
    """Return every name a file assigns or takes as a parameter, which an import's name may be hidden by."""
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))}
    return names | {node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)}


def assigned_outside_classes(tree):
    """Return every name a file assigns but for a class's own attributes, which are read through the class and hide no import."""
    of_classes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for statement in node.body:
                if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                    targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                    of_classes.update(id(name) for target in targets for name in ast.walk(target) if isinstance(name, ast.Name))
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and id(node) not in of_classes}


def bound_names(tree):
    """Return every name a file binds itself: what it assigns, its parameters, its functions and classes, and what it imports."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((alias.asname or alias.name).split(DOT)[0] for alias in node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def split_module(name):
    """Return a module's package and its own name: ('llamatron.music', 'sound'), or (None, 'measuring') for a module with no package."""
    package, _, own = name.rpartition(DOT)
    return (package or None), own


def imported_as(*, tree, module):
    """Return the name a file already imports a module itself under, or None."""
    package, own = split_module(module)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == package and not node.level:
            for alias in node.names:
                if alias.name == own:
                    return alias.asname or alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module and (alias.asname or package is None):
                    return alias.asname or alias.name
    return None


def is_free(*, name, taken):
    return name not in taken and not hasattr(builtins, name) and not keyword.iskeyword(name)


def name_for(*, module, taken):
    """Return what a file imports a module as: the module's own name where that is free, and otherwise the name with a word after it, or its package's name before it."""
    package, own = split_module(module)
    choices = [own, OTHER_NAME.format(name=own)]
    if package:
        choices.append(split_module(package)[1] + '_' + own)
    return next(choice for choice in choices if is_free(name=choice, taken=taken))


def import_line(*, module, other, indent):
    """Return the line that imports a module itself, under another name where it needs one."""
    package, own = split_module(module)
    names = own if other == own else AS_NAME.format(name=own, other=other)
    if package is None:
        return PLAIN_IMPORT.format(indent=indent, names=names)
    return FROM_IMPORT.format(indent=indent, package=package, names=names)


def kept_line(*, node, moved, indent):
    """Return an import statement with the moved names taken out, on one line, or None when no name is left."""
    kept = [alias for alias in node.names if (alias.asname or alias.name) not in moved]
    if not kept:
        return None
    names = NAME_SEPARATOR.join(AS_NAME.format(name=alias.name, other=alias.asname) if alias.asname else alias.name for alias in kept)
    return FROM_IMPORT.format(indent=indent, package=node.module, names=names)


def replaced_in_line(*, line, changes):
    """Return a line with each (column, end column, text) put in, the columns counted in bytes as the syntax tree counts them."""
    data = line.encode(FILE_ENCODING)
    for start, end, text in sorted(changes, reverse=True):
        data = data[:start] + text.encode(FILE_ENCODING) + data[end:]
    return data.decode(FILE_ENCODING)


def rewritten(*, module, project, prefixes=None):
    """Return a module's source with its constants named through their modules, how many names moved, and a line for each import left alone and why."""
    moves = moves_of(module=module, project=project, prefixes=prefixes)
    lines = module.source.split('\n')
    path = module.path.relative_to(ROOT).as_posix()
    assigned = assigned_outside_classes(module.tree)
    skipped = []
    kept = []
    for move in moves:
        inside = lines[move.node.lineno - 1:move.node.end_lineno]
        if move.local in assigned:
            skipped.append(SKIPPED.format(path=path, line=move.node.lineno, why=WHY_ASSIGNED.format(name=move.local)))
        elif any('#' in line for line in inside) and move.node.end_lineno != move.node.lineno:
            skipped.append(SKIPPED.format(path=path, line=move.node.lineno, why=WHY_COMMENT))
        else:
            kept.append(move)
    passed = passed_on(module=module, project=project, prefixes=prefixes)
    if not kept and not passed:
        return module.source, 0, sorted(set(skipped))
    taken = bound_names(module.tree)
    names = {}
    already = {}
    for move in kept:
        if move.module not in names:
            already[move.module] = imported_as(tree=module.tree, module=move.module)
            names[move.module] = already[move.module] or name_for(module=move.module, taken=taken | set(names.values()))
    for _, _, origin, _ in passed:
        if origin not in names:
            already[origin] = imported_as(tree=module.tree, module=origin)
            names[origin] = already[origin] or name_for(module=origin, taken=taken | set(names.values()))
    top_level = {id(node) for node in module.tree.body}
    imported_at_top = {move.module for move in kept if id(move.node) in top_level}
    written = set()
    # Each import statement becomes the module's own import and what is left of the statement.
    statements = {}
    for move in kept:
        statements.setdefault(id(move.node), (move.node, []))[1].append(move)
    replaced = {}
    for node, moved in statements.values():
        indent = ' ' * node.col_offset
        new = []
        for move in moved:
            is_top = id(node) in top_level
            needed = already[move.module] is None and (is_top or move.module not in imported_at_top)
            if needed and (move.module, id(node) if not is_top else None) not in written:
                written.add((move.module, id(node) if not is_top else None))
                new.append(import_line(module=move.module, other=names[move.module], indent=indent))
        rest = kept_line(node=node, moved={move.local for move in moved}, indent=indent)
        if rest:
            new.append(rest)
        # A comment after a one-line import, such as one for a checker, stays on every line the import becomes.
        after = lines[node.end_lineno - 1].encode(FILE_ENCODING)[node.end_col_offset:].decode(FILE_ENCODING)
        replaced[node.lineno - 1] = (node.end_lineno, [line + after for line in new])
    uses = {move.local: THROUGH_MODULE.format(module=names[move.module], name=move.name) for move in kept}
    changes = {}
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in uses:
            changes.setdefault(node.lineno - 1, []).append((node.col_offset, node.end_col_offset, uses[node.id]))
    # A module a passed-on constant needs is imported straight after the import of the module the constant was read through.
    added = {}
    for node, statement, origin, name in passed:
        changes.setdefault(node.lineno - 1, []).append((node.col_offset, node.end_col_offset, THROUGH_MODULE.format(module=names[origin], name=name)))
        if already[origin] is None and origin not in imported_at_top and (origin, None) not in written:
            written.add((origin, None))
            added.setdefault(statement.end_lineno - 1, []).append(import_line(module=origin, other=names[origin], indent=' ' * statement.col_offset))
    result = []
    place = 0
    while place < len(lines):
        if place in replaced:
            end, new = replaced[place]
            result += new
            result += added.get(end - 1, [])
            place = end
            continue
        result.append(replaced_in_line(line=lines[place], changes=changes[place]) if place in changes else lines[place])
        result += added.get(place, [])
        place += 1
    return '\n'.join(result), len(kept) + len(passed), sorted(set(skipped))


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--write', action='store_true', help='rewrite the files; without it, only say what would change')
    parser.add_argument('--from', dest='prefixes', nargs='*', default=None, help='only the constants these modules or packages define')
    options = parser.parse_args(arguments)
    project = Project.read()
    moved = 0
    files = 0
    for module in project.modules.values():
        source, count, skipped = rewritten(module=module, project=project, prefixes=options.prefixes)
        for line in skipped:
            print(line)
        if count:
            moved += count
            files += 1
            if options.write:
                module.path.write_text(source, encoding=FILE_ENCODING)
    print(SUMMARY.format(names=moved, files=files))
    return 0


if __name__ == '__main__':
    sys.exit(main())
