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

"""The Document's file: opening and saving the set, noticing what changed on disk, and exporting the current song."""

import contextlib
import io
import os

from llamatron.exporters.exports import earlier_export, export_name, make_exporter, shown_export_path, remove_earlier_export
from llamatron.composition.file_format import SetlistSetting
from llamatron.composition.setlist import Setlist, file_stem
from llamatron.support.ordered_data import same_in_order
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings.errors import ERR_FILE_PROTECTED, ERR_NOTHING_TO_EXPORT, ERR_SAVE_BEFORE_EXPORT

# What the set is called in the title until it's saved.
UNTITLED = 'untitled'


def comparable(data):
    """Return a set's data without its version, which is the one thing saving changes on its own."""
    return {key: value for key, value in data.items() if key != SetlistSetting.VERSION}


def file_data(path):
    """Return what a set file holds, as it would be saved back, or None if it can't be read."""
    try:
        setlist = Setlist.read_file(path)
    except (OSError, SongFileError):
        return None
    setlist.fill_in_defaults()
    return comparable(setlist.to_data())


class DocumentFiles:
    """What Document knows about the set's file: where it is, whether it holds what the set does now, and where exports go.

    It works on what Document keeps: the set, the path, the data the file held when it was read
    or last saved, and the mark that says there are unsaved changes.
    """

    __slots__ = ()

    # Opening, saving and exporting.

    @classmethod
    def load(cls, path):
        """Return a set from a file, or raise SongFileError if something's wrong with it."""
        return cls(setlist=Setlist.read_file(path), path=path)

    @classmethod
    def load_or_correct(cls, path):
        """Return a set from a file, and the corrections it took to read the file: none when nothing in it is wrong.

        A file that holds values that can't be used, each with an allowed value near it, is read
        with those values in their place (Setlist.read_file_corrected), and the set is unsaved,
        since the file still holds what it did. Whoever asks shows the corrections and lets the
        user decide before the set is opened. Any other problem raises SongFileError.
        """
        try:
            return cls.load(path), []
        except SongFileError as error:
            if error.get_correction() is None:
                raise
        setlist, corrections = Setlist.read_file_corrected(path)
        document = cls(setlist=setlist, path=path)
        document._differs_from_its_file()
        return document, corrections

    def _differs_from_its_file(self):
        """Note that the set isn't what its file holds, so that it needs saving, and that no undo goes back to a saved state."""
        self._dirty = True
        self._clean_data = None

    def save(self, *, path=None):
        """Write the set to a file, making any folders that it needs. Every saved file records the version that wrote it.

        A protected set's own file is never written over, which raises SongFileError.
        """
        path = path or self._path
        if self.file_is_protected(path=path):
            raise SongFileError(ERR_FILE_PROTECTED.format(path=path))
        self._setlist.write_file(path)
        self._path = path
        self._dirty = False
        self._saved_data = self._own_data()
        self._clean_data = self._saved_data

    def _own_data(self):
        """Return the set as it would be saved, without the version, which saving always brings up to date. Only for comparing: the pieces are the ones the set's objects keep, and are never changed."""
        return comparable(self._setlist.kept_data())

    def save_as(self, path):
        """Save the set under a name the user chose: a copy of a protected set is theirs, so the copy isn't protected."""
        if self._setlist.is_protected() and self._path is not None and path != self._path:
            self._setlist.set_protected(False)
        self.save(path=path)

    def file_is_protected(self, *, path=None):
        """Return whether saving to a path, or where the set came from, would write over a protected set's own file."""
        path = path or self._path
        return self._setlist.is_protected() and path is not None and path == self._path and os.path.exists(path)

    def file_holds_this_set(self):
        """Return whether the set's file already holds exactly what saving would write, so that saving would change nothing.

        The data is compared as it's loaded, not as text, with the order of lists and of each
        section's items counted, since moving a pattern up a list is a change worth saving. A set whose file holds it has
        nothing unsaved, even after a change that was changed back.
        """
        held = file_data(self._path) if self._path is not None else None
        if held is None or not same_in_order(first=held, second=self._own_data()):
            return False
        self._dirty = False
        return True

    def file_changed_elsewhere(self):
        """Return whether something else has changed the set's file since it was opened or last saved here.

        A file that can no longer be read counts as changed, so that saving asks before writing
        over whatever is there.
        """
        if self._path is None or not os.path.exists(self._path):
            return False
        return file_data(self._path) != self._saved_data

    def get_path(self):
        """Return the file the set came from or was last saved to, or None if it has none yet."""
        return self._path

    def is_dirty(self):
        """Return whether the set has changed since it was opened or saved."""
        return self._dirty

    def get_file_name(self):
        """Return the file's name without its folders, for the header's crumb, or None before the set is saved."""
        return os.path.basename(self._path) if self._path else None

    def get_name(self):
        """Return the set's name, which is its file's name without the suffix, or untitled until it's saved."""
        if not self._path:
            return UNTITLED
        return file_stem(self._path)

    def can_export(self):
        """Return whether the set has a file, which exports are named after and written beside, so it has to be saved first."""
        return self._path is not None

    def export_directory(self):
        """Return the directory the current song's exports go in: the set's file's, the current one for a bare file name, or None until it's saved."""
        if not self._path:
            return None
        return os.path.dirname(self._path) or os.curdir

    def export_name(self):
        """Return what the current song's exports are named after: <set>_<song>."""
        return export_name(setlist=self.get_name(), song=self._current)

    def export_path(self, to):
        """Return where an export will write, for people: the file for a Live set or a single MIDI file, or the files' pattern for stems and clips."""
        return os.path.normpath(shown_export_path(kind=to, directory=self.export_directory(), name=self.export_name()))

    def export_exists(self, to):
        """Return whether exporting would replace an earlier export of the same kind."""
        return bool(earlier_export(kind=to, directory=self.export_directory(), name=self.export_name()))

    def export(self, to):
        """Export the current song beside the set's file, replacing an earlier export, and return where it went, or raise SongFileError if it can't be."""
        if not self.can_export():
            raise SongFileError(ERR_SAVE_BEFORE_EXPORT)
        song = self.song()
        if not song.get_track_names() or not song.get_scenes():
            raise SongFileError(ERR_NOTHING_TO_EXPORT)
        grid = SongRenderer(song).render()
        directory = self.export_directory()
        name = self.export_name()
        remove_earlier_export(kind=to, directory=directory, name=name)
        # Exporters print warnings, which would write over the screen.
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                make_exporter(kind=to, directory=directory, name=name, grid=grid).export()
            except (ValueError, OSError) as error:
                raise SongFileError(str(error)) from error
        return self.export_path(to)
