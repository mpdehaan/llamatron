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

"""Checks that several objects make on the values they read from a song file.

Each raises SongFileError with a message that starts with where in the file the value is.
"""

from fractions import Fraction

from llamatron.composition.file_format import MAX_LIVE_OCTAVE, MIN_LIVE_OCTAVE
from llamatron.composition.song_file_error import SongFileError


def check_keys(data, where, allowed):
    """Refuse any setting that isn't one of the allowed names."""
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise SongFileError(f'{where}: unknown setting {unknown[0]!r}, expected one of {sorted(allowed)}')


def number(value, where):
    """Return a number written like 2 or 1/8 as an exact fraction."""
    if isinstance(value, bool):
        raise SongFileError(f'{where}: expected a number, got {value!r}')
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise SongFileError(f'{where}: expected a number like 2 or 1/8, got {value!r}') from None


def positive_length(value, where):
    """Return a length in whole notes, which has to be more than zero."""
    length = number(value, where)
    if length <= 0:
        raise SongFileError(f'{where}: a length must be more than zero, got {value!r}')
    return length


def live_octave(value, where):
    """Return an octave as Live numbers them, checking that it's in range."""
    if type(value) is not int or not MIN_LIVE_OCTAVE <= value <= MAX_LIVE_OCTAVE:
        raise SongFileError(f'{where}: an octave must be a whole number from {MIN_LIVE_OCTAVE} to {MAX_LIVE_OCTAVE}, got {value!r}')
    return value
