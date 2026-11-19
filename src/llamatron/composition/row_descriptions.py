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
"""One description of each row of a pattern: what a step may hold on the row, and what the row is like.

A pattern keeps a list of values for each row, one value a step, and a row's description here
says once what those values are: whether a step is on or off, a whole number within limits, a
length or one of a few choices, what a blank step plays as, and what the row does in a drum
pattern. Reading a file, a pattern's setter and the tracker's pattern editor all ask the one
description, so a file, a key press and the editor's range can't come to disagree about a row,
and a new row is one line of ROW_DESCRIPTIONS.

The descriptions check and describe. They hold no steps: a pattern's values stay plain lists,
which playback reads directly, since it reads every step of every pass.
"""

from llamatron.composition import corrections, defaults, file_format, limits
from llamatron.composition.checks import is_true_or_false, is_whole_number, is_whole_number_from, listed
from llamatron.composition.file_format import RegisterUse, Row, StatementPart
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.named_scale import scale_type_names
from llamatron.composition.setting import Length
from llamatron.music import midi
from llamatron.strings import errors

# A drum pattern's degree row holds one note letter per step.
NOTE_LETTER_LENGTH = 1
# What a blank step holds on a row of numbers, lengths or choices, and on a row that is on or off.
BLANK = None
OFF = False
# A ratchet offset or a register change of nothing, which is what a blank step has.
NO_RATCHET_OFFSET = 0
NO_REGISTER_CHANGE = 0
# A row whose blank step has no number to play as: a blank CC step sends nothing, so the last value holds.
NO_DEFAULT = None


class RowDescription:
    """What a step may hold on one row of a pattern. Each kind of row is a subclass.

    kept_by_a_rest says the row's value stays on a step whose note is cleared, as a CC value, a
    slide and a register change do. changes_with_drums says the row means something else in a
    drum pattern, so its values go when a pattern is made a drum pattern or made one no longer.
    """

    __slots__ = ('_name', '_kept_by_a_rest', '_changes_with_drums')

    def __init__(self, *, name, kept_by_a_rest=False, changes_with_drums=False):
        self._name = name
        self._kept_by_a_rest = kept_by_a_rest
        self._changes_with_drums = changes_with_drums

    def get_name(self):
        """Return the row's name, as a file writes it."""
        return self._name

    def is_kept_by_a_rest(self):
        return self._kept_by_a_rest

    def changes_with_drums(self):
        return self._changes_with_drums

    def is_in_drum_patterns(self):
        """Return whether a drum pattern has the row at all. It has every row but the ones that need a scale."""
        return True

    def is_on_or_off(self):
        """Return whether each step is on or off on the row, which a file writes as true or false and never leaves blank."""
        return False

    def blank(self):
        """Return what a step holds on the row when nothing is set."""
        return BLANK

    def written(self, values):
        """Return the row's values as a file writes them, in a list of their own."""
        return list(values)

    def read(self, values):
        """Return a file's values as the pattern holds them, in a list of its own, once they're checked."""
        return list(values)

    def kept(self, value):
        """Return one step's checked value as the pattern holds it, which is the value itself on every row but one that holds a list."""
        return value

    def problem_with(self, value, *, drum):
        """Return what a step's value has to be when it isn't that, in the words that follow the row's name in a message, or None when nothing is wrong. A blank step isn't asked about."""
        raise NotImplementedError

    def check(self, value, *, drum):
        """Refuse a value a step can't hold on the row, saying which row and what the value has to be."""
        problem = self.problem_with(value, drum=drum)
        if problem:
            raise InvalidValue(errors.ERR_BAD_STEP_VALUE.format(row=self._name, problem=problem, value=value))

    def nearest(self, value, *, drum):
        """Return the allowed value nearest a wrong one, or NO_NEAREST_VALUE: only a row with limits has one."""
        return corrections.NO_NEAREST_VALUE


