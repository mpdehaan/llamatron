# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Checks that several objects make on their values, whether read from a song file, typed in the tracker or set on the grid.

Each check raises InvalidValue with a message that says only what's wrong with the value. A
function named for a value, like number(), returns it converted, and one named check_ only refuses. While
a file is being read, the object's from_data() wraps its checks in reading(where), which adds
where in the file the value is and raises SongFileError instead, so a file's problems are
reported with their place and an edit's problems without one.
"""

from contextlib import contextmanager
from math import isfinite
import re
from typing import NamedTuple

from llamatron.math.rational import Rational
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.values.note import _check_length
from llamatron.model.values.scale import Scale
from llamatron.model.values.time_signature import TimeSignature
from llamatron.model.vocabulary import file_format, limits
from llamatron.user_strings import errors

# A length has to be longer than nothing.
NO_LENGTH = 0
# A whole number has this denominator.
WHOLE = 1
# A length that isn't a whole number, as a file writes it.
FRACTION_TEXT = '{numerator}/{denominator}'

# The place reading() is given for one of the set's own settings whose message names the setting, so that no place is put in front.
TOP_OF_FILE = None
# A length is written as a whole number or a fraction of whole numbers, like 2 or 5/16, never as a decimal.
WRITTEN_LENGTH = re.compile(r'[0-9]+(/[0-9]+)?')


@contextmanager
def reading(where):
    """Turn an InvalidValue raised inside into a SongFileError that says where in the file it was.

    where names the place, like "scene 2, track 'bass'", or is TOP_OF_FILE for one of the set's
    own settings whose message names the setting itself. A SongFileError raised inside, by a
    part of the file that was read within this one, already says where it was and passes through.
    """
    try:
        yield
    except InvalidValue as problem:
        correction = problem.get_correction()
        if correction is not None:
            correction.set_place(where)
        raise SongFileError(str(problem) if where is TOP_OF_FILE else errors.ERR_AT.format(where=where, problem=problem), correction=correction) from None

# How messages list choices, like "arp, auto_ratchet".
LIST_SEPARATOR = ', '


def listed(items):
    """Return items as text for a message, separated by commas and never shown as a Python list."""
    return LIST_SEPARATOR.join(str(item) for item in items)



def pass_over_unknown(*, data, allowed):
    """Take every name that isn't allowed out of data, without a word, so that a file from another version opens and a name
    the program doesn't know, such as a setting taken away from it, is never kept or written again. The data is changed in
    place, as a correction changes it, since a correction keeps the part of the data it puts right; only data read from a file
    can hold such a name, since nothing the program writes does."""
    for name in unknown_names(data=data, allowed=allowed):
        del data[name]


def refuse_unknown(*, data, allowed):
    """Refuse any name that isn't allowed, naming the first one found: for settings handed over by the program itself, by a
    setter or the song wizard, where a name no object knows is a mistake in the code, never a file from another version."""
    unknown = unknown_names(data=data, allowed=allowed)
    if unknown:
        raise InvalidValue(errors.ERR_UNKNOWN_SETTING.format(name=unknown[0], allowed=listed(sorted(allowed))))


def unknown_names(*, data, allowed):
    """Return the names in data that aren't allowed."""
    return [name for name in data if name not in allowed]


def is_whole_number(value):
    """Return whether a value is a whole number, not counting true and false, which Python treats as 1 and 0."""
    return type(value) is int


def is_whole_number_from(*, value, lowest, highest=None):
    """Return whether a value is a whole number at least lowest, and at most highest if given."""
    return is_whole_number(value) and value >= lowest and (highest is None or value <= highest)


def is_true_or_false(value):
    return type(value) is bool


# The values the written settings parse to, by their text. The getters parse a setting on every
# read, and the tracker reads the step size and the time signature for every cell it draws, so
# each distinct text is parsed once; a text always parses to the same immutable value, so nothing
# here ever needs forgetting. Only text and whole numbers are remembered, since a bad value of
# another type can't be a key, and the checks below refuse it anyway.
_PARSED_NUMBERS = {}
_PARSED_LENGTHS = {}
_PARSED_TIME_SIGNATURES = {}


def can_be_remembered(value):
    """Return whether a written value is text or a whole number, the kinds the parsers remember by."""
    return isinstance(value, (str, int)) and not isinstance(value, bool)


def number(value):
    """Return a number written like 2 or 1/8 as an exact fraction."""
    if isinstance(value, bool):
        raise InvalidValue(errors.ERR_EXPECTED_NUMBER.format(value=value))
    if can_be_remembered(value) and value in _PARSED_NUMBERS:
        return _PARSED_NUMBERS[value]
    try:
        parsed = Rational(str(value))
    except (ValueError, ZeroDivisionError):
        raise InvalidValue(errors.ERR_EXPECTED_NUMBER_LIKE.format(value=value)) from None
    if can_be_remembered(value):
        _PARSED_NUMBERS[value] = parsed
    return parsed


def positive_length(value):
    """Return a length in whole notes, which has to be more than zero."""
    length = number(value)
    if length <= NO_LENGTH:
        raise InvalidValue(errors.ERR_LENGTH_NOT_POSITIVE.format(value=value))
    return length


