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
"""The one description of each row of a pattern (composition/row_descriptions.py).

Each kind of row is tested on its own, then the rules: every row a file writes is described
once, the tracker draws and labels every described row, and a file, a pattern's setter and the
pattern editor's rows all refuse and allow the same values, because all three ask the one
description.
"""

import unittest

from llamatron.composition.corrections import NO_NEAREST_VALUE
from llamatron.composition.defaults import DEFAULT_PROBABILITY, DEFAULT_RATCHET, DEFAULT_VELOCITY
from llamatron.composition.file_format import (
    ACCIDENTAL_CYCLE, CC_ROWS, CHORD_SYMBOLS, PATTERN_ROWS, REGISTER_ADD_ROWS, REGISTER_NOTE_ROWS, REGISTER_SET_ROWS, REGISTER_VELOCITY_ROWS, Accidental,
    ChordSymbol, GateModifier, PatternSetting, RegisterName, RegisterUse, Row, Section, Tension,
)
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MAX_GATE, MAX_OCTAVE, MAX_RATCHET, MAX_RATCHET_OFFSET, MIN_DEGREE, MIN_OCTAVE, MIN_RATCHET
from llamatron.composition.pattern import NOTE_ROWS, REST_ROWS
from llamatron.composition.row_descriptions import (
    ROW_DESCRIPTIONS, RowOfChoices, RowOfChords, RowOfDegrees, RowOfLengths, RowOfNoteMoves, RowOfNumbers, RowOfOctaves, RowOfRegisterUses, RowOfTensions,
    RowOfToggles,
    is_note_letter, row_described, rows_where,
)
from llamatron.composition.setlist import Setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.midi import MAX_VELOCITY, MIN_VELOCITY
from llamatron.music.note import NoteName
from llamatron.strings.errors import (
    ERR_BAD_STEP_VALUE, ERR_CHECKS_BAD_OCTAVE, ERR_CHORD_ON_DRUMS, ERR_NO_SUCH_ROW, ERR_NOT_ACCIDENTAL, ERR_NOT_CHORD, ERR_NOT_DEGREE,
    ERR_NOT_GATE_MODIFIER, ERR_NOT_IN_RANGE, ERR_NOT_NOTE_LETTER, ERR_NOT_REGISTER_USE, ERR_PATTERN_NOT_TRUE_OR_FALSE, ERR_REGISTER_NOTE_ON_DRUMS,
)
from llamatron.strings.labels import MSG_ROW_LABELS
from llamatron.tui.components.number_row import NumberRow
from llamatron.tui.components.pattern_rows import PINNED_ROWS, ROW_CLASSES, SECTIONS

TUNE = 'tune'
STEPS = 2
FIRST_STEP = 0
SECOND_STEP = 1
A_DEGREE = 3
A_VELOCITY = 90
QUARTER = '1/4'
NOT_A_NUMBER = 'loud'
NOT_A_CHOICE = 'x'
NOT_A_ROW = 'duration'
HALF = 1.5
NOT_A_LETTER = 'H'
TWO_LETTERS = 'CD'
A_BARE_NUMBER_CHORD = 7
# What each number row's blank step plays as, where the tests can name it from the program's own defaults.
DEFAULTS = {Row.VELOCITY: DEFAULT_VELOCITY, Row.PROBABILITY: DEFAULT_PROBABILITY, Row.RATCHET: DEFAULT_RATCHET}
# The rows a blank step changes nothing on, which the editor shows as a dot until they're set.
QUIET = (Row.RATCHET, Row.RATCHET_OFFSET, *CC_ROWS, *REGISTER_ADD_ROWS.values(), *REGISTER_SET_ROWS.values())


def rows_of(kind):
    """Return the descriptions that are exactly one kind of row, by name."""
    return {name: row for name, row in ROW_DESCRIPTIONS.items() if type(row) is kind}


