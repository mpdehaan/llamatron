# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The contract every generator plugin fills, and the plugins found.

A generator plugin is a folder under engine/generators/ whose declaration.py holds a PLUGIN: the name a set file and a chain
write it by, the section of a set that holds its generators, the class of its settings, which reads and checks them and makes
the generator that runs, and its own words. Wherever llamatron lists or writes the plugins by kind, they come in the order of
their names. The Model reads a set's generators through this contract alone, so it names no plugin: the plugins are
found once, by looking in their folder, the first time any is asked for, and a new generator changes no file outside its folder.
"""

import functools
import importlib
import pkgutil
from typing import NamedTuple

from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Section

# Where the plugins are, and the module of each that declares it.
PLUGINS_PACKAGE = 'llamatron.engine.generators'
DECLARATION = 'declaration'


class GeneratorPlugin(NamedTuple):
    """What a generator plugin declares: its name, the section of a set that holds its generators, its settings' class, and
    its strings module, which holds every word it shows: MSG_LABEL, what it is called beside a generator's name, MSG_KIND_WORD,
    the word a generator named for its kind takes, MSG_CAPTION_WORD, the word its page's caption names it by, and
    MSG_CHANGED_WORD, the word an undo of a change to one of its generators says."""

    name: str
    section: str
    settings: type
    strings: object


@functools.cache
def plugins():
    """Return every generator plugin by its name, in the order of the names, found once: each folder of the plugins' package
    with a declaration."""
    package = importlib.import_module(PLUGINS_PACKAGE)
    found = []
    for folder in pkgutil.iter_modules(package.__path__):
        if folder.ispkg:
            found.append(importlib.import_module(f'{PLUGINS_PACKAGE}.{folder.name}.{DECLARATION}').PLUGIN)
    return {plugin.name: plugin for plugin in sorted(found, key=lambda plugin: plugin.name)}


@functools.cache
def plugins_by_section():
    """Return every generator plugin by the section of a set that holds its generators."""
    return {plugin.section: plugin for plugin in plugins().values()}


def settings_of(name):
    """Return the class of the settings of the generator plugin of a name."""
    return plugins()[name].settings


def is_plugin(name):
    """Return whether a name is a generator plugin's."""
    return name in plugins()


@functools.cache
def sections_by_name():
    """Return the section of a set that holds each plugin's generators, by the plugin's name, in the order of the names."""
    return {name: plugin.section for name, plugin in plugins().items()}


@functools.cache
def listed_sections():
    """Return the section of each kind a set file's list of generators holds, the chains last, by the kind's name."""
    return {**sections_by_name(), file_format.CHAIN_KIND: Section.CHAINS}


@functools.cache
def names_by_section():
    """Return each plugin's name by the section of a set that holds its generators."""
    return {plugin.section: name for name, plugin in plugins().items()}


def is_generator_entry(entry):
    """Return whether an entry of a generator order is a one-key map of a generator's kind, a plugin's or a chain's, to a name."""
    if not isinstance(entry, dict) or len(entry) != 1:
        return False
    kind, name = next(iter(entry.items()))
    return kind in listed_sections() and isinstance(name, str)


def sensible_generator_order(value):
    """Return a generator order made sensible: each entry a one-key map of a generator's kind to its name, anything else left
    out, never refused, since the order only says how the Generators page lists them; None for none."""
    entries = value if isinstance(value, list) else []
    kept = [dict(entry) for entry in entries if is_generator_entry(entry)]
    return kept or None


@functools.cache
def sections_adding_to_registers():
    """Return the sections of the plugins whose generators may add to the registers as they play."""
    return tuple(plugin.section for plugin in plugins().values() if plugin.settings.MAY_ADD_TO_REGISTERS)


@functools.cache
def names_naming(section):
    """Return the names of the plugins whose generators' settings name an item of a section, as a Hocket names a track."""
    return tuple(name for name, plugin in plugins().items() if section in plugin.settings.REFERENCES)
