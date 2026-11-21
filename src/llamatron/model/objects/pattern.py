# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A pattern: a row of steps, with one list of values for each row of the pattern editor.

Everything that reads or changes a pattern's steps is here: reading and saving it, checking its
values, editing single values, resizing and rearranging it, and working out what a step plays.
"""

from math import floor

from llamatron.caching.revised import notes_change
from llamatron.math.random_source import random_source
from llamatron.model.file import corrections
from llamatron.model.file.checks import is_whole_number_from, pass_over_unknown, reading, time_signature, written_length
from llamatron.model.file.corrections import Correction
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.conditions import check_statement, draws_read, statement_of
from llamatron.model.objects.llama_data import HoldsSettings, written_settings
from llamatron.model.objects.pattern_munges import PatternMunges
from llamatron.model.objects.pattern_notes import PatternNotes
from llamatron.model.schema import file_format, limits, row_descriptions
from llamatron.model.schema.file_format import Direction, PatternSetting, Row, StepStatement
from llamatron.model.schema.row_descriptions import row_described, rows_where
from llamatron.model.schema.setting import Checked, Choice, described, Flag, Length, settings_held, Text, WholeNumber
from llamatron.model.values import midi
from llamatron.model.values.note import Note
from llamatron.user_strings import errors

# Steps are counted from 1 in messages, as the editor shows them.
FIRST_STEP_NUMBER = 1
# The first step, which cannot start the pattern over, since that would take no time, and where a statement's register stands among its rows.
FIRST_STEP = 0
# What is added before rounding down, so that a value halfway between two whole numbers goes up.
HALF = 0.5
REGISTER_PART = 0
# A pattern's settings besides its steps and rows, each described once, in the order they're written to a file.
SETTINGS = described(
    Length(name=PatternSetting.STEP_SIZE, most=limits.MAX_STEP_SIZE),
    Checked(name=PatternSetting.TIME_SIGNATURE, check=time_signature),
    Length(name=PatternSetting.ENTRY_SIZE, most=limits.MAX_GATE),
    Flag(name=PatternSetting.DRUM, error=errors.ERR_DRUM_NOT_TRUE_OR_FALSE),
    Choice(name=PatternSetting.DIRECTION, choices=file_format.DIRECTIONS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_DIRECTION),
    Text(name=PatternSetting.GROUP, error=errors.ERR_NOT_TEXT),
    WholeNumber(name=PatternSetting.SCALE_LENGTH, lowest=limits.MIN_SCALE_LENGTH, highest=limits.MAX_SCALE_LENGTH, error=errors.ERR_BAD_SCALE_LENGTH),
)
# The settings a file's problem with is placed by the setting's name, like "pattern (tune), step_size: ...". The messages of the others name the setting themselves.
PLACED_BY_NAME = (PatternSetting.STEP_SIZE, PatternSetting.TIME_SIGNATURE, PatternSetting.ENTRY_SIZE)
# What a rest keeps when a note is cleared from a step: its time, the CC values it sends, and what
# it adds to the registers. Each row's one description says whether it is such a row (model/schema/row_descriptions.py).
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


class Pattern(PatternNotes, PatternMunges, HoldsSettings):
    """A number of steps, and for each row, like degree or velocity, a value for every step.

    A row the file leaves out is kept as None, which means every step is blank on that row. A
    blank degree is a rest, and other blanks mean that row's default. A drum pattern holds note
    letters in its degree row instead of scale degrees. What it knows about its notes as the bars
    a piano roll draws, each a note with its gate and ties, is in PatternNotes, and the munges of its notes are in PatternMunges.
    """

    __slots__ = ('_steps', '_rows')

    SETTINGS = SETTINGS

    def __init__(self, *, steps, rows, step_size=None, time_signature=None, entry_size=None, drum=None, direction=None, group=None, scale_length=None):
        self.note_change()
        self._steps = steps
        self._rows = _copied_rows(rows)
        self._settings = {
            PatternSetting.STEP_SIZE: step_size, PatternSetting.TIME_SIGNATURE: time_signature, PatternSetting.ENTRY_SIZE: entry_size,
            PatternSetting.DRUM: drum, PatternSetting.DIRECTION: direction, PatternSetting.GROUP: group, PatternSetting.SCALE_LENGTH: scale_length,
        }

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_PATTERN_EXPECTED_SETTINGS)
            pass_over_unknown(data=data, allowed={PatternSetting.STEPS, *SETTINGS, *file_format.PATTERN_ROWS})
            steps = data.get(PatternSetting.STEPS)
            if not is_whole_number_from(value=steps, lowest=limits.MIN_STEPS):
                raise InvalidValue(errors.ERR_BAD_STEPS.format(lowest=limits.MIN_STEPS, value=steps))
            for setting in settings_held(settings=SETTINGS, data=data):
                name = setting.get_name()
                with reading(errors.ERR_WHERE_IN_ROW.format(where=where, row=name) if name in PLACED_BY_NAME else where):
                    setting.check_held(data)
            drum = data.get(PatternSetting.DRUM, False)
            for row in file_format.PATTERN_ROWS:
                _check_row(row=row, data=data, steps=steps, drum=drum, where=where)
            _check_ties(data=data, steps=steps)
            rows = {row: data.get(row) for row in file_format.PATTERN_ROWS}
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
        return None if step_size is None else written_length(value=step_size, most=limits.MAX_STEP_SIZE)

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
        return None if entry_size is None else written_length(value=entry_size, most=limits.MAX_GATE)

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
        return any(self._adds_on(row) for row in file_format.REGISTER_ADD_ROWS.values())

    def adds_anything(self, row):
        """Return whether any step of a register's += row adds or takes away anything at all: most patterns add nothing, and
        whoever checks a limit asks this first, since finding the limit means searching every clip of every song."""
        return any(self._rows[row] or [])

    def adds_past(self, *, row, most):
        """Return whether any step of a register's += row adds or takes away more than most."""
        return any(value and abs(value) > most for value in self._rows[row] or [])

    @notes_change
    def hold_adds(self, *, row, most):
        """Bring every step of a register's += row within most either way, as lowering the register's Allowed Inc Max does."""
        self._rows[row] = [held_add(value=value, most=most) for value in self._rows[row]]

    def sets_registers(self):
        """Return whether any step sets a register to a value, which is a value on a register's = row, 0 included."""
        return any(value is not None for row in file_format.REGISTER_SET_ROWS.values() for value in self._rows[row] or [])

    def changes_registers(self):
        """Return whether any step sets a register or adds to one, so that playing the pattern changes the registers' values."""
        return self.adds_to_registers() or self.sets_registers()

    def uses_registers(self):
        """Return whether any step reads a register: a row of +Note or +Vel switched on there, or a statement about the registers."""
        if any(self._adds_on(row) for rows in (file_format.REGISTER_NOTE_ROWS, file_format.REGISTER_VELOCITY_ROWS) for row in rows.values()):
            return True
        return any(self.has_statements(kind) for kind in file_format.STATEMENT_ROWS)

    def uses_draws(self):
        """Return whether any step uses a draw or resets one: a row of the Use Draws section switched on there."""
        return any(self._adds_on(row) for rows in (file_format.DRAW_NOTE_ROWS, file_format.DRAW_VELOCITY_ROWS, file_format.DRAW_RESET_ROWS) for row in rows.values())

    def reads_draws(self):
        """Return whether any step's statement reads a draw, which a draw that redraws in conditions draws from."""
        return any(draws_read(statement) for kind in file_format.STATEMENT_ROWS for statement in (self.get_statements(kind) or []) if statement is not None)

    def has_statements(self, kind):
        """Return whether any step holds a statement of a kind about the registers: one that stops the clip, starts the pattern over or mutes the step."""
        return any(self._rows[file_format.STATEMENT_ROWS[kind][REGISTER_PART]] or [])

    def cuts_passes_short(self):
        """Return whether any step can stop the clip or start the pattern over, so that how long a pass lasts is known only as it plays."""
        return any(self.has_statements(kind) for kind in file_format.STATEMENTS_CUTTING_A_PASS)

    def get_statement(self, *, kind, step):
        """Return the statement of a kind a step holds, as a file writes one on a clip, or None when the step holds none or holds parts that make no statement."""
        return statement_of([self.get_value(row=row, step=step) for row in file_format.STATEMENT_ROWS[kind]])

    def get_statements(self, kind):
        """Return every step's statement of a kind, None where a step holds none, or None when no step holds one."""
        if not self.has_statements(kind):
            return None
        return [self.get_statement(kind=kind, step=step) for step in range(self._steps)]

    def sends_keyswitches(self):
        """Return whether any step names a keyswitch slot."""
        return any(self._rows[Row.KEYSWITCH] or [])

    def sends_controls(self):
        """Return whether any step holds a CC value, which a value of 0 is too."""
        return any(value is not None for row in file_format.CC_ROWS for value in self._rows[row] or [])

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
        if any(self.get_value(row=row, step=step) is not None for row in file_format.CC_ROWS):
            return True
        return any(self.get_value(row=row, step=step) not in (None, NO_CHANGE) for row in file_format.REGISTER_ADD_ROWS.values())

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
        octaves_up, place = divmod(degree - limits.MIN_DEGREE, len(half_steps))
        moved = half_steps[place] + octaves_up * midi.HALF_STEPS_PER_OCTAVE + file_format.ACCIDENTALS.get(accidental, 0)
        note = Note(name=scale.get_root(), octave_number=REFERENCE_OCTAVE).half_step(moved)
        return NOTE_NAME.format(name=note.get_name(), octave=note.get_octave_number() - REFERENCE_OCTAVE + octave - octave_label_offset)

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
    def set_statement(self, *, kind, step, statement):
        """Give a step a statement of a kind about the registers, written across the kind's five rows, or None to take the step's away."""
        self._check_step(step)
        if statement is not None:
            check_statement(name=kind, statement=statement)
            if kind == StepStatement.RESTART and step == FIRST_STEP:
                raise InvalidValue(errors.ERR_RESTART_ON_FIRST_STEP)
        for row, part in zip(file_format.STATEMENT_ROWS[kind], file_format.STATEMENT_PARTS):
            value = None if statement is None else statement.get(part)
            if value is None and self._rows[row] is None:
                continue
            if self._rows[row] is None:
                self._rows[row] = _blank_row(row=row, steps=self._steps)
            self._rows[row][step] = value

    @notes_change
    def clear_sound(self, step):
        """Empty a step of its note, keeping only what a rest can hold: CC values, slides and every register row.

        The ties on the steps right after it go too, since they held this note and would be left
        hanging onto an earlier one. A register's +Note and
        +Vel rows stay with its += row: erasing takes the note and the ties
        that drew it, and nothing a rest can hold.
        """
        self._check_step(step)
        for row in file_format.PATTERN_ROWS:
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
        if not is_whole_number_from(value=steps, lowest=limits.MIN_STEPS):
            raise InvalidValue(errors.ERR_BAD_STEPS.format(lowest=limits.MIN_STEPS, value=steps))
        for row, values in self._rows.items():
            if values is not None:
                self._rows[row] = (values + _blank_row(row=row, steps=steps))[:steps]
        self._steps = steps

    @notes_change
    def insert_step(self, step):
        """Put an empty step before a step, or at the end if step is the number of steps."""
        if not is_whole_number_from(value=step, lowest=0, highest=self._steps):
            raise InvalidValue(errors.ERR_PATTERN_NO_SUCH_STEP.format(step=step, steps=self._steps))
        for row, values in self._rows.items():
            if values is not None:
                values.insert(step, blank_value(row))
        self._steps += 1

    @notes_change
    def remove_step(self, step):
        """Take a step out, which a pattern with only one step can't do."""
        self._check_step(step)
        if self._steps <= limits.MIN_STEPS:
            raise InvalidValue(errors.ERR_BAD_STEPS.format(lowest=limits.MIN_STEPS, value=self._steps - 1))
        for values in self._rows.values():
            if values is not None:
                values.pop(step)
        self._steps -= 1

    def set_step_size(self, step_size):
        """Give it a step size of its own, written like 1/8, or None to use the song's."""
        self.set_written(name=PatternSetting.STEP_SIZE, value=step_size)

    def set_time_signature(self, text):
        """Give it a time signature of its own, written like 6/8, or None to use the song's."""
        self.set_written(name=PatternSetting.TIME_SIGNATURE, value=text)

    def set_entry_size(self, entry_size):
        """Give it an entry size of its own, written like 1/8, or None to use the song's."""
        self.set_written(name=PatternSetting.ENTRY_SIZE, value=entry_size)

    @notes_change
    def set_drum(self, drum):
        """Make it a drum pattern or not, which clears the notes, since they mean something else in each."""
        SETTINGS[PatternSetting.DRUM].check(drum)
        for row in NOTE_ROWS:
            self._rows[row] = None
        self._settings[PatternSetting.DRUM] = True if drum else None
        if drum:
            # A drum's notes are of no scale.
            self._settings[PatternSetting.SCALE_LENGTH] = None

    def get_scale_length(self):
        """Return how many notes the scale has that it was written for, or None for a pattern written for any scale, as a drum pattern and an older file's are."""
        return self._settings[PatternSetting.SCALE_LENGTH]

    def set_scale_length(self, scale_length):
        """Say how many notes the scale has that it was written for, or None for any; no note changes."""
        self.set_written(name=PatternSetting.SCALE_LENGTH, value=scale_length)

    def suits_scale_of(self, size):
        """Return whether it was written for a scale of this many notes, as a pattern written for any scale is."""
        return self.get_scale_length() in (None, size)

    def get_group(self):
        """Return the group the Patterns page lists it under, or None for a pattern in no group, as an older file's is."""
        return self._settings[PatternSetting.GROUP]

    @notes_change
    def set_group(self, group):
        """Put it in a group, by the group's name, or in none."""
        if group is not None:
            SETTINGS[PatternSetting.GROUP].check(group)
        self._settings[PatternSetting.GROUP] = group or None

    @notes_change
    def set_direction(self, direction):
        """Set the order its steps play in, with forward left out of the file as the default."""
        SETTINGS[PatternSetting.DIRECTION].check(direction)
        self._settings[PatternSetting.DIRECTION] = None if direction == Direction.FORWARD else direction

    @notes_change
    def rearrange(self, order):
        """Put the steps in a new order, given as the old place of each new step, with every value of a step moving together."""
        if sorted(order) != list(range(self._steps)):
            raise InvalidValue(errors.ERR_PATTERN_NOT_AN_ORDER.format(order=order))
        self.take_steps(order)

    @notes_change
    def take_steps(self, order):
        """Make the pattern of its own steps in a new order, given as the old place of each new step, where a step may come more than once: the pattern is then as long as the order."""
        if not order or len(order) > limits.MAX_STEPS or any(not is_whole_number_from(value=step, lowest=0, highest=self._steps - 1) for step in order):
            raise InvalidValue(errors.ERR_PATTERN_NOT_AN_ORDER.format(order=order))
        for row, values in self._rows.items():
            if values is not None:
                self._rows[row] = [own_step_value(values[step]) for step in order]
        self._steps = len(order)
        # The first step can never start the pattern over, since the pattern would never get past it.
        for row in file_format.STATEMENT_ROWS[StepStatement.RESTART]:
            if self._rows[row] is not None:
                self._rows[row][FIRST_STEP] = blank_value(row)

    def repeat_at_end(self, *, first, last):
        """Add a copy of the steps from first through last after the last step."""
        self._check_step(first)
        self._check_step(last)
        self.take_steps([*range(self._steps), *range(first, last + 1)])

    def repeat_at_start(self, *, first, last):
        """Put a copy of the steps from first through last before the first step."""
        self._check_step(first)
        self._check_step(last)
        self.take_steps([*range(first, last + 1), *range(self._steps)])

    def roll(self, steps):
        """Turn the pattern so many steps to the left, or to the right when negative: a step pushed off one end comes in at the other."""
        self.take_steps([(step + steps) % self._steps for step in range(self._steps)])

    def roll_through(self, step):
        """Turn a step and every step before it one step to the left among themselves: the first step comes in at the step's place."""
        self._check_step(step)
        order = list(range(self._steps))
        self.take_steps([*order[1:step + 1], FIRST_STEP, *order[step + 1:]])

    def roll_from(self, step):
        """Turn a step and every step after it one step to the right among themselves: the last step comes in at the step's place."""
        self._check_step(step)
        order = list(range(self._steps))
        self.take_steps([*order[:step], order[-1], *order[step:-1]])

    def shuffle_from(self, step):
        """Put a step and every step after it in a random order among themselves."""
        self._check_step(step)
        self._shuffle_part(first=step, last=self._steps - 1)

    def shuffle_through(self, step):
        """Put a step and every step before it in a random order among themselves."""
        self._check_step(step)
        self._shuffle_part(first=FIRST_STEP, last=step)

    def _shuffle_part(self, *, first, last):
        order = list(range(self._steps))
        part = order[first:last + 1]
        random_source(None).shuffle(part)
        self.rearrange([*order[:first], *part, *order[last + 1:]])

    @notes_change
    def clear_rows(self, rows):
        """Blank every step of some rows."""
        for row in rows:
            if self._rows[row] is not None:
                self._rows[row] = _blank_row(row=row, steps=self._steps)

    def clear_all_but_pitch(self):
        """Blank everything a step holds but which notes it plays: its degree, octave, sharp or flat and chord stay."""
        self.clear_rows([row for row in file_format.PATTERN_ROWS if row not in file_format.PITCH_ROWS])

    def clear_chords(self):
        """Blank every step's chord, with its tensions, borrowed scale and inversion, leaving the note each chord was built on."""
        self.clear_rows(file_format.CHORD_ROWS)

    def clear_register_changes(self):
        """Blank the rows that set a register and that add to one."""
        self.clear_rows([*file_format.REGISTER_SET_ROWS.values(), *file_format.REGISTER_ADD_ROWS.values()])

    def clear_statements(self):
        """Blank every step's statements about the registers: what stops the clip, starts the pattern over and mutes the step."""
        self.clear_rows(list(file_format.STATEMENT_OF_ROW))

    def mirror(self):
        """Add its steps again after the last, backwards, so that it plays forward and then back and is twice as long."""
        steps = list(range(self._steps))
        self.take_steps([*steps, *steps[::-1]])

    @notes_change
    def interleave(self, other):
        """Put a step of another pattern after each of its own, so that it is twice as long: the other's steps are read round and round, or as far as needed, and the other is not changed."""
        if self._steps * 2 > limits.MAX_STEPS or other.is_drum() != self.is_drum():
            raise InvalidValue(errors.ERR_PATTERN_CANNOT_INTERLEAVE)
        for row in file_format.PATTERN_ROWS:
            own = self._rows[row]
            others = other._row_values(row)
            if own is None and others is None:
                continue
            own = own or _blank_row(row=row, steps=self._steps)
            others = others or _blank_row(row=row, steps=other.get_steps())
            woven = []
            for step in range(self._steps):
                woven += [own[step], own_step_value(others[step % len(others)])]
            self._rows[row] = woven
        self._steps *= 2

    @notes_change
    def splice(self, *, other, at=None):
        """Add another pattern's steps after its own last step, or before the step at a place, 0 for before its first; the other is not changed."""
        at = self._steps if at is None else at
        if not is_whole_number_from(value=at, lowest=0, highest=self._steps):
            raise InvalidValue(errors.ERR_PATTERN_NO_SUCH_STEP.format(step=at, steps=self._steps))
        if self._steps + other.get_steps() > limits.MAX_STEPS or other.is_drum() != self.is_drum():
            raise InvalidValue(errors.ERR_PATTERN_CANNOT_INTERLEAVE)
        for row in file_format.PATTERN_ROWS:
            own = self._rows[row]
            others = other._row_values(row)
            if own is None and others is None:
                continue
            own = own or _blank_row(row=row, steps=self._steps)
            others = others or _blank_row(row=row, steps=other.get_steps())
            taken = [own_step_value(value) for value in others]
            self._rows[row] = [*own[:at], *taken, *own[at:]]
        self._steps += other.get_steps()

    def _row_values(self, row):
        """Return a row's values as held, or None for a row no step uses, for another pattern that takes copies of them."""
        return self._rows[row]

    @notes_change
    def smooth_rows(self, *, rows, notes_only=False):
        """Fill the blank steps between two values of a row from a straight line between the two, on each of some rows; with notes_only, a step that plays nothing is left blank, though it still counts along the line."""
        for row in rows:
            values = self._rows[row]
            if values is None:
                continue
            given = [step for step, value in enumerate(values) if value is not None]
            for start, end in zip(given, given[1:]):
                for step in range(start + 1, end):
                    if notes_only and not self.has_sound(step):
                        continue
                    values[step] = floor(values[start] + (values[end] - values[start]) * (step - start) / (end - start) + HALF)

    def smooth_ccs(self):
        """Fill the blank steps between two values of each CC row."""
        self.smooth_rows(rows=file_format.CC_ROWS)

    def smooth_velocity(self):
        """Fill the blank velocities between two typed ones, on the steps that play a note."""
        self.smooth_rows(rows=[Row.VELOCITY], notes_only=True)

    def smooth_register_sets(self, register):
        """Fill the blank steps between two values of the row that sets a register."""
        self.smooth_rows(rows=[file_format.REGISTER_SET_ROWS[register]])

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
            raise InvalidValue(errors.ERR_PATTERN_NO_SUCH_STEP.format(step=step, steps=self._steps))


