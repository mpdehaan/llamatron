# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Songs page: the set's songs, which one is current, and each one's settings."""

from llamatron.interface.pages.song_list import SongListPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.set.song_page import SongPage
from llamatron.interface.tracker.screens.shared.named_list_page import NamedListPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import errors, help as help_text, labels, legends, messages


class SongsPage(NamedListPage):
    """Every song in the set, with the current one marked, from the Song list presenter (interface/pages/song_list.py)."""

    KEYS = keybindings.SongsPage
    LISTED_SECTION = Section.SONGS
    RENAME_PROMPT = messages.MSG_RENAME_SONG_PROMPT
    WHAT = legends.MSG_SONG_WHAT
    crumbs = (labels.Crumb.SONGS,)
    HELP = help_text.HELP_SONGS_PAGE
    columns = SongListPresenter.COLUMNS

    def presenter(self):
        return SongListPresenter(page=self, document=self.document())

    def rows(self):
        return self.presenter().rows()

    def enter_binding(self):
        return self.KEYS.SETTINGS

    def item_keys(self):
        return [self.bind(self.KEYS.CURRENT, action=self.make_current), *super().item_keys()]

    def make_current(self):
        self.presenter().make_current(self.current())

    def open_item(self):
        """Make the selected song current, so that its page and the rest of the tracker work on it, then open its settings."""
        self.make_current()
        self.show_page(SongPage(self.holder))

    def add(self):
        self.presenter().add()

    def delete(self):
        """Delete the selected song after asking, unless it's the last, since there is always a current song."""
        if len(self.names()) <= 1:
            self.refuse(errors.ERR_LAST_SONG_SHOWN)
            return
        super().delete()