def a_pattern(*, drum=False, rows=None):
    """Return a pattern of two steps with a note on the first and nothing on the second, and any other rows given."""
    degrees = [NoteName.C if drum else A_DEGREE, None]
    data = {PatternSetting.STEPS: STEPS, Row.DEGREE: degrees, **(rows or {})}
    if drum:
        data[PatternSetting.DRUM] = True
    return Setlist.from_data(data={Section.PATTERNS: {TUNE: data}}).get_pattern(TUNE)


def a_value_of(row, *, drum=False):
    """Return a value a step can hold on a row, which isn't what a blank step holds."""
    described = ROW_DESCRIPTIONS[row]
    if isinstance(described, RowOfToggles):
        return True
    if isinstance(described, RowOfRegisterUses):
        return RegisterUse.ADD
    if isinstance(described, RowOfChords):
        return ChordSymbol.DOMINANT7
    if isinstance(described, RowOfTensions):
        return (Tension.NINTH,)
    if isinstance(described, RowOfChoices):
        return described.get_choices()[0]
    if isinstance(described, RowOfLengths):
        return QUARTER
    if isinstance(described, RowOfDegrees):
        return NoteName.D if drum else A_DEGREE
    return described.get_highest()


def a_wrong_value_of(row):
    """Return a value no step can hold on a row, in a drum pattern or any other."""
    return HALF if isinstance(ROW_DESCRIPTIONS[row], (RowOfToggles, RowOfRegisterUses)) else [NOT_A_CHOICE]


class TestRowsOfNumbers(unittest.TestCase):

    def test_both_ends_are_allowed_and_one_past_either_is_refused_in_the_rows_words(self):
        for name, row in {**rows_of(RowOfNumbers), **rows_of(RowOfOctaves)}.items():
            with self.subTest(row=name):
                row.check(row.get_lowest(), drum=False)
                row.check(row.get_highest(), drum=False)
                self.assertIsNone(row.problem_with(row.get_lowest(), drum=False))
                for wrong in (row.get_lowest() - 1, row.get_highest() + 1, NOT_A_NUMBER, HALF, True):
                    self.assertEqual(row.problem_with(wrong, drum=False), ERR_NOT_IN_RANGE.format(lowest=row.get_lowest(), highest=row.get_highest()))
                    with self.assertRaises(InvalidValue):
                        row.check(wrong, drum=False)

    def test_a_refusal_names_the_row_and_the_value(self):
        row = ROW_DESCRIPTIONS[Row.VELOCITY]
        with self.assertRaises(InvalidValue) as refused:
            row.check(MAX_VELOCITY + 1, drum=False)
        problem = ERR_NOT_IN_RANGE.format(lowest=MIN_VELOCITY, highest=MAX_VELOCITY)
        self.assertEqual(str(refused.exception), ERR_BAD_STEP_VALUE.format(row=Row.VELOCITY, problem=problem, value=MAX_VELOCITY + 1))

    def test_an_octave_is_refused_in_the_words_every_octave_is(self):
        with self.assertRaises(InvalidValue) as refused:
            ROW_DESCRIPTIONS[Row.OCTAVE].check(MAX_OCTAVE + 1, drum=False)
        self.assertEqual(str(refused.exception), ERR_CHECKS_BAD_OCTAVE.format(lowest=MIN_OCTAVE, highest=MAX_OCTAVE, value=MAX_OCTAVE + 1))

    def test_the_nearest_value_is_the_nearest_end_and_nothing_for_what_is_no_number(self):
        for name, row in {**rows_of(RowOfNumbers), **rows_of(RowOfOctaves)}.items():
            with self.subTest(row=name):
                self.assertEqual(row.nearest(row.get_highest() + 1, drum=False), row.get_highest())
                self.assertEqual(row.nearest(row.get_lowest() - 1, drum=False), row.get_lowest())
                self.assertEqual(row.nearest(row.get_lowest(), drum=False), row.get_lowest())
                self.assertIs(row.nearest(NOT_A_NUMBER, drum=False), NO_NEAREST_VALUE)
                self.assertIs(row.nearest(True, drum=False), NO_NEAREST_VALUE)

    def test_a_ratchet_and_a_ratchet_offset_have_the_limits_the_editor_always_had(self):
        ratchet = ROW_DESCRIPTIONS[Row.RATCHET]
        offset = ROW_DESCRIPTIONS[Row.RATCHET_OFFSET]
        self.assertEqual((ratchet.get_lowest(), ratchet.get_highest()), (MIN_RATCHET, MAX_RATCHET))
        self.assertEqual((offset.get_lowest(), offset.get_highest()), (-MAX_RATCHET_OFFSET, MAX_RATCHET_OFFSET))

    def test_what_a_blank_step_plays_as(self):
        for name, default in DEFAULTS.items():
            self.assertEqual(ROW_DESCRIPTIONS[name].get_default(), default)
        for name in CC_ROWS:
            self.assertIsNone(ROW_DESCRIPTIONS[name].get_default())
        self.assertIsNone(ROW_DESCRIPTIONS[Row.OCTAVE].get_default())

    def test_the_rows_a_blank_step_changes_nothing_on(self):
        self.assertEqual({name for name, row in rows_of(RowOfNumbers).items() if row.is_quiet()}, set(QUIET))

    def test_a_blank_step_holds_nothing_and_a_row_is_written_as_it_is(self):
        row = ROW_DESCRIPTIONS[Row.VELOCITY]
        self.assertIsNone(row.blank())
        self.assertFalse(row.is_on_or_off())
        values = [A_VELOCITY, None]
        self.assertEqual(row.written(values), values)
        self.assertIsNot(row.written(values), values)