def _copied_rows(rows):
    """Return a copy of every row's list of values as the pattern holds them, with None for a row that isn't given, so the pattern owns its lists."""
    return {row: (None if rows.get(row) is None else row_descriptions.ROW_DESCRIPTIONS[row].read(rows[row])) for row in file_format.PATTERN_ROWS}


def own_step_value(value):
    """Return a step's value as a step of its own may hold it: a list, such as a step's keyswitch slots, is copied, so that two steps never share one."""
    return list(value) if isinstance(value, list) else value


def blank_value(row):
    """Return what a step holds on a row when nothing is set: off on an on or off row, and None otherwise."""
    return row_descriptions.ROW_DESCRIPTIONS[row].blank()


def _blank_row(*, row, steps):
    return [blank_value(row)] * steps


def _holds_something(*, row, values):
    """Return whether a row has any step that isn't the row's blank, which is what makes it worth writing to a file."""
    if values is None:
        return False
    blank = row_descriptions.ROW_DESCRIPTIONS[row].blank()
    return any(value is not None and value != blank for value in values)


def _saved_row(*, row, values):
    """Return a row as a file writes it: a copy, with an on or off row as true and false."""
    return row_descriptions.ROW_DESCRIPTIONS[row].written(values)


def _check_row(*, row, data, steps, drum, where):
    """Refuse a row of a file's data that isn't a list with a value for every step, or that holds a value it can't.

    A value outside its row's limits is refused carrying the correction that brings every such
    value of the row within them, so that a row is corrected once however many steps need it.
    """
    values = data.get(row)
    if values is None:
        return
    if not isinstance(values, list) or len(values) != steps:
        raise InvalidValue(errors.ERR_ROW_WRONG_LENGTH.format(row=row, steps=steps, value=values))
    description = row_descriptions.ROW_DESCRIPTIONS[row]
    never_blank = description.is_on_or_off()
    for value in values:
        if value is None:
            if never_blank:
                raise InvalidValue(errors.ERR_TOGGLE_IS_NULL.format(row=row))
        else:
            try:
                description.check(value, drum=drum)
            except InvalidValue as problem:
                with reading(errors.ERR_WHERE_IN_ROW.format(where=where, row=row)):
                    raise problem.with_correction(_row_correction(data=data, row=row, drum=drum)) from None


def nearest_step_value(*, row, value, drum):
    """Return the allowed value nearest a step's wrong value on a row, or NO_NEAREST_VALUE when the row has no limits or the value isn't a number at all. A blank step stays blank."""
    return None if value is None else row_descriptions.ROW_DESCRIPTIONS[row].nearest(value, drum=drum)


def held_add(*, value, most):
    """Return a step's add on a += row held within most either way, or a blank as it is."""
    if not value or abs(value) <= most:
        return value
    return most if value > 0 else -most


def _row_correction(*, data, row, drum):
    """Return the correction that brings every step of a row within the row's limits, or None when a value on the row has no allowed value near it."""
    found = data[row]
    used = [nearest_step_value(row=row, value=value, drum=drum) for value in found]
    if any(value is corrections.NO_NEAREST_VALUE for value in used):
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
            raise InvalidValue(errors.ERR_TIE_ON_A_NOTE.format(step=step + FIRST_STEP_NUMBER))
