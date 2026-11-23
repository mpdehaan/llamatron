# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Conditional Execution: a scene's and a clip's sets and adds of the registers, and the statements about the registers that bypass generators or make a clip sit out.

Every song here plays one note a pass, moved up C major by AX, so that the notes heard say
what AX was as each pass started, and a Chords generator that moves every note to chord II, one
note of the scale higher, so that a pass a note higher is one the generator ran on.
"""

import unittest

from llamatron.engine.generators import chords as chords_plugin
from llamatron.engine.generators.chords import model as chords_model
from llamatron.engine.generators.chords.model import ChordsSetting, ProgressionSetting
from llamatron.engine.timing.timing import timed_events
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects import conditions
from llamatron.model.objects.named_scale import scale_type_name
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import ChainSetting, ClipSlotSetting, Operator, PatternSetting, RegisterName, RegisterSetting, RegisterUse, Row, ScaleSetting, SceneSetting, Section, SongSetting, StatementPart, TrackSetting
from llamatron.model.values import midi
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType
from tests.support.rendering import render_data, setlist_from_data

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
# The other track's pattern: one note a pass, changing nothing.
PLAIN = 'plain'
TWICE = 'up'
DOUBLED = 'moved'
PARTS_AS_READ = (StatementPart.REGISTER, StatementPart.OPERATOR, StatementPart.VALUE, StatementPart.COMPARISON, StatementPart.AGAINST)
# How many notes of the scale the Chords generator moves each note up: chord II is one above chord I.
MOVED_BY = 1
CHORD_II = 2
# AX is free to count well past the passes any test plays.
ROOMY = {AX: {RegisterSetting.MAXIMUM: 100}, BX: {RegisterSetting.MAXIMUM: 100}}
# A pattern's step that adds 1 to AX, and AX starting at 1, so that the passes start with AX 1, 2, 3 and 4 and their notes, moved
# after the add, are a note higher.
COUNTING_ROW = {file_format.REGISTER_ADD_ROWS[AX]: [1]}
COUNTING_REGISTERS = {AX: {RegisterSetting.MAXIMUM: 100, RegisterSetting.DEFAULT: 1}, BX: {RegisterSetting.MAXIMUM: 100}}


def scale_note(value):
    octaves, place = divmod(value, len(C_MAJOR_STEPS))
    return ROOT + octaves * midi.HALF_STEPS_PER_OCTAVE + C_MAJOR_STEPS[place]


def statement(*parts):
    """Return a statement as a file writes it, from its parts in the order they are read aloud: AX, %, 3, =, 0."""
    return dict(zip(PARTS_AS_READ, parts))


def song(*, clip=None, scene=None, track=None, chain=None, generator=None, chained=False, registers=None, other=None, counting=False):
    """Return a song whose lead plays one note a pass, moved by AX, with what is given added to its clip, scene, track, chain and
    generator; counting, AX starts at 1 and the note's step adds 1 to it, so that each pass starts with AX one more than the last."""
    tracks = {LEAD: dict(track or {})}
    clips = {LEAD: {ClipSlotSetting.PATTERN: X, **(clip or {})}}
    if chained:
        clips[LEAD][ClipSlotSetting.CHAINS] = [DOUBLED]
    if other is not None:
        tracks[OTHER] = {}
        clips[OTHER] = {ClipSlotSetting.PATTERN: PLAIN, **other}
    steps = [{chords_plugin.NAME: TWICE}]
    return {
        Section.SCALES: {MAIN: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.MAJOR)}}, SongSetting.SCALE: MAIN,
        Section.PATTERNS: {X: {
            PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: [1], Row.OCTAVE: [OCTAVE], file_format.REGISTER_NOTE_ROWS[AX]: [RegisterUse.ADD],
            **(COUNTING_ROW if counting else {}),
        }, PLAIN: {
            PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: STEP_SIZE, Row.DEGREE: [1], Row.OCTAVE: [OCTAVE],
        }},
        chords_plugin.SECTION: {TWICE: {ChordsSetting.MODE: chords_model.PROGRESSION, ProgressionSetting.CHORDS: [CHORD_II], **(generator or {})}},
        Section.CHAINS: {DOUBLED: steps if chain is None else {ChainSetting.STEPS: steps, **chain}},
        Section.REGISTERS: registers or (COUNTING_REGISTERS if counting else ROOMY),
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


class TestSittingOut(unittest.TestCase):
    """A clip sits a pass out while a statement of its own or its track's holds."""

    COUNTING = {ClipSlotSetting.REPEAT: 4}

    def test_a_clip_plays_every_other_pass_and_lasts_as_long(self):
        data = song(clip={**self.COUNTING, ClipSlotSetting.SKIP_WHEN: [statement(AX, Operator.EVEN)]}, counting=True)
        self.assertEqual(heard(data), notes_at([2, 4]))
        self.assertEqual(length_of(data), length_of(song(clip=self.COUNTING, counting=True)))

    def test_a_track_table_silences_its_clip_and_no_other_track(self):
        data = song(clip=self.COUNTING, track={TrackSetting.SKIP_WHEN: [statement(AX, Operator.MORE, 2)]}, other={ClipSlotSetting.REPEAT: 4}, counting=True)
        self.assertEqual(heard(data), notes_at([2, 3]))
        self.assertEqual(len(heard(data, track=OTHER)), 4)

    def test_a_pass_that_sits_out_still_adds_to_the_registers(self):
        data = song(clip={**self.COUNTING, ClipSlotSetting.SKIP_WHEN: [statement(AX, Operator.SAME, 2)]}, counting=True)
        self.assertEqual(heard(data), notes_at([2, 4, 5]))