class RowOfNumbers(RowDescription):
    """A row whose steps hold a whole number from lowest to highest, like Velocity.

    default is the number a blank step plays as, or NO_DEFAULT where a blank step plays as no
    number at all. quiet says a blank step changes nothing about how the step plays, as no
    ratchet and no register change do, where a blank Velocity is still a velocity.
    """

    __slots__ = ('_lowest', '_highest', '_default', '_quiet', '_problem')

    def __init__(self, *, name, lowest, highest, default, quiet=False, kept_by_a_rest=False):
        super().__init__(name=name, kept_by_a_rest=kept_by_a_rest)
        self._lowest = lowest
        self._highest = highest
        self._default = default
        self._quiet = quiet
        self._problem = errors.ERR_NOT_IN_RANGE.format(lowest=lowest, highest=highest)

    def get_lowest(self):
        return self._lowest

    def get_highest(self):
        return self._highest

    def get_default(self):
        return self._default

    def is_quiet(self):
        return self._quiet

    def problem_with(self, value, *, drum):
        # Written out rather than asked of nearest(), since reading a file checks every step's value with this.
        return self._problem if type(value) is not int or value < self._lowest or value > self._highest else None

    def nearest(self, value, *, drum):
        """Return the end of the range nearest a whole number outside it."""
        if not is_whole_number(value):
            return corrections.NO_NEAREST_VALUE
        return max(min(value, self._highest), self._lowest)


class RowOfOctaves(RowOfNumbers):
    """The Octave row, which refuses a value in the words every octave is refused with."""

    __slots__ = ()

    def check(self, value, *, drum):
        if self.problem_with(value, drum=drum):
            raise InvalidValue(errors.ERR_CHECKS_BAD_OCTAVE.format(lowest=self._lowest, highest=self._highest, value=value))


class RowOfDegrees(RowDescription):
    """The Degree row: a scale degree from lowest up, with no highest, since the scale that sets one is bound late. In a drum pattern each step holds a note letter."""

    __slots__ = ('_lowest', '_problem')

    def __init__(self, *, name, lowest):
        super().__init__(name=name, changes_with_drums=True)
        self._lowest = lowest
        self._problem = errors.ERR_NOT_DEGREE.format(lowest=lowest)

    def get_lowest(self):
        return self._lowest

    def problem_with(self, value, *, drum):
        if drum:
            return None if is_note_letter(value) else errors.ERR_NOT_NOTE_LETTER
        return self._problem if type(value) is not int or value < self._lowest else None

    def nearest(self, value, *, drum):
        """Return the lowest degree for a whole number under it. A drum pattern's note letter has no nearest."""
        if drum or not is_whole_number(value):
            return corrections.NO_NEAREST_VALUE
        return max(value, self._lowest)


class RowOfLengths(RowDescription):
    """The Gate row: a length written as a whole number or a fraction, like 2 or 5/16, at most most."""

    __slots__ = ('_length',)

    def __init__(self, *, name, most):
        super().__init__(name=name)
        self._length = Length(name=name, most=most)

    def get_most(self):
        return self._length.get_most()

    def problem_with(self, value, *, drum):
        return self._length.problem_with(value)

    def check(self, value, *, drum):
        """Refuse a length in the words every length is refused with."""
        self._length.check(value)

    def nearest(self, value, *, drum):
        return self._length.nearest(value)


class RowOfChoices(RowDescription):
    """A row whose steps hold one of a few fixed choices, like the Dot row's dotted and triplet."""

    __slots__ = ('_choices', '_problem')

    def __init__(self, *, name, choices, problem, changes_with_drums=False):
        super().__init__(name=name, changes_with_drums=changes_with_drums)
        self._choices = tuple(choices)
        self._problem = problem

    def get_choices(self):
        """Return the choices, in the order a key steps through them."""
        return list(self._choices)

    def problem_with(self, value, *, drum):
        return None if value in self._choices else self._problem


class RowOfChords(RowOfChoices):
    """The Chord row: a chord symbol, which a file may write as a bare number. A drum pattern has no chords."""

    __slots__ = ()

    def __init__(self, *, name, symbols):
        super().__init__(name=name, choices=symbols, problem=errors.ERR_NOT_CHORD.format(symbols=listed(symbols)), changes_with_drums=True)

    def is_in_drum_patterns(self):
        return False

    def problem_with(self, value, *, drum):
        if drum:
            return errors.ERR_CHORD_ON_DRUMS
        return None if str(value) in self._choices else self._problem


