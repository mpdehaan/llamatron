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

from llamatron.composition.checks import check_keys, reading, is_true_or_false, is_whole_number, is_whole_number_from, live_octave, written_length
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, CHORD_SYMBOLS, DIRECTIONS, GATE_MODIFIERS, NOTE_LETTERS, PATTERN_ROWS, REGISTER_ADD_ROWS,
    REGISTER_NOTE_ROWS, SIGNED_ROWS, TOGGLE_ROWS, Direction, PatternSetting, Row,
)
from llamatron.composition.limits import (
    MAX_CC_VALUE, MAX_GATE, MAX_PROBABILITY, MAX_REGISTER_VALUE, MAX_STEP_SIZE, MAX_VELOCITY, MIN_CC_VALUE, MIN_DEGREE,
    MIN_PROBABILITY, MIN_RATCHET, MIN_REGISTER_VALUE, MIN_STEPS, MIN_VELOCITY,
)
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.invalid_value import InvalidValue

MSG_EXPECTED_SETTINGS = 'expected settings like steps, degree and gate'
MSG_BAD_STEPS = 'steps must be a whole number of {lowest} or more, got {value!r}'
MSG_DRUM_NOT_TRUE_OR_FALSE = 'drum must be true or false, got {value!r}'
MSG_BAD_DIRECTION = 'direction must be one of {directions}, got {value!r}'
MSG_ROW_WRONG_LENGTH = '{row} must be a list of {steps} values, got {value!r}'
MSG_TOGGLE_IS_NULL = '{row} must be true or false, got null'
MSG_BAD_STEP_VALUE = '{row} {problem}, got {value!r}'
MSG_TIE_ON_A_NOTE = "step {step} has a note and a tie, but a tied step only holds the note before it, so it can't have its own"
# Steps are counted from 1 in messages, as the editor shows them.
FIRST_STEP_NUMBER = 1
# What a step's value has to be on each kind of row, for MSG_BAD_STEP_VALUE.
PROBLEM_NOT_NOTE_LETTER = 'in a drum pattern, must be a note letter from A to G'
PROBLEM_NOT_DEGREE = 'must be a scale degree of {lowest} or more'
PROBLEM_NOT_ACCIDENTAL = 'must be # or b'
PROBLEM_NOT_GATE_MODIFIER = 'must be d for dotted or t for triplet'
PROBLEM_CHORD_ON_DRUMS = "isn't used in a drum pattern"
PROBLEM_REGISTER_NOTE_ON_DRUMS = "can't move notes in a drum pattern, so it can only be false"
PROBLEM_NOT_CHORD = 'must be one of {symbols}'
PROBLEM_NOT_IN_RANGE = 'must be a whole number from {lowest} to {highest}'
PROBLEM_TOO_SMALL = 'must be a whole number of {lowest} or more'
PROBLEM_NOT_TRUE_OR_FALSE = 'must be true or false'
PROBLEM_NOT_WHOLE_NUMBER = 'must be a whole number'
# How the places of a gate, an octave or a step size in a pattern are named in messages.
WHERE_IN_ROW = '{where}, {row}'
# Chord symbols, as messages list them.
SYMBOL_SEPARATOR = ', '
# A drum pattern's degree row holds one note letter per step.
NOTE_LETTER_LENGTH = 1
# A pattern's settings besides its rows, in the order they're written to a file.
SETTINGS = [PatternSetting.STEP_SIZE, PatternSetting.DRUM, PatternSetting.DIRECTION]


