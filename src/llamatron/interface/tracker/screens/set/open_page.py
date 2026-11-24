# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Open page: picks a set file to open, starting in the examples folder. Ctrl+O shows it from every page.

The same page picks the MIDI file to import, given the files to show, where to start, its crumbs
and what to do with the file chosen, until the file picker is designed for the whole tracker
(.claude/planning/IDEAS.yml, "The file picker, shared and better").
"""

import os
from rich.text import Text

from llamatron.interface.pages.folder_list import FolderListPresenter
from llamatron.interface.tracker import drawing, keybindings, themes
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared import shared
from llamatron.interface.tracker.screens.shared.everywhere import open_file
from llamatron.interface.tracker.screens.shared.list_page import ListPage
from llamatron.user_strings import help as help_text, labels


class OpenPage(ListPage):
    """Picks a set file, starting in the examples folder, from the folder list presenter (interface/pages/folder_list.py)."""

    THEME = themes.SET_FILE

    KEYS = keybindings.OpenPage

    crumbs = (labels.Crumb.FILE, labels.Crumb.OPEN)
    HELP = help_text.HELP_OPEN_PAGE
    columns = FolderListPresenter.COLUMNS
    # Files' names are as long as they are.
    NAME_COLUMN_WIDTH = None

    def __init__(self, *, holder, then, suffixes=shared.SONG_SUFFIXES, folder=None, crumbs=None, chosen=None):
        super().__init__(holder)
        self.then = then
        # The files shown, by their endings, and what Enter on one does: open it as a set, or hand its path to chosen.
        self.suffixes = suffixes
        self.chosen = chosen
        if crumbs is not None:
            self.crumbs = crumbs
        self.folder = FolderListPresenter.starting_folder(remembered=self.holder.last_folders.get(self.suffixes), given=folder)

    def remember_folder(self):
        """Keep the directory shown, for the session, so that the next picker of these files starts in it."""
        self.holder.last_folders[self.suffixes] = self.folder

    def duration(self):
        return False

    def presenter(self):
        return FolderListPresenter(folder=self.folder, suffixes=self.suffixes)

    def rows(self):
        return self.presenter().rows()

    def rows_depend_on(self):
        """The rows are the directory's, of the files shown, which no change to the set moves: going into a directory must list it afresh."""
        return (os.path.abspath(self.folder), self.suffixes)

    def keys(self):
        return [self.bind(self.KEYS.BACK, action=self.go_back), *self.move_keys(), self.bind(self.KEYS.OPEN, action=self.open)]

    def body(self, *, width, height):
        return [Text(drawing.INDENT + self.presenter().shown_path(), style=Style.DIM), Text(drawing.NOTHING), *super().body(width=width, height=height - 2)]

    def open(self):
        name = self.current()
        path = self.presenter().path_of(name)
        if os.path.isdir(path):
            self.folder = path
            self.cursor.set_place(0)
            self.remember_folder()
            return
        self.remember_folder()
        if self.chosen is not None:
            self.chosen(path)
            return
        open_file(page=self, path=path, then=self.opened)

    def opened(self, document):
        """Close the page and hand the opened set to whoever showed it."""
        self.app.pop_screen()
        self.then(document)