class RowOfInversions(RowOfChoices):
    """The Inversion row: how many of a chord's lowest notes move up an octave, or blank for root position. A drum pattern has no chords, so no inversions."""

    __slots__ = ()

    def __init__(self, *, name, choices):
        super().__init__(name=name, choices=choices, problem=errors.ERR_NOT_INVERSION.format(choices=listed(choices)), changes_with_drums=True)

    def is_in_drum_patterns(self):
        return False

    def problem_with(self, value, *, drum):
        if drum:
            return errors.ERR_INVERSION_ON_DRUMS
        return super().problem_with(value, drum=drum)


class RowOfTensions(RowDescription):
    """The Tension row: the notes added on top of a step's chord, a few of the tensions, each once. A pattern holds a step's as
    a tuple, lowest first, which nothing can change, and a file writes a list. A drum pattern has no chords, so no tensions."""

    __slots__ = ('_choices', '_problem')

    def __init__(self, *, name, choices):
        super().__init__(name=name, changes_with_drums=True)
        self._choices = tuple(choices)
        self._problem = errors.ERR_NOT_TENSIONS.format(choices=listed(self._choices))

    def get_choices(self):
        """Return the tensions, in the order the editor offers them."""
        return list(self._choices)

    def is_in_drum_patterns(self):
        return False

    def in_order(self, tensions):
        """Return some tensions as a step holds them: a tuple, lowest first, or nothing when there are none."""
        return tuple(tension for tension in self._choices if tension in tensions) or None

    def kept(self, value):
        return self.in_order(value)

    def written(self, values):
        return [None if value is None else list(value) for value in values]

    def read(self, values):
        return [None if value is None else self.in_order(value) for value in values]

    def problem_with(self, value, *, drum):
        if drum:
            return errors.ERR_TENSION_ON_DRUMS
        if not isinstance(value, (list, tuple)) or not value or len(set(value)) != len(value) or any(tension not in self._choices for tension in value):
            return self._problem
        return None


class RowOfKeyswitches(RowDescription):
    """The Keyswitch row: which of its instrument's keyswitch slots a step's note is played with, each once. A pattern holds a
    step's as a tuple, lowest first, which nothing can change, and a file writes a list. A pattern names slots and never notes,
    since the notes are the instrument's, and a drum pattern's steps take them as any other's."""

    __slots__ = ('_choices', '_problem')

    def __init__(self, *, name, choices):
        super().__init__(name=name)
        self._choices = tuple(choices)
        self._problem = errors.ERR_NOT_KEYSWITCHES.format(choices=listed(self._choices))

    def get_choices(self):
        """Return the slots, in order."""
        return list(self._choices)

    def in_order(self, slots):
        """Return some slots as a step holds them: a tuple, lowest first, or nothing when there are none."""
        return tuple(slot for slot in self._choices if slot in slots) or None

    def kept(self, value):
        return self.in_order(value)

    def written(self, values):
        return [None if value is None else list(value) for value in values]

    def read(self, values):
        return [None if value is None else self.in_order(value) for value in values]

    def problem_with(self, value, *, drum):
        if not isinstance(value, (list, tuple)) or not value or len(set(value)) != len(value) or any(type(slot) is not int or slot not in self._choices for slot in value):
            return self._problem
        return None


class RowOfChordScales(RowOfChoices):
    """The Scale row: the scale type a step's degree and chord are drawn from, on the clip's root, or blank for the clip's own scale. A drum pattern has no scale."""

    __slots__ = ()

    def __init__(self, *, name, choices):
        super().__init__(name=name, choices=choices, problem=errors.ERR_NOT_CHORD_SCALE.format(choices=listed(choices)), changes_with_drums=True)

    def is_in_drum_patterns(self):
        return False

    def problem_with(self, value, *, drum):
        if drum:
            return errors.ERR_CHORD_SCALE_ON_DRUMS
        return super().problem_with(value, drum=drum)


class RowOfToggles(RowDescription):
    """A row whose steps are each on or off, like Glide."""

    __slots__ = ()

    def is_on_or_off(self):
        return True

    def blank(self):
        return OFF

    def written(self, values):
        return [bool(value) for value in values]

    def problem_with(self, value, *, drum):
        return None if is_true_or_false(value) else errors.ERR_PATTERN_NOT_TRUE_OR_FALSE