class Pattern(LlamaData):
    """A number of steps, and for each row, like degree or velocity, a value for every step.

    A row the file leaves out is kept as None, which means every step is blank on that row. A
    blank degree is a rest, and other blanks mean that row's default. A drum pattern holds note
    letters in its degree row instead of scale degrees.
    """

    __slots__ = ('_steps', '_rows', '_settings')

    def __init__(self, steps, rows, step_size=None, drum=None, direction=None):
        self._steps = steps
        self._rows = _copied_rows(rows)
        self._settings = {PatternSetting.STEP_SIZE: step_size, PatternSetting.DRUM: drum, PatternSetting.DIRECTION: direction}

    @classmethod
    def from_data(cls, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(MSG_EXPECTED_SETTINGS)
            check_keys(data, {PatternSetting.STEPS, *SETTINGS, *PATTERN_ROWS})
            check_direction(data.get(PatternSetting.DIRECTION, Direction.FORWARD))
            steps = data.get(PatternSetting.STEPS)
            if not is_whole_number_from(steps, MIN_STEPS):
                raise InvalidValue(MSG_BAD_STEPS.format(lowest=MIN_STEPS, value=steps))
            if PatternSetting.STEP_SIZE in data:
                with reading(WHERE_IN_ROW.format(where=where, row=PatternSetting.STEP_SIZE)):
                    written_length(data[PatternSetting.STEP_SIZE], MAX_STEP_SIZE)
            drum = data.get(PatternSetting.DRUM, False)
            if not is_true_or_false(drum):
                raise InvalidValue(MSG_DRUM_NOT_TRUE_OR_FALSE.format(value=drum))
            for row in PATTERN_ROWS:
                _check_row(row, data.get(row), steps, drum, where)
            _check_ties(data, steps)
            rows = {row: data.get(row) for row in PATTERN_ROWS}
            return cls(steps, rows, **{name: data.get(name) for name in SETTINGS})

    def to_data(self):
        data = {PatternSetting.STEPS: self._steps}
        data.update({name: value for name, value in self._settings.items() if value is not None})
        data.update({row: list(values) for row, values in self._rows.items() if values is not None})
        return data

    def get_steps(self):
        return self._steps

    def get_step_size(self):
        """Return how long each of its steps is, in whole notes, or None to use the song's step size."""
        step_size = self.get_written_step_size()
        return None if step_size is None else written_length(step_size, MAX_STEP_SIZE)

    def get_written_step_size(self):
        """Return its step size as the file writes it, like 1/8, or None to use the song's."""
        return self._settings[PatternSetting.STEP_SIZE]

    def is_drum(self):
        return bool(self._settings[PatternSetting.DRUM])

    def get_direction(self):
        """Return the order its steps play in, forward unless the pattern sets another."""
        return self._settings[PatternSetting.DIRECTION] or Direction.FORWARD

    def get_row(self, row):
        """Return a copy of one row's values, one per step, or None if the row is blank throughout."""
        values = self._rows[row]
        return None if values is None else list(values)

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


def check_direction(direction):
    """Refuse a play direction that isn't one of the Cirklon's names for them."""
    if direction not in DIRECTIONS:
        raise InvalidValue(MSG_BAD_DIRECTION.format(directions=DIRECTIONS, value=direction))


def _check_row(row, values, steps, drum, where):
    """Refuse a row that isn't a list with a value for every step, or that holds a value it can't."""
    if values is None:
        return
    if not isinstance(values, list) or len(values) != steps:
        raise InvalidValue(MSG_ROW_WRONG_LENGTH.format(row=row, steps=steps, value=values))
    for value in values:
        if row in TOGGLE_ROWS and value is None:
            raise InvalidValue(MSG_TOGGLE_IS_NULL.format(row=row))
        if value is not None:
            _check_step_value(row, value, drum, where)


def _check_ties(data, steps):
    """Refuse a tie on a step that has a note, since a tied step plays nothing of its own."""
    ties, degrees = data.get(Row.TIE), data.get(Row.DEGREE)
    if not ties or not degrees:
        return
    for step in range(steps):
        if ties[step] and degrees[step] is not None:
            raise InvalidValue(MSG_TIE_ON_A_NOTE.format(step=step + FIRST_STEP_NUMBER))


def _check_step_value(row, value, drum, where):
    """Refuse a value that doesn't belong on a row, saying which row and what it should be."""
    with reading(WHERE_IN_ROW.format(where=where, row=row)):
        if row == Row.GATE:
            written_length(value, MAX_GATE)
        elif row == Row.OCTAVE:
            live_octave(value)
    problem = _step_value_problem(row, value, drum)
    if problem:
        raise InvalidValue(MSG_BAD_STEP_VALUE.format(row=row, problem=problem, value=value))


def _step_value_problem(row, value, drum):
    """Return what's wrong with a step's value on a row, or None if nothing is."""
    if row == Row.DEGREE:
        if drum and not _is_note_letter(value):
            return PROBLEM_NOT_NOTE_LETTER
        if not drum and not is_whole_number_from(value, MIN_DEGREE):
            return PROBLEM_NOT_DEGREE.format(lowest=MIN_DEGREE)
    elif row == Row.ACCIDENTAL and value not in ACCIDENTALS:
        return PROBLEM_NOT_ACCIDENTAL
    elif row == Row.DOT and value not in GATE_MODIFIERS:
        return PROBLEM_NOT_GATE_MODIFIER
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
    elif row in REGISTER_NOTE_ROWS.values() and drum and value:
        return PROBLEM_REGISTER_NOTE_ON_DRUMS
    elif row in REGISTER_ADD_ROWS.values() and not is_whole_number_from(value, MIN_REGISTER_VALUE, MAX_REGISTER_VALUE):
        return PROBLEM_NOT_IN_RANGE.format(lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE)
    elif row in CC_ROWS and not is_whole_number_from(value, MIN_CC_VALUE, MAX_CC_VALUE):
        return PROBLEM_NOT_IN_RANGE.format(lowest=MIN_CC_VALUE, highest=MAX_CC_VALUE)
    elif row in SIGNED_ROWS and not is_whole_number(value):
        return PROBLEM_NOT_WHOLE_NUMBER
    return None


def _is_note_letter(value):
    """Return whether a value is one note letter, A to G, as a drum pattern's degree row holds."""
    return isinstance(value, str) and len(value) == NOTE_LETTER_LENGTH and value in NOTE_LETTERS
