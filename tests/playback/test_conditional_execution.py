# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Conditional Execution: a scene's and a clip's sets and adds of the registers, and the statements about the registers that bypass generators or make a clip sit out.

Every song here plays one note a pass, moved up C major by AX, so that the notes heard say
what AX was as each pass started, and an AutoRatchet that plays every note twice, so that a
pass with two notes is one the generator ran on.
"""

import unittest

from llamatron.composition import conditions, file_format, limits
from llamatron.composition.file_format import ChainSetting, ClipSlotSetting, GeneratorKind, Operator, PatternSetting, RegisterName, RegisterSetting, RegisterUse, ResetBehavior, Row, ScaleSetting, SceneSetting, Section, SongSetting, StatementPart, TrackSetting
from llamatron.composition.generator_settings import AutoRatchetSetting
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from llamatron.music import midi
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from tests.support.rendering import render_data, setlist_from_data, song_from_data

AX = RegisterName.AX
BX = RegisterName.BX
OCTAVE = 5
ROOT = 60
C_MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
STEP_SIZE = '1/4'
# Names the tests give to their own things.
LEAD = 'lead'
OTHER = 'other'
MAIN = 'main'
X = 'x'
TWICE = 'twice'
DOUBLED = 'doubled'
PARTS_AS_READ = (StatementPart.REGISTER, StatementPart.OPERATOR, StatementPart.VALUE, StatementPart.COMPARISON, StatementPart.AGAINST)
# How many notes the AutoRatchet makes of each note.
RATCHETS = 2
# AX is free to count well past the passes any test plays.
ROOMY = {AX: {RegisterSetting.MAXIMUM: 100}, BX: {RegisterSetting.MAXIMUM: 100}}


def scale_note(value):
    octaves, place = divmod(value, len(C_MAJOR_STEPS))
    return ROOT + octaves * midi.HALF_STEPS_PER_OCTAVE + C_MAJOR_STEPS[place]


def statement(*parts):
    """Return a statement as a file writes it, from its parts in the order they are read aloud: AX, %, 3, =, 0."""
    return dict(zip(PARTS_AS_READ, parts))


def song(*, clip=None, scene=None, track=None, chain=None, generator=None, chained=False, registers=None, other=None):
    """Return a song whose lead plays one note a pass, moved by AX, with what is given added to its clip, scene, track, chain and generator."""
    tracks = {LEAD: dict(track or {})}
    clips = {LEAD: {ClipSlotSetting.PATTERN: X, **(clip or {})}}
    if chained:
        clips[LEAD][ClipSlotSetting.CHAINS] = [DOUBLED]
    if other is not None:
        tracks[OTHER] = {}
        clips[OTHER] = {ClipSlotSetting.PATTERN: X, **other}
    steps = [{GeneratorKind.AUTO_RATCHET: TWICE}]
    return {
        Section.SCALES: {MAIN: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}, SongSetting.SCALE: MAIN,
        Section.PATTERNS: {X: {
            PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: [1], Row.OCTAVE: [OCTAVE], file_format.REGISTER_NOTE_ROWS[AX]: [RegisterUse.ADD],
        }},
        Section.AUTO_RATCHETS: {TWICE: {AutoRatchetSetting.COUNTS: [RATCHETS], **(generator or {})}},
        Section.CHAINS: {DOUBLED: steps if chain is None else {ChainSetting.STEPS: steps, **chain}},
        Section.REGISTERS: registers or ROOMY,
        Section.TRACKS: tracks,
        Section.SCENES: [{**(scene or {}), SceneSetting.TRACKS: clips}],
    }


def heard(data, *, scene=1, track=LEAD):
    """Return the pitch of each note a track plays in a written-out scene, in time order."""
    grid = render_data(data)
    found = grid.get_clip(row=grid.get_rows()[scene - 1], column=[each for each in grid.get_columns() if each.get_name() == track][0])
    return [pitch for _, _, pitch, _ in sorted(timed_events(clip=found, scale=found.get_scale())[0])]


def length_of(data):
    """Return how long the lead's clip lasts in the song's first scene."""
    grid = render_data(data)
    return grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0]).total_length()


def notes_at(values):
    return [scale_note(value) for value in values]


class TestStatements(unittest.TestCase):
    """One statement judged against the registers' values, and what a table refuses."""

    VALUES = {RegisterName.AX: 6, RegisterName.BX: 3, RegisterName.CX: 0, RegisterName.DX: -1}

    def holds(self, *parts):
        return conditions.is_true(statement=statement(*parts), values=self.VALUES)

    def test_each_comparison(self):
        self.assertTrue(self.holds(AX, Operator.LESS, 7))
        self.assertFalse(self.holds(AX, Operator.LESS, 6))
        self.assertTrue(self.holds(AX, Operator.AT_MOST, 6))
        self.assertTrue(self.holds(AX, Operator.SAME, 6))
        self.assertTrue(self.holds(AX, Operator.AT_LEAST, 6))
        self.assertFalse(self.holds(AX, Operator.MORE, 6))
        self.assertTrue(self.holds(AX, Operator.DIFFERENT, 5))

    def test_odd_and_even_below_zero_too(self):
        self.assertTrue(self.holds(AX, Operator.EVEN))
        self.assertFalse(self.holds(AX, Operator.ODD))
        self.assertTrue(self.holds(BX, Operator.ODD))
        self.assertTrue(self.holds(RegisterName.CX, Operator.EVEN))
        self.assertTrue(self.holds(RegisterName.DX, Operator.ODD))

    def test_a_sum_is_worked_out_and_then_compared(self):
        self.assertTrue(self.holds(AX, Operator.REMAINDER, 3, Operator.SAME, 0))
        self.assertTrue(self.holds(AX, Operator.PLUS, 2, Operator.AT_LEAST, 8))
        self.assertTrue(self.holds(AX, Operator.MINUS, 7, Operator.LESS, 0))
        self.assertTrue(self.holds(AX, Operator.TIMES, 2, Operator.MORE, 11))
        self.assertTrue(self.holds(AX, Operator.DIVIDED_BY, 4, Operator.SAME, 1))

    def test_a_division_rounds_down_and_a_remainder_below_zero_counts_from_zero_up(self):
        self.assertTrue(self.holds(RegisterName.DX, Operator.DIVIDED_BY, 2, Operator.SAME, -1))
        self.assertTrue(self.holds(RegisterName.DX, Operator.REMAINDER, 3, Operator.SAME, 2))

    def test_a_register_stands_wherever_a_number_does(self):
        self.assertTrue(self.holds(AX, Operator.MORE, BX))
        self.assertTrue(self.holds(AX, Operator.TIMES, BX, Operator.SAME, 18))
        self.assertTrue(self.holds(AX, Operator.MINUS, BX, Operator.SAME, BX))
        self.assertTrue(self.holds(AX, Operator.REMAINDER, BX, Operator.SAME, RegisterName.CX))

    def test_a_register_that_divides_and_holds_zero_makes_the_statement_true(self):
        self.assertTrue(self.holds(AX, Operator.DIVIDED_BY, RegisterName.CX, Operator.SAME, 99))
        self.assertTrue(self.holds(AX, Operator.REMAINDER, RegisterName.CX, Operator.LESS, 0))

    def test_any_statement_true_makes_the_table_true_and_no_statement_none(self):
        table = [statement(AX, Operator.LESS, 0), statement(BX, Operator.ODD)]
        self.assertTrue(conditions.any_true(statements=table, values=self.VALUES))
        self.assertFalse(conditions.any_true(statements=table[:1], values=self.VALUES))
        self.assertFalse(conditions.any_true(statements=[], values=self.VALUES))

    def refused(self, table):
        with self.assertRaises(InvalidValue):
            conditions.statements_setting(file_format.BYPASS_WHEN).check(table)

    def test_what_a_table_refuses(self):
        self.refused([statement(AX, Operator.DIVIDED_BY, 0, Operator.SAME, 0)])
        self.refused([statement(AX, Operator.REMAINDER, 0, Operator.SAME, 0)])
        self.refused([statement(LEAD, Operator.LESS, 1)])
        self.refused([statement(AX, LEAD, 1)])
        self.refused([statement(AX, Operator.LESS)])
        self.refused([statement(AX, Operator.ODD, 1)])
        self.refused([statement(AX, Operator.LESS, 1, Operator.SAME, 1)])
        self.refused([statement(AX, Operator.PLUS, 1)])
        self.refused([statement(AX, Operator.PLUS, 1, Operator.ODD, 1)])
        self.refused([statement(AX, Operator.LESS, limits.MAX_STATEMENT_NUMBER + 1)])
        self.refused([statement(AX, Operator.ODD)] * (limits.MAX_STATEMENTS + 1))
        self.refused(statement(AX, Operator.ODD))

    def test_a_changed_operator_keeps_what_it_can_and_never_divides_by_zero(self):
        first = conditions.new_statement(AX)
        divided = conditions.with_operator(statement=first, operator=Operator.DIVIDED_BY)
        conditions.check_statement(name=file_format.BYPASS_WHEN, statement=divided)
        self.assertEqual(conditions.parts_of(Operator.EVEN), ())
        parity = conditions.with_operator(statement=divided, operator=Operator.EVEN)
        self.assertEqual(parity, statement(AX, Operator.EVEN))


