# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Grooves page as a presenter: every groove a song can choose, the factory ones first, each with its cells, its cell length
and its uses."""

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.forms.text import numbers_text
from llamatron.interface.pages.places import ItemPlace
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels, marks, names


class GrooveListPresenter:
    """What the Grooves page lists and does. Its page does what only the tracker can: put_cursor_on(name) and open_place(place)."""

    COLUMNS = (
        ListColumn(heading=labels.Column.SELECT_GROOVE, width=None, align=Align.LEFT), ListColumn(heading=labels.Column.FROM, width=9, align=Align.LEFT),
        ListColumn(heading=labels.Column.CELLS, width=40, align=Align.LEFT), ListColumn(heading=labels.Column.CELL, width=5, align=Align.RIGHT),
        ListColumn(heading=labels.Column.USED, width=4, align=Align.RIGHT),
    )

    __slots__ = ('_page', '_document')

    def __init__(self, *, page, document):
        self._page = page
        self._document = document

    def rows(self):
        """Return each groove's name and its row: its name, whether it is a factory groove, its cells, its cell length and its uses."""
        setlist = self._document.get_setlist()
        rows = []
        for name in self._document.names_of(Section.GROOVES):
            kept = setlist.get_groove(name)
            source = marks.MSG_FACTORY_GROOVE_SHOWN if setlist.is_factory_groove(name) else marks.MSG_OWN_GROOVE_SHOWN
            uses = self._document.uses(section=Section.GROOVES, name=name)
            rows.append((name, [name, source, numbers_text(kept.get_cells()), kept.get_cell_length_text(), len(uses)]))
        return rows

    @staticmethod
    def place_of(name):
        """Return the place of a groove's own page."""
        return ItemPlace(section=Section.GROOVES, name=name)

    @staticmethod
    def is_factory(name):
        """Return whether a groove is one of the factory grooves, which can only be looked at and copied."""
        return Setlist.is_factory_groove(name)

    @staticmethod
    def own_place(place):
        """Return a groove's place among the set's own grooves from its row, the factory ones coming first."""
        return place - Setlist.factory_groove_count()

    def add(self):
        """Add a straight groove, numbered like new tracks and scenes, and open it."""
        name = self._document.new_name(section=Section.GROOVES, word=names.MSG_NEW_GROOVE_WORD)
        self._document.add_groove(name)
        self._page.put_cursor_on(name)
        self._page.open_place(self.place_of(name))