class TestRowsOfToggles(unittest.TestCase):

    def test_true_and_false_are_allowed_and_nothing_else(self):
        for name, row in rows_of(RowOfToggles).items():
            with self.subTest(row=name):
                self.assertIsNone(row.problem_with(True, drum=False))
                self.assertIsNone(row.problem_with(False, drum=False))
                for wrong in (1, 0, NOT_A_NUMBER, None):
                    self.assertEqual(row.problem_with(wrong, drum=False), ERR_PATTERN_NOT_TRUE_OR_FALSE)
                self.assertIs(row.nearest(1, drum=False), NO_NEAREST_VALUE)

    def test_a_blank_step_is_off_and_a_file_writes_true_and_false(self):
        row = ROW_DESCRIPTIONS[Row.GLIDE]
        self.assertIs(row.blank(), False)
        self.assertTrue(row.is_on_or_off())
        self.assertEqual(row.written([True, False, None]), [True, False, False])

    def test_the_rows_that_are_on_or_off(self):
        toggles = {Row.GLIDE, Row.TIE, Row.GRAB, Row.SLIDE}
        self.assertEqual(set(rows_where(lambda row: row.is_on_or_off())), toggles)


class TestRowsOfRegisterUses(unittest.TestCase):
    """The +Note and +Vel rows: 1 adds the register, -1 subtracts it and 0 does neither, the user's design of 2026-11-09, where the rows were toggles."""

    def test_the_rows_that_use_a_register(self):
        uses = {*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values()}
        self.assertEqual(set(rows_of(RowOfRegisterUses)) | set(rows_of(RowOfNoteMoves)), uses)
        self.assertEqual(set(rows_of(RowOfNoteMoves)), set(REGISTER_NOTE_ROWS.values()))

    def test_add_subtract_and_off_are_allowed_and_so_are_true_and_false_from_an_older_file(self):
        for name in (*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values()):
            row = ROW_DESCRIPTIONS[name]
            with self.subTest(row=name):
                for allowed in (RegisterUse.ADD, RegisterUse.SUBTRACT, RegisterUse.OFF, True, False):
                    self.assertIsNone(row.problem_with(allowed, drum=False))
                for wrong in (2, -2, HALF, NOT_A_NUMBER, None, [RegisterUse.ADD]):
                    self.assertEqual(row.problem_with(wrong, drum=False), ERR_NOT_REGISTER_USE)
                self.assertIs(row.nearest(2, drum=False), NO_NEAREST_VALUE)
                self.assertFalse(row.is_on_or_off())
                self.assertTrue(row.is_kept_by_a_rest())

    def test_a_blank_step_is_off_and_a_file_holds_the_numbers_with_true_and_false_read_as_add_and_off(self):
        row = ROW_DESCRIPTIONS[REGISTER_VELOCITY_ROWS[RegisterName.AX]]
        self.assertEqual(row.blank(), RegisterUse.OFF)
        self.assertEqual(row.get_choices(), [RegisterUse.ADD, RegisterUse.SUBTRACT])
        values = [RegisterUse.ADD, RegisterUse.SUBTRACT, RegisterUse.OFF, None, True, False]
        held = [RegisterUse.ADD, RegisterUse.SUBTRACT, RegisterUse.OFF, RegisterUse.OFF, RegisterUse.ADD, RegisterUse.OFF]
        self.assertEqual(row.read(values), held)
        self.assertEqual(row.written(values), held)
        self.assertIsNot(row.written(held), held)
        for value in row.read(values):
            self.assertIs(type(value), int)

    def test_a_file_holding_true_reads_as_add_and_is_written_as_1(self):
        row = REGISTER_NOTE_ROWS[RegisterName.BX]
        pattern = a_pattern(rows={row: [True, False]})
        self.assertEqual(pattern.get_value(row=row, step=FIRST_STEP), RegisterUse.ADD)
        self.assertIs(type(pattern.get_value(row=row, step=FIRST_STEP)), int)
        self.assertEqual(pattern.to_data()[row], [RegisterUse.ADD, RegisterUse.OFF])
        # A row with every step off isn't written at all.
        pattern.set_value(row=row, step=FIRST_STEP, value=RegisterUse.OFF)
        self.assertNotIn(row, pattern.to_data())
        pattern.set_value(row=row, step=SECOND_STEP, value=RegisterUse.SUBTRACT)
        self.assertEqual(pattern.to_data()[row], [RegisterUse.OFF, RegisterUse.SUBTRACT])

    def test_a_registers_note_row_can_only_be_off_in_a_drum_pattern_which_does_not_have_the_row(self):
        for name in REGISTER_NOTE_ROWS.values():
            row = ROW_DESCRIPTIONS[name]
            for on in (RegisterUse.ADD, RegisterUse.SUBTRACT, True):
                self.assertEqual(row.problem_with(on, drum=True), ERR_REGISTER_NOTE_ON_DRUMS)
            self.assertIsNone(row.problem_with(RegisterUse.OFF, drum=True))
            self.assertIsNone(row.problem_with(False, drum=True))
            self.assertEqual(row.problem_with(2, drum=True), ERR_NOT_REGISTER_USE)
            self.assertFalse(row.is_in_drum_patterns())
        for name in REGISTER_VELOCITY_ROWS.values():
            self.assertIsNone(ROW_DESCRIPTIONS[name].problem_with(RegisterUse.SUBTRACT, drum=True))
            self.assertTrue(ROW_DESCRIPTIONS[name].is_in_drum_patterns())


