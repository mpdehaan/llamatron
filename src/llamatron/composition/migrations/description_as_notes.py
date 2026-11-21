# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Files saved before 1.0.155 held the set's long text under description, which is now notes; a description is one line."""

SINCE = '1.0.155'
DESCRIPTION = 'description'
NOTES = 'notes'


def is_before(data):
    """A file with no version gives no sign of which its description is, and is taken as current."""
    return False


def moved(*, data, conversion):
    if DESCRIPTION not in data:
        return data
    moved_data = dict(data)
    moved_data[NOTES] = moved_data.pop(DESCRIPTION)
    return moved_data
