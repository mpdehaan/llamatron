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

"""A pattern: a row of steps, with one list of values for each row of the pattern editor.

Everything that reads or changes a pattern's steps is here: reading and saving it, checking its
values, editing single values, resizing and rearranging it, and working out what a step plays.
"""

from llamatron.composition.checks import check_keys, is_whole_number, is_whole_number_from, reading, time_signature, written_length
from llamatron.composition.file_format import (
    ACCIDENTALS, CC_ROWS, DIRECTIONS, PATTERN_ROWS, REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, Direction, PatternSetting, Row,
    CONDITION_ROWS, REGISTER_SET_ROWS,
)
from llamatron.music.note import Note
from llamatron.support.random_source import random_source
from llamatron.composition.limits import MAX_GATE, MAX_STEP_SIZE, MIN_DEGREE, MIN_STEPS
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.composition.llama_data import LlamaData, written_settings
from llamatron.composition.pattern_notes import PatternNotes
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.corrections import LEFT_OUT, NO_NEAREST_VALUE, Correction
from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS, row_described, rows_where
from llamatron.composition.setting import Checked, Choice, Flag, Length, described, settings_held
from llamatron.strings.errors import (
    ERR_BAD_DIRECTION, ERR_BAD_STEPS, ERR_DRUM_NOT_TRUE_OR_FALSE, ERR_PATTERN_EXPECTED_SETTINGS, ERR_PATTERN_NO_SUCH_STEP,
    ERR_PATTERN_NOT_AN_ORDER, ERR_ROW_WRONG_LENGTH, ERR_TIE_ON_A_NOTE, ERR_TOGGLE_IS_NULL, ERR_WHERE_IN_ROW,
)
from llamatron.support.revised import notes_change

# Steps are counted from 1 in messages, as the editor shows them.
FIRST_STEP_NUMBER = 1
# A pattern's settings besides its steps and rows, each described once, in the order they're written to a file.
SETTINGS = described(
    Length(name=PatternSetting.STEP_SIZE, most=MAX_STEP_SIZE),
    Checked(name=PatternSetting.TIME_SIGNATURE, check=time_signature),
    Length(name=PatternSetting.ENTRY_SIZE, most=MAX_GATE),
    Flag(name=PatternSetting.DRUM, error=ERR_DRUM_NOT_TRUE_OR_FALSE),
    Choice(name=PatternSetting.DIRECTION, choices=DIRECTIONS, default=LEFT_OUT, error=ERR_BAD_DIRECTION),
)
# The settings a file's problem with is placed by the setting's name, like "pattern (tune), step_size: ...". The messages of the others name the setting themselves.
PLACED_BY_NAME = (PatternSetting.STEP_SIZE, PatternSetting.TIME_SIGNATURE, PatternSetting.ENTRY_SIZE)
# What a rest keeps when a note is cleared from a step: its time, the CC values it sends, and what
# it adds to the registers. Each row's one description says whether it is such a row (composition/row_descriptions.py).
REST_ROWS = rows_where(lambda row: row.is_kept_by_a_rest())
# The rows that mean something else in a drum pattern, so they're cleared when a pattern changes kind.
NOTE_ROWS = rows_where(lambda row: row.changes_with_drums())
# A register change of nothing, which is the same as none.
NO_CHANGE = 0
# No accidental, as a note name is written.
NO_ACCIDENTAL = ''
# The octave notes are built in before being moved to the step's, which keeps them inside the MIDI range.
REFERENCE_OCTAVE = 5
# A step's note, as the editor shows it: like F#3, with the octave in the song's octave labels.
NOTE_NAME = '{name}{octave}'


