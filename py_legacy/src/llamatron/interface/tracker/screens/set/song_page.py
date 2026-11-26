# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Song page: the Song presenter's form (interface/pages/song.py) shown on a page of its own, reached from the Songs page,
which makes the song current first; the page renames the song, its crumbs following, and gives the form its Export button."""

import functools

from llamatron.interface.pages.song import SongPresenter
from llamatron.interface.tracker import keybindings, themes
from llamatron.interface.tracker.screens.shared.everywhere import export
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, messages


class SongPage(FieldPage):
    """The current song's own settings."""

    THEME = themes.SONGS

    KEYS = keybindings.SongPage

    HELP = help_text.HELP_SONG_PAGE


    def crumb_trail(self):
        # The current song can be renamed here and by an undo, so the crumb is read each time.
        return (labels.Crumb.SONGS, self.document().get_current_song_name())


    def caption(self):
        what = labels.MSG_CAPTION_WORDS[Section.SONGS].upper()
        return labels.MSG_EDITING_CAPTION.format(what=what, name=self.document().get_current_song_name())


    def duration(self):
        lengths = self.document().lengths()
        return lengths.song_seconds()


    def song(self):
        return self.document().song()


    def rename(self):
        """Rename the current song, which the Songs page's N does too, and put the new name in the crumbs."""
        document = self.document()
        name = document.get_current_song_name()

        def renamed(new):
            document.rename_named(section=Section.SONGS, old=name, new=new)
            self.crumbs = (labels.Crumb.SONGS, new)
        self.ask_name(title=messages.MSG_RENAME_SONG_PROMPT.format(name=name), value=name, taken=document.song_names(), then=renamed)

    def presenter(self):
        """Return what the page shows, for the song as it is now."""
        export_button = self.button(binding=self.KEYS.EXPORT, label=labels.PageName.EXPORT, action=functools.partial(export, self))
        return SongPresenter(page=self, document=self.document(), rename=self.rename, export_button=export_button)

    def fields(self):
        return self.presenter().form()
