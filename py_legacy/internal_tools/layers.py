# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Find the imports that cross the program's layers the wrong way, and keep the list of those still allowed.

The program is layers of packages, each presenting a few modules to the layers above. Three rules
say what an import may do, and tests/rules/test_layers.py holds them:

- Order. A package imports only packages below it in LAYERS.
- Front doors. Outside a package of FRONT_DOORS, only its front-door modules are imported, and
  the real-time package is imported only by the files of REALTIME_USERS.
- Pages. A page, a file under interface/tracker/screens/ outside shared/, imports no other page, and of the
  model in model/ only the schema's names and the version of PAGE_SCHEMA, and the values.

The imports that broke a rule when it was made are listed in tests/rules/layer_exceptions.py,
and the list may only shrink: a new crossing fails the test, and so does a listed crossing that
is gone, until this tool takes it off the list.

    internal_tools/layers.sh             # list the crossings, each marked allowed or new
    internal_tools/layers.sh --prune     # take the crossings that are gone off the list of those allowed
"""

import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'src' / 'llamatron'
EXCEPTIONS_FILE = ROOT / 'tests' / 'rules' / 'layer_exceptions.py'
PROGRAM = 'llamatron'
PYTHON_FILES = '*.py'
FILE_ENCODING = 'utf-8'
DOT = '.'
# What stands for any one module's name in a front door.
WILDCARD = '*'
TOP = '(top)'
# The packages from the bottom up: each imports only those before it. The strings package is text every layer may name.
# music_theory comes in two tiers: its fundamentals, facts that know nothing of llamatron's objects, under the model; the rest,
# which understands patterns and songs, over the model and under the engine, whose generators ask it.
FUNDAMENTALS = 'music_theory.fundamentals'
MUSIC_THEORY = 'music_theory'
LAYERS = ('math', FUNDAMENTALS, 'caching', 'user_strings', 'model', MUSIC_THEORY, 'engine', 'exporters', 'importers', 'realtime',
          'wizards', 'interface', TOP)
VOCABULARY_PACKAGES = ('user_strings',)
# The modules of a package that the packages above it may import.
FRONT_DOORS = {
    # Of the Engine, the Realizer is reached only through the song's realizer; its clips, timing, parts and plugins are open.
    # Of the generator plugins, a plugin's package, declaration, model, schema and strings, and the registry and the parts their models own.
    'engine': ('clips', 'timing', 'realizer.song_realizer', 'realizer.as_written', 'generators.registry',
               'generators.*', 'generators.*.model', 'generators.*.schema', 'generators.*.strings', 'generators.*.declaration'),
    # Of the Model, its values and schema, the set and the song, the names it makes, and the toolkit that settings and the generator
    # plugins' models are written with; the rest of its objects and its file are its own.
    'model': ('values', 'schema', 'objects.setlist', 'objects.song', 'objects.naming', 'objects.llama_data', 'objects.traits',
              'objects.conditions', 'objects.shapes', 'objects.strum', 'objects.velocity_ramps', 'file.song_file_error',
              'file.checks', 'file.invalid_value', 'file.corrections', 'file.version', 'file.files'),
    'exporters': ('exports',),
    'importers': ('midi_import',),
    'wizards': ('create_song.wizard_choices', 'create_song.wizard_limits', 'create_song.wizard_names', 'create_song.wizard_file'),
    # Real-time playback is reached through its door: what the tracker uses, and the words they share.
    'realtime': ('playback_service', 'realtime_names'),
}
# The only files outside the real-time package that import it.
REALTIME_USERS = ('interface/tracker/transport.py', 'interface/tracker/pattern_preview.py', 'cli.py')
REALTIME = 'realtime'
PAGES_FOLDER = ('interface', 'tracker', 'screens')
SHARED_PAGES = 'shared'
MODEL = 'model'
# What a page may import of the Model: its names, which are words and no behaviour, the generator plugins found, and the version every file records.
PAGE_SCHEMA = (('schema', 'file_format'), ('schema', 'generator_plugins'), ('file', 'version'))
# The Model's musical values, which every page may use, as it always could.
PAGE_VALUES = 'values'
# The rules' names, which the list of exceptions is kept under.
ORDER = 'order'
DOORS = 'front doors'
PAGES = 'pages'
RULES = (ORDER, DOORS, PAGES)
CROSSING = '{file} imports {module}'
SHOWN = '{rule}: {crossing} ({state})'
ALLOWED = 'allowed'
NEW = 'new'
GONE = 'gone'
SUMMARY = '{rule}: {count} allowed, {new} new, {gone} gone'
EXCEPTIONS_NAME = 'ALLOWED'
EXCEPTIONS_START = "ALLOWED = {\n"
EXCEPTIONS_RULE = "    {rule!r}: (\n"
EXCEPTIONS_ROW = "        {crossing!r},\n"
EXCEPTIONS_RULE_END = "    ),\n"
EXCEPTIONS_END = "}\n"


def is_front_door(*, module, doors):
    """Return whether a module of the program, as parts under the program, is one of a package's front doors, named below the package."""
    below = DOT.join(module[1:])
    return any(door_pattern(door).fullmatch(below) for door in doors)


def door_pattern(door):
    """Return what a front door matches: the module it names and every module inside it, or, where * stands for one module's
    name, as for each generator plugin, that module alone."""
    if WILDCARD in door:
        return re.compile(re.escape(door).replace(re.escape(WILDCARD), '[^.]+'))
    return re.compile(re.escape(door) + r'(\..+)?')