class RowOfRegisterUses(RowDescription):
    """A register's +Vel row: each step adds the register's value (1), subtracts it (-1) or does neither (0).

    A rest can hold the row, as it can hold every register row, so erasing a note leaves it on the
    step. A file from before the change held true and false, which read as 1 and 0, and a null
    reads as 0, so the pattern always holds one of the three numbers.
    """

    __slots__ = ()

    def __init__(self, *, name, changes_with_drums=False):
        super().__init__(name=name, kept_by_a_rest=True, changes_with_drums=changes_with_drums)

    def blank(self):
        return RegisterUse.OFF

    def get_choices(self):
        """Return the uses a key cycles through after off, in order: add, then subtract."""
        return list(file_format.REGISTER_USES)

    def written(self, values):
        return [RegisterUse.OFF if value is None else int(value) for value in values]

    def read(self, values):
        return self.written(values)

    def problem_with(self, value, *, drum):
        if is_true_or_false(value) or (is_whole_number(value) and value in (RegisterUse.ADD, RegisterUse.SUBTRACT, RegisterUse.OFF)):
            return None
        return errors.ERR_NOT_REGISTER_USE


class RowOfNoteMoves(RowOfRegisterUses):
    """A register's +Note row, which moves the step's note along the scale by the register's value, up or down. A drum pattern has no scale, so the row can only be off there."""

    __slots__ = ()

    def __init__(self, *, name):
        super().__init__(name=name, changes_with_drums=True)

    def is_in_drum_patterns(self):
        return False

    def problem_with(self, value, *, drum):
        problem = super().problem_with(value, drum=drum)
        if problem is None and drum and value:
            return errors.ERR_REGISTER_NOTE_ON_DRUMS
        return problem


def is_note_letter(value):
    """Return whether a value is one note letter, A to G, as a drum pattern's degree row holds."""
    return isinstance(value, str) and len(value) == NOTE_LETTER_LENGTH and value in file_format.NOTE_LETTERS


def described_rows(*rows):
    """Return row descriptions by the names a file gives the rows, in the order given."""
    return {row.get_name(): row for row in rows}


def control_row(name):
    """Return the description of one CC row: a value a rest can send too, and nothing sent where a step is blank."""
    return RowOfNumbers(name=name, lowest=midi.MIN_CC_VALUE, highest=midi.MAX_CC_VALUE, default=NO_DEFAULT, quiet=True, kept_by_a_rest=True)


def register_change_row(name):
    """Return the description of one register's += row: how much a step adds to the register, which a rest can do too."""
    return RowOfNumbers(name=name, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, default=NO_REGISTER_CHANGE, quiet=True, kept_by_a_rest=True)


def register_set_row(name):
    """Return the description of one register's = row: the value a step sets the register to before anything adds to it, or blank to leave it, which a rest can do too."""
    return RowOfNumbers(name=name, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, default=NO_DEFAULT, quiet=True, kept_by_a_rest=True)


class RowOfStatementValues(RowDescription):
    """A row that holds a number or a register's name: what a step's statement about the registers compares with, or reckons with. A rest holds one too."""

    __slots__ = ()

    def __init__(self, *, name):
        super().__init__(name=name, kept_by_a_rest=True)

    def problem_with(self, value, *, drum):
        if value in file_format.REGISTER_NAMES or is_whole_number_from(value=value, lowest=-limits.MAX_STATEMENT_NUMBER, highest=limits.MAX_STATEMENT_NUMBER):
            return None
        return errors.ERR_NOT_STATEMENT_VALUE.format(lowest=-limits.MAX_STATEMENT_NUMBER, highest=limits.MAX_STATEMENT_NUMBER, choices=listed(file_format.REGISTER_NAMES))


class RowOfStatementChoices(RowOfChoices):
    """A row that holds one part of a step's statement about the registers chosen from a list: the register, the operator or the comparison of a sum's result. A rest holds one too."""

    __slots__ = ()

    def __init__(self, *, name, choices):
        super().__init__(name=name, choices=choices, problem=errors.ERR_NOT_STATEMENT_CHOICE.format(choices=listed(choices)))
        self._kept_by_a_rest = True


