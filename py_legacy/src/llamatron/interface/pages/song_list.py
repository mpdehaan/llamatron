# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Songs page as a presenter: every song of the set, the current one marked, each with its tempo, its scale, and how many
tracks and scenes it has."""

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.forms.text import tempo_text
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels, marks, messages

NO_MARK = ''
NO_NAME = ''


class SongListPresenter:
    """What the Songs page lists and does. Its page does what only the tracker can: ask_name, put_cursor_on(name) and opening
    a song's settings."""

    COLUMNS = (
        ListColumn(heading=labels.Column.SELECT_SONG, width=None, align=Align.LEFT), ListColumn(heading=labels.Column.CURRENT, width=7, align=Align.LEFT),
        ListColumn(heading=labels.Column.TEMPO, width=7, align=Align.RIGHT), ListColumn(heading=labels.Column.SCALE, width=14, align=Align.LEFT),
        ListColumn(heading=labels.Column.TRACKS, width=6, align=Align.RIGHT), ListColumn(heading=labels.Column.SCENES, width=6, align=Align.RIGHT),
    )

    __slots__ = ('_page', '_document')

    def __init__(self, *, page, document):
        self._page = page
        self._document = document

    def rows(self):
        """Return each song's name and its row: its name, whether it is current, its tempo, its scale and its tracks and scenes."""
        setlist = self._document.get_setlist()
        current = self._document.get_current_song_name()
        rows = []
        for name in self._document.names_of(Section.SONGS):
            song = setlist.get_song(name)
            mark = marks.MSG_CURRENT_SONG_MARK if name == current else NO_MARK
            rows.append((name, [name, mark, tempo_text(song.get_tempo()), song.get_scale_name() or marks.MSG_NONE_SHOWN, len(song.get_track_names()), len(song.get_scenes())]))
        return rows

    def make_current(self, name):
        self._document.select_song(name)

    def add(self):
        """Ask for a new song's name, and add it."""
        taken = self._document.names_of(Section.SONGS)
        self._page.ask_name(title=messages.MSG_NEW_SONG_PROMPT, value=NO_NAME, taken=taken, then=self._named)

    def _named(self, text):
        self._document.add_song(text)
        self._page.put_cursor_on(text)