class TestRowsOfChoices(unittest.TestCase):

    def test_the_dot_row_takes_dotted_and_triplet_in_the_order_a_key_steps_through_them(self):
        row = ROW_DESCRIPTIONS[Row.DOT]
        self.assertEqual(row.get_choices(), [GateModifier.DOTTED, GateModifier.TRIPLET])
        for choice in row.get_choices():
            self.assertIsNone(row.problem_with(choice, drum=False))
        self.assertEqual(row.problem_with(NOT_A_CHOICE, drum=False), ERR_NOT_GATE_MODIFIER)

    def test_the_accidental_row_takes_sharp_and_flat_in_the_cycles_order(self):
        row = ROW_DESCRIPTIONS[Row.ACCIDENTAL]
        self.assertEqual([None, *row.get_choices()], ACCIDENTAL_CYCLE)
        self.assertIsNone(row.problem_with(Accidental.SHARP, drum=True))
        self.assertEqual(row.problem_with(NOT_A_CHOICE, drum=False), ERR_NOT_ACCIDENTAL)

    def test_a_value_that_is_not_text_is_refused_rather_than_breaking(self):
        for name in (Row.DOT, Row.ACCIDENTAL, Row.CHORD):
            self.assertIsNotNone(ROW_DESCRIPTIONS[name].problem_with([NOT_A_CHOICE], drum=False))
            self.assertIsNotNone(ROW_DESCRIPTIONS[name].problem_with({}, drum=False))

    def test_a_wrong_choice_has_no_nearest_value(self):
        self.assertIs(ROW_DESCRIPTIONS[Row.DOT].nearest(NOT_A_CHOICE, drum=False), NO_NEAREST_VALUE)

    def test_the_chord_row_takes_every_symbol_and_a_bare_number_and_lists_the_symbols_otherwise(self):
        row = ROW_DESCRIPTIONS[Row.CHORD]
        for symbol in CHORD_SYMBOLS:
            self.assertIsNone(row.problem_with(symbol, drum=False))
        self.assertIsNone(row.problem_with(A_BARE_NUMBER_CHORD, drum=False))
        problem = row.problem_with(NOT_A_CHOICE, drum=False)
        self.assertEqual(problem, ERR_NOT_CHORD.format(symbols=', '.join(CHORD_SYMBOLS)))

    def test_a_drum_pattern_has_no_chords(self):
        row = ROW_DESCRIPTIONS[Row.CHORD]
        self.assertEqual(row.problem_with(ChordSymbol.DOMINANT7, drum=True), ERR_CHORD_ON_DRUMS)
        self.assertFalse(row.is_in_drum_patterns())


