# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A step's statements: Stop When, Restart When and Mute When, read as the step is reached, after the step takes its draws.

Stop When ends the clip as if every repeat were played, Restart When starts the pattern over and uses a repeat, and Mute When
silences the step. The tests count with the draw AD, whose slots run 1, 2, 3 and on, taken by a step's Vel+=AD row, which moves
no pitch, so that a step taking it counts one more; before anything takes it, AD reads 0. A scene holding a clip a statement can
cut short is played to find how long it lasts, so these tests cover that path.
"""

import unittest

from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.pattern import Pattern
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import ClipSlotSetting, DrawName, DrawSetting, Operator, RegisterUse, Row, SceneSetting, StatementPart, StepStatement
from tests.support import song_playing
from tests.support.song_playing import pattern, pitches, scale_notes, song

DRIVER = 'driver'
STEPS = 4
FIRST = 0
SECOND = 1
THIRD = 2
LAST = 3
ONE = 1
REPEATS = 5
# The count at which the tests' clips stop.
STOPS_AT = 2
AD = DrawName.AD
# AD's slots: 1, 2, 3 and on, enough for every count a test reaches.
COUNTING = {AD: {DrawSetting.SLOTS: list(range(1, limits.MAX_DRAW_SLOTS + 1))}}
COUNTING_FROM_ZERO = {AD: {DrawSetting.SLOTS: list(range(limits.MAX_DRAW_SLOTS))}}


def comparing(*, operator, value):
    """Return a statement that compares AD with a number."""
    return {StatementPart.REGISTER: AD, StatementPart.OPERATOR: operator, StatementPart.VALUE: value}


def parity(operator):
    return {StatementPart.REGISTER: AD, StatementPart.OPERATOR: operator}


def statements(*, kind, at, steps=STEPS):
    """Return the five rows of a kind of statement for a pattern, holding a statement on each step named in at."""
    rows = {}
    for row, part in zip(file_format.STATEMENT_ROWS[kind], file_format.STATEMENT_PARTS):
        rows[row] = [at[step].get(part) if step in at else None for step in range(steps)]
    return rows


def counts(*, at, steps=STEPS):
    """Return AD's Vel+= row taking AD on the steps named in at, which counts one more on each."""
    return {Row.AD_VELOCITY: [RegisterUse.ADD if step in at else 0 for step in range(steps)]}


def clip_of(*, rows, repeat=REPEATS, loop=False, beside=None, draws=None):
    """Return a song whose lead plays a pattern of four steps with rows, and beside it, when given, a driver's pattern to the lead's left."""
    slot = {ClipSlotSetting.PATTERN: song_playing.X, ClipSlotSetting.REPEAT: repeat}
    if loop:
        slot = {ClipSlotSetting.PATTERN: song_playing.X, ClipSlotSetting.LOOP: True}
    patterns = {song_playing.X: pattern(STEPS, **rows)}
    tracks = {song_playing.LEAD: slot}
    names = (song_playing.LEAD,)
    if beside is not None:
        patterns[song_playing.Y] = beside
        tracks = {DRIVER: {ClipSlotSetting.PATTERN: song_playing.Y}, song_playing.LEAD: slot}
        names = (DRIVER, song_playing.LEAD)
    return song(patterns=patterns, scenes=[{SceneSetting.TRACKS: tracks}], draws=draws or COUNTING, tracks=names)


def read(data):
    """Return the Pattern a file's data makes."""
    return Pattern.from_data(data=data, where=song_playing.X)


