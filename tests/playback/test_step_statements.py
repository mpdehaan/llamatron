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

"""A step's statements about the registers: Stop When, Restart When and Mute When, read as the step is reached, before the step changes anything.

Stop When ends the clip as if every repeat were played, Restart When starts the pattern over and
uses a repeat, and Mute When silences the step, which still changes the registers. A scene that
holds a clip the registers can cut short is played until its registers settle, so these tests
cover that path, and tests/playback/test_registers.py the path every other scene takes.
"""

import unittest

from llamatron.composition import limits
from llamatron.composition import file_format
from llamatron.composition.file_format import ClipSlotSetting, Operator, RegisterSetting, RegisterUse, SceneSetting, StatementPart, StepStatement
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.pattern import Pattern
from llamatron.composition.song_file_error import SongFileError
from tests.playback.test_registers import AX, LEAD, X, Y, pattern, pitches, scale_notes, song

DRIVER = 'driver'
STEPS = 4
FIRST = 0
SECOND = 1
THIRD = 2
LAST = 3
ONE = 1
REPEATS = 5
# The register value at which the tests' clips stop.
STOPS_AT = 2
PAST_THE_STOP = 5
WIDE = {RegisterSetting.MINIMUM: limits.MIN_REGISTER_VALUE, RegisterSetting.MAXIMUM: limits.MAX_REGISTER_VALUE}


def comparing(*, operator, value, register=AX):
    """Return a statement that compares a register with a number."""
    return {StatementPart.REGISTER: register, StatementPart.OPERATOR: operator, StatementPart.VALUE: value}


def parity(operator):
    return {StatementPart.REGISTER: AX, StatementPart.OPERATOR: operator}


def statements(*, kind, at, steps=STEPS):
    """Return the five rows of a kind of statement for a pattern, holding a statement on each step named in at."""
    rows = {}
    for row, part in zip(file_format.STATEMENT_ROWS[kind], file_format.STATEMENT_PARTS):
        rows[row] = [at[step].get(part) if step in at else None for step in range(steps)]
    return rows


def adds(*, at, steps=STEPS, amount=ONE):
    """Return AX's += row adding an amount on one step."""
    return {file_format.REGISTER_ADD_ROWS[AX]: [amount if step == at else 0 for step in range(steps)]}


def clip_of(*, rows, repeat=REPEATS, loop=False, registers=None, beside=None):
    """Return a song whose lead plays a pattern of four steps with rows, and beside it, when given, a driver's pattern to the lead's left."""
    slot = {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat}
    if loop:
        slot = {ClipSlotSetting.PATTERN: X, ClipSlotSetting.LOOP: True}
    patterns = {X: pattern(STEPS, **rows)}
    tracks = {LEAD: slot}
    names = (LEAD,)
    if beside is not None:
        patterns[Y] = beside
        tracks = {DRIVER: {ClipSlotSetting.PATTERN: Y}, LEAD: slot}
        names = (DRIVER, LEAD)
    return song(patterns=patterns, scenes=[{SceneSetting.TRACKS: tracks}], registers=registers, tracks=names)


def read(data):
    """Return the Pattern a file's data makes."""
    return Pattern.from_data(data=data, where=X)


def starting_at(value):
    return {AX: {**WIDE, RegisterSetting.DEFAULT: value}}


class TestMuteWhen(unittest.TestCase):

    def test_a_muted_step_is_silent_and_still_changes_the_registers(self):
        every = {step: parity(Operator.ODD) for step in range(STEPS)}
        rows = {**statements(kind=StepStatement.MUTE, at=every), file_format.REGISTER_ADD_ROWS[AX]: [ONE] * STEPS}
        # AX reads 0, 1, 2, 3 as the steps are reached, since each mute is read before its step adds.
        self.assertEqual(len(pitches(clip_of(rows=rows, repeat=ONE))), STEPS // 2)

    def test_a_statement_is_read_before_the_steps_own_set(self):
        rows = {**statements(kind=StepStatement.MUTE, at={FIRST: comparing(operator=Operator.SAME, value=STOPS_AT)}), file_format.REGISTER_SET_ROWS[AX]: [STOPS_AT, None, None, None]}
        self.assertEqual(len(pitches(clip_of(rows=rows, repeat=ONE))), STEPS)

    def test_a_scene_with_only_mutes_plays_as_long_as_it_did(self):
        rows = statements(kind=StepStatement.MUTE, at={SECOND: parity(Operator.EVEN)})
        self.assertEqual(len(pitches(clip_of(rows=rows, repeat=REPEATS))), REPEATS * (STEPS - 1))


class TestStopWhen(unittest.TestCase):

    def stopping(self, *, stop_on, add_on):
        return {**statements(kind=StepStatement.STOP, at={stop_on: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)}), **adds(at=add_on)}

    def test_the_clip_is_done_at_the_step_whose_statement_holds(self):
        # The second pass brings AX to 2 on its second step, so its third step stops the clip: four notes and two.
        data = clip_of(rows=self.stopping(stop_on=THIRD, add_on=SECOND))
        self.assertEqual(len(pitches(data)), STEPS + THIRD)

    def test_a_stop_on_the_first_step_ends_the_clip_on_the_edge_of_a_pass(self):
        data = clip_of(rows=self.stopping(stop_on=FIRST, add_on=LAST))
        self.assertEqual(len(pitches(data)), STOPS_AT * STEPS)

    def test_a_stop_true_at_the_clips_first_step_plays_nothing(self):
        data = clip_of(rows=self.stopping(stop_on=FIRST, add_on=LAST), registers=starting_at(PAST_THE_STOP), beside=pattern(STEPS))
        self.assertEqual(pitches(data), [])
        self.assertEqual(len(pitches(data, track=DRIVER)), STEPS)

    def test_a_stop_that_never_holds_leaves_every_repeat_playing(self):
        rows = statements(kind=StepStatement.STOP, at={THIRD: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)})
        self.assertEqual(len(pitches(clip_of(rows=rows))), REPEATS * STEPS)

    def test_the_stopping_step_never_makes_its_own_changes(self):
        rows = {**self.stopping(stop_on=FIRST, add_on=FIRST), file_format.REGISTER_NOTE_ROWS[AX]: [RegisterUse.ADD] * STEPS}
        # AX is 1 through the first pass and 2 through the second, and the third pass stops before its first step adds.
        self.assertEqual(pitches(clip_of(rows=rows)), scale_notes([1] * STEPS + [STOPS_AT] * STEPS))

    def test_a_looping_clip_stops_and_its_scene_then_ends(self):
        data = clip_of(rows=self.stopping(stop_on=THIRD, add_on=SECOND), loop=True)
        self.assertEqual(len(pitches(data)), STEPS + THIRD)

    def test_a_clip_stops_on_what_a_track_to_its_left_adds(self):
        driver = pattern(STEPS, **{file_format.REGISTER_ADD_ROWS[AX]: [ONE] * STEPS})
        rows = statements(kind=StepStatement.STOP, at={step: comparing(operator=Operator.AT_LEAST, value=STOPS_AT + 1) for step in range(STEPS)})
        # The driver's add on a step is made before the lead reads on the same step, so the lead hears two steps and stops on the third.
        data = clip_of(rows=rows, loop=True, beside=driver)
        self.assertEqual(len(pitches(data)), THIRD)
        self.assertEqual(len(pitches(data, track=DRIVER)), STEPS)

    def test_the_song_plays_the_same_every_time(self):
        data = clip_of(rows=self.stopping(stop_on=THIRD, add_on=SECOND), loop=True, beside=pattern(STEPS))
        self.assertEqual(pitches(data), pitches(data))


