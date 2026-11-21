# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the ways the Munge dialog changes a pattern, on Pattern alone: copies of steps, rolls, shuffles of a part, a mirror, an interleave, the rows cleared and the rows smoothed.

The pattern has eight steps whose degrees count from 1 to 8, so that a step is known by its degree
wherever it goes, with a velocity on every step that moves with the step.
"""

import unittest

from llamatron.composition import limits
from llamatron.composition.file_format import ChordSymbol, Operator, PatternSetting, RegisterName, Row, StatementPart, StepStatement
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.pattern import Pattern
from llamatron.math.rational import Rational
from llamatron.music import midi
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType

SIXTEENTH = Rational(1, 16)
C_MAJOR = NamedScale(root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR))
SCALE_SIZE = 7
OCTAVE = 4

HERE = 'a test'
STEPS = 8
DEGREES = [1, 2, 3, 4, 5, 6, 7, 8]
VELOCITIES = [10, 20, 30, 40, 50, 60, 70, 80]
# The cursor's step in the examples: the third.
THIRD = 2
OTHER_DEGREES = [7, 6, 5]
QUARTER = '1/4'
MAJOR_SEVENTH = 7
LOW = 20
HIGH = 100
A_STATEMENT = {StatementPart.REGISTER: RegisterName.AX, StatementPart.OPERATOR: Operator.LESS, StatementPart.VALUE: 1}
FIFTH = 4
FOURTH = 4
HALF_STEP = '1/32'
TRIES = 20


def pattern_of(*, degrees=None, drum=None, **rows):
    """Return a pattern of the given degrees, the eight by default, with any other rows."""
    degrees = DEGREES if degrees is None else degrees
    data = {PatternSetting.STEPS: len(degrees), Row.DEGREE: list(degrees), **rows}
    if drum:
        data[PatternSetting.DRUM] = True
    return Pattern.from_data(data=data, where=HERE)


class TestCopiesOfSteps(unittest.TestCase):

    def test_the_steps_through_the_cursor_are_copied_to_the_end(self):
        pattern = pattern_of(**{Row.VELOCITY: VELOCITIES})
        pattern.repeat_at_end(first=0, last=THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3])
        self.assertEqual(pattern.get_row(Row.VELOCITY), [*VELOCITIES, 10, 20, 30])
        self.assertEqual(pattern.get_steps(), STEPS + 3)

    def test_the_steps_from_the_cursor_are_copied_to_the_end(self):
        pattern = pattern_of()
        pattern.repeat_at_end(first=THIRD, last=STEPS - 1)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 2, 3, 4, 5, 6, 7, 8, 3, 4, 5, 6, 7, 8])

    def test_steps_are_copied_before_the_start(self):
        pattern = pattern_of()
        pattern.repeat_at_start(first=0, last=THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 2, 3, 1, 2, 3, 4, 5, 6, 7, 8])
        pattern = pattern_of()
        pattern.repeat_at_start(first=THIRD, last=STEPS - 1)
        self.assertEqual(pattern.get_row(Row.DEGREE), [3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 5, 6, 7, 8])

    def test_a_copy_past_the_most_steps_is_refused(self):
        pattern = pattern_of()
        with self.assertRaises(InvalidValue):
            pattern.take_steps([0] * (limits.MAX_STEPS + 1))
        self.assertEqual(pattern.get_steps(), STEPS)

    def test_a_statement_that_starts_the_pattern_over_never_lands_on_the_first_step(self):
        pattern = pattern_of()
        pattern.set_statement(kind=StepStatement.RESTART, step=THIRD, statement=A_STATEMENT)
        pattern.repeat_at_start(first=THIRD, last=THIRD)
        self.assertIsNone(pattern.get_statement(kind=StepStatement.RESTART, step=0))
        self.assertEqual(pattern.get_statement(kind=StepStatement.RESTART, step=THIRD + 1), A_STATEMENT)

    def test_a_mirror_adds_the_steps_backwards(self):
        pattern = pattern_of(degrees=[1, 2, 3, 4])
        pattern.mirror()
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 2, 3, 4, 4, 3, 2, 1])


class TestRollsAndShuffles(unittest.TestCase):

    def test_a_roll_left_sends_the_first_steps_round_to_the_end(self):
        pattern = pattern_of(**{Row.VELOCITY: VELOCITIES})
        pattern.roll(3)
        self.assertEqual(pattern.get_row(Row.DEGREE), [4, 5, 6, 7, 8, 1, 2, 3])
        self.assertEqual(pattern.get_row(Row.VELOCITY), [40, 50, 60, 70, 80, 10, 20, 30])

    def test_a_roll_right_sends_the_last_steps_round_to_the_start(self):
        pattern = pattern_of()
        pattern.roll(-3)
        self.assertEqual(pattern.get_row(Row.DEGREE), [6, 7, 8, 1, 2, 3, 4, 5])

    def test_a_full_turn_changes_nothing(self):
        pattern = pattern_of()
        pattern.roll(STEPS)
        self.assertEqual(pattern.get_row(Row.DEGREE), DEGREES)

    def test_a_roll_at_a_step_turns_one_side_of_it_by_one_step(self):
        pattern = pattern_of(degrees=[1, 2, 3, 4, 5])
        pattern.roll_through(THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE), [2, 3, 1, 4, 5])
        pattern.roll_from(THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE), [2, 3, 5, 1, 4])
        with self.assertRaises(InvalidValue):
            pattern.roll_from(pattern.get_steps())

    def test_a_shuffle_from_a_step_leaves_the_steps_before_it(self):
        pattern = pattern_of()
        pattern.shuffle_from(THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE)[:THIRD], DEGREES[:THIRD])
        self.assertEqual(sorted(pattern.get_row(Row.DEGREE)[THIRD:]), DEGREES[THIRD:])

    def test_a_shuffle_through_a_step_leaves_the_steps_after_it(self):
        pattern = pattern_of()
        pattern.shuffle_through(THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE)[THIRD + 1:], DEGREES[THIRD + 1:])
        self.assertEqual(sorted(pattern.get_row(Row.DEGREE)[:THIRD + 1]), DEGREES[:THIRD + 1])


class TestInterleaving(unittest.TestCase):

    def test_the_other_pattern_s_steps_go_between_and_are_read_round(self):
        pattern = pattern_of(degrees=[1, 2, 3, 4], **{Row.VELOCITY: [10, 20, 30, 40]})
        other = pattern_of(degrees=OTHER_DEGREES)
        pattern.interleave(other)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 7, 2, 6, 3, 5, 4, 7])
        # A row only one of the two holds is blank on the other's steps.
        self.assertEqual(pattern.get_row(Row.VELOCITY), [10, None, 20, None, 30, None, 40, None])
        self.assertEqual(other.get_row(Row.DEGREE), OTHER_DEGREES)

    def test_a_longer_pattern_gives_only_as_many_steps_as_are_needed(self):
        pattern = pattern_of(degrees=[1, 2])
        pattern.interleave(pattern_of())
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 1, 2, 2])

    def test_a_splice_adds_the_other_pattern_after_the_last_step(self):
        pattern = pattern_of(degrees=[1, 2], **{Row.VELOCITY: [10, 20]})
        other = pattern_of(degrees=OTHER_DEGREES, **{Row.CC1: [1, 2, 3]})
        pattern.splice(other=other)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 2, *OTHER_DEGREES])
        self.assertEqual(pattern.get_row(Row.VELOCITY), [10, 20, None, None, None])
        self.assertEqual(pattern.get_row(Row.CC1), [None, None, 1, 2, 3])
        self.assertEqual(other.get_steps(), len(OTHER_DEGREES))
        with self.assertRaises(InvalidValue):
            pattern.splice(other=pattern_of(degrees=[None], drum=True))
        pattern.splice(other=pattern_of(degrees=[8]), at=0)
        self.assertEqual(pattern.get_row(Row.DEGREE), [8, 1, 2, *OTHER_DEGREES])
        pattern.splice(other=pattern_of(degrees=[4, 4]), at=THIRD)
        self.assertEqual(pattern.get_row(Row.DEGREE), [8, 1, 4, 4, 2, *OTHER_DEGREES])
        with self.assertRaises(InvalidValue):
            pattern.splice(other=pattern_of(degrees=[4]), at=pattern.get_steps() + 1)

    def test_a_drum_pattern_and_a_pattern_of_notes_are_refused(self):
        pattern = pattern_of()
        with self.assertRaises(InvalidValue):
            pattern.interleave(pattern_of(degrees=[None, None], drum=True))
        self.assertEqual(pattern.get_steps(), STEPS)


class TestClearing(unittest.TestCase):

    def test_everything_but_pitch_is_cleared(self):
        pattern = pattern_of(**{Row.VELOCITY: VELOCITIES, Row.GATE: [QUARTER] * STEPS, Row.CHORD: [MAJOR_SEVENTH] * STEPS, Row.OCTAVE: [4] * STEPS, Row.CC1: VELOCITIES, Row.AX_ADD: [1] * STEPS})
        pattern.clear_all_but_pitch()
        self.assertEqual(pattern.get_row(Row.DEGREE), DEGREES)
        self.assertEqual(pattern.get_row(Row.CHORD), [MAJOR_SEVENTH] * STEPS)
        self.assertEqual(pattern.get_row(Row.OCTAVE), [4] * STEPS)
        for row in (Row.VELOCITY, Row.GATE, Row.CC1, Row.AX_ADD):
            with self.subTest(row=row):
                self.assertFalse(any(pattern.get_row(row)))

    def test_chords_are_cleared_and_their_notes_stay(self):
        pattern = pattern_of(**{Row.CHORD: [MAJOR_SEVENTH] * STEPS, Row.INVERSION: [1] * STEPS, Row.VELOCITY: VELOCITIES})
        pattern.clear_chords()
        self.assertFalse(any(pattern.get_row(Row.CHORD)))
        self.assertFalse(any(pattern.get_row(Row.INVERSION)))
        self.assertEqual(pattern.get_row(Row.DEGREE), DEGREES)
        self.assertEqual(pattern.get_row(Row.VELOCITY), VELOCITIES)

    def test_register_changes_are_cleared_and_the_rows_that_use_a_register_stay(self):
        pattern = pattern_of(**{Row.AX_ADD: [1] * STEPS, Row.BX_SET: [5] * STEPS, Row.AX_NOTE: [1] * STEPS})
        pattern.clear_register_changes()
        self.assertFalse(pattern.changes_registers())
        self.assertEqual(pattern.get_row(Row.AX_NOTE), [1] * STEPS)

    def test_statements_are_cleared_and_register_changes_stay(self):
        pattern = pattern_of(**{Row.AX_ADD: [1] * STEPS})
        pattern.set_statement(kind=StepStatement.MUTE, step=THIRD, statement=A_STATEMENT)
        pattern.set_statement(kind=StepStatement.STOP, step=THIRD, statement=A_STATEMENT)
        pattern.clear_statements()
        self.assertFalse(pattern.has_statements(StepStatement.MUTE))
        self.assertFalse(pattern.has_statements(StepStatement.STOP))
        self.assertTrue(pattern.changes_registers())


class TestSmoothing(unittest.TestCase):

    def test_blank_steps_between_two_cc_values_take_a_straight_line(self):
        pattern = pattern_of(**{Row.CC1: [LOW, None, None, None, HIGH, None, 70, None], Row.CC3: [None, 0, None, 1, None, None, None, None]})
        pattern.smooth_ccs()
        # The steps after the last value stay blank, and a value halfway goes up.
        self.assertEqual(pattern.get_row(Row.CC1), [LOW, 40, 60, 80, HIGH, 85, 70, None])
        self.assertEqual(pattern.get_row(Row.CC3), [None, 0, 1, 1, None, None, None, None])
        self.assertIsNone(pattern.get_row(Row.CC2))

    def test_a_velocity_is_smoothed_only_on_steps_that_play(self):
        pattern = pattern_of(degrees=[1, 2, None, 4, 5], **{Row.VELOCITY: [40, None, None, None, 120]})
        pattern.smooth_velocity()
        self.assertEqual(pattern.get_row(Row.VELOCITY), [40, 60, None, 100, 120])

    def test_one_register_s_sets_are_smoothed_and_another_s_are_left(self):
        sets = [0, None, None, None, 8, None, None, None]
        pattern = pattern_of(**{Row.AX_SET: sets, Row.BX_SET: sets})
        pattern.smooth_register_sets(RegisterName.AX)
        self.assertEqual(pattern.get_row(Row.AX_SET)[:FIFTH + 1], [0, 2, 4, 6, 8])
        self.assertEqual(pattern.get_row(Row.BX_SET), sets)


class TestMungesOfNotes(unittest.TestCase):

    def test_steps_next_to_each_other_at_one_pitch_become_one_long_note(self):
        pattern = pattern_of(degrees=[1, 1, 1, 2, None, 2, 2, 3], **{Row.GATE: [HALF_STEP, None, None, None, None, None, None, None], Row.VELOCITY: VELOCITIES})
        pattern.join_repeated_notes()
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, None, None, 2, None, 2, None, 3])
        self.assertEqual(pattern.get_row(Row.TIE), [False, True, True, False, False, False, True, False])
        # The joined note lasts through its ties, and the notes it took in leave nothing of their own.
        self.assertIsNone(pattern.get_value(row=Row.GATE, step=0))
        self.assertEqual(pattern.get_row(Row.VELOCITY), [10, None, None, 40, 50, 60, None, 80])

    def test_notes_an_octave_apart_are_not_joined(self):
        pattern = pattern_of(degrees=[1, 1], **{Row.OCTAVE: [3, 4]})
        pattern.join_repeated_notes()
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 1])

    def test_a_long_note_becomes_a_note_on_every_step_it_covered(self):
        pattern = pattern_of(degrees=[1, None, None, 2, None, None, None, 3], **{Row.TIE: [False, True, True, False, False, False, False, False], Row.GATE: [None, None, None, QUARTER, None, None, None, None], Row.VELOCITY: [10, None, None, 40, None, None, None, 80]})
        pattern.divide_long_notes(step_size=SIXTEENTH)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 1, 1, 2, 2, 2, 2, 3])
        self.assertEqual(pattern.get_row(Row.VELOCITY), [10, 10, 10, 40, 40, 40, 40, 80])
        self.assertFalse(any(pattern.get_row(Row.TIE)))
        self.assertFalse(any(pattern.get_row(Row.GATE)))
        # Joining them again gives the long notes back, as ties.
        pattern.join_repeated_notes()
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, None, None, 2, None, None, None, 3])

    def test_a_random_rhythm_keeps_the_notes_in_order_with_their_ties_and_every_rest(self):
        degrees = [1, None, 2, None, None, 3, None, None]
        ties = [False, True, False, False, False, False, False, False]
        for _ in range(TRIES):
            pattern = pattern_of(degrees=degrees, **{Row.TIE: ties})
            pattern.randomize_rhythm()
            now = pattern.get_row(Row.DEGREE)
            self.assertEqual([degree for degree in now if degree is not None], [1, 2, 3])
            self.assertEqual(len(now), len(degrees))
            self.assertTrue(pattern.get_value(row=Row.TIE, step=now.index(1) + 1))
            self.assertEqual(sum(pattern.get_row(Row.TIE)), 1)

    def test_the_pitches_are_reversed_and_shuffled_on_the_same_rhythm(self):
        pattern = pattern_of(degrees=[1, None, 2, 3], **{Row.OCTAVE: [3, None, 4, 5], Row.VELOCITY: [10, None, 30, 40]})
        pattern.reverse_pitches()
        self.assertEqual(pattern.get_row(Row.DEGREE), [3, None, 2, 1])
        self.assertEqual(pattern.get_row(Row.OCTAVE), [5, None, 4, 3])
        self.assertEqual(pattern.get_row(Row.VELOCITY), [10, None, 30, 40])
        pattern.randomize_pitches()
        self.assertEqual(sorted(degree for degree in pattern.get_row(Row.DEGREE) if degree is not None), [1, 2, 3])
        self.assertIsNone(pattern.get_value(row=Row.DEGREE, step=1))
        self.assertEqual(sorted(zip(pattern.get_row(Row.DEGREE)[2:], pattern.get_row(Row.OCTAVE)[2:]))[0][1] in (3, 4, 5), True)

    def test_every_so_many_steps_is_made_a_rest_and_keeps_what_a_rest_holds(self):
        pattern = pattern_of(**{Row.CC1: VELOCITIES})
        pattern.clear_every(FOURTH)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 2, 3, None, 5, 6, 7, None])
        self.assertEqual(pattern.get_row(Row.CC1), VELOCITIES)
        for wrong in (0, STEPS + 1):
            with self.assertRaises(InvalidValue):
                pattern.clear_every(wrong)

    def test_humanize_moves_each_typed_velocity_within_its_limits_and_leaves_a_blank(self):
        for _ in range(TRIES):
            pattern = pattern_of(degrees=[1, 2, 3, 4], **{Row.VELOCITY: [midi.MIN_VELOCITY, None, HIGH, midi.MAX_VELOCITY]})
            pattern.humanize_velocity(FOURTH)
            low, blank, middle, high = pattern.get_row(Row.VELOCITY)
            self.assertIsNone(blank)
            self.assertTrue(midi.MIN_VELOCITY <= low <= midi.MIN_VELOCITY + FOURTH)
            self.assertTrue(HIGH - FOURTH <= middle <= HIGH + FOURTH)
            self.assertTrue(midi.MAX_VELOCITY - FOURTH <= high <= midi.MAX_VELOCITY)


class TestInvertMelody(unittest.TestCase):

    def test_every_note_is_mirrored_around_the_cursors_note(self):
        pattern = pattern_of(degrees=[1, 2, 3, 5, 3, 2, 1, None])
        pattern.invert_melody(step=THIRD, scale_size=SCALE_SIZE, default_octave=OCTAVE)
        self.assertEqual(pattern.get_row(Row.DEGREE), [5, 4, 3, 1, 3, 4, 5, None])
        self.assertFalse(any(pattern.get_row(Row.OCTAVE) or []))

    def test_a_note_mirrored_under_the_first_degree_is_written_an_octave_lower(self):
        pattern = pattern_of(degrees=[1, 3])
        pattern.invert_melody(step=0, scale_size=SCALE_SIZE, default_octave=OCTAVE)
        self.assertEqual(pattern.get_row(Row.DEGREE), [1, 6])
        self.assertEqual(pattern.get_row(Row.OCTAVE), [None, OCTAVE - 1])

    def test_a_rest_a_drum_pattern_and_an_octave_out_of_range_refuse_it_all(self):
        with self.assertRaises(InvalidValue):
            pattern_of(degrees=[None, 1]).invert_melody(step=0, scale_size=SCALE_SIZE, default_octave=OCTAVE)
        with self.assertRaises(InvalidValue):
            pattern_of(degrees=[None], drum=True).invert_melody(step=0, scale_size=SCALE_SIZE, default_octave=OCTAVE)
        low = pattern_of(degrees=[1, 2, 3])
        with self.assertRaises(InvalidValue):
            low.invert_melody(step=0, scale_size=SCALE_SIZE, default_octave=limits.MIN_OCTAVE)
        self.assertEqual(low.get_row(Row.DEGREE), [1, 2, 3])


class TestVoiceLeading(unittest.TestCase):

    def chords(self, *, degrees, octaves, inversions=None):
        rows = {Row.CHORD: [ChordSymbol.SCALE_TRIAD] * len(degrees), Row.OCTAVE: octaves}
        if inversions:
            rows[Row.INVERSION] = inversions
        return pattern_of(degrees=degrees, **rows)

    def test_a_chord_takes_the_inversion_nearest_the_chord_before_and_the_first_stays(self):
        pattern = self.chords(degrees=[1, 5], octaves=[OCTAVE, OCTAVE - 1], inversions=[None, 3])
        self.assertEqual(pattern.apply_voice_leading(scale=C_MAJOR, default_octave=OCTAVE), 2)
        self.assertEqual(pattern.get_row(Row.INVERSION), [None, 1])
        self.assertEqual(pattern.get_row(Row.OCTAVE), [OCTAVE, OCTAVE - 1])

    def test_an_inversion_is_blanked_where_root_position_is_nearest(self):
        pattern = self.chords(degrees=[1, 1], octaves=[OCTAVE, OCTAVE], inversions=[None, 2])
        pattern.apply_voice_leading(scale=C_MAJOR, default_octave=OCTAVE)
        self.assertFalse(any(pattern.get_row(Row.INVERSION)))

    def test_the_first_chords_inversion_is_what_the_next_is_led_from(self):
        pattern = self.chords(degrees=[5, 1], octaves=[OCTAVE - 1, OCTAVE], inversions=[1, None])
        pattern.apply_voice_leading(scale=C_MAJOR, default_octave=OCTAVE)
        self.assertEqual(pattern.get_row(Row.INVERSION), [1, None])

    def test_with_octaves_a_chord_may_move_an_octave_to_be_nearer(self):
        still = self.chords(degrees=[1, 4], octaves=[OCTAVE, OCTAVE])
        still.apply_voice_leading(scale=C_MAJOR, default_octave=OCTAVE)
        self.assertFalse(any(still.get_row(Row.INVERSION) or []))
        moved = self.chords(degrees=[1, 4], octaves=[OCTAVE, None])
        moved.apply_voice_leading(scale=C_MAJOR, default_octave=OCTAVE, octaves=True)
        self.assertEqual(moved.get_row(Row.INVERSION), [None, 2])
        self.assertEqual(moved.get_row(Row.OCTAVE), [OCTAVE, OCTAVE - 1])

    def test_notes_with_no_chord_are_passed_over(self):
        pattern = pattern_of(degrees=[1, 2, 3])
        self.assertEqual(pattern.apply_voice_leading(scale=C_MAJOR, default_octave=OCTAVE), 0)
        self.assertIsNone(pattern.get_row(Row.INVERSION))
