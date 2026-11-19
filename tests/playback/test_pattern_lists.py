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

"""Tests of a clip that plays a list of patterns, laid end to end as one long pattern, and of the order it plays them in.

Three patterns of two quarter notes each: a plays C and D, b plays E and F, and c plays G and A.
"""

import unittest

from llamatron.composition import file_format
from llamatron.composition.file_format import ClipSlotSetting, Direction, Operator, PatternOrder, PatternSetting, RegisterName, Section, StatementPart, StepStatement
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.pattern_order import ordered_patterns
from llamatron.support.random_source import random_source
from tests.support import song_testing
from tests.support.rendering import render_data
from tests.support.song_testing import clip, pat, pitches, with_parts

QUARTER = '1/4'
EIGHTH = '1/8'
A = 'a'
B = 'b'
C = 'c'
HIT = 'hit'
LIST = [A, B, C]
# The MIDI numbers each pattern plays.
PLAYED = {A: [48, 50], B: [52, 53], C: [55, 57]}
SEED = 'a seed'
TRIES = 20
RESTARTS_UNDER = 2


def patterns(**changed):
    made = {A: pat([1, QUARTER], [2, QUARTER]), B: pat([3, QUARTER], [4, QUARTER]), C: pat([5, QUARTER], [6, QUARTER])}
    for name, settings in changed.items():
        made[name] = {**made[name], **settings}
    return made


def played(*, names=None, repeat=1, order=None, direction=None, changed=None, slot=None):
    """Return the MIDI numbers a clip of a list of patterns plays."""
    clip_slot = {ClipSlotSetting.PATTERNS: names or LIST, ClipSlotSetting.REPEAT: repeat, **(slot or {})}
    if order:
        clip_slot[ClipSlotSetting.PATTERN_ORDER] = order
    if direction:
        clip_slot[ClipSlotSetting.DIRECTION] = direction
    data = with_parts(patterns=patterns(**(changed or {})), scenes=[{Section.TRACKS: {song_testing.LEAD: clip_slot}}])
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
        statement = {StatementPart.REGISTER: RegisterName.AX, StatementPart.OPERATOR: Operator.LESS, StatementPart.VALUE: RESTARTS_UNDER}
        rows = {row: [None, statement.get(part)] for row, part in zip(file_format.STATEMENT_ROWS[StepStatement.RESTART], file_format.STATEMENT_PARTS)}
        # The first pattern counts the passes, and the second starts over on its second step while the count is low.
        counted = {file_format.REGISTER_ADD_ROWS[RegisterName.AX]: [1, 0]}
        notes = played(repeat=4, changed={A: counted, B: rows})
        cut = [*PLAYED[A], PLAYED[B][0]]
        self.assertEqual(notes[:len(cut) + len(PLAYED[A])], [*cut, *PLAYED[A]])
        self.assertEqual(notes[-len(notes_of(A, B, C)):], notes_of(A, B, C))


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