class Pattern(PatternNotes, LlamaData):
    """A number of steps, and for each row, like degree or velocity, a value for every step.

    A row the file leaves out is kept as None, which means every step is blank on that row. A
    blank degree is a rest, and other blanks mean that row's default. A drum pattern holds note
    letters in its degree row instead of scale degrees. What it knows about its notes as the bars
    a piano roll draws, each a note with its gate and ties, is in PatternNotes.
    """

    __slots__ = ('_steps', '_rows', '_settings')

    def __init__(self, *, steps, rows, step_size=None, time_signature=None, entry_size=None, drum=None, direction=None):
        self.note_change()
        self._steps = steps
        self._rows = _copied_rows(rows)
        self._settings = {
            PatternSetting.STEP_SIZE: step_size, PatternSetting.TIME_SIGNATURE: time_signature, PatternSetting.ENTRY_SIZE: entry_size,
            PatternSetting.DRUM: drum, PatternSetting.DIRECTION: direction,
        }

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(ERR_PATTERN_EXPECTED_SETTINGS)
            check_keys(data=data, allowed={PatternSetting.STEPS, *SETTINGS, *PATTERN_ROWS})
            steps = data.get(PatternSetting.STEPS)
            if not is_whole_number_from(value=steps, lowest=MIN_STEPS):
                raise InvalidValue(ERR_BAD_STEPS.format(lowest=MIN_STEPS, value=steps))
            for setting in settings_held(settings=SETTINGS, data=data):
                name = setting.get_name()
                with reading(ERR_WHERE_IN_ROW.format(where=where, row=name) if name in PLACED_BY_NAME else where):
                    setting.check_held(data)
            drum = data.get(PatternSetting.DRUM, False)
            for row in PATTERN_ROWS:
                _check_row(row=row, data=data, steps=steps, drum=drum, where=where)
            _check_ties(data=data, steps=steps)
            rows = {row: data.get(row) for row in PATTERN_ROWS}
            return cls(steps=steps, rows=rows, **{name: data.get(name) for name in SETTINGS})

    def to_data(self):
        """Return its settings and rows, leaving out rows with nothing in them, so that files stay short."""
        data = {PatternSetting.STEPS: self._steps}
        data.update(written_settings(self._settings))
        data.update({row: _saved_row(row=row, values=values) for row, values in self._rows.items() if _holds_something(row=row, values=values)})
        return data

    def copy(self):
        """Return a pattern just like this one, with lists of its own."""
        return Pattern(steps=self._steps, rows=self._rows, **self._settings)

    def get_steps(self):
        return self._steps

    def get_step_size(self):
        """Return how long each of its steps is, in whole notes, or None to use the song's step size."""
        step_size = self.get_written_step_size()
        return None if step_size is None else written_length(value=step_size, most=MAX_STEP_SIZE)

    def get_written_step_size(self):
        """Return its step size as the file writes it, like 1/8, or None to use the song's."""
        return self._settings[PatternSetting.STEP_SIZE]

    def get_time_signature(self):
        """Return the time signature it's drawn in, or None to use the song's."""
        text = self.get_written_time_signature()
        return None if text is None else time_signature(text)

    def get_written_time_signature(self):
        """Return its time signature as the file writes it, like 6/8, or None to use the song's."""
        return self._settings[PatternSetting.TIME_SIGNATURE]

    def get_entry_size(self):
        """Return how long a note placed on its piano roll lasts, in whole notes, or None to use the song's entry size."""
        entry_size = self.get_written_entry_size()
        return None if entry_size is None else written_length(value=entry_size, most=MAX_GATE)

    def get_written_entry_size(self):
        """Return its entry size as the file writes it, like 1/8, or None to use the song's."""
        return self._settings[PatternSetting.ENTRY_SIZE]

    def is_drum(self):
        return bool(self._settings[PatternSetting.DRUM])

    def get_direction(self):
        """Return the order its steps play in, forward unless the pattern sets another."""
        return self._settings[PatternSetting.DIRECTION] or Direction.FORWARD

    def get_row(self, row):
        """Return a copy of one row's values, one per step, or None if the row is blank throughout."""
        values = self._rows[row]
        return None if values is None else list(values)

    def get_value(self, *, row, step):
        """Return one step's value on a row, or None if it's blank there."""
        values = self._rows[row]
        return values[step] if values else None

    def get_every_step_values(self, *, rows):
        """Return every step's values on some rows, a dictionary by row for each step in order, with None where a step is blank.

        Playing reads every row of every step, so the whole pattern is gathered in one go: each
        step starts from one dictionary of blanks and takes its values only from the rows that
        hold any, since asking all thirty rows about every step was an eighth of a render.
        """
        blank = dict.fromkeys(rows)
        held = [(row, self._rows[row]) for row in rows if self._rows[row]]
        every = []
        for step in range(self._steps):
            values = dict(blank)
            for row, column in held:
                values[row] = column[step]
            every.append(values)
        return every

    def adds_to_registers(self):
        """Return whether any step adds to a register, which is a non-zero value on a register change row."""
        return any(self._adds_on(row) for row in REGISTER_ADD_ROWS.values())

    def adds_past(self, *, row, most):
        """Return whether any step of a register's += row adds or takes away more than most."""
        return any(value and abs(value) > most for value in self._rows[row] or [])

    @notes_change
    def hold_adds(self, *, row, most):
        """Bring every step of a register's += row within most either way, as lowering the register's Allowed Inc Max does."""
        self._rows[row] = [held_add(value=value, most=most) for value in self._rows[row]]

    def sets_registers(self):
        """Return whether any step sets a register to a value, which is a value on a register's = row, 0 included."""
        return any(value is not None for row in REGISTER_SET_ROWS.values() for value in self._rows[row] or [])

    def changes_registers(self):
        """Return whether any step sets a register or adds to one, so that playing the pattern changes the registers' values."""
        return self.adds_to_registers() or self.sets_registers()

    def uses_registers(self):
        """Return whether any step reads a register: a row of +Note or +Vel switched on there, or a condition."""
        return any(self._adds_on(row) for rows in (REGISTER_NOTE_ROWS, REGISTER_VELOCITY_ROWS, CONDITION_ROWS) for row in rows.values())

    def sends_controls(self):
        """Return whether any step holds a CC value, which a value of 0 is too."""
        return any(value is not None for row in CC_ROWS for value in self._rows[row] or [])

    def _adds_on(self, row):
        """Return whether any step has a non-zero value on a row."""
        return any(self._rows[row] or [])

    def has_sound(self, step):
        """Return whether a step plays something: it has a degree, or it's marked to grab its note from another track, which a file can hold without a degree."""
        return self.get_value(row=Row.DEGREE, step=step) is not None or bool(self.get_value(row=Row.GRAB, step=step))

    def get_note_steps(self):
        """Return the steps that play something, which are the ones with a degree or a grab."""
        return [step for step in range(self._steps) if self.has_sound(step)]

    def get_first_octave(self):
        """Return the octave of the first step that sets one, or None if no step does."""
        octaves = self._rows[Row.OCTAVE] or []
        return next((octave for octave in octaves if octave is not None), None)

    def has_notes(self):
        return any(self.has_sound(step) for step in range(self._steps))

    def has_grab_steps(self):
        """Return whether any step is marked to grab its note from another track."""
        return any(self._rows[Row.GRAB] or [])

    def holds_anything(self, step):
        """Return whether a step plays a note, holds one with a tie, sends a CC value or adds to a register."""
        self._check_step(step)
        if self.has_sound(step) or self.get_value(row=Row.TIE, step=step):
            return True
        if any(self.get_value(row=row, step=step) is not None for row in CC_ROWS):
            return True
        return any(self.get_value(row=row, step=step) not in (None, NO_CHANGE) for row in REGISTER_ADD_ROWS.values())

    def steps_with_anything_from(self, start):
        """Return how many steps from a position onward hold anything, which shortening the pattern would lose."""
        return sum(1 for step in range(start, self._steps) if self.holds_anything(step))

    def get_note_name(self, *, step, scale, default_octave, default_drum_octave, octave_label_offset):
        """Return the name of a step's note in a scale, like F#3, or None if the step has none.

        scale is the NamedScale the pattern plays in, or None, which gives None for a scale
        degree. A drum step names its note letter directly, and needs no scale. The octave is
        shown octave_label_offset below the file's numbering, which is 2 for Live's labels.
        """
        degree = self.get_value(row=Row.DEGREE, step=step)
        if degree is None:
            return None
        accidental = self.get_value(row=Row.ACCIDENTAL, step=step) or NO_ACCIDENTAL
        octave = self.get_value(row=Row.OCTAVE, step=step)
        if self.is_drum():
            octave = default_drum_octave if octave is None else octave
            return NOTE_NAME.format(name=degree + accidental, octave=octave - octave_label_offset)
        if scale is None:
            return None
        octave = default_octave if octave is None else octave
        half_steps = scale.get_half_steps()
        octaves_up, place = divmod(degree - MIN_DEGREE, len(half_steps))
        moved = half_steps[place] + octaves_up * HALF_STEPS_PER_OCTAVE + ACCIDENTALS.get(accidental, 0)
        note = Note(name=scale.get_root(), octave_number=REFERENCE_OCTAVE).half_step(moved)
        return NOTE_NAME.format(name=note.get_name(), octave=note.get_octave_number() - REFERENCE_OCTAVE + octave - octave_label_offset)

    @classmethod
    def with_octaves_moved(cls, *, data, offset):
        """Return a copy of a pattern's file data with every whole number in its octave row moved by an offset.

        This is how a file written in Live's numbering is read. Anything that isn't a list of
        numbers is left for the usual checks to refuse.
        """
        if not isinstance(data, dict) or not isinstance(data.get(Row.OCTAVE), list):
            return data
        moved = dict(data)
        moved[Row.OCTAVE] = [octave + offset if is_whole_number(octave) else octave for octave in data[Row.OCTAVE]]
        return moved

    # Changing the pattern. Every change checks its value the way reading a file does, and raises
    # InvalidValue if it's wrong, leaving the pattern as it was.

    @notes_change
    def set_value(self, *, row, step, value):
        """Set one step's value on a row, where None makes the step blank there."""
        description = row_described(row)
        self._check_step(step)
        if value is None:
            value = description.blank()
        else:
            description.check(value, drum=self.is_drum())
            value = description.kept(value)
        if self._rows[row] is None:
            self._rows[row] = _blank_row(row=row, steps=self._steps)
        self._rows[row][step] = value

    @notes_change
    def clear_sound(self, step):
        """Empty a step of its note, keeping only what a rest can hold: CC values, slides and every register row.

        The ties on the steps right after it go too, since they held this note and would be left
        hanging onto an earlier one, as the user decided on 2026-11-08. A register's +Note and
        +Vel rows stay with its += row, as the user decided: erasing takes the note and the ties
        that drew it, and nothing a rest can hold.
        """
        self._check_step(step)
        for row in PATTERN_ROWS:
            if row not in REST_ROWS and self._rows[row] is not None:
                self._rows[row][step] = blank_value(row)
        ties = self._rows[Row.TIE]
        later = step + 1
        while ties is not None and later < self._steps and ties[later]:
            ties[later] = blank_value(Row.TIE)
            later += 1

    @notes_change
    def set_steps(self, steps):
        """Change how many steps it has, cutting steps off the end or adding empty ones."""
        if not is_whole_number_from(value=steps, lowest=MIN_STEPS):
            raise InvalidValue(ERR_BAD_STEPS.format(lowest=MIN_STEPS, value=steps))
        for row, values in self._rows.items():
            if values is not None:
                self._rows[row] = (values + _blank_row(row=row, steps=steps))[:steps]
        self._steps = steps

    @notes_change
    def insert_step(self, step):
        """Put an empty step before a step, or at the end if step is the number of steps."""
        if not is_whole_number_from(value=step, lowest=0, highest=self._steps):
            raise InvalidValue(ERR_PATTERN_NO_SUCH_STEP.format(step=step, steps=self._steps))
        for row, values in self._rows.items():
            if values is not None:
                values.insert(step, blank_value(row))
        self._steps += 1

    @notes_change
    def remove_step(self, step):
        """Take a step out, which a pattern with only one step can't do."""
        self._check_step(step)
        if self._steps <= MIN_STEPS:
            raise InvalidValue(ERR_BAD_STEPS.format(lowest=MIN_STEPS, value=self._steps - 1))
        for values in self._rows.values():
            if values is not None:
                values.pop(step)
        self._steps -= 1

    @notes_change
    def set_step_size(self, step_size):
        """Give it a step size of its own, written like 1/8, or None to use the song's."""
        if step_size is not None:
            SETTINGS[PatternSetting.STEP_SIZE].check(step_size)
        self._settings[PatternSetting.STEP_SIZE] = step_size

    @notes_change
    def set_time_signature(self, text):
        """Give it a time signature of its own, written like 6/8, or None to use the song's."""
        if text is not None:
            SETTINGS[PatternSetting.TIME_SIGNATURE].check(text)
        self._settings[PatternSetting.TIME_SIGNATURE] = text

    @notes_change
    def set_entry_size(self, entry_size):
        """Give it an entry size of its own, written like 1/8, or None to use the song's."""
        if entry_size is not None:
            SETTINGS[PatternSetting.ENTRY_SIZE].check(entry_size)
        self._settings[PatternSetting.ENTRY_SIZE] = entry_size

    @notes_change
    def set_drum(self, drum):
        """Make it a drum pattern or not, which clears the notes, since they mean something else in each."""
        SETTINGS[PatternSetting.DRUM].check(drum)
        for row in NOTE_ROWS:
            self._rows[row] = None
        self._settings[PatternSetting.DRUM] = True if drum else None

    @notes_change
    def set_direction(self, direction):
        """Set the order its steps play in, with forward left out of the file as the default."""
        SETTINGS[PatternSetting.DIRECTION].check(direction)
        self._settings[PatternSetting.DIRECTION] = None if direction == Direction.FORWARD else direction

    @notes_change
    def rearrange(self, order):
        """Put the steps in a new order, given as the old place of each new step, with every value of a step moving together."""
        if sorted(order) != list(range(self._steps)):
            raise InvalidValue(ERR_PATTERN_NOT_AN_ORDER.format(order=order))
        for row, values in self._rows.items():
            if values is not None:
                self._rows[row] = [values[step] for step in order]

    def reverse_after(self, step):
        """Reverse every step after a step, leaving it and the steps before it where they are."""
        self._check_step(step)
        steps = list(range(self._steps))
        self.rearrange(steps[:step + 1] + steps[step + 1:][::-1])

    def reverse_before(self, step):
        """Reverse every step before a step, leaving it and the steps after it where they are."""
        self._check_step(step)
        steps = list(range(self._steps))
        self.rearrange(steps[:step][::-1] + steps[step:])

    def reverse(self):
        """Reverse the whole pattern, so that its last step plays first."""
        self.rearrange(list(range(self._steps))[::-1])

    def pivot_around(self, step):
        """Swap what's before a step with what's after it, and return where the step ends up."""
        self._check_step(step)
        steps = list(range(self._steps))
        before = steps[:step]
        after = steps[step + 1:]
        self.rearrange([*after, step, *before])
        return len(after)

    def shuffle(self):
        """Put the steps in a random order, from the program's own random stream: this edits the pattern, so no seed applies."""
        order = list(range(self._steps))
        random_source(None).shuffle(order)
        self.rearrange(order)

    def _check_step(self, step):
        if not is_whole_number_from(value=step, lowest=0, highest=self._steps - 1):
            raise InvalidValue(ERR_PATTERN_NO_SUCH_STEP.format(step=step, steps=self._steps))


