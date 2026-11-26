# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Scales page as a presenter: the set's scales, each with its notes, its size and how much uses it, the song's own marked."""

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.pages.places import ItemPlace
from llamatron.model.schema.file_format import Section
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import scale_type_name, ScaleType
from llamatron.user_strings import labels, marks, names

# What a new scale is until changed: C major.
NEW_SCALE_ROOT = NoteName.C
NEW_SCALE_KIND = scale_type_name(ScaleType.MAJOR)
NO_MARK = ''


class ScaleListPresenter:
    """What the Scales page lists and does. Its page does what only the tracker can: put_cursor_on(name) and open_place(place)."""

    COLUMNS = (
        ListColumn(heading=labels.Column.SELECT_SCALE, width=None, align=Align.LEFT), ListColumn(heading=labels.Column.SCALE, width=24, align=Align.LEFT),
        ListColumn(heading=labels.Column.NOTES, width=5, align=Align.RIGHT), ListColumn(heading=labels.Column.USED, width=4, align=Align.RIGHT),
    )

    __slots__ = ('_page', '_document')

    def __init__(self, *, page, document):
        self._page = page
        self._document = document

    def rows(self):
        """Return each scale's name and its row: its name, marked where it is the song's, its notes, its size and its uses."""
        document = self._document
        song = document.song()
        rows = []
        for name in document.names_of(Section.SCALES):
            mark = marks.MSG_SONG_SCALE_MARK if song.get_scale_name() == name else NO_MARK
            uses = document.uses(section=Section.SCALES, name=name)
            rows.append((name, [name + mark, document.scale_notes_text(name), document.scale_size(name), len(uses)]))
        return rows

    @staticmethod
    def place_of(name):
        """Return the place of a scale's own page."""
        return ItemPlace(section=Section.SCALES, name=name)

    def add(self):
        """Add a C major scale, named by its number as every new thing is (since a name after its notes was wrong once the notes
        changed), and open its page to change it."""
        name = self._document.new_name(section=Section.SCALES, word=names.MSG_NEW_SCALE_WORD)
        self._document.add_scale(name=name, root=NEW_SCALE_ROOT, kind=NEW_SCALE_KIND)
        self._page.put_cursor_on(name)
        self._page.open_place(self.place_of(name))
