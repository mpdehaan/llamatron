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

from llamatron.composition.checks import check_keys, live_octave, positive_length
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, CHORD_SYMBOLS, DEFAULT_ACCUMULATOR_LIMIT, DIRECTIONS, FORWARD, NOTE_LETTERS,
    PATTERN_ROWS, TOGGLE_ROWS,
)
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError


class Pattern(LlamaData):
    """A number of steps, and for each row, like degree or velocity, a value for every step.

    A row the file leaves out is kept as None, which means every step is blank on that row. A
    blank degree is a rest, and other blanks mean that row's default. A drum pattern holds note
    letters in its degree row instead of scale degrees.
    """

    def __init__(self, steps, rows, drum=None, direction=None, accumulator_limit=None):
        self._steps = steps
        self._rows = {row: (None if rows.get(row) is None else list(rows[row])) for row in PATTERN_ROWS}
        self._drum = drum
        self._direction = direction
        self._accumulator_limit = accumulator_limit

    @classmethod
    def from_data(cls, data, where, song=None):
        if not isinstance(data, dict):
            raise SongFileError(f'{where}: expected settings like steps, degree and duration')
        check_keys(data, where, {'steps', 'drum', 'direction', 'accumulator_limit', *PATTERN_ROWS})
        limit = data.get('accumulator_limit', DEFAULT_ACCUMULATOR_LIMIT)
        if type(limit) is not int or limit < 1:
            raise SongFileError(f'{where}: accumulator_limit must be a whole number of 1 or more, got {limit!r}')
        check_direction(data.get('direction', FORWARD), where)
        steps = data.get('steps')
        if type(steps) is not int or steps < 1:
            raise SongFileError(f'{where}: steps must be a whole number of 1 or more, got {steps!r}')
        drum = data.get('drum', False)
        if type(drum) is not bool:
            raise SongFileError(f'{where}: drum must be true or false, got {drum!r}')
        for row in PATTERN_ROWS:
            values = data.get(row)
            if values is None:
                continue
            if not isinstance(values, list) or len(values) != steps:
                raise SongFileError(f'{where}: {row} must be a list of {steps} values, got {values!r}')
            for value in values:
                if row in TOGGLE_ROWS and value is None:
                    raise SongFileError(f'{where}: {row} must be true or false, got null')
                if value is not None:
                    _check_step_value(row, value, drum, where)
        rows = {row: data.get(row) for row in PATTERN_ROWS}
        return cls(steps, rows, data.get('drum'), data.get('direction'), data.get('accumulator_limit'))

    def to_data(self):
        data = {'steps': self._steps}
        for name, value in (('drum', self._drum), ('direction', self._direction), ('accumulator_limit', self._accumulator_limit)):
            if value is not None:
                data[name] = value
        for row in PATTERN_ROWS:
            if self._rows[row] is not None:
                data[row] = list(self._rows[row])
        return data

    def get_steps(self):
        return self._steps

    def is_drum(self):
        return bool(self._drum)

    def get_direction(self):
        """Return the order its steps play in, forward unless the pattern sets another."""
        return self._direction or FORWARD

    def get_accumulator_limit(self):
        """Return how far its note and velocity totals can go, either way, before they clear."""
        return DEFAULT_ACCUMULATOR_LIMIT if self._accumulator_limit is None else self._accumulator_limit

    def get_value(self, row, step):
        """Return one step's value on a row, or None if it's blank there."""
        values = self._rows[row]
        return values[step] if values else None

    def get_note_steps(self):
        """Return the steps that play something, which are the ones with a degree."""
        return [step for step in range(self._steps) if self.get_value('degree', step) is not None]

    def get_first_octave(self):
        """Return the octave of the first step that sets one, or None if no step does."""
        return next((value for value in (self._rows['octave'] or []) if value is not None), None)


def check_direction(direction, where):
    """Refuse a play direction that isn't one of the Cirklon's names for them."""
    if direction not in DIRECTIONS:
        raise SongFileError(f'{where}: direction must be one of {DIRECTIONS}, got {direction!r}')


def _check_step_value(row, value, drum, where):
    """Refuse a value that doesn't belong on a row, saying which row and what it should be."""
    problem = None
    if row == 'degree':
        if drum and (not isinstance(value, str) or value not in NOTE_LETTERS or len(value) != 1):
            problem = 'in a drum pattern, must be a note letter from A to G'
        if not drum and (type(value) is not int or value < 1):
            problem = 'must be a scale degree of 1 or more'
    elif row == 'duration':
        positive_length(value, f'{where}, duration')
    elif row == 'accidental' and value not in ACCIDENTALS:
        problem = 'must be # or b'
    elif row == 'octave':
        live_octave(value, f'{where}, octave')
    elif row == 'chord':
        if drum:
            problem = 'isn\'t used in a drum pattern'
        elif str(value) not in CHORD_SYMBOLS:
            problem = f"must be one of {', '.join(CHORD_SYMBOLS)}"
    elif row == 'velocity' and (type(value) is not int or not 1 <= value <= 127):
        problem = 'must be a whole number from 1 to 127'
    elif row == 'probability' and (type(value) is not int or not 0 <= value <= 100):
        problem = 'must be a whole number from 0 to 100'
    elif row == 'ratchet' and (type(value) is not int or value < 1):
        problem = 'must be a whole number of 1 or more'
    elif row in TOGGLE_ROWS and type(value) is not bool:
        problem = 'must be true or false'
    elif row in CC_ROWS and (type(value) is not int or not 0 <= value <= 127):
        problem = 'must be a whole number from 0 to 127'
    elif row in ('ratchet_offset', 'note_add', 'velocity_add') and type(value) is not int:
        problem = 'must be a whole number'
    if problem:
        raise SongFileError(f'{where}: {row} {problem}, got {value!r}')
