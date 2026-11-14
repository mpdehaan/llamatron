# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The Songs page: the set's songs, which one is current, and each one's settings."""

from llamatron.composition.file_format import Section
from llamatron.tui.drawing import Align, NOTHING
from llamatron.strings.help import HELP_SONGS_PAGE
from llamatron.tui.screens.named_list_page import NamedListPage
from llamatron.tui.screens.song_page import SongPage
from llamatron.tui.text import tempo_text
from llamatron.strings.errors import ERR_LAST_SONG_SHOWN
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.legends import MSG_SONG_WHAT
from llamatron.strings.marks import MSG_CURRENT_SONG_MARK, MSG_NONE_SHOWN
from llamatron.strings.messages import MSG_NEW_SONG_PROMPT, MSG_RENAME_SONG_PROMPT
from llamatron.tui import keybindings


class SongsPage(NamedListPage):
    """Every song in the set, with the current one marked."""

    KEYS = keybindings.SongsPage
    LISTED_SECTION = Section.SONGS
    RENAME_PROMPT = MSG_RENAME_SONG_PROMPT
    WHAT = MSG_SONG_WHAT
    crumbs = (Crumb.SONGS,)
    HELP = HELP_SONGS_PAGE
    columns = (
        (Column.SELECT_SONG, None, Align.LEFT), (Column.CURRENT, 7, Align.LEFT), (Column.TEMPO, 7, Align.RIGHT), (Column.SCALE, 14, Align.LEFT),
        (Column.TRACKS, 6, Align.RIGHT), (Column.SCENES, 6, Align.RIGHT),
    )

    def rows(self):
        document = self.document()
        setlist = document.setlist()
        return [(name, self.row_of(name=name, song=setlist.get_song(name), current=name == document.current_song_name())) for name in self.names()]

    def row_of(self, *, name, song, current):
        mark = MSG_CURRENT_SONG_MARK if current else NOTHING
        return [name, mark, tempo_text(song.get_tempo()), song.get_scale_name() or MSG_NONE_SHOWN, len(song.get_track_names()), len(song.get_scenes())]

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
        self.ask_name(title=MSG_NEW_SONG_PROMPT, value=NOTHING, taken=self.names(), then=named)

    def delete(self):
        """Delete the selected song after asking, unless it's the last, since there is always a current song."""
        if len(self.names()) <= 1:
            self.refuse(ERR_LAST_SONG_SHOWN)
            return
        super().delete()