class TestBypassingGenerators(unittest.TestCase):
    """A pass goes by a generator, a chain or every chain while a statement holds where it is written."""

    COUNTING = {ClipSlotSetting.REPEAT: 4}
    EVERY_PASS_MOVED = [value + MOVED_BY for value in (2, 3, 4, 5)]
    # AX is odd as the first and third passes start, which go by the generator, and even as the others start, which it moves.
    ODD_PASSES_UNMOVED = [2, 3 + MOVED_BY, 4, 5 + MOVED_BY]
    TABLE = [statement(AX, Operator.ODD)]

    def test_the_generator_runs_on_every_pass_with_no_statement(self):
        self.assertEqual(heard(song(clip=self.COUNTING, chained=True, counting=True)), notes_at(self.EVERY_PASS_MOVED))

    def test_a_statement_on_the_generator(self):
        data = song(clip=self.COUNTING, chained=True, counting=True, generator={file_format.BYPASS_WHEN: self.TABLE})
        self.assertEqual(heard(data), notes_at(self.ODD_PASSES_UNMOVED))

    def test_a_statement_on_the_chain(self):
        data = song(clip=self.COUNTING, chained=True, counting=True, chain={ChainSetting.BYPASS_WHEN: self.TABLE})
        self.assertEqual(heard(data), notes_at(self.ODD_PASSES_UNMOVED))

    def test_a_statement_on_the_clip_the_scene_and_the_track(self):
        on_clip = song(clip={**self.COUNTING, ClipSlotSetting.BYPASS_WHEN: self.TABLE}, chained=True, counting=True)
        on_scene = song(clip=self.COUNTING, chained=True, counting=True, scene={SceneSetting.BYPASS_WHEN: self.TABLE})
        on_track = song(clip=self.COUNTING, chained=True, counting=True, track={TrackSetting.BYPASS_WHEN: self.TABLE})
        for data in (on_clip, on_scene, on_track):
            self.assertEqual(heard(data), notes_at(self.ODD_PASSES_UNMOVED))

    def test_a_statement_true_on_every_pass_and_on_none(self):
        always = song(clip=self.COUNTING, chained=True, counting=True, generator={file_format.BYPASS_WHEN: [statement(AX, Operator.MORE, 0)]})
        never = song(clip=self.COUNTING, chained=True, counting=True, generator={file_format.BYPASS_WHEN: [statement(AX, Operator.LESS, 0)]})
        self.assertEqual(heard(always), notes_at([2, 3, 4, 5]))
        self.assertEqual(heard(never), notes_at(self.EVERY_PASS_MOVED))

    def test_a_chain_and_a_generator_keep_their_statements_through_a_save(self):
        data = song(chained=True, chain={ChainSetting.BYPASS_WHEN: self.TABLE}, generator={file_format.BYPASS_WHEN: self.TABLE})
        setlist = setlist_from_data(data)
        self.assertEqual(setlist.get_chain(DOUBLED).get_bypass_when(), self.TABLE)
        self.assertEqual(setlist.get_chain(DOUBLED).to_data()[ChainSetting.BYPASS_WHEN], self.TABLE)
        self.assertEqual(setlist.get_generator_settings(kind=chords_plugin.NAME, name=TWICE).get_bypass_when(), self.TABLE)
        self.assertIsInstance(setlist_from_data(song(chained=True)).get_chain(DOUBLED).to_data(), list)



class TestASwitchedOffGenerator(unittest.TestCase):
    """A generator whose Enabled is off is passed over wherever a chain or a list of generators names it, and only off is written."""

    OFF = {file_format.GENERATOR_ENABLED: False}
    UNMOVED = [0]
    MOVED = [MOVED_BY]

    def test_a_chain_passes_it_over(self):
        self.assertEqual(heard(song(chained=True)), notes_at(self.MOVED))
        self.assertEqual(heard(song(chained=True, generator=self.OFF)), notes_at(self.UNMOVED))

    def test_a_clips_list_naming_it_alone_passes_it_over(self):
        self.assertEqual(heard(song(clip={ClipSlotSetting.CHAINS: [TWICE]})), notes_at(self.MOVED))
        self.assertEqual(heard(song(clip={ClipSlotSetting.CHAINS: [TWICE]}, generator=self.OFF)), notes_at(self.UNMOVED))

    def test_only_off_is_written(self):
        setlist = setlist_from_data(song(chained=True))
        settings = setlist.get_generator_settings(kind=chords_plugin.NAME, name=TWICE)
        self.assertTrue(settings.is_enabled())
        settings.set_written(name=file_format.GENERATOR_ENABLED, value=False)
        self.assertFalse(settings.is_enabled())
        self.assertIs(settings.to_data()[file_format.GENERATOR_ENABLED], False)
        with self.assertRaises(InvalidValue):
            settings.set_written(name=file_format.GENERATOR_ENABLED, value=OCTAVE)


if __name__ == '__main__':
    unittest.main()
