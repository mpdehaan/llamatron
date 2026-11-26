# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The base class for everything a set file stores."""

import functools

from llamatron.caching.revised import notes_change, Revised
from llamatron.model.objects import sections
from llamatron.user_strings import errors


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


def left_out_if_default(*, value, default):
    """Return a setting's value as a file keeps it: None, which leaves it out of the file, where the value is its default."""
    if value == default:
        return None
    return value


def or_default(*, value, default):
    """Return a setting's value, or its default if the file left it out."""
    if value is None:
        return default
    return value


@functools.cache
def references_of(kind):
    """Return which settings of a class of stored object name an item of which section: its REFERENCES, with the settings that
    list generators and chains naming an item of every generator section, whichever plugins there are."""
    if not kind.CHAINS_NAMED_BY:
        return kind.REFERENCES
    references = dict(kind.REFERENCES)
    for section in sections.generator_sections():
        references[section] = kind.CHAINS_NAMED_BY
    return references


class LlamaData(Revised):
    """Something stored in a set file, which can turn itself into file data and back.

    to_data() returns the object's settings as plain data, in the set file's format: dictionaries,
    lists, text, numbers, true or false, and None. from_data() is a class method that builds the
    object from that data, checks it, and raises SongFileError for anything wrong, naming where in
    the file the problem is. A setting the data leaves out gets its default, so that a file from an
    older version still loads.

    Every one carries a revision (caching/revised.py), which its constructor and every method that
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

    __slots__ = ('_cached',)

    # Which of its settings hold the name of an item of which section, like a clip's pattern, as {section: (setting, ...)}.
    REFERENCES = {}
    # The settings that list the generators and chains it runs, which name an item of every generator section, as (setting, ...).
    CHAINS_NAMED_BY = ()

    def note_change(self):
        """Take a new revision, and drop the data kept, which the change may have made wrong."""
        Revised.note_change(self)
        self._cached = None

    def kept_data(self):
        """Return what to_data() returns, built once and kept until this object changes.

        What comes back is shared with the undo history and with every earlier asker, so it is
        never changed: a caller that wants data to change asks to_data().
        """
        if self._cached is None:
            self._cached = self.to_data()
        return self._cached

    def names_item(self, *, section, name):
        """Return whether one of its own settings names an item of a section, as a clip names its pattern."""
        references = references_of(type(self))
        for setting in references.get(section, ()):
            if _names(value=self._settings.get(setting), name=name):
                return True
        return False

    def named_items(self):
        """Return everything its own settings name, as a set of (section, name): what names_item() answers one item at a time,
        gathered in one go for a search of everything a set uses."""
        named = set()
        for section, settings in references_of(type(self)).items():
            for setting in settings:
                named.update(_named_by(section=section, value=self._settings.get(setting)))
        return named

    def everything_named(self):
        """Return everything it names and everything the objects it holds name, as a set of (section, name)."""
        named = self.named_items()
        for part in self.referring_parts():
            named |= part.everything_named()
        return named

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

    def to_data(self):
        """Return this object's settings as plain data in the set file's format."""
        raise NotImplementedError(errors.ERR_NEEDS_TO_DATA.format(kind=type(self).__name__))

    def copy(self):
        """Return an object just like this one that shares no list or dictionary with it, which copying a named thing makes."""
        raise NotImplementedError(errors.ERR_NEEDS_COPY.format(kind=type(self).__name__))

    @classmethod
    def from_data(cls, *, data, where, song=None):
        """Return an object built from plain data, or raise SongFileError if the data is wrong.

        where names the place in the file, like "scene 2", for error messages. song is the song
        being read, for objects that need to check names that other parts of the file define; the
        parts of the set that every song shares, like a chain, take the setlist instead.
        """
        raise NotImplementedError(errors.ERR_NEEDS_FROM_DATA.format(kind=cls.__name__))

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        for setting in references_of(type(self))[section]:
            value = self._settings[setting]
            if isinstance(value, list):
                self._settings[setting] = _renamed_in(items=value, old=old, new=new)
            elif value == old:
                self._settings[setting] = new


class HoldsSettings(LlamaData):
    """A stored object that holds settings: each a name of its class's SETTINGS with the value the file writes for it, or None where the file leaves it out.

    SETTINGS describes every setting once (model/schema/setting.py), and set_written() is the one
    place a value is checked against its description and stored, so that a setter of a subclass
    says only what is its own: `set_tempo(tempo)` is the readable name, and one line. A subclass
    whose file data is its settings alone needs no to_data() of its own.
    """

    __slots__ = ('_settings',)

    # Every setting the class holds, by name, each described once: what a file may hold for it and what a setter accepts.
    SETTINGS = {}

    def get_written(self, name):
        """Return a setting as the file holds it, or None where the file leaves it out and its default applies."""
        return self._settings[name]

    @notes_change
    def set_written(self, *, name, value, song=None):
        """Store a setting's value once its description allows it, or None to leave the setting out of the file.

        song is the song the object is in, for a setting that names something of the song or the set.
        """
        if value is not None:
            self.SETTINGS[name].check(value, song=song)
        self._settings[name] = value

    def set_written_unless_default(self, *, name, value, default, song=None):
        """Store a setting's value as set_written() does, leaving the setting out of the file where the value is its default."""
        if value is not None:
            self.SETTINGS[name].check(value, song=song)
        if value == default:
            value = None
        self.set_written(name=name, value=value, song=song)

    def to_data(self):
        """Return the settings the file writes: those that hold a value."""
        return written_settings(self._settings)


def _names(*, value, name):
    """Return whether a setting names an item: holds its name, or a list holding it, as a list of chains does."""
    if isinstance(value, list):
        return name in value
    return value == name


def _named_by(*, section, value):
    """Return what one setting names, as (section, name) pairs: each name of a list, the one name it holds, or nothing where the file
    leaves the setting out."""
    if isinstance(value, list):
        named = []
        for name in value:
            named.append((section, name))
        return named
    if value is None:
        return []
    return [(section, value)]


def _renamed_in(*, items, old, new):
    """Return a list of names with one renamed wherever it stands."""
    renamed = []
    for item in items:
        if item == old:
            item = new
        renamed.append(item)
    return renamed