class TestTheDegreeRow(unittest.TestCase):

    def test_a_degree_is_a_whole_number_from_the_lowest_with_no_highest(self):
        row = ROW_DESCRIPTIONS[Row.DEGREE]
        self.assertEqual(row.get_lowest(), MIN_DEGREE)
        self.assertIsNone(row.problem_with(MIN_DEGREE, drum=False))
        self.assertIsNone(row.problem_with(MIN_DEGREE + MAX_VELOCITY, drum=False))
        for wrong in (MIN_DEGREE - 1, NoteName.C, HALF, True):
            self.assertEqual(row.problem_with(wrong, drum=False), ERR_NOT_DEGREE.format(lowest=MIN_DEGREE))

    def test_a_drum_patterns_step_holds_one_note_letter(self):
        row = ROW_DESCRIPTIONS[Row.DEGREE]
        self.assertIsNone(row.problem_with(NoteName.C, drum=True))
        for wrong in (A_DEGREE, NOT_A_LETTER, TWO_LETTERS):
            self.assertEqual(row.problem_with(wrong, drum=True), ERR_NOT_NOTE_LETTER)
        self.assertTrue(is_note_letter(NoteName.G))
        self.assertFalse(is_note_letter(A_DEGREE))

    def test_a_degree_too_low_has_the_lowest_as_its_nearest_and_a_note_letter_has_none(self):
        row = ROW_DESCRIPTIONS[Row.DEGREE]
        self.assertEqual(row.nearest(MIN_DEGREE - 1, drum=False), MIN_DEGREE)
        self.assertEqual(row.nearest(A_DEGREE, drum=False), A_DEGREE)
        self.assertIs(row.nearest(NOT_A_NUMBER, drum=False), NO_NEAREST_VALUE)
        self.assertIs(row.nearest(MIN_DEGREE - 1, drum=True), NO_NEAREST_VALUE)


