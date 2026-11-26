# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The list a Generators field opens as a presenter: generators by name, a chain among them, in the order they run, a generator
listed more than once running more than once. It edits whatever list its page hands over: names() returns the list as it is,
and store(names) keeps a new one, so that the clip page, the Scene page and the track editor share it."""

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.pages.generator_names import generators_to_add, listed_generator
from llamatron.user_strings import labels


class GeneratorListPresenter:
    """What the list of generators shows and does to the list it is handed."""

    COLUMNS = (ListColumn(heading=labels.Column.SELECT_ANY_GENERATOR, width=None, align=Align.LEFT),)

    __slots__ = ('_document', '_names', '_store')

    def __init__(self, *, document, names, store):
        self._document = document
        self._names = names
        self._store = store

    def rows(self):
        """Return each generator's place in the list and its row, its name as lists show it."""
        setlist = self._document.get_setlist()
        return [(place, [listed_generator(setlist=setlist, name=name)]) for place, name in enumerate(self._names())]

    def offered(self):
        """Return the names of the generators that can be added, and each as the picker shows it."""
        setlist = self._document.get_setlist()
        names = [name for _, name in generators_to_add(setlist)]
        return names, [listed_generator(setlist=setlist, name=name) for name in names]

    def add(self, name):
        """Add a generator at the end of the list, and return its place."""
        self._store([*self._names(), name])
        return len(self._names()) - 1

    def remove(self, place):
        names = self._names()
        names.pop(place)
        self._store(names)

    def swap(self, *, place, offset):
        """Swap the generator at a place with its neighbour offset away, and return whether it moved."""
        names = self._names()
        moved = place + offset
        if not 0 <= moved < len(names):
            return False
        names[place], names[moved] = names[moved], names[place]
        self._store(names)
        return True
