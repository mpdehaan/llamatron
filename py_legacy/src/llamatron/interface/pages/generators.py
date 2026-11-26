# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Generators page as a presenter: every generator of the set under a heading for its type, the types sorted by name and
the generators sorted under each, a type's generators showing while it is open, then the row that adds one."""

from typing import NamedTuple

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.pages import generator_kinds
from llamatron.interface.pages.places import ItemPlace
from llamatron.model.objects.naming import name_order
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import labels, marks

# The kinds of row the page lists: a generator, a type's heading, and the row that adds a generator.
GENERATOR = 'generator'
HEADING = 'heading'
NEW_GENERATOR = 'new generator'
# How far a type's generators stand in from its heading.
INDENT = '    '
USED_WIDTH = 4
NO_TEXT = ''


class Listed(NamedTuple):
    """What a row of the Generators page is: the row's kind, the generators' kind, and the generator's name on a generator's row."""

    row: str
    kind: object = None
    name: object = None


class GeneratorsPresenter:
    """What the Generators page lists: its rows, from the set, which keeps which types are open, and whether a search looks
    inside every type."""

    COLUMNS = (ListColumn(heading=labels.Column.SELECT_ANY_GENERATOR, width=None, align=Align.LEFT), ListColumn(heading=labels.Column.USED, width=USED_WIDTH, align=Align.RIGHT))

    __slots__ = ('_document',)

    def __init__(self, *, document):
        self._document = document

    def kinds(self):
        """Return the kinds of generator the set has any of, sorted by what the tracker calls each."""
        held = {kind for kind, _ in self._document.get_setlist().ordered_generators()}
        return sorted(held, key=lambda kind: name_order(generator_kinds.kind_listed(kind).label))

    def names_of_kind(self, kind):
        return sorted(self._document.names_of(generator_plugins.listed_sections()[kind]), key=name_order)

    def is_closed(self, kind):
        """Return whether a type is closed, as every type is until opened; the set keeps which are open, so that the page comes
        back as it was left."""
        return not self._document.get_page_memory().is_generator_type_open(kind)

    def rows(self, *, searching):
        """Return every type's rows, then the row that adds a generator."""
        rows = []
        for kind in self.kinds():
            rows += self.kind_rows(kind=kind, searching=searching)
        rows.append((Listed(NEW_GENERATOR), self.one_cell(marks.MSG_NEW_ROW)))
        return rows

    def kind_rows(self, *, kind, searching):
        """Return a type's rows: its heading, and while it is open, or a search looks inside it, its generators."""
        names = self.names_of_kind(kind)
        closed = self.is_closed(kind) and not searching
        mark = marks.MSG_SECTION_CLOSED_MARK if closed else marks.MSG_SECTION_OPEN_MARK
        heading = labels.MSG_GROUP_HEADING.format(mark=mark, name=generator_kinds.kind_listed(kind).label, count=len(names))
        rows = [(Listed(HEADING, kind), self.one_cell(heading))]
        if not closed:
            rows += [(Listed(GENERATOR, kind, name), [INDENT + name, len(self.uses(kind=kind, name=name))]) for name in names]
        return rows

    def one_cell(self, text):
        """Return the cells of a row that holds only its first."""
        return [text, *[NO_TEXT] * (len(self.COLUMNS) - 1)]

    def uses(self, *, kind, name):
        return self._document.uses(section=generator_plugins.listed_sections()[kind], name=name)

    @staticmethod
    def place_of(*, kind, name):
        """Return the place of a generator's own page."""
        return ItemPlace(section=generator_kinds.kind_listed(kind).section, name=name)