def _copied_rows(rows):
    """Return a copy of every row's list of values as the pattern holds them, with None for a row that isn't given, so the pattern owns its lists."""
    return {row: (None if rows.get(row) is None else ROW_DESCRIPTIONS[row].read(rows[row])) for row in PATTERN_ROWS}


def blank_value(row):
    """Return what a step holds on a row when nothing is set: off on an on or off row, and None otherwise."""
    return ROW_DESCRIPTIONS[row].blank()


def _blank_row(*, row, steps):
    return [blank_value(row)] * steps


def _holds_something(*, row, values):
    """Return whether a row has any step that isn't the row's blank, which is what makes it worth writing to a file."""
    if values is None:
        return False
    blank = ROW_DESCRIPTIONS[row].blank()
    return any(value is not None and value != blank for value in values)


def _saved_row(*, row, values):
    """Return a row as a file writes it: a copy, with an on or off row as true and false."""
    return ROW_DESCRIPTIONS[row].written(values)


def _check_row(*, row, data, steps, drum, where):
    """Refuse a row of a file's data that isn't a list with a value for every step, or that holds a value it can't.

    A value outside its row's limits is refused carrying the correction that brings every such
    value of the row within them, so that a row is corrected once however many steps need it.
    """
    values = data.get(row)
    if values is None:
        return
    if not isinstance(values, list) or len(values) != steps:
        raise InvalidValue(ERR_ROW_WRONG_LENGTH.format(row=row, steps=steps, value=values))
    description = ROW_DESCRIPTIONS[row]
    never_blank = description.is_on_or_off()
    for value in values:
        if value is None:
            if never_blank:
                raise InvalidValue(ERR_TOGGLE_IS_NULL.format(row=row))
        else:
            try:
                description.check(value, drum=drum)
            except InvalidValue as problem:
                with reading(ERR_WHERE_IN_ROW.format(where=where, row=row)):
                    raise problem.with_correction(_row_correction(data=data, row=row, drum=drum)) from None


