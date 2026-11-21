# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The contract every generator plugin fills, and the plugins found.

A generator plugin is a folder under engine/generators/ whose declaration.py holds a PLUGIN: the name a set file and a chain
write it by, the section of a set that holds its generators, and the class of its settings, which reads and checks them and makes
the generator that runs. The Model reads a set's generators through this contract alone, so it names no plugin: the plugins are
found once, by looking in their folder, the first time any is asked for, and a new generator changes no file outside its folder.
"""

import functools
import importlib
import pkgutil
from typing import NamedTuple

# Where the plugins are, and the module of each that declares it.
PLUGINS_PACKAGE = 'llamatron.engine.generators'
DECLARATION = 'declaration'


class GeneratorPlugin(NamedTuple):
    """What a generator plugin declares: its name, the section of a set that holds its generators, and its settings' class."""

    name: str
    section: str
    settings: type


@functools.cache
def plugins():
    """Return every generator plugin by its name, found once: each folder of the plugins' package with a declaration."""
    package = importlib.import_module(PLUGINS_PACKAGE)
    found = {}
    for folder in pkgutil.iter_modules(package.__path__):
        if folder.ispkg:
            plugin = importlib.import_module(f'{PLUGINS_PACKAGE}.{folder.name}.{DECLARATION}').PLUGIN
            found[plugin.name] = plugin
    return found


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