class TestRegistersSetAndAdded(unittest.TestCase):
    """A scene and a clip set registers once and add to them every time round."""

    def test_a_scene_adds_on_every_play_and_sets_only_as_it_first_starts(self):
        data = song(scene={SceneSetting.REPEAT: 3, SceneSetting.SET_REGISTERS: {AX: 4}, SceneSetting.ADD_REGISTERS: {AX: 1}})
        self.assertEqual([heard(data, scene=number) for number in (1, 2, 3)], [notes_at([5]), notes_at([6]), notes_at([7])])

    def test_a_clip_sets_as_it_launches_and_adds_every_time_its_pattern_starts_over(self):
        data = song(clip={ClipSlotSetting.REPEAT: 3, ClipSlotSetting.SET_REGISTERS: {AX: 2}, ClipSlotSetting.ADD_REGISTERS: {AX: 1}})
        self.assertEqual(heard(data), notes_at([3, 4, 5]))

    def test_the_scene_acts_before_its_clips_and_a_clip_before_any_step(self):
        data = song(
            scene={SceneSetting.SET_REGISTERS: {AX: 10}}, clip={ClipSlotSetting.ADD_REGISTERS: {AX: 1}}, other={ClipSlotSetting.ADD_REGISTERS: {AX: 2}},
        )
        self.assertEqual(heard(data), notes_at([13]))
        self.assertEqual(heard(data, track=OTHER), notes_at([13]))

    def test_an_add_past_the_limit_does_what_the_register_says(self):
        registers = {AX: {RegisterSetting.MAXIMUM: 3, RegisterSetting.RESET_BEHAVIOR: ResetBehavior.OVERFLOW}}
        data = song(clip={ClipSlotSetting.REPEAT: 5, ClipSlotSetting.ADD_REGISTERS: {AX: 1}}, registers=registers)
        self.assertEqual(heard(data), notes_at([1, 2, 3, 0, 1]))

    def test_a_song_with_only_a_scene_or_a_clip_changing_registers_counts_as_changing_them(self):
        self.assertFalse(song_from_data(song()).changes_registers())
        self.assertTrue(song_from_data(song(scene={SceneSetting.ADD_REGISTERS: {AX: 1}})).changes_registers())
        self.assertTrue(song_from_data(song(clip={ClipSlotSetting.SET_REGISTERS: {AX: 1}})).changes_registers())

    def test_what_a_file_refuses(self):
        for wrong in ({LEAD: 1}, {AX: limits.MAX_REGISTER_VALUE + 1}, {AX: None}, [AX]):
            with self.assertRaises(SongFileError):
                setlist_from_data(song(scene={SceneSetting.SET_REGISTERS: wrong}))
            with self.assertRaises(SongFileError):
                setlist_from_data(song(clip={ClipSlotSetting.ADD_REGISTERS: wrong}))


