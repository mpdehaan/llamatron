# llamatron: a Python language and framework for producing MIDI clips.
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


class InvalidValue(Exception):
    """A value that doesn't fit where it's being put, such as a tempo of zero or a repeat of 1.5.

    Its message says only what's wrong with the value, like "repeat must be a positive whole
    number, got 1.5", so the tracker can show it beside the field being edited. While a file
    is being read, checks.reading() adds where in the file the value is and raises it again as
    a SongFileError.
    """