def package_of(parts):
    """Return the package a file or a module of the program is in, from its parts under the program: its first folder, or the
    top; music_theory's fundamentals are a layer of their own."""
    if len(parts) > 2 and DOT.join(parts[:2]) == FUNDAMENTALS:
        return FUNDAMENTALS
    return parts[0] if len(parts) > 1 else TOP


def imported_modules(tree):
    """Return the modules of the program a file imports, each as its parts under the program: ('engine', 'realizer', 'song_realizer')."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level and node.module.split(DOT)[0] == PROGRAM:
            base = tuple(node.module.split(DOT)[1:])
            for alias in node.names:
                whole = (*base, alias.name)
                found.add(whole if is_module(whole) else base)
    return {parts for parts in found if parts}


def is_module(parts):
    return (SOURCE / pathlib.Path(*parts)).with_suffix('.py').exists() or (SOURCE / pathlib.Path(*parts)).is_dir()


def is_page(parts):
    return parts[:len(PAGES_FOLDER)] == PAGES_FOLDER and len(parts) > len(PAGES_FOLDER) + 1 and parts[len(PAGES_FOLDER)] != SHARED_PAGES


def breaks(*, file, module):
    """Return the rules an import breaks: file and module are parts under the program, the file with its .py."""
    own = package_of(file)
    other = package_of(module)
    broken = []
    if other == own or other in VOCABULARY_PACKAGES:
        return broken
    if other in LAYERS and own in LAYERS and LAYERS.index(other) > LAYERS.index(own):
        broken.append(ORDER)
    if other in FRONT_DOORS:
        allowed_file = other != REALTIME or '/'.join(file) in REALTIME_USERS
        allowed_module = is_front_door(module=module, doors=FRONT_DOORS[other])
        if not (allowed_file and allowed_module):
            broken.append(DOORS)
    if is_page(file) and other == MODEL and tuple(module[1:3]) not in PAGE_SCHEMA and tuple(module[1:2]) != (PAGE_VALUES,):
        broken.append(PAGES)
    return broken


def page_breaks(*, file, module):
    """Return whether a page imports another page, which the order of packages cannot see, both being in the text UI."""
    return is_page(file) and is_page((*module, '')) and module != file[:-1] + (file[-1][:-len('.py')],)


def crossings():
    """Return every import that breaks a rule, by rule: each a line naming the file and the module."""
    found = {rule: set() for rule in RULES}
    for path in sorted(SOURCE.rglob(PYTHON_FILES)):
        file = path.relative_to(SOURCE).parts
        for module in imported_modules(ast.parse(path.read_text(encoding=FILE_ENCODING))):
            line = CROSSING.format(file='/'.join(file), module=DOT.join(module))
            for rule in breaks(file=file, module=module):
                found[rule].add(line)
            if page_breaks(file=file, module=module):
                found[PAGES].add(line)
    return {rule: sorted(lines) for rule, lines in found.items()}


def allowed():
    """Return the crossings still allowed, by rule, as the exceptions file lists them."""
    if not EXCEPTIONS_FILE.exists():
        return {rule: [] for rule in RULES}
    names = {}
    exec(compile(EXCEPTIONS_FILE.read_text(encoding=FILE_ENCODING), str(EXCEPTIONS_FILE), 'exec'), names)
    return {rule: list(names[EXCEPTIONS_NAME].get(rule, ())) for rule in RULES}


def exceptions_text(*, header, lists):
    """Return the exceptions file's text: its header and docstring as they are, then the lists."""
    text = header + EXCEPTIONS_START
    for rule in RULES:
        text += EXCEPTIONS_RULE.format(rule=rule) + ''.join(EXCEPTIONS_ROW.format(crossing=crossing) for crossing in lists[rule]) + EXCEPTIONS_RULE_END
    return text + EXCEPTIONS_END


def pruned(*, found, listed):
    """Return the allowed crossings with those that are gone taken off: a list only ever loses rows."""
    return {rule: [crossing for crossing in listed[rule] if crossing in found[rule]] for rule in RULES}


def main(*, arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--prune', action='store_true', help='take the crossings that are gone off the list of those allowed')
    parser.add_argument('--quiet', action='store_true', help='print only the summary')
    options = parser.parse_args(arguments)
    found = crossings()
    listed = allowed()
    for rule in RULES:
        new = [crossing for crossing in found[rule] if crossing not in listed[rule]]
        gone = [crossing for crossing in listed[rule] if crossing not in found[rule]]
        if not options.quiet:
            for crossing in found[rule]:
                print(SHOWN.format(rule=rule, crossing=crossing, state=NEW if crossing in new else ALLOWED))
            for crossing in gone:
                print(SHOWN.format(rule=rule, crossing=crossing, state=GONE))
        print(SUMMARY.format(rule=rule, count=len(found[rule]) - len(new), new=len(new), gone=len(gone)))
    if options.prune:
        text = EXCEPTIONS_FILE.read_text(encoding=FILE_ENCODING)
        header = text[:text.index(EXCEPTIONS_START)]
        EXCEPTIONS_FILE.write_text(exceptions_text(header=header, lists=pruned(found=found, listed=listed)), encoding=FILE_ENCODING)
    return 0


if __name__ == '__main__':
    sys.exit(main())
