# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""llamatron's version, which the title shows and every saved song file records, and when it was built.

The version is a string of three whole numbers separated by dots, like 1.0.2. The last number
goes up with every commit that changes the program's Python code, and the user changes the
first two when they choose. Versions are compared number by number, never as decimals, so
1.0.10 comes after 1.0.9. Nothing builds the program, so the build date and time are the date
and time of the last version bump, written here by hand with it, and the About dialog shows them.
"""

from llamatron.user_strings import errors

VERSION = '1.0.660'
BUILD_DATE = '2026-11-23'
BUILD_TIME = '21:42'

DATE_SEPARATOR = '-'

VERSION_SEPARATOR = '.'
VERSION_PARTS = 3


def build_year():
    """Return the year of the build date, for the copyright line."""
    return BUILD_DATE.split(DATE_SEPARATOR)[0]


def is_version(text):
    """Return whether text is a version: three whole numbers separated by dots, like 1.0.2."""
    if not isinstance(text, str):
        return False
    parts = text.split(VERSION_SEPARATOR)
    if len(parts) != VERSION_PARTS:
        return False
    for part in parts:
        if not part.isdigit() or not part.isascii():
            return False
    return True


def version_numbers(text):
    """Return a version's three numbers, so versions compare number by number, like (1, 0, 2)."""
    if not is_version(text):
        raise ValueError(errors.ERR_BAD_VERSION_TEXT.format(value=text))
    parts = text.split(VERSION_SEPARATOR)
    return tuple(map(int, parts))
