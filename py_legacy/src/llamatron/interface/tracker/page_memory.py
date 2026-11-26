# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the pages remember of how they show a set, which is no part of the set's music: the types of generator the Generators
page shows open. The set keeps it as a record its file holds, which
nothing undoes and saving keeps, and the document holds this memory of it."""

from llamatron.model.schema import file_format, generator_plugins


class PageMemory:
    """The pages' open and closed state for one set, read from the record its file held and written back to it as it is saved."""

    __slots__ = ('_open_types',)

    def __init__(self, record):
        """record is what the set's file held of it, by the file's names, each a list, anything else taken as none."""
        self._open_types = [kind for kind in _texts(record.get(file_format.OPEN_GENERATOR_TYPES)) if generator_plugins.is_plugin(kind)]

    def record(self, setlist):
        """Return what the set's file holds of it, leaving out a type no generator is of any more."""
        record = {}
        opened = self.open_generator_types(setlist)
        if opened:
            record[file_format.OPEN_GENERATOR_TYPES] = opened
        return record

    def is_generator_type_open(self, kind):
        return kind in self._open_types

    def show_generator_type(self, *, kind, opened):
        """Show a type of generator open or closed on the Generators page."""
        self._open_types = [held for held in self._open_types if held != kind]
        if opened:
            self._open_types.append(kind)

    def open_generator_types(self, setlist):
        """Return the types of generator the Generators page shows open, in the order the plugins are listed, leaving out any the set has no generator of any more."""
        return [kind for kind in generator_plugins.plugins() if kind in self._open_types and setlist.get_generator_names(kind)]


def _texts(held):
    """Return the texts of a list a file held, and none where it held anything else, since a view's state is never worth refusing a file for."""
    return [value for value in held if isinstance(value, str)] if isinstance(held, list) else []
