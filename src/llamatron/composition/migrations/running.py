# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Running the migrations: which are due for a file, in what order, and what they moved."""

from llamatron.composition.migrations import description_as_notes, lists, live_octaves, one_song
from llamatron.composition.migrations.helpers import has_version, saved_before


class Conversion:
    """What reading a file moved: whether any migration ran, and each name a migration had to change, as (kind, old, new). It
    also holds what a migration may need of the file beyond its data: the name its one song takes in a file from before sets."""

    __slots__ = ('_moved', '_renames', '_one_song_name')

    def __init__(self, *, one_song_name=None):
        self._moved = False
        self._renames = []
        self._one_song_name = one_song_name

    def has_moved(self):
        return self._moved

    def get_renames(self):
        return list(self._renames)

    def get_one_song_name(self):
        return self._one_song_name

    def note_moved(self):
        self._moved = True

    def note_rename(self, *, kind, old, new):
        self._renames.append((kind, old, new))


class Migration:
    """One breaking change of the set file's layout: the version that first wrote the new layout, how to tell the old layout by its
    shape when a file records no version, and the change itself, which takes the data and the Conversion and returns new data."""

    __slots__ = ('_since', '_is_before', '_change')

    def __init__(self, *, since, is_before, change):
        self._since = since
        self._is_before = is_before
        self._change = change

    def is_due(self, data):
        """Return whether a file's data is in the layout before this migration."""
        if has_version(data):
            return saved_before(data=data, version=self._since)
        return self._is_before(data)

    def run(self, *, data, conversion):
        conversion.note_moved()
        return self._change(data=data, conversion=conversion)


# Every migration, in the order of the versions that made them.
MIGRATIONS = [Migration(since=module.SINCE, is_before=module.is_before, change=module.moved) for module in (live_octaves, one_song, description_as_notes, lists)]


def migrated(data, *, one_song_name=None):
    """Return a file's data moved to the layout written now, and the Conversion that says what moving it did. one_song_name names
    the one song of a file from before sets, after the file."""
    conversion = Conversion(one_song_name=one_song_name)
    for migration in MIGRATIONS:
        if isinstance(data, dict) and migration.is_due(data):
            data = migration.run(data=data, conversion=conversion)
    return data, conversion
