# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The error raised for anything wrong in a song file."""


class SongFileError(Exception):
    """A problem with a song file, described in a way that points to where to fix it.

    When the problem is a value with an allowed value near it, the error carries the Correction
    that would put that value in the file's data (composition/corrections.py).
    """

    def __init__(self, message, *, correction=None):
        super().__init__(message)
        self._correction = correction

    def get_correction(self):
        """Return the correction that would put the problem right, or None when the file can only be refused."""
        return self._correction