def nearest_step_value(*, row, value, drum):
    """Return the allowed value nearest a step's wrong value on a row, or NO_NEAREST_VALUE when the row has no limits or the value isn't a number at all. A blank step stays blank."""
    return None if value is None else ROW_DESCRIPTIONS[row].nearest(value, drum=drum)


def held_add(*, value, most):
    """Return a step's add on a += row held within most either way, or a blank as it is."""
    if not value or abs(value) <= most:
        return value
    return most if value > 0 else -most


def _row_correction(*, data, row, drum):
    """Return the correction that brings every step of a row within the row's limits, or None when a value on the row has no allowed value near it."""
    found = data[row]
    used = [nearest_step_value(row=row, value=value, drum=drum) for value in found]
    if any(value is NO_NEAREST_VALUE for value in used):
        return None
    return Correction(holder=data, key=row, name=row, found=found, used=used)


def _check_ties(*, data, steps):
    """Refuse a tie on a step that has a note or grabs one, since a tied step plays nothing of its own."""
    ties = data.get(Row.TIE)
    degrees = data.get(Row.DEGREE) or [None] * steps
    grabs = data.get(Row.GRAB) or [False] * steps
    if not ties:
        return
    for step in range(steps):
        if ties[step] and (degrees[step] is not None or grabs[step]):
            raise InvalidValue(ERR_TIE_ON_A_NOTE.format(step=step + FIRST_STEP_NUMBER))
