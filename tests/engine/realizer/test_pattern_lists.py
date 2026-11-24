# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a clip that plays a list of patterns, laid end to end as one long pattern, and of the order it plays them in.

Three patterns of two quarter notes each: a plays C and D, b plays E and F, and c plays G and A.
"""

import unittest

from llamatron.engine.realizer.pattern_order import ordered_patterns
from llamatron.engine.timing.timing import timed_events
from llamatron.math.random_source import random_source
from llamatron.math.rational import Rational
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting, Direction, DrawName, DrawSetting, Operator, PatternOrder, PatternSetting, RegisterUse, Row, Section, StatementPart, StepStatement
from tests.support import song_testing
from tests.support.rendering import render_data
from tests.support.song_testing import clip, pat, pitches, with_parts

QUARTER = '1/4'
EIGHTH = '1/8'
A = 'a'
B = 'b'
C = 'c'
HIT = 'hit'
TIES = 'ties'
LIST = [A, B, C]
# The MIDI numbers each pattern plays.
PLAYED = {A: [48, 50], B: [52, 53], C: [55, 57]}
SEED = 'a seed'
TRIES = 20
RESTARTS_UNDER = 2
# The slots of the draw that counts the passes.
COUNTING = [1, 2, 3, 4, 5, 6, 7, 8]


def patterns(**changed):
    made = {A: pat([1, QUARTER], [2, QUARTER]), B: pat([3, QUARTER], [4, QUARTER]), C: pat([5, QUARTER], [6, QUARTER])}
    for name, settings in changed.items():
        made[name] = {**made[name], **settings}
    return made


def played(*, names=None, repeat=1, order=None, direction=None, changed=None, slot=None, draws=None):
    """Return the MIDI numbers a clip of a list of patterns plays."""
    clip_slot = {ClipSlotSetting.PATTERNS: names or LIST, ClipSlotSetting.REPEAT: repeat, **(slot or {})}
    if order:
        clip_slot[ClipSlotSetting.PATTERN_ORDER] = order
    if direction:
        clip_slot[ClipSlotSetting.DIRECTION] = direction
    data = with_parts(patterns=patterns(**(changed or {})), scenes=[{Section.TRACKS: {song_testing.LEAD: clip_slot}}])
    if draws:
        data[Section.DRAWS] = draws
    return pitches(clip(song=render_data(data), scene=1, track=song_testing.LEAD))


def notes_of(*names):
    return [pitch for name in names for pitch in PLAYED[name]]


class TestAClipOfSeveralPatterns(unittest.TestCase):

    def test_the_patterns_play_one_after_another_and_the_list_repeats_whole(self):
        self.assertEqual(played(), notes_of(A, B, C))
        self.assertEqual(played(repeat=2), notes_of(A, B, C, A, B, C))

    def test_a_pattern_may_be_in_the_list_more_than_once(self):
        self.assertEqual(played(names=[A, B, A, C]), notes_of(A, B, A, C))

    def test_a_list_of_one_plays_as_one_pattern_does(self):
        self.assertEqual(played(names=[B], repeat=2), notes_of(B, B))

    def test_each_pattern_plays_in_its_own_direction_inside(self):
        self.assertEqual(played(changed={B: {PatternSetting.DIRECTION: Direction.REVERSE_B}}), [*PLAYED[A], *reversed(PLAYED[B]), *PLAYED[C]])

    def test_the_clips_direction_is_the_direction_of_the_steps_of_every_pattern(self):
        self.assertEqual(played(direction=Direction.REVERSE_B), [*reversed(PLAYED[A]), *reversed(PLAYED[B]), *reversed(PLAYED[C])])

    def test_each_pattern_keeps_its_own_step_size(self):
        short = {B: {**pat([3, EIGHTH], [4, EIGHTH]), PatternSetting.STEP_SIZE: EIGHTH}}
        data = with_parts(patterns={**patterns(), **short}, scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERNS: LIST}}}])
        a_clip = clip(song=render_data(data), scene=1, track=song_testing.LEAD)
        self.assertEqual(pitches(a_clip), notes_of(A, B, C))
        whole = clip(song=render_data(with_parts(patterns=patterns(), scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERNS: LIST}}}])), scene=1, track=song_testing.LEAD)
        self.assertLess(a_clip.total_length(), whole.total_length())

    def test_a_drum_pattern_and_a_pattern_of_notes_cannot_share_a_list(self):
        made = {**patterns(), HIT: pat([C.upper(), QUARTER], drum=True)}
        with self.assertRaises(SongFileError):
            render_data(with_parts(patterns=made, scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERNS: [A, HIT]}}}]))

    def test_a_step_that_starts_the_pattern_over_starts_the_whole_list_over(self):
        statement = {StatementPart.REGISTER: DrawName.AD, StatementPart.OPERATOR: Operator.LESS, StatementPart.VALUE: RESTARTS_UNDER}
        rows = {row: [None, statement.get(part)] for row, part in zip(file_format.STATEMENT_ROWS[StepStatement.RESTART], file_format.STATEMENT_PARTS)}
        # The first pattern counts the passes, taking AD's next slot, 1, 2 and on, and the second starts over on its second step
        # while the count is low.
        counted = {Row.AD_VELOCITY: [RegisterUse.ADD, 0]}
        notes = played(repeat=4, changed={A: counted, B: rows}, draws={DrawName.AD: {DrawSetting.SLOTS: COUNTING}})
        cut = [*PLAYED[A], PLAYED[B][0]]
        self.assertEqual(notes[:len(cut) + len(PLAYED[A])], [*cut, *PLAYED[A]])
        self.assertEqual(notes[-len(notes_of(A, B, C)):], notes_of(A, B, C))

    def test_a_note_tied_on_through_patterns_of_ties_alone_lasts_through_them_all(self):
        # A chord of four quarter steps held by ties, two patterns of ties alone, and a pattern whose ties end it before a note.
        held = {PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: QUARTER, Row.DEGREE: [1, None, None, None], Row.CHORD: [file_format.ChordSymbol.MAJOR, None, None, None], Row.TIE: [False, True, True, True]}
        ties = {PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: QUARTER, Row.TIE: [True, True, True, True]}
        ending = {PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: QUARTER, Row.DEGREE: [None, None, 3, None], Row.TIE: [True, True, False, False]}
        made = {A: held, TIES: ties, B: ending}
        data = with_parts(patterns=made, scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERNS: [A, TIES, TIES, B]}}}])
        a_clip = clip(song=render_data(data), scene=1, track=song_testing.LEAD)
        events = sorted(timed_events(clip=a_clip, scale=a_clip.get_scale())[0])
        held_quarters = 4 + 4 + 4 + 2
        self.assertEqual({event.end for event in events[:-1]}, {Rational(held_quarters, 4)})
        self.assertEqual(events[-1].start, Rational(held_quarters, 4))


class TestPatternOrder(unittest.TestCase):

    def test_forward_is_the_default_and_every_order_plays_every_pattern_once_a_pass(self):
        self.assertEqual(played(repeat=2, order=PatternOrder.FORWARD), played(repeat=2))
        for order in file_format.PATTERN_ORDERS:
            for place in range(TRIES):
                with self.subTest(order=order, place=place):
                    self.assertEqual(sorted(ordered_patterns(names=LIST, order=order, place=place, rolls=random_source(place))), LIST)

    def test_the_reverses(self):
        self.assertEqual(played(repeat=2, order=PatternOrder.REVERSE_B), notes_of(C, B, A, C, B, A))
        self.assertEqual(played(repeat=2, order=PatternOrder.REVERSE_A), notes_of(A, C, B, A, C, B))

    def test_alternate_goes_forward_then_backward(self):
        self.assertEqual(played(repeat=3, order=PatternOrder.ALTERNATE), notes_of(A, B, C, C, B, A, A, B, C))

    def test_pendulum_comes_back_from_the_pattern_before_the_last_and_ends_on_the_last(self):
        self.assertEqual(played(repeat=3, order=PatternOrder.PENDULUM), notes_of(A, B, C, B, A, C, A, B, C))

    def test_random_draws_each_pass_again_and_first_then_random_starts_on_the_first(self):
        orders = set()
        for seed in range(TRIES):
            drawn = ordered_patterns(names=LIST, order=PatternOrder.RANDOM, place=0, rolls=random_source(seed))
            orders.add(tuple(drawn))
            first = ordered_patterns(names=LIST, order=PatternOrder.FIRST_THEN_RANDOM, place=seed, rolls=random_source(seed))
            self.assertEqual(first[0], A)
        self.assertGreater(len(orders), 1)

    def test_a_list_of_one_is_the_same_in_every_order(self):
        for order in file_format.PATTERN_ORDERS:
            self.assertEqual(played(names=[A], repeat=2, order=order), notes_of(A, A))

    def test_a_file_refuses_an_order_that_is_not_one(self):
        with self.assertRaises(SongFileError):
            played(order=SEED)
