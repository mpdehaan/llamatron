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

"""Checks that several objects make on their values, whether read from a song file or typed in the tracker.

Each check raises InvalidValue with a message that says only what's wrong with the value. While
a file is being read, the object's from_data() wraps its checks in reading(where), which adds
where in the file the value is and raises SongFileError instead, so a file's problems are
reported with their place and an edit's problems without one.
"""

import re
from contextlib import contextmanager

from llamatron.rational import Rational
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MAX_LIVE_OCTAVE, MIN_LIVE_OCTAVE
from llamatron.composition.song_file_error import SongFileError

# A length has to be longer than nothing.
NO_LENGTH = 0

# A length is written as a whole number or a fraction of whole numbers, like 2 or 5/16, never as a decimal.
WRITTEN_LENGTH = re.compile(r'[0-9]+(/[0-9]+)?')
MSG_AT = '{where}: {problem}'
MSG_BAD_WRITTEN_LENGTH = 'expected a whole number or a fraction like 1/8, got {value!r}'
MSG_LENGTH_TOO_LONG = 'a length can be at most {most}, got {value!r}'
MSG_UNKNOWN_SETTING = 'unknown setting {name!r}, expected one of {allowed}'
MSG_EXPECTED_NUMBER = 'expected a number, got {value!r}'
MSG_EXPECTED_NUMBER_LIKE = 'expected a number like 2 or 1/8, got {value!r}'
MSG_LENGTH_NOT_POSITIVE = 'a length must be more than zero, got {value!r}'
MSG_BAD_OCTAVE = 'an octave must be a whole number from {lowest} to {highest}, got {value!r}'


@contextmanager
def reading(where):
    """Turn an InvalidValue raised inside into a SongFileError that says where in the file it was.

    where names the place, like "scene 2, track 'bass'". A SongFileError raised inside, by a
    part of the file that was read within this one, already says where it was and passes through.
    """
    try:
        yield
    except InvalidValue as problem:
        raise SongFileError(MSG_AT.format(where=where, problem=problem)) from None


def check_keys(data, allowed):
    """Refuse any setting that isn't one of the allowed names, naming the first one found."""
    unknown = unknown_settings(data, allowed)
    if unknown:
        raise InvalidValue(MSG_UNKNOWN_SETTING.format(name=unknown[0], allowed=sorted(allowed)))


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


def number(value):
    """Return a number written like 2 or 1/8 as an exact fraction."""
    if isinstance(value, bool):
        raise InvalidValue(MSG_EXPECTED_NUMBER.format(value=value))
    try:
        return Rational(str(value))
    except (ValueError, ZeroDivisionError):
        raise InvalidValue(MSG_EXPECTED_NUMBER_LIKE.format(value=value)) from None


def positive_length(value):
    """Return a length in whole notes, which has to be more than zero."""
    length = number(value)
    if length <= NO_LENGTH:
        raise InvalidValue(MSG_LENGTH_NOT_POSITIVE.format(value=value))
    return length


def live_octave(value):
    """Return an octave as Live numbers them, checking that it's in range."""
    if not is_whole_number_from(value, MIN_LIVE_OCTAVE, MAX_LIVE_OCTAVE):
        raise InvalidValue(MSG_BAD_OCTAVE.format(lowest=MIN_LIVE_OCTAVE, highest=MAX_LIVE_OCTAVE, value=value))
    return value


def written_length(value, most):
    """Return a length written as a whole number or a fraction, like 2 or 5/16, more than zero and at most most.

    Decimals are refused, since they're imprecise and hard to read.
    """
    if not is_written_length(value):
        raise InvalidValue(MSG_BAD_WRITTEN_LENGTH.format(value=value))
    length = positive_length(value)
    if length > most:
        raise InvalidValue(MSG_LENGTH_TOO_LONG.format(most=most, value=value))
    return length


def is_written_length(value):
    """Return whether a value is a whole number or a fraction of whole numbers, not counting true and false."""
    if is_whole_number(value):
        return True
    return isinstance(value, str) and WRITTEN_LENGTH.fullmatch(value) is not None