class TestSittingOut(unittest.TestCase):
    """A clip sits a pass out while a statement of its own or its track's holds."""

    COUNTING = {ClipSlotSetting.REPEAT: 4, ClipSlotSetting.ADD_REGISTERS: {AX: 1}}

    def test_a_clip_plays_every_other_pass_and_lasts_as_long(self):
        data = song(clip={**self.COUNTING, ClipSlotSetting.SKIP_WHEN: [statement(AX, Operator.EVEN)]})
        self.assertEqual(heard(data), notes_at([1, 3]))
        self.assertEqual(length_of(data), length_of(song(clip=self.COUNTING)))

    def test_a_track_table_silences_its_clip_and_no_other_track(self):
        data = song(clip=self.COUNTING, track={TrackSetting.SKIP_WHEN: [statement(AX, Operator.MORE, 2)]}, other={ClipSlotSetting.REPEAT: 4})
        self.assertEqual(heard(data), notes_at([1, 2]))
        self.assertEqual(len(heard(data, track=OTHER)), 4)

    def test_a_pass_that_sits_out_still_adds_to_the_registers(self):
        data = song(clip={**self.COUNTING, ClipSlotSetting.SKIP_WHEN: [statement(AX, Operator.SAME, 2)]})
        self.assertEqual(heard(data), notes_at([1, 3, 4]))