class TestRestartWhen(unittest.TestCase):

    def restarting(self):
        return {**statements(kind=StepStatement.RESTART, at={THIRD: parity(Operator.ODD)}), **adds(at=FIRST)}

    def test_the_pattern_starts_over_and_the_pass_counts_as_a_repeat(self):
        # AX is 1, 2 and 3 through the three passes, so the first and the third are cut at their third step.
        self.assertEqual(len(pitches(clip_of(rows=self.restarting(), repeat=3))), THIRD + STEPS + THIRD)

    def test_a_looping_pattern_runs_on_in_passes_of_uneven_length(self):
        data = clip_of(rows=self.restarting(), loop=True, beside=pattern(STEPS * 3))
        # Twelve steps hold a pass of two, of four, of two, and the first four steps of the next.
        self.assertEqual(len(pitches(data)), STEPS * 3)
        self.assertEqual(len(pitches(data, track=DRIVER)), STEPS * 3)

    def test_the_restarting_step_never_makes_its_own_changes(self):
        rows = {**statements(kind=StepStatement.RESTART, at={THIRD: comparing(operator=Operator.LESS, value=STOPS_AT)}), file_format.REGISTER_ADD_ROWS[AX]: [0, 0, ONE, 0]}
        # The third step would add, and it restarts instead for as long as AX is under 2, which is then for every repeat.
        self.assertEqual(len(pitches(clip_of(rows=rows, repeat=3))), 3 * THIRD)

    def test_a_stop_is_read_before_a_restart_on_the_same_step(self):
        rows = {
            **statements(kind=StepStatement.RESTART, at={THIRD: parity(Operator.ODD)}),
            **statements(kind=StepStatement.STOP, at={THIRD: parity(Operator.ODD)}), **adds(at=FIRST),
        }
        self.assertEqual(len(pitches(clip_of(rows=rows))), THIRD)


class TestStatementsOnAPattern(unittest.TestCase):

    def made(self):
        return read(pattern(STEPS))

    def test_a_statement_is_written_across_its_rows_and_read_back(self):
        made = self.made()
        statement = {StatementPart.REGISTER: AX, StatementPart.OPERATOR: Operator.REMAINDER, StatementPart.VALUE: STEPS, StatementPart.COMPARISON: Operator.SAME, StatementPart.AGAINST: ONE}
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
        rows = {file_format.STATEMENT_ROWS[StepStatement.MUTE][FIRST]: [AX, None, None, None]}
        self.assertIsNone(read(pattern(STEPS, **rows)).get_statement(kind=StepStatement.MUTE, step=FIRST))

    def test_a_row_refuses_what_is_no_part_of_a_statement(self):
        with self.assertRaises(SongFileError):
            read(pattern(STEPS, **{file_format.STATEMENT_ROWS[StepStatement.MUTE][SECOND]: [DRIVER, None, None, None]}))


class TestAStopThatNeverComes(unittest.TestCase):

    def test_a_looping_clip_gives_up_after_the_most_passes_a_clip_can_repeat(self):
        rows = statements(kind=StepStatement.STOP, at={THIRD: comparing(operator=Operator.AT_LEAST, value=STOPS_AT)})
        self.assertEqual(len(pitches(clip_of(rows=rows, loop=True))), limits.MAX_CLIP_REPEAT * STEPS)