# What each part of a statement may be, by the part.
STATEMENT_PART_CHOICES = {StatementPart.REGISTER: file_format.REGISTER_NAMES, StatementPart.OPERATOR: file_format.OPERATORS, StatementPart.COMPARISON: file_format.RESULT_COMPARISONS}


def statement_row(name):
    """Return the description of one row of a step's statements: the row of one part of one kind of statement."""
    _, part = file_format.STATEMENT_OF_ROW[name]
    if part in STATEMENT_PART_CHOICES:
        return RowOfStatementChoices(name=name, choices=STATEMENT_PART_CHOICES[part])
    return RowOfStatementValues(name=name)


# Every row of a pattern, described once, in the order a file writes the rows (PATTERN_ROWS).
ROW_DESCRIPTIONS = described_rows(
    RowOfDegrees(name=Row.DEGREE, lowest=limits.MIN_DEGREE),
    RowOfLengths(name=Row.GATE, most=limits.MAX_GATE),
    RowOfChoices(name=Row.DOT, choices=file_format.GATE_MODIFIERS, problem=errors.ERR_NOT_GATE_MODIFIER),
    RowOfChoices(name=Row.ACCIDENTAL, choices=file_format.ACCIDENTALS, problem=errors.ERR_NOT_ACCIDENTAL, changes_with_drums=True),
    RowOfOctaves(name=Row.OCTAVE, lowest=limits.MIN_OCTAVE, highest=limits.MAX_OCTAVE, default=NO_DEFAULT),
    RowOfChords(name=Row.CHORD, symbols=file_format.CHORD_SYMBOLS),
    RowOfInversions(name=Row.INVERSION, choices=limits.INVERSIONS),
    RowOfTensions(name=Row.TENSION, choices=file_format.TENSIONS),
    RowOfChordScales(name=Row.CHORD_SCALE, choices=scale_type_names()),
    RowOfNumbers(name=Row.VELOCITY, lowest=midi.MIN_VELOCITY, highest=midi.MAX_VELOCITY, default=defaults.DEFAULT_VELOCITY),
    RowOfToggles(name=Row.ACCENT),
    RowOfNumbers(name=Row.PROBABILITY, lowest=limits.MIN_PROBABILITY, highest=limits.MAX_PROBABILITY, default=defaults.DEFAULT_PROBABILITY),
    RowOfToggles(name=Row.GLIDE),
    RowOfToggles(name=Row.TIE),
    RowOfNumbers(name=Row.RATCHET, lowest=limits.MIN_RATCHET, highest=limits.MAX_RATCHET, default=defaults.DEFAULT_RATCHET, quiet=True),
    RowOfNumbers(name=Row.RATCHET_OFFSET, lowest=-limits.MAX_RATCHET_OFFSET, highest=limits.MAX_RATCHET_OFFSET, default=NO_RATCHET_OFFSET, quiet=True),
    RowOfToggles(name=Row.GRAB),
    RowOfKeyswitches(name=Row.KEYSWITCH, choices=file_format.KEYSWITCH_SLOTS),
    *[control_row(name) for name in file_format.CC_ROWS],
    RowOfToggles(name=Row.SLIDE, kept_by_a_rest=True),
    *[RowOfNoteMoves(name=name) for name in file_format.REGISTER_NOTE_ROWS.values()],
    *[RowOfRegisterUses(name=name) for name in file_format.REGISTER_VELOCITY_ROWS.values()],
    *[register_change_row(name) for name in file_format.REGISTER_ADD_ROWS.values()],
    *[register_set_row(name) for name in file_format.REGISTER_SET_ROWS.values()],
    *[statement_row(name) for name in file_format.STATEMENT_OF_ROW],
)


def row_described(name):
    """Return the description of a row by its name, or raise InvalidValue for a name that is no row of a pattern."""
    if name not in ROW_DESCRIPTIONS:
        raise InvalidValue(errors.ERR_NO_SUCH_ROW.format(row=name))
    return ROW_DESCRIPTIONS[name]


def rows_where(condition):
    """Return the names of the rows whose description a condition is true of, in the order a file writes them."""
    return tuple(name for name in file_format.PATTERN_ROWS if condition(ROW_DESCRIPTIONS[name]))
