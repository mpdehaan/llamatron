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