class TestTheGateRow(unittest.TestCase):

    def test_a_gate_is_a_length_up_to_the_longest(self):
        row = ROW_DESCRIPTIONS[Row.GATE]
        self.assertEqual(row.get_most(), MAX_GATE)
        row.check(QUARTER, drum=False)
        row.check(MAX_GATE, drum=False)
        for wrong in (MAX_GATE + 1, NOT_A_NUMBER, HALF, 0):
            with self.assertRaises(InvalidValue):
                row.check(wrong, drum=False)
            self.assertIsNotNone(row.problem_with(wrong, drum=False))

    def test_a_gate_too_long_has_the_longest_as_its_nearest(self):
        row = ROW_DESCRIPTIONS[Row.GATE]
        self.assertEqual(row.nearest(MAX_GATE + 1, drum=False), MAX_GATE)
        self.assertIs(row.nearest(NOT_A_NUMBER, drum=False), NO_NEAREST_VALUE)


class TestEveryRowIsDescribedOnce(unittest.TestCase):
    """The rules: a row's facts are in its one description, and everything else that lists rows lists the same rows."""

    def test_the_descriptions_are_the_rows_a_file_writes_in_the_files_order(self):
        self.assertEqual(list(ROW_DESCRIPTIONS), PATTERN_ROWS)

    def test_each_description_goes_by_its_rows_name(self):
        for name, row in ROW_DESCRIPTIONS.items():
            self.assertEqual(row.get_name(), name)

    def test_a_name_that_is_no_row_is_refused(self):
        self.assertIs(row_described(Row.GATE), ROW_DESCRIPTIONS[Row.GATE])
        with self.assertRaises(InvalidValue) as refused:
            row_described(NOT_A_ROW)
        self.assertEqual(str(refused.exception), ERR_NO_SUCH_ROW.format(row=NOT_A_ROW))

    def test_the_tracker_has_a_component_and_a_label_for_every_described_row_and_no_other(self):
        self.assertEqual(set(ROW_CLASSES), set(ROW_DESCRIPTIONS))
        self.assertEqual(set(MSG_ROW_LABELS), set(ROW_DESCRIPTIONS))

    def test_the_pattern_editor_shows_every_described_row_in_one_place(self):
        shown = [*PINNED_ROWS, *[name for names in SECTIONS.values() for name in names]]
        self.assertEqual(sorted(shown), sorted(ROW_DESCRIPTIONS))

    def test_the_editors_number_rows_are_the_rows_described_as_numbers(self):
        numbers = {name for name, component in ROW_CLASSES.items() if issubclass(component, NumberRow)}
        self.assertEqual(numbers, set(rows_of(RowOfNumbers)))

    def test_what_a_rest_keeps_and_what_changes_with_drums_come_from_the_descriptions(self):
        # A rest can hold every register row that changes or uses a register, so erasing a note keeps +Note and +Vel with = and +=; a condition only silences a note, so it goes with the note.
        register_rows = {*REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values(), *REGISTER_ADD_ROWS.values(), *REGISTER_SET_ROWS.values()}
        self.assertEqual(set(REST_ROWS), {*CC_ROWS, Row.SLIDE, *register_rows})
        self.assertEqual(set(NOTE_ROWS), {Row.DEGREE, Row.ACCIDENTAL, Row.CHORD, Row.INVERSION, Row.TENSION, Row.CHORD_SCALE, *REGISTER_NOTE_ROWS.values()})
        self.assertEqual(set(rows_where(lambda row: not row.is_in_drum_patterns())), {Row.CHORD, Row.INVERSION, Row.TENSION, Row.CHORD_SCALE, *REGISTER_NOTE_ROWS.values()})


