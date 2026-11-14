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

"""The Open page: picks a set file to open, starting in the examples folder. Ctrl+O shows it from every page.

The same page picks the MIDI file to import, given the files to show, where to start, its crumbs
and what to do with the file chosen, until the file picker is designed for the whole tracker
(dev_notes/IDEAS.md, "The file picker, shared and better").
"""

import os

from rich.text import Text

from llamatron.tui.drawing import Align, INDENT, NOTHING, Style
from llamatron.strings.help import HELP_OPEN_PAGE
from llamatron.tui.screens.everywhere import open_file
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.shared import SONG_SUFFIXES
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.marks import MSG_FOLDER_ROW, MSG_PARENT_ROW
from llamatron.tui import themes
from llamatron.tui import keybindings


# The file picker.
EXAMPLES_FOLDER = 'examples'
HERE = '.'
PARENT = '..'
HIDDEN_PREFIX = '.'


class OpenPage(ListPage):
    """Picks a set file, starting in the examples folder."""

    THEME = themes.SET_FILE

    KEYS = keybindings.OpenPage

    crumbs = (Crumb.FILE, Crumb.OPEN)
    HELP = HELP_OPEN_PAGE
    columns = ((Column.SELECT_FILE, None, Align.LEFT),)

    def __init__(self, *, holder, then, suffixes=SONG_SUFFIXES, folder=None, crumbs=None, chosen=None):
        super().__init__(holder)
        self.then = then
        # The files shown, by their endings, and what Enter on one does: open it as a set, or hand its path to chosen.
        self.suffixes = suffixes
        self.chosen = chosen
        if crumbs is not None:
            self.crumbs = crumbs
        self.folder = folder or (EXAMPLES_FOLDER if os.path.isdir(EXAMPLES_FOLDER) else HERE)

    def duration(self):
        return False

    def is_folder(self, name):
        return os.path.isdir(os.path.join(self.folder, name)) and not name.startswith(HIDDEN_PREFIX)

    def rows(self):
        try:
            names = sorted(os.listdir(self.folder), key=str.lower)
        except OSError:
            names = []
        folders = [name for name in names if self.is_folder(name)]
        files = [name for name in names if name.lower().endswith(self.suffixes)]
        rows = [(PARENT, [MSG_PARENT_ROW])]
        rows += [(name, [MSG_FOLDER_ROW.format(name=name)]) for name in folders]
        rows += [(name, [name]) for name in files]
        return rows

    def rows_depend_on(self):
        """The rows are the directory's, of the files shown, which no change to the set moves: going into a directory must list it afresh."""
        return (os.path.abspath(self.folder), self.suffixes)

    def keys(self):
        return [self.bind(self.KEYS.BACK, action=self.go_back), *self.move_keys(), self.bind(self.KEYS.OPEN, action=self.open)]

    def body(self, *, width, height):
        return [Text(INDENT + os.path.abspath(self.folder), style=Style.DIM), Text(NOTHING), *super().body(width=width, height=height - 2)]

    def open(self):
        name = self.current()
        path = os.path.normpath(os.path.join(self.folder, name))
        if os.path.isdir(path):
            self.folder = path
            self.place = 0
            return
        if self.chosen is not None:
            self.chosen(path)
            return
        open_file(page=self, path=path, then=self.opened)

    def opened(self, document):
        """Close the page and hand the opened set to whoever showed it."""
        self.app.pop_screen()
        self.then(document)