class TestBypassingGenerators(unittest.TestCase):
    """A pass goes by a generator, a chain or every chain while a statement holds where it is written."""

    COUNTING = {ClipSlotSetting.REPEAT: 4, ClipSlotSetting.ADD_REGISTERS: {AX: 1}}
    EVERY_PASS_TWICE = [value for value in (1, 2, 3, 4) for _ in range(RATCHETS)]
    ODD_PASSES_ONCE = [1, 2, 2, 3, 4, 4]
    TABLE = [statement(AX, Operator.ODD)]

    def test_the_generator_runs_on_every_pass_with_no_statement(self):
        self.assertEqual(heard(song(clip=self.COUNTING, chained=True)), notes_at(self.EVERY_PASS_TWICE))

    def test_a_statement_on_the_generator(self):
        data = song(clip=self.COUNTING, chained=True, generator={file_format.BYPASS_WHEN: self.TABLE})
        self.assertEqual(heard(data), notes_at(self.ODD_PASSES_ONCE))

    def test_a_statement_on_the_chain(self):
        data = song(clip=self.COUNTING, chained=True, chain={ChainSetting.BYPASS_WHEN: self.TABLE})
        self.assertEqual(heard(data), notes_at(self.ODD_PASSES_ONCE))

    def test_a_statement_on_the_clip_the_scene_and_the_track(self):
        on_clip = song(clip={**self.COUNTING, ClipSlotSetting.BYPASS_WHEN: self.TABLE}, chained=True)
        on_scene = song(clip=self.COUNTING, chained=True, scene={SceneSetting.BYPASS_WHEN: self.TABLE})
        on_track = song(clip=self.COUNTING, chained=True, track={TrackSetting.BYPASS_WHEN: self.TABLE})
        for data in (on_clip, on_scene, on_track):
            self.assertEqual(heard(data), notes_at(self.ODD_PASSES_ONCE))

    def test_a_statement_true_on_every_pass_and_on_none(self):
        always = song(clip=self.COUNTING, chained=True, generator={file_format.BYPASS_WHEN: [statement(AX, Operator.MORE, 0)]})
        never = song(clip=self.COUNTING, chained=True, generator={file_format.BYPASS_WHEN: [statement(AX, Operator.LESS, 0)]})
        self.assertEqual(heard(always), notes_at([1, 2, 3, 4]))
        self.assertEqual(heard(never), notes_at(self.EVERY_PASS_TWICE))

    def test_a_chain_and_a_generator_keep_their_statements_through_a_save(self):
        data = song(chained=True, chain={ChainSetting.BYPASS_WHEN: self.TABLE}, generator={file_format.BYPASS_WHEN: self.TABLE})
        setlist = setlist_from_data(data)
        self.assertEqual(setlist.get_chain(DOUBLED).get_bypass_when(), self.TABLE)
        self.assertEqual(setlist.get_chain(DOUBLED).to_data()[ChainSetting.BYPASS_WHEN], self.TABLE)
        self.assertEqual(setlist.get_generator_settings(kind=GeneratorKind.AUTO_RATCHET, name=TWICE).get_bypass_when(), self.TABLE)
        self.assertIsInstance(setlist_from_data(song(chained=True)).get_chain(DOUBLED).to_data(), list)


if __name__ == '__main__':
    unittest.main()
