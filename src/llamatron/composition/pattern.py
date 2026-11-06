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

"""A pattern: a row of steps, with one list of values for each row of the pattern editor."""

from llamatron.composition.checks import check_keys, is_true_or_false, is_whole_number, is_whole_number_from, live_octave, positive_length
from llamatron.composition.defaults import DEFAULT_ACCUMULATOR_LIMIT
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, CHORD_SYMBOLS, DIRECTIONS, NOTE_LETTERS, PATTERN_ROWS, SIGNED_ROWS, TOGGLE_ROWS,
    Direction, PatternSetting, Row,
)
from llamatron.composition.limits import (
    MAX_CC_VALUE, MAX_PROBABILITY, MAX_VELOCITY, MIN_ACCUMULATOR_LIMIT, MIN_CC_VALUE, MIN_DEGREE, MIN_PROBABILITY,
    MIN_RATCHET, MIN_STEPS, MIN_VELOCITY,
)
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError

MSG_EXPECTED_SETTINGS = '{where}: expected settings like steps, degree and duration'
MSG_BAD_ACCUMULATOR_LIMIT = '{where}: accumulator_limit must be a whole number of {lowest} or more, got {value!r}'
MSG_BAD_STEPS = '{where}: steps must be a whole number of {lowest} or more, got {value!r}'
MSG_DRUM_NOT_TRUE_OR_FALSE = '{where}: drum must be true or false, got {value!r}'
MSG_BAD_DIRECTION = '{where}: direction must be one of {directions}, got {value!r}'
MSG_ROW_WRONG_LENGTH = '{where}: {row} must be a list of {steps} values, got {value!r}'
MSG_TOGGLE_IS_NULL = '{where}: {row} must be true or false, got null'
MSG_BAD_STEP_VALUE = '{where}: {row} {problem}, got {value!r}'
# What a step's value has to be on each kind of row, for MSG_BAD_STEP_VALUE.
PROBLEM_NOT_NOTE_LETTER = 'in a drum pattern, must be a note letter from A to G'
PROBLEM_NOT_DEGREE = 'must be a scale degree of {lowest} or more'
PROBLEM_NOT_ACCIDENTAL = 'must be # or b'
PROBLEM_CHORD_ON_DRUMS = "isn't used in a drum pattern"
PROBLEM_NOT_CHORD = 'must be one of {symbols}'
PROBLEM_NOT_IN_RANGE = 'must be a whole number from {lowest} to {highest}'
PROBLEM_TOO_SMALL = 'must be a whole number of {lowest} or more'
PROBLEM_NOT_TRUE_OR_FALSE = 'must be true or false'
PROBLEM_NOT_WHOLE_NUMBER = 'must be a whole number'
# How the places of a duration or an octave in a pattern are named in messages.
WHERE_IN_ROW = '{where}, {row}'
# Chord symbols, as messages list them.
SYMBOL_SEPARATOR = ', '
# A drum pattern's degree row holds one note letter per step.
NOTE_LETTER_LENGTH = 1
# A pattern's settings besides its rows, in the order they're written to a file.
SETTINGS = [PatternSetting.DRUM, PatternSetting.DIRECTION, PatternSetting.ACCUMULATOR_LIMIT]


class Pattern(LlamaData):
    """A number of steps, and for each row, like degree or velocity, a value for every step.

    A row the file leaves out is kept as None, which means every step is blank on that row. A
    blank degree is a rest, and other blanks mean that row's default. A drum pattern holds note
    letters in its degree row instead of scale degrees.
    """

    __slots__ = ('_steps', '_rows', '_settings')

    def __init__(self, steps, rows, drum=None, direction=None, accumulator_limit=None):
        self._steps = steps
        self._rows = _copied_rows(rows)
        self._settings = {PatternSetting.DRUM: drum, PatternSetting.DIRECTION: direction, PatternSetting.ACCUMULATOR_LIMIT: accumulator_limit}

    @classmethod
    def from_data(cls, data, where, song=None):
        if not isinstance(data, dict):
            raise SongFileError(MSG_EXPECTED_SETTINGS.format(where=where))
        check_keys(data, where, {PatternSetting.STEPS, *SETTINGS, *PATTERN_ROWS})
        limit = data.get(PatternSetting.ACCUMULATOR_LIMIT, DEFAULT_ACCUMULATOR_LIMIT)
        if not is_whole_number_from(limit, MIN_ACCUMULATOR_LIMIT):
            raise SongFileError(MSG_BAD_ACCUMULATOR_LIMIT.format(where=where, lowest=MIN_ACCUMULATOR_LIMIT, value=limit))
        check_direction(data.get(PatternSetting.DIRECTION, Direction.FORWARD), where)
        steps = data.get(PatternSetting.STEPS)
        if not is_whole_number_from(steps, MIN_STEPS):
            raise SongFileError(MSG_BAD_STEPS.format(where=where, lowest=MIN_STEPS, value=steps))
        drum = data.get(PatternSetting.DRUM, False)
        if not is_true_or_false(drum):
            raise SongFileError(MSG_DRUM_NOT_TRUE_OR_FALSE.format(where=where, value=drum))
        for row in PATTERN_ROWS:
            _check_row(row, data.get(row), steps, drum, where)
        rows = {row: data.get(row) for row in PATTERN_ROWS}
        return cls(steps, rows, **{name: data.get(name) for name in SETTINGS})

    def to_data(self):
        data = {PatternSetting.STEPS: self._steps}
        data.update({name: value for name, value in self._settings.items() if value is not None})
        data.update({row: list(values) for row, values in self._rows.items() if values is not None})
        return data

    def get_steps(self):
        return self._steps

    def is_drum(self):
        return bool(self._settings[PatternSetting.DRUM])

    def get_direction(self):
        """Return the order its steps play in, forward unless the pattern sets another."""
        return self._settings[PatternSetting.DIRECTION] or Direction.FORWARD

    def get_accumulator_limit(self):
        """Return how far its note and velocity totals can go, either way, before they clear."""
        limit = self._settings[PatternSetting.ACCUMULATOR_LIMIT]
        return DEFAULT_ACCUMULATOR_LIMIT if limit is None else limit

    def get_value(self, row, step):
        """Return one step's value on a row, or None if it's blank there."""
        values = self._rows[row]
        return values[step] if values else None

    def get_note_steps(self):
        """Return the steps that play something, which are the ones with a degree."""
        return [step for step in range(self._steps) if self.get_value(Row.DEGREE, step) is not None]

    def get_first_octave(self):
        """Return the octave of the first step that sets one, or None if no step does."""
        octaves = self._rows[Row.OCTAVE] or []
        return next((octave for octave in octaves if octave is not None), None)


