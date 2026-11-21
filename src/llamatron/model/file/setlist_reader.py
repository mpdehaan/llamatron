# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reading a set file: the file's data, an older file's layout brought to the one a set is written in now, and the corrections a file with values out of range is opened with.

The set builds itself from the objects' data (model/objects/setlist.py); what knows of files and of
YAML is here, beside the writer (model/file/setlist_writer.py). What older versions wrote is moved to
the layout written now by the migrations (model/file/migrations/), and the file's lists become the
objects' data in model/file/file_layout.py.
"""

import os
import yaml

from llamatron.model.file import files
from llamatron.model.file.checks import pass_over_unknown, reading
from llamatron.model.file.file_layout import as_object_layout
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.migrations import migrated
from llamatron.model.file.safe_yaml import load_safely
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects import sections
from llamatron.model.objects.naming import is_taken
from llamatron.model.vocabulary import file_format
from llamatron.user_strings import errors

# The most corrections one file is opened with, so that a correction that fails to put its value right cannot go on for ever.
MOST_CORRECTIONS = 10000


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


def set_file_data(path):
    """Return a set file's data as the objects read it, and the Conversion that says what moving it from an older layout did:
    the file is read, moved by every migration due (model/file/migrations.py) and turned from the file's lists into the
    objects' layout (model/file/file_layout.py)."""
    data, conversion = migrated(file_data(path), one_song_name=file_stem(path))
    return as_object_layout(data), conversion


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


def as_a_set_is_written(*, data, where, allowed):
    """Return a set's data, checked to be one, or raise SongFileError if it isn't a set at all. allowed is the names of the
    settings a set holds."""
    # Every setting has a default, so an empty file is an empty set.
    data = {} if data is None else data
    if not isinstance(data, dict):
        raise SongFileError(errors.ERR_NOT_A_SETLIST)
    with reading(where):
        pass_over_unknown(data=data, allowed={*allowed, *sections.SETLIST_SECTIONS, file_format.CLOSED_PATTERN_GROUPS, file_format.OPEN_GENERATOR_TYPES})
        _check_generator_names(data)
    return data


def _check_generator_names(data):
    """Refuse two generators of different kinds, a chain among them, of one name: a set file lists them in one list."""
    held = []
    for section in sections.GENERATOR_SECTIONS:
        for name in data.get(section) or {}:
            if is_taken(name=name, taken=held):
                raise InvalidValue(errors.ERR_NAME_TAKEN.format(label=sections.SECTION_LABELS[section], name=name))
            held.append(name)


def read_corrected(*, read, data):
    """Return what read(data) makes of a set file's data once every value that can't be used is changed to the allowed value nearest it, and the corrections made, in the order found.

    Reading stops at the first wrong value. A value with an allowed value near it comes with a
    correction (model/file/corrections.py), which is applied to the data before reading again,
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
