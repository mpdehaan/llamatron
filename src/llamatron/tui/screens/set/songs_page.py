# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Songs page: the set's songs, which one is current, and each one's settings."""

from llamatron.composition.file_format import Section
from llamatron.tui import drawing, keybindings
from llamatron.tui.drawing import Align
from llamatron.tui.screens.set.song_page import SongPage
from llamatron.tui.screens.shared.named_list_page import NamedListPage
from llamatron.tui.text import tempo_text
from llamatron.user_strings import errors, help as help_text, labels, legends, marks, messages


class SongsPage(NamedListPage):
    """Every song in the set, with the current one marked."""

    KEYS = keybindings.SongsPage
    LISTED_SECTION = Section.SONGS
    RENAME_PROMPT = messages.MSG_RENAME_SONG_PROMPT
    WHAT = legends.MSG_SONG_WHAT
    crumbs = (labels.Crumb.SONGS,)
    HELP = help_text.HELP_SONGS_PAGE
    columns = (
        (labels.Column.SELECT_SONG, None, Align.LEFT), (labels.Column.CURRENT, 7, Align.LEFT), (labels.Column.TEMPO, 7, Align.RIGHT), (labels.Column.SCALE, 14, Align.LEFT),
        (labels.Column.TRACKS, 6, Align.RIGHT), (labels.Column.SCENES, 6, Align.RIGHT),
    )

    def rows(self):
        document = self.document()
        setlist = document.get_setlist()
        return [(name, self.row_of(name=name, song=setlist.get_song(name), current=name == document.get_current_song_name())) for name in self.names()]

    def row_of(self, *, name, song, current):
        mark = marks.MSG_CURRENT_SONG_MARK if current else drawing.NOTHING
        return [name, mark, tempo_text(song.get_tempo()), song.get_scale_name() or marks.MSG_NONE_SHOWN, len(song.get_track_names()), len(song.get_scenes())]

    def enter_binding(self):
        return self.KEYS.SETTINGS

    def item_keys(self):
        return [self.bind(self.KEYS.CURRENT, action=self.make_current), *super().item_keys()]

    def make_current(self):
        self.document().select_song(self.current())

    def open_item(self):
        """Make the selected song current, so that its page and the rest of the tracker work on it, then open its settings."""
        self.make_current()
        self.show_page(SongPage(self.holder))

    def add(self):
        def named(text):
            self.document().add_song(text)
            self.put_cursor_on(text)
        self.ask_name(title=messages.MSG_NEW_SONG_PROMPT, value=drawing.NOTHING, taken=self.names(), then=named)

    def delete(self):
        """Delete the selected song after asking, unless it's the last, since there is always a current song."""
        if len(self.names()) <= 1:
            self.refuse(errors.ERR_LAST_SONG_SHOWN)
            return
        super().delete()