def _copied_rows(rows):
    """Return a copy of every row's list of values, with None for a row that isn't given, so the pattern owns its lists."""
    return {row: (None if rows.get(row) is None else list(rows[row])) for row in PATTERN_ROWS}


def check_direction(direction, where):
    """Refuse a play direction that isn't one of the Cirklon's names for them."""
    if direction not in DIRECTIONS:
        raise SongFileError(MSG_BAD_DIRECTION.format(where=where, directions=DIRECTIONS, value=direction))


def _check_row(row, values, steps, drum, where):
    """Refuse a row that isn't a list with a value for every step, or that holds a value it can't."""
    if values is None:
        return
    if not isinstance(values, list) or len(values) != steps:
        raise SongFileError(MSG_ROW_WRONG_LENGTH.format(where=where, row=row, steps=steps, value=values))
    for value in values:
        if row in TOGGLE_ROWS and value is None:
            raise SongFileError(MSG_TOGGLE_IS_NULL.format(where=where, row=row))
        if value is not None:
            _check_step_value(row, value, drum, where)


def _check_step_value(row, value, drum, where):
    """Refuse a value that doesn't belong on a row, saying which row and what it should be."""
    if row == Row.DURATION:
        positive_length(value, WHERE_IN_ROW.format(where=where, row=row))
    elif row == Row.OCTAVE:
        live_octave(value, WHERE_IN_ROW.format(where=where, row=row))
    problem = _step_value_problem(row, value, drum)
    if problem:
        raise SongFileError(MSG_BAD_STEP_VALUE.format(where=where, row=row, problem=problem, value=value))


def _step_value_problem(row, value, drum):
    """Return what's wrong with a step's value on a row, or None if nothing is."""
    if row == Row.DEGREE:
        if drum and not _is_note_letter(value):
            return PROBLEM_NOT_NOTE_LETTER
        if not drum and not is_whole_number_from(value, MIN_DEGREE):
            return PROBLEM_NOT_DEGREE.format(lowest=MIN_DEGREE)
    elif row == Row.ACCIDENTAL and value not in ACCIDENTALS:
        return PROBLEM_NOT_ACCIDENTAL
    elif row == Row.CHORD:
        if drum:
            return PROBLEM_CHORD_ON_DRUMS
        if str(value) not in CHORD_SYMBOLS:
            return PROBLEM_NOT_CHORD.format(symbols=SYMBOL_SEPARATOR.join(CHORD_SYMBOLS))
    elif row == Row.VELOCITY and not is_whole_number_from(value, MIN_VELOCITY, MAX_VELOCITY):
        return PROBLEM_NOT_IN_RANGE.format(lowest=MIN_VELOCITY, highest=MAX_VELOCITY)
    elif row == Row.PROBABILITY and not is_whole_number_from(value, MIN_PROBABILITY, MAX_PROBABILITY):
        return PROBLEM_NOT_IN_RANGE.format(lowest=MIN_PROBABILITY, highest=MAX_PROBABILITY)
    elif row == Row.RATCHET and not is_whole_number_from(value, MIN_RATCHET):
        return PROBLEM_TOO_SMALL.format(lowest=MIN_RATCHET)
    elif row in TOGGLE_ROWS and not is_true_or_false(value):
        return PROBLEM_NOT_TRUE_OR_FALSE
    elif row in CC_ROWS and not is_whole_number_from(value, MIN_CC_VALUE, MAX_CC_VALUE):
        return PROBLEM_NOT_IN_RANGE.format(lowest=MIN_CC_VALUE, highest=MAX_CC_VALUE)
    elif row in SIGNED_ROWS and not is_whole_number(value):
        return PROBLEM_NOT_WHOLE_NUMBER
    return None


def _is_note_letter(value):
    """Return whether a value is one note letter, A to G, as a drum pattern's degree row holds."""
    return isinstance(value, str) and len(value) == NOTE_LETTER_LENGTH and value in NOTE_LETTERS