class TestMuteWhen(unittest.TestCase):

    def test_a_muted_step_is_silent_and_still_takes_its_draw(self):
        every = {step: parity(Operator.ODD) for step in range(STEPS)}
        rows = {**statements(kind=StepStatement.MUTE, at=every), **counts(at=range(STEPS))}
        # Each step takes 0, 1, 2 and 3 before its mute reads AD, so the second and fourth are muted, and the count goes on.
        data = clip_of(rows=rows, repeat=ONE, draws=COUNTING_FROM_ZERO)
        self.assertEqual(len(pitches(data)), STEPS // 2)

    def test_a_scene_with_only_mutes_plays_as_long_as_it_did(self):
        rows = statements(kind=StepStatement.MUTE, at={SECOND: parity(Operator.EVEN)})
        # Nothing takes AD, which reads 0, so the second step is muted on every pass.
        self.assertEqual(len(pitches(clip_of(rows=rows, repeat=REPEATS))), REPEATS * (STEPS - 1))


class TestStopWhen(unittest.TestCase):

    def stopping(self, *, stop_on, count_on):
        return {**statements(kind=StepStatement.STOP, at={stop_on: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)}), **counts(at=(count_on,))}

    def test_the_clip_is_done_at_the_step_whose_statement_holds(self):
        # The second pass brings AD to 2 on its second step, so its third step stops the clip: four notes and two.
        data = clip_of(rows=self.stopping(stop_on=THIRD, count_on=SECOND))
        self.assertEqual(len(pitches(data)), STEPS + THIRD)

    def test_a_stop_on_the_first_step_ends_the_clip_on_the_edge_of_a_pass(self):
        data = clip_of(rows=self.stopping(stop_on=FIRST, count_on=LAST))
        self.assertEqual(len(pitches(data)), STOPS_AT * STEPS)

    def test_a_stop_true_at_the_clips_first_step_plays_nothing(self):
        rows = statements(kind=StepStatement.STOP, at={FIRST: comparing(operator=Operator.LESS, value=ONE)})
        data = clip_of(rows=rows, beside=pattern(STEPS))
        self.assertEqual(pitches(data), [])
        self.assertEqual(len(pitches(data, track=DRIVER)), STEPS)

    def test_a_stop_that_never_holds_leaves_every_repeat_playing(self):
        rows = statements(kind=StepStatement.STOP, at={THIRD: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)})
        self.assertEqual(len(pitches(clip_of(rows=rows))), REPEATS * STEPS)

    def test_a_stop_reads_the_draw_its_own_step_takes(self):
        # The first step takes 1 and plays on, and takes 2 on the second pass and stops there, its note unplayed.
        rows = self.stopping(stop_on=FIRST, count_on=FIRST)
        self.assertEqual(len(pitches(clip_of(rows=rows))), STEPS)

    def test_a_stop_on_a_draw_that_redraws_counts_the_passes_without_a_step_taking_it(self):
        # Conditions redraw: the third step's Stop When takes AD itself, once a pass, 1, 2: the second pass stops there.
        draws = {AD: {**COUNTING[AD], DrawSetting.CONDITIONS_REDRAW: True}}
        rows = statements(kind=StepStatement.STOP, at={THIRD: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)})
        self.assertEqual(len(pitches(clip_of(rows=rows, loop=True, draws=draws))), STEPS + THIRD)

    def test_a_looping_clip_stops_and_its_scene_then_ends(self):
        data = clip_of(rows=self.stopping(stop_on=THIRD, count_on=SECOND), loop=True)
        self.assertEqual(len(pitches(data)), STEPS + THIRD)

    def test_a_clip_stops_on_what_a_track_to_its_left_takes(self):
        driver = pattern(STEPS, **counts(at=range(STEPS)))
        rows = statements(kind=StepStatement.STOP, at={step: comparing(operator=Operator.AT_LEAST, value=STOPS_AT + 1) for step in range(STEPS)})
        # The driver takes AD on a step before the lead reads it on the same step, so the lead hears two steps and stops on the third.
        data = clip_of(rows=rows, loop=True, beside=driver)
        self.assertEqual(len(pitches(data)), THIRD)
        self.assertEqual(len(pitches(data, track=DRIVER)), STEPS)

    def test_the_song_plays_the_same_every_time(self):
        data = clip_of(rows=self.stopping(stop_on=THIRD, count_on=SECOND), loop=True, beside=pattern(STEPS))
        self.assertEqual(pitches(data), pitches(data))


class TestRestartWhen(unittest.TestCase):

    def restarting(self):
        return {**statements(kind=StepStatement.RESTART, at={THIRD: parity(Operator.ODD)}), **counts(at=(FIRST,))}

    def test_the_pattern_starts_over_and_the_pass_counts_as_a_repeat(self):
        # AD is 1, 2 and 3 through the three passes, so the first and the third are cut at their third step.
        self.assertEqual(len(pitches(clip_of(rows=self.restarting(), repeat=3))), THIRD + STEPS + THIRD)

    def test_a_looping_pattern_runs_on_in_passes_of_uneven_length(self):
        data = clip_of(rows=self.restarting(), loop=True, beside=pattern(STEPS * 3))
        # Twelve steps hold a pass of two, of four, of two, and the first four steps of the next.
        self.assertEqual(len(pitches(data)), STEPS * 3)
        self.assertEqual(len(pitches(data, track=DRIVER)), STEPS * 3)

    def test_a_restart_reads_the_draw_its_own_step_takes(self):
        rows = {**statements(kind=StepStatement.RESTART, at={THIRD: comparing(operator=Operator.LESS, value=STOPS_AT)}), **counts(at=(THIRD,))}
        # The third step takes 1 and starts over, then takes 2 and 3 and plays on: two notes, then four and four.
        self.assertEqual(len(pitches(clip_of(rows=rows, repeat=3))), THIRD + STEPS + STEPS)

    def test_a_stop_is_read_before_a_restart_on_the_same_step(self):
        rows = {
            **statements(kind=StepStatement.RESTART, at={THIRD: parity(Operator.ODD)}),
            **statements(kind=StepStatement.STOP, at={THIRD: parity(Operator.ODD)}), **counts(at=(FIRST,)),
        }
        self.assertEqual(len(pitches(clip_of(rows=rows))), THIRD)


