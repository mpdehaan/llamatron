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

"""The error raised for a value that an object refuses."""


class InvalidValue(ValueError):
    """A value that doesn't fit where it's being put, such as a tempo of zero or a repeat of 1.5.

    It's a ValueError, so that code which only knows Python's own errors still catches it, and it's
    the one error every check in llamatron raises, whether on a song file's objects or the grid's.

    Its message says only what's wrong with the value, like "repeat must be a positive whole
    number, got 1.5", so the tracker can show it beside the field being edited. While a file
    is being read, checks.reading() adds where in the file the value is and raises it again as
    a SongFileError.

    A value that can't be used but has an allowed value near it, like a repeat of 0, can carry
    the Correction that would put the nearest value in the file's data
    (composition/corrections.py), for whoever offers to open the file corrected.
    """

    def __init__(self, message, *, correction=None):
        super().__init__(message)
        self._correction = correction

    def get_correction(self):
        """Return the correction that would put this value right, or None when no allowed value is near it."""
        return self._correction

    def with_correction(self, correction):
        """Return this same problem carrying a correction, or None for none."""
        return InvalidValue(str(self), correction=correction)
