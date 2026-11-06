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

import re
from fractions import Fraction

from llamatron.composition.limits import MAX_LIVE_OCTAVE, MIN_LIVE_OCTAVE
from llamatron.composition.song_file_error import SongFileError

# A length has to be longer than nothing.
NO_LENGTH = 0

# A length is written as a whole number or a fraction of whole numbers, like 2 or 5/16, never as a decimal.
WRITTEN_LENGTH = re.compile(r'[0-9]+(/[0-9]+)?')
MSG_BAD_WRITTEN_LENGTH = '{where}: expected a whole number or a fraction like 1/8, got {value!r}'
MSG_LENGTH_TOO_LONG = '{where}: a length can be at most {most}, got {value!r}'
MSG_UNKNOWN_SETTING = '{where}: unknown setting {name!r}, expected one of {allowed}'
MSG_EXPECTED_NUMBER = '{where}: expected a number, got {value!r}'
MSG_EXPECTED_NUMBER_LIKE = '{where}: expected a number like 2 or 1/8, got {value!r}'
MSG_LENGTH_NOT_POSITIVE = '{where}: a length must be more than zero, got {value!r}'
MSG_BAD_OCTAVE = '{where}: an octave must be a whole number from {lowest} to {highest}, got {value!r}'


def check_keys(data, where, allowed):
    """Refuse any setting that isn't one of the allowed names, naming the first one found."""
    unknown = unknown_settings(data, allowed)
    if unknown:
        raise SongFileError(MSG_UNKNOWN_SETTING.format(where=where, name=unknown[0], allowed=sorted(allowed)))


def unknown_settings(data, allowed):
    """Return the names in data that aren't allowed, in alphabetical order."""
    return sorted(set(data) - set(allowed))


def is_whole_number(value):
    """Return whether a value is a whole number, not counting true and false, which Python treats as 1 and 0."""
    return type(value) is int


def is_whole_number_from(value, lowest, highest=None):
    """Return whether a value is a whole number at least lowest, and at most highest if given."""
    return is_whole_number(value) and value >= lowest and (highest is None or value <= highest)


def is_true_or_false(value):
    return type(value) is bool


def number(value, where):
    """Return a number written like 2 or 1/8 as an exact fraction."""
    if isinstance(value, bool):
        raise SongFileError(MSG_EXPECTED_NUMBER.format(where=where, value=value))
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise SongFileError(MSG_EXPECTED_NUMBER_LIKE.format(where=where, value=value)) from None


def positive_length(value, where):
    """Return a length in whole notes, which has to be more than zero."""
    length = number(value, where)
    if length <= NO_LENGTH:
        raise SongFileError(MSG_LENGTH_NOT_POSITIVE.format(where=where, value=value))
    return length


def live_octave(value, where):
    """Return an octave as Live numbers them, checking that it's in range."""
    if not is_whole_number_from(value, MIN_LIVE_OCTAVE, MAX_LIVE_OCTAVE):
        raise SongFileError(MSG_BAD_OCTAVE.format(where=where, lowest=MIN_LIVE_OCTAVE, highest=MAX_LIVE_OCTAVE, value=value))
    return value


def written_length(value, where, most):
    """Return a length written as a whole number or a fraction, like 2 or 5/16, more than zero and at most most.

    Decimals are refused, since they're imprecise and hard to read.
    """
    if not is_written_length(value):
        raise SongFileError(MSG_BAD_WRITTEN_LENGTH.format(where=where, value=value))
    length = positive_length(value, where)
    if length > most:
        raise SongFileError(MSG_LENGTH_TOO_LONG.format(where=where, most=most, value=value))
    return length


def is_written_length(value):
    """Return whether a value is a whole number or a fraction of whole numbers, not counting true and false."""
    if is_whole_number(value):
        return True
    return isinstance(value, str) and WRITTEN_LENGTH.fullmatch(value) is not None
