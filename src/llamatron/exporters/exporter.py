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
"""What every exporter is: something that writes a played song into a directory, as files named after the song.

An Exporter holds the directory, the grid of finished clips and the name its files take, and
export() writes them. Each kind of export is one subclass, which says what --to calls it (KIND)
and what people are shown for it (LABEL), so that exporters/exports.py only has to list the
classes. A kind writes either one file or several, and the two mixins here say where those files
are and how to find what an earlier export left: WritesOneFile for <name>.als and <name>.mid, and
WritesManyFiles for the stems and the clips, whose files are found by a pattern. Adding a kind,
for another DAW say, is one class and its place in the lists of exports.py.
"""

import glob
import os

from llamatron.grid.clip_grid import ClipGrid
from llamatron.strings.errors import ERR_BAD_DIRECTORY, ERR_FILES_EXIST, ERR_NEEDS_EXPORT, ERR_NEEDS_FILES, ERR_NOT_A_GRID

# What joins the names of the files that are in the way, in a warning.
FILE_LIST_SEPARATOR = ', '


class ExportKind:
    """What --to can write, as it's named on the command line."""

    ABLETON = 'ableton'
    MIDI_FILE = 'midi'
    STEMS = 'stems'
    CLIP_TREE = 'cliptree'
    GENERAL_MIDI = 'gm'
    WAV = 'wav'


def check_directory(directory):
    if not isinstance(directory, (str, os.PathLike)) or not os.fspath(directory):
        raise ValueError(ERR_BAD_DIRECTORY.format(value=directory))


def check_grid(grid):
    if not isinstance(grid, ClipGrid):
        raise ValueError(ERR_NOT_A_GRID.format(value=grid))


class Exporter:
    """One kind of export: a played song written into a directory, as a file or files named after a name.

    The name is the directory's own unless one is given, which the tracker and the command line
    always do: <set>_<song>. A subclass sets KIND and LABEL, writes its files in export(), and
    takes one of the two mixins below for where its files are.
    """

    __slots__ = ('_directory', '_grid', '_name')

    # What --to calls this kind of export, one of ExportKind.
    KIND = None
    # What people are shown for this kind of export.
    LABEL = None

    def __init__(self, *, directory, grid, name=None):
        self.set_directory(directory)
        self.set_grid(grid)
        self._name = name

    @classmethod
    def for_song(cls, *, directory, grid, name, template=None):
        """Return this kind's exporter of a played song. The template is for a kind that is built from one, and the others have no use for it."""
        return cls(directory=directory, grid=grid, name=name)

    def get_name(self):
        """Return what the files are named after: the name given, or the directory's."""
        return self._name or os.path.basename(os.path.abspath(self._directory))

    def get_directory(self):
        return self._directory

    def set_directory(self, directory):
        check_directory(directory)
        self._directory = directory

    def get_grid(self):
        return self._grid

    def set_grid(self, grid):
        check_grid(grid)
        self._grid = grid

    def export(self):
        """Write the song's files, leaving every other file in the directory in place, and writing nothing if a file is in the way."""
        raise NotImplementedError(ERR_NEEDS_EXPORT.format(kind=type(self).__name__))

    @classmethod
    def shown_path(cls, *, directory, name):
        """Return where this kind of export goes, as shown to people: the file, or a pattern for a kind that writes several."""
        raise NotImplementedError(ERR_NEEDS_FILES.format(kind=cls.__name__))

    @classmethod
    def earlier_files(cls, *, directory, name):
        """Return the files an earlier export of this kind left in a directory, and nothing else that's there."""
        raise NotImplementedError(ERR_NEEDS_FILES.format(kind=cls.__name__))

    @classmethod
    def remove_earlier_files(cls, *, directory, name):
        """Remove what an earlier export of this kind left in a directory, and leave everything else."""
        for path in cls.earlier_files(directory=directory, name=name):
            os.remove(path)

    def can_write(self, filenames):
        """Make the directory, and return whether the files can be written: none of them exists yet.

        Prints a warning and answers no if any exists. Other files are never touched.
        """
        os.makedirs(self._directory, exist_ok=True)
        existing = set(os.listdir(self._directory))
        conflicts = sorted(existing.intersection(filenames))
        if conflicts:
            print(ERR_FILES_EXIST.format(directory=os.fspath(self._directory), files=FILE_LIST_SEPARATOR.join(conflicts)))
            return False
        return True


class WritesOneFile:
    """What an exporter of one file knows about that file: FILE is its name, like {name}.als."""

    __slots__ = ()

    FILE = None

    @classmethod
    def file_path(cls, *, directory, name):
        """Return the file an export named name writes in a directory."""
        return os.path.join(directory, cls.FILE.format(name=name))

    def path(self):
        """Return the file this writes."""
        return self.file_path(directory=self.get_directory(), name=self.get_name())

    @classmethod
    def shown_path(cls, *, directory, name):
        return cls.file_path(directory=directory, name=name)

    @classmethod
    def earlier_files(cls, *, directory, name):
        path = cls.file_path(directory=directory, name=name)
        return [path] if os.path.exists(path) else []


class WritesManyFiles:
    """What an exporter of several files knows about them: FILES is a glob pattern matching them all and nothing another kind writes, and FILES_SHOWN how they're described to people."""

    __slots__ = ()

    FILES = None
    FILES_SHOWN = None

    @classmethod
    def files_pattern(cls, *, directory, name):
        """Return a glob pattern matching the files an export named name wrote in a directory, which --replace removes."""
        return os.path.join(glob.escape(os.fspath(directory)), cls.FILES.format(name=glob.escape(name)))

    @classmethod
    def shown_path(cls, *, directory, name):
        return os.path.join(directory, cls.FILES_SHOWN.format(name=name))

    @classmethod
    def earlier_files(cls, *, directory, name):
        return sorted(glob.glob(cls.files_pattern(directory=directory, name=name)))
