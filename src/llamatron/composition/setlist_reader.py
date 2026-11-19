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
"""Reading a set file: the file's data, an older file's layout brought to the one a set is written in now, and the corrections a file with values out of range is opened with.

The set builds itself from data in the layout written now (composition/setlist.py); everything
that knows of files, of YAML and of what older versions wrote is here, beside the writer
(composition/setlist_writer.py).
"""

import os
import yaml

from llamatron.composition import file_format, sections
from llamatron.composition.checks import check_keys, is_whole_number, reading
from llamatron.composition.file_format import Section, SetlistSetting, SongSetting
from llamatron.composition.pattern import Pattern
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings import errors
from llamatron.support import files
from llamatron.support.safe_yaml import load_safely
from llamatron.support.version import is_version, version_numbers

# The most corrections one file is opened with, so that a correction that fails to put its value right cannot go on for ever.
MOST_CORRECTIONS = 10000
# The keys a file saved before SETLISTS_SINCE held at the top, which now belong to a song.
ONE_SONG_KEYS = [
    SongSetting.TEMPO, SongSetting.TIME_SIGNATURE, SongSetting.ENTRY_SIZE, SongSetting.SCALE, SongSetting.SEED, SongSetting.GROOVE,
    Section.REGISTERS, Section.TRACKS, Section.SCENES,
]


def file_stem(path):
    """Return a file's name without its directory or suffix, which names an older file's one song."""
    return os.path.splitext(os.path.basename(path))[0]


def file_data(path):
    """Return the plain data a set file holds, or raise SongFileError if the file can't be read or isn't YAML.

    The file is read with load_safely, which only ever makes plain data, so reading a file can
    never run code.
    """
    try:
        with open(path, encoding=files.FILE_ENCODING) as file:
            return load_safely(file)
    except OSError as error:
        raise SongFileError(errors.ERR_CANT_READ.format(path=path, reason=error.strerror)) from error
    except yaml.YAMLError as error:
        raise SongFileError(errors.ERR_NOT_YAML.format(path=path, problem=error)) from error


def closed_groups_held(data):
    """Return the pattern groups a file's data shows closed: its list's names, and none where the file holds anything else, since a view's state is never worth refusing a file for."""
    held = data.get(file_format.CLOSED_PATTERN_GROUPS)
    if not isinstance(held, list):
        return []
    return [name for name in held if isinstance(name, str)]


def open_types_held(data):
    """Return the types of generator a file's data shows open: its list's kinds of generator, and none where the file holds anything else, as for the closed groups."""
    held = data.get(file_format.OPEN_GENERATOR_TYPES)
    if not isinstance(held, list):
        return []
    return [kind for kind in held if isinstance(kind, str) and kind in file_format.NAMED_GENERATORS]


def as_a_set_is_written(*, data, where, one_song_name, allowed):
    """Return a file's data in the layout a set is written in now, or raise SongFileError if it isn't a set at all.

    A file saved before sets existed becomes a set holding its one song under one_song_name, and
    a file saved with Live's octave numbers has them moved to the numbering from C0. allowed is
    the names of the settings a set holds.
    """
    # Every setting has a default, so an empty file is an empty set.
    data = {} if data is None else data
    if not isinstance(data, dict):
        raise SongFileError(errors.ERR_NOT_A_SETLIST)
    if holds_one_song(data):
        data = as_setlist_data(data=data, song_name=one_song_name)
    with reading(where):
        check_keys(data=data, allowed={*allowed, *sections.SETLIST_SECTIONS, file_format.CLOSED_PATTERN_GROUPS, file_format.OPEN_GENERATOR_TYPES})
    if _saved_before(data=data, version=file_format.LLAMATRON_OCTAVES_SINCE):
        data = _with_live_octaves_moved_up(data)
    if _saved_before(data=data, version=file_format.NOTES_SINCE) and SetlistSetting.DESCRIPTION in data:
        data = _with_description_as_notes(data)
    return data


def _with_description_as_notes(data):
    """Return a copy of an older file's data with its description, which was the long text, under notes."""
    moved = dict(data)
    moved[SetlistSetting.NOTES] = moved.pop(SetlistSetting.DESCRIPTION)
    return moved


def _saved_before(*, data, version):
    """Return whether a file records being saved by a version of llamatron older than one.

    A file with no version, or one that isn't a version, counts as current, and the usual checks
    refuse the latter.
    """
    saved = data.get(SetlistSetting.VERSION)
    return is_version(saved) and version_numbers(saved) < version_numbers(version)


def holds_one_song(data):
    """Return whether a file is from before sets existed, with one song's settings at the top and no songs section."""
    if Section.SONGS in data:
        return False
    return _saved_before(data=data, version=file_format.SETLISTS_SINCE) or any(key in data for key in ONE_SONG_KEYS)


def as_setlist_data(*, data, song_name):
    """Return an older file's data as a set holding its one song under a name."""
    moved = {key: value for key, value in data.items() if key not in ONE_SONG_KEYS}
    moved[Section.SONGS] = {song_name: {key: data[key] for key in ONE_SONG_KEYS if key in data}}
    return moved


def _with_live_octaves_moved_up(data):
    """Return a copy of an older file's data with every octave moved from Live's labels to the numbering from C0.

    Only whole numbers move, so that anything else is still refused by the usual checks.
    """
    moved = dict(data)
    for name in (SetlistSetting.DEFAULT_OCTAVE, SetlistSetting.DEFAULT_DRUM_OCTAVE):
        if is_whole_number(moved.get(name)):
            moved[name] = moved[name] + file_format.LIVE_OCTAVE_OFFSET
    patterns = moved.get(Section.PATTERNS)
    if isinstance(patterns, dict):
        moved[Section.PATTERNS] = {name: Pattern.with_octaves_moved(data=pattern, offset=file_format.LIVE_OCTAVE_OFFSET) for name, pattern in patterns.items()}
    return moved


def read_corrected(*, read, data):
    """Return what read(data) makes of a set file's data once every value that can't be used is changed to the allowed value nearest it, and the corrections made, in the order found.

    Reading stops at the first wrong value. A value with an allowed value near it comes with a
    correction (composition/corrections.py), which is applied to the data before reading again,
    until the data reads. A problem with no correction raises SongFileError. The data given is
    changed, so the caller hands over a copy.
    """
    corrections = []
    while True:
        try:
            return read(data), corrections
        except SongFileError as problem:
            correction = problem.get_correction()
            # Each correction puts one wrong value right, so a file can't need more of them than MOST_CORRECTIONS unless one fails to.
            if correction is None or len(corrections) >= MOST_CORRECTIONS:
                raise
            correction.apply()
            corrections.append(correction)
