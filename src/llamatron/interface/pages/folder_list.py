# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Open page as a presenter: a folder's rows, the folder above first, then its folders, then the files of the endings shown,
each sorted by name with capitals ignored, and where each row leads."""

import os

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.user_strings import labels, marks

# Where the file picker starts: the examples folder where there is one, else the folder llamatron runs in.
EXAMPLES_FOLDER = 'examples'
HERE = '.'
# The row of the folder above, and what starts a hidden folder's name.
PARENT = '..'
HIDDEN_PREFIX = '.'


class FolderListPresenter:
    """What the Open page lists in a folder, for the files of some endings."""

    COLUMNS = (ListColumn(heading=labels.Column.SELECT_FILE, width=None, align=Align.LEFT),)

    __slots__ = ('_folder', '_suffixes')

    def __init__(self, *, folder, suffixes):
        self._folder = folder
        self._suffixes = suffixes

    @staticmethod
    def starting_folder(*, remembered, given):
        """Return the folder the picker starts in: the one remembered for the session, the one given, the examples folder, or here."""
        if remembered is not None and os.path.isdir(remembered):
            return remembered
        if given:
            return given
        return EXAMPLES_FOLDER if os.path.isdir(EXAMPLES_FOLDER) else HERE

    def rows(self):
        """Return the folder's rows: the folder above, its folders, then its files of the endings shown."""
        try:
            names = sorted(os.listdir(self._folder), key=str.lower)
        except OSError:
            names = []
        rows = [(PARENT, [marks.MSG_PARENT_ROW])]
        rows += [(name, [marks.MSG_FOLDER_ROW.format(name=name)]) for name in names if self.is_folder(name)]
        rows += [(name, [name]) for name in names if name.lower().endswith(self._suffixes)]
        return rows

    def is_folder(self, name):
        """Return whether a name in the folder is a folder the picker shows, hidden ones left out."""
        return os.path.isdir(os.path.join(self._folder, name)) and not name.startswith(HIDDEN_PREFIX)

    def path_of(self, name):
        """Return the path a row leads to."""
        return os.path.normpath(os.path.join(self._folder, name))

    def shown_path(self):
        """Return the whole path of the folder, which the page shows over its rows."""
        return os.path.abspath(self._folder)
