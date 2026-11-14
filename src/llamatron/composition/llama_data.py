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

"""The base class for everything a set file stores."""

from llamatron.strings.errors import ERR_NEEDS_FROM_DATA, ERR_NEEDS_TO_DATA
from llamatron.support.revised import Revised, notes_change


def settings_by_name(*, names, given):
    """Return every setting in names, taking the value given for it, or None, meaning its default."""
    return {name: given.get(name) for name in names}


def own_copy(value):
    """Return plain data with every list and dictionary in it copied, so that the copy shares nothing that can change with what was given."""
    if isinstance(value, dict):
        return {key: own_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [own_copy(item) for item in value]
    return value


def written_settings(settings):
    """Return the settings a file writes: those that aren't None, in their order, each list a copy so that the data shares nothing with the object."""
    return {name: own_copy(value) for name, value in settings.items() if value is not None}


def data_built_anew(part):
    """Return a part's data built anew, which whoever asked for it may change."""
    return part.to_data()


def data_as_kept(part):
    """Return a part's data as the part keeps it, which is shared and never changed."""
    return part.kept_data()


def or_default(*, value, default):
    """Return a setting's value, or its default if the file left it out."""
    return default if value is None else value


class LlamaData(Revised):
    """Something stored in a set file, which can turn itself into file data and back.

    to_data() returns the object's settings as plain data, in the set file's format: dictionaries,
    lists, text, numbers, true or false, and None. from_data() is a class method that builds the
    object from that data, checks it, and raises SongFileError for anything wrong, naming where in
    the file the problem is. A setting the data leaves out gets its default, so that a file from an
    older version still loads.

    Every one carries a revision (support/revised.py), which its constructor and every method that
    changes it move with note_change(), so that what is worked out from an object can be kept until
    the object changes.

    Every subclass defines both, and a test checks that they do. Objects that contain others call
    their parts' methods, so a set saves and loads itself, and nothing else needs to know how an
    object is stored.

    kept_data() is the same data, built once and kept until the object changes, for whoever only
    reads it: the undo history keeps the set's data after every edit, and with this an edit to one
    pattern builds one pattern's data, and every snapshot shares the rest. An object that holds
    others (a scene, a song, the set) puts its kept data together from its parts' each time, since
    a part can change without its holder changing. What to_data() returns shares no list or
    dictionary with the object, so that data kept can't change when the object does.

    Objects refer to each other by name. A class says once, in REFERENCES, which of its settings
    hold the name of an item of which section, and names_item() and rename_references() read
    that, so that asking what uses an item and renaming it can't disagree about where names are
    kept. An object that holds others lists them in referring_parts(), and a rename reaches them
    through it.
    """

    __slots__ = ('_kept',)

    # Which of its settings hold the name of an item of which section, like a clip's pattern, as {section: (setting, ...)}.
    REFERENCES = {}

    def note_change(self):
        """Take a new revision, and drop the data kept, which the change may have made wrong."""
        Revised.note_change(self)
        self._kept = None

    def kept_data(self):
        """Return what to_data() returns, built once and kept until this object changes.

        What comes back is shared with the undo history and with every earlier asker, so it is
        never changed: a caller that wants data to change asks to_data().
        """
        if self._kept is None:
            self._kept = self.to_data()
        return self._kept

    def names_item(self, *, section, name):
        """Return whether one of its own settings names an item of a section, as a clip names its pattern."""
        return any(_names(value=self._settings[setting], name=name) for setting in self.REFERENCES.get(section, ()))

    def referring_parts(self):
        """Return the objects it holds that may name things too, which a rename is passed on to: none, unless a subclass holds some."""
        return ()

    def rename_references(self, *, section, old, new):
        """Follow the rename of an item of a section: each of its own settings that named the item names it still, and so does everything it holds.

        Only what named the item changes, so what didn't keeps its revision and the data it keeps.
        """
        if self.names_item(section=section, name=old):
            self._rename_own_references(section=section, old=old, new=new)
        for part in self.referring_parts():
            part.rename_references(section=section, old=old, new=new)

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        for setting in self.REFERENCES[section]:
            value = self._settings[setting]
            if isinstance(value, list):
                self._settings[setting] = [new if item == old else item for item in value]
            elif value == old:
                self._settings[setting] = new

    def to_data(self):
        """Return this object's settings as plain data in the set file's format."""
        raise NotImplementedError(ERR_NEEDS_TO_DATA.format(kind=type(self).__name__))

    @classmethod
    def from_data(cls, *, data, where, song=None):
        """Return an object built from plain data, or raise SongFileError if the data is wrong.

        where names the place in the file, like "scene 2", for error messages. song is the song
        being read, for objects that need to check names that other parts of the file define; the
        parts of the set that every song shares, like a chain, take the setlist instead.
        """
        raise NotImplementedError(ERR_NEEDS_FROM_DATA.format(kind=cls.__name__))


def _names(*, value, name):
    """Return whether a setting names an item: holds its name, or a list holding it, as a list of chains does."""
    return name in value if isinstance(value, list) else value == name