class TestAPatternAsksTheDescriptions(unittest.TestCase):
    """A pattern's setter and a file's reading refuse a step's value in the same words, and a pattern clears what the descriptions say."""

    def test_the_setter_takes_a_rows_value_and_refuses_a_wrong_one_as_the_description_does(self):
        for name, row in ROW_DESCRIPTIONS.items():
            with self.subTest(row=name):
                pattern = a_pattern()
                pattern.set_value(row=name, step=FIRST_STEP, value=a_value_of(name))
                self.assertEqual(pattern.get_value(row=name, step=FIRST_STEP), a_value_of(name))
                with self.assertRaises(InvalidValue) as by_the_setter:
                    pattern.set_value(row=name, step=FIRST_STEP, value=a_wrong_value_of(name))
                with self.assertRaises(InvalidValue) as by_the_description:
                    row.check(a_wrong_value_of(name), drum=False)
                self.assertEqual(str(by_the_setter.exception), str(by_the_description.exception))

    def test_a_file_refuses_the_same_value_in_the_same_words_after_its_place(self):
        for name, row in ROW_DESCRIPTIONS.items():
            with self.subTest(row=name):
                with self.assertRaises(InvalidValue) as by_the_description:
                    row.check(a_wrong_value_of(name), drum=False)
                data = {PatternSetting.STEPS: STEPS, Row.DEGREE: [A_DEGREE, None], name: [a_wrong_value_of(name), row.blank()]}
                with self.assertRaises(SongFileError) as by_the_file:
                    Setlist.from_data(data={Section.PATTERNS: {TUNE: data}})
                self.assertTrue(str(by_the_file.exception).endswith(str(by_the_description.exception)), by_the_file.exception)

    def test_setting_nothing_makes_the_step_what_the_description_calls_blank(self):
        for name, row in ROW_DESCRIPTIONS.items():
            with self.subTest(row=name):
                pattern = a_pattern()
                pattern.set_value(row=name, step=FIRST_STEP, value=a_value_of(name))
                pattern.set_value(row=name, step=FIRST_STEP, value=None)
                self.assertEqual(pattern.get_value(row=name, step=FIRST_STEP), row.blank())

    def test_a_row_that_is_no_row_is_refused_by_the_setter(self):
        with self.assertRaises(InvalidValue):
            a_pattern().set_value(row=NOT_A_ROW, step=FIRST_STEP, value=A_DEGREE)

    def test_clearing_a_note_keeps_only_the_rows_a_rest_keeps(self):
        for name, row in ROW_DESCRIPTIONS.items():
            if name in (Row.TIE, Row.DEGREE):
                continue
            with self.subTest(row=name):
                pattern = a_pattern()
                pattern.set_value(row=name, step=FIRST_STEP, value=a_value_of(name))
                pattern.clear_sound(FIRST_STEP)
                kept = pattern.get_value(row=name, step=FIRST_STEP)
                self.assertEqual(kept, a_value_of(name) if row.is_kept_by_a_rest() else row.blank())

    def test_making_a_drum_pattern_clears_only_the_rows_that_mean_something_else_there(self):
        for name, row in ROW_DESCRIPTIONS.items():
            if name in (Row.TIE, Row.DEGREE):
                continue
            with self.subTest(row=name):
                pattern = a_pattern()
                pattern.set_value(row=name, step=FIRST_STEP, value=a_value_of(name))
                pattern.set_drum(True)
                kept = pattern.get_value(row=name, step=FIRST_STEP)
                if row.changes_with_drums():
                    # A row a pattern no longer holds reads as nothing, whichever kind of row it is.
                    self.assertIsNone(kept)
                else:
                    self.assertEqual(kept, a_value_of(name))

    def test_a_drum_pattern_takes_a_note_letter_and_refuses_a_chord_and_a_note_move(self):
        pattern = a_pattern(drum=True)
        pattern.set_value(row=Row.DEGREE, step=SECOND_STEP, value=a_value_of(Row.DEGREE, drum=True))
        for name in (Row.CHORD, *REGISTER_NOTE_ROWS.values()):
            with self.assertRaises(InvalidValue):
                pattern.set_value(row=name, step=FIRST_STEP, value=a_value_of(name))

    def test_a_pattern_writes_an_on_or_off_row_as_true_and_false(self):
        pattern = a_pattern()
        pattern.set_value(row=Row.GLIDE, step=FIRST_STEP, value=True)
        self.assertEqual(pattern.to_data()[Row.GLIDE], [True, False])


if __name__ == '__main__':
    unittest.main()
