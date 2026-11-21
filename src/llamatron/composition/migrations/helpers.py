# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The helpers every migration may use, which never change once a migration uses them."""

from llamatron.support.version import is_version, version_numbers

# What a file records the version that saved it under, and the name of a named thing in the layout of lists.
VERSION = 'version'
NAME = 'name'


def saved_before(*, data, version):
    """Return whether a file records being saved by a version of llamatron older than one."""
    saved = data.get(VERSION)
    return is_version(saved) and version_numbers(saved) < version_numbers(version)


def has_version(data):
    return is_version(data.get(VERSION))


def as_items(mapping, *, key=NAME):
    """Return a mapping of things by name as a list, each item a copy of the thing's settings with its name first under key. A
    value that is not settings is left as it was, for the reader to refuse."""
    if not isinstance(mapping, dict) or not all(isinstance(settings, dict) for settings in mapping.values()):
        return mapping
    return [{key: name, **settings} for name, settings in mapping.items()]


def with_key_replaced(settings, *, old, new, value):
    """Return a copy of settings with one key put in place of another, in its place, holding a value."""
    return {(new if key == old else key): (value if key == old else held) for key, held in settings.items()}


def name_references(names):
    """Return a list of names as the file writes references to things by name, each { name: x }."""
    return [{NAME: name} for name in names] if isinstance(names, list) else names