def fraction_text(value):
    """Return an exact length the way a file holds it, as a whole number or text like 3/16, which written_length reads back."""
    if value.denominator == WHOLE:
        return int(value)
    return FRACTION_TEXT.format(numerator=value.numerator, denominator=value.denominator)


def written_length(*, value, most):
    """Return a length written as a whole number or a fraction, like 2 or 5/16, more than zero and at most most.

    Decimals are refused, since they're imprecise and hard to read.
    """
    key = (value, most)
    if can_be_remembered(value) and key in _PARSED_LENGTHS:
        return _PARSED_LENGTHS[key]
    if not is_written_length(value):
        raise InvalidValue(errors.ERR_BAD_WRITTEN_LENGTH.format(value=value))
    length = positive_length(value)
    if length > most:
        raise InvalidValue(errors.ERR_LENGTH_TOO_LONG.format(most=most, value=value))
    _PARSED_LENGTHS[key] = length
    return length


def is_written_length(value):
    """Return whether a value is a whole number or a fraction of whole numbers, not counting true and false."""
    if is_whole_number(value):
        return True
    return isinstance(value, str) and WRITTEN_LENGTH.fullmatch(value) is not None


# The checks the grid's objects share: a ClipGrid, ClipRow, ClipColumn or Clip holds a value, like
# a Scale or a tempo number, rather than the text a file holds.

def check_name(name):
    if name is not None and not isinstance(name, str):
        raise InvalidValue(errors.ERR_INVALID_NAME.format(name=name))


def time_signature(value):
    """Return a time signature written like 6/8 as a TimeSignature."""
    if can_be_remembered(value) and value in _PARSED_TIME_SIGNATURES:
        return _PARSED_TIME_SIGNATURES[value]
    try:
        parsed = TimeSignature.from_text(value)
    except ValueError as problem:
        raise InvalidValue(str(problem)) from None
    if can_be_remembered(value):
        _PARSED_TIME_SIGNATURES[value] = parsed
    return parsed


def check_time_signature(value):
    if not isinstance(value, TimeSignature):
        raise InvalidValue(errors.ERR_NOT_A_TIME_SIGNATURE.format(value=value))


def check_time_signature_override(value):
    """Check a time signature that can be None, meaning the song's."""
    if value is not None:
        check_time_signature(value)


def check_tempo(tempo):
    # bool is a subclass of int, but True is not a real tempo.
    if type(tempo) not in (int, float) or not isfinite(tempo) or tempo < limits.MIN_TEMPO:
        raise InvalidValue(errors.ERR_INVALID_TEMPO.format(tempo=tempo, lowest=limits.MIN_TEMPO))


def check_tempo_override(tempo):
    """Check a tempo that can be None, meaning the song's."""
    if tempo is not None:
        check_tempo(tempo)


def check_scale(scale):
    if scale is not None and not isinstance(scale, Scale):
        raise InvalidValue(errors.ERR_NOT_A_SCALE.format(scale=scale))


def check_loop(loop):
    if type(loop) is not bool:
        raise InvalidValue(errors.ERR_INVALID_LOOP.format(loop=loop))


def check_mute(mute):
    if type(mute) is not bool:
        raise InvalidValue(errors.ERR_INVALID_MUTE.format(mute=mute))


def check_drum(drum):
    if type(drum) is not bool:
        raise InvalidValue(errors.ERR_INVALID_DRUM.format(drum=drum))


def check_fluidsynth(fluidsynth):
    if type(fluidsynth) is not bool:
        raise InvalidValue(errors.ERR_INVALID_FLUIDSYNTH.format(fluidsynth=fluidsynth))


def check_gm_sound(sound):
    """Check a General MIDI sound, 1 to 128 as people number them, or None for none."""
    if sound is not None and (type(sound) is not int or not limits.MIN_GM_SOUND <= sound <= limits.MAX_GM_SOUND):
        raise InvalidValue(errors.ERR_BAD_GM_SOUND.format(lowest=limits.MIN_GM_SOUND, highest=limits.MAX_GM_SOUND, value=sound))


def check_clip_length(length):
    """Check a clip's length or note length, which can be None."""
    if length is not None:
        _check_length(length)


class Bars(NamedTuple):
    """A time setting written as a count of bars, which only the song's time signature can turn into a length."""

    count: int


def bars_written(value):
    """Return the count of bars a text like 2 bars or 1 bar says, or None for any other value."""
    if not isinstance(value, str):
        return None
    if value == file_format.ONE_BAR_WRITTEN:
        return 1
    words = value.split()
    if len(words) == len(file_format.BARS_WRITTEN.split()) and words[0].isdigit() and file_format.BARS_WRITTEN.format(count=words[0]) == value and int(words[0]) > 0:
        return int(words[0])
    return None


def time_length(value):
    """Return a time setting as Bars, for a value like 2 bars, or as a positive length in whole notes, for one like 1/8."""
    count = bars_written(value)
    if count is not None:
        return Bars(count)
    try:
        length = number(value)
    except InvalidValue:
        raise InvalidValue(errors.ERR_BAD_TIME.format(value=value)) from None
    if length <= 0:
        raise InvalidValue(errors.ERR_BAD_TIME.format(value=value))
    return length


def in_whole_notes(*, time, bar):
    """Return a time setting as a length in whole notes, a count of bars taking a bar as long as given."""
    parsed = time_length(time)
    return bar * parsed.count if isinstance(parsed, Bars) else parsed