class TestStatementsMoveNotes(unittest.TestCase):

    def test_a_step_that_moves_by_a_draw_and_a_statement_on_it_see_one_value(self):
        rows = {**statements(kind=StepStatement.MUTE, at={FIRST: comparing(operator=Operator.SAME, value=STOPS_AT)}), Row.AD_NOTE: [RegisterUse.ADD, 0, 0, 0]}
        # The first step takes 1, 2 and 3 pass by pass, moving its note by it, and is muted when it took 2.
        firsts = [pitch for place, pitch in enumerate(pitches(clip_of(rows=rows, repeat=3))) if place in (0, STEPS, 2 * STEPS - 1)]
        self.assertEqual(firsts, scale_notes([1, 0, 3]))


class TestStatementsOnAPattern(unittest.TestCase):

    def made(self):
        return read(pattern(STEPS))

    def test_a_statement_is_written_across_its_rows_and_read_back(self):
        made = self.made()
        statement = {StatementPart.REGISTER: AD, StatementPart.OPERATOR: Operator.REMAINDER, StatementPart.VALUE: STEPS, StatementPart.COMPARISON: Operator.SAME, StatementPart.AGAINST: ONE}
        made.set_statement(kind=StepStatement.MUTE, step=SECOND, statement=statement)
        self.assertEqual(made.get_statement(kind=StepStatement.MUTE, step=SECOND), statement)
        self.assertEqual(read(made.to_data()).get_statement(kind=StepStatement.MUTE, step=SECOND), statement)
        self.assertIsNone(made.get_statement(kind=StepStatement.MUTE, step=FIRST))
        self.assertFalse(made.cuts_passes_short())

    def test_a_shorter_statement_leaves_nothing_of_the_longer_one(self):
        made = self.made()
        made.set_statement(kind=StepStatement.STOP, step=SECOND, statement=comparing(operator=Operator.LESS, value=ONE))
        made.set_statement(kind=StepStatement.STOP, step=SECOND, statement=parity(Operator.ODD))
        self.assertEqual(made.get_statement(kind=StepStatement.STOP, step=SECOND), parity(Operator.ODD))
        self.assertTrue(made.cuts_passes_short())
        made.set_statement(kind=StepStatement.STOP, step=SECOND, statement=None)
        self.assertFalse(made.cuts_passes_short())

    def test_the_first_step_cannot_start_the_pattern_over(self):
        with self.assertRaises(InvalidValue):
            self.made().set_statement(kind=StepStatement.RESTART, step=FIRST, statement=parity(Operator.ODD))

    def test_half_a_statement_in_a_file_is_no_statement(self):
        rows = {file_format.STATEMENT_ROWS[StepStatement.MUTE][FIRST]: [AD, None, None, None]}
        self.assertIsNone(read(pattern(STEPS, **rows)).get_statement(kind=StepStatement.MUTE, step=FIRST))

    def test_a_row_refuses_what_is_no_part_of_a_statement(self):
        with self.assertRaises(SongFileError):
            read(pattern(STEPS, **{file_format.STATEMENT_ROWS[StepStatement.MUTE][SECOND]: [DRIVER, None, None, None]}))


class TestAStopThatNeverComes(unittest.TestCase):

    def test_a_looping_clip_gives_up_after_the_most_passes_a_clip_can_repeat(self):
        rows = statements(kind=StepStatement.STOP, at={THIRD: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)})
        self.assertEqual(len(pitches(clip_of(rows=rows, loop=True))), limits.MAX_CLIP_REPEAT * STEPS)


if __name__ == '__main__':
    unittest.main()
