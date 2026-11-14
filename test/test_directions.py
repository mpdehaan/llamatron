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

"""Play directions on patterns and clips."""

import unittest
from fractions import Fraction

from llamatron.composition.clip_slot import morph_style_name
from llamatron.generators.blend import BlendMode
from llamatron.music.note import Note, NoteName, Rest
from rendering import render_data
from llamatron.composition.file_format import ClipSlotSetting, Direction, PatternSetting, Row, Section
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.step_order import StepOrder
from llamatron.support.random_source import random_source
from song_testing import LEAD, X, clip, pat, pitches, with_parts

QUARTER = '1/4'
HALF = '1/2'
SIXTEENTH = '1/16'
KICK = 'kick'
LONG = 'long'
THREE_SIXTEENTHS = '3/16'
Y = 'y'
SIDEWAYS = 'sideways'


class TestPlayDirections(unittest.TestCase):

    NOTES = pat([1, '1/4'], [2, '1/4'], [3, '1/4'])
    # The MIDI numbers of the three notes the pattern plays, C3, D3 and E3.
    C = 48
    D = 50
    E = 52

    def played(self, repeat=2, pattern_direction=None, clip_direction=None, pattern=None, **parts):
        pattern = dict(pattern or self.NOTES)
        if pattern_direction:
            pattern[PatternSetting.DIRECTION] = pattern_direction
        clip_slot = {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat}
        if clip_direction:
            clip_slot[PatternSetting.DIRECTION] = clip_direction
        data = with_parts(patterns={X: pattern}, scenes=[{Section.TRACKS: {LEAD: clip_slot}}], **parts)
        return clip(song=render_data(data), scene=1, track=LEAD)

    def order(self, *arguments, **parts):
        return pitches(self.played(*arguments, **parts))

    def test_forward_is_the_default(self):
        self.assertEqual(self.order(), [self.C, self.D, self.E] * 2)

    def test_reverse_a_starts_on_the_first_step(self):
        self.assertEqual(self.order(pattern_direction=Direction.REVERSE_A), [self.C, self.E, self.D] * 2)

    def test_reverse_b_starts_on_the_last_step(self):
        self.assertEqual(self.order(pattern_direction=Direction.REVERSE_B), [self.E, self.D, self.C] * 2)

    def test_alternate_goes_forward_then_reverse(self):
        self.assertEqual(self.order(pattern_direction=Direction.ALTERNATE), [self.C, self.D, self.E, self.E, self.D, self.C])

    def test_pendulum_does_not_repeat_the_ends(self):
        self.assertEqual(self.order(pattern_direction=Direction.PENDULUM), [self.C, self.D, self.E, self.D, self.C, self.D])

    def test_a_clip_overrides_the_pattern(self):
        self.assertEqual(self.order(pattern_direction=Direction.REVERSE_B, clip_direction=Direction.FORWARD), [self.C, self.D, self.E] * 2)
        self.assertEqual(self.order(pattern_direction=Direction.ALTERNATE, clip_direction=Direction.REVERSE_B), [self.E, self.D, self.C] * 2)

    def test_chosen_directions_are_the_same_every_render_with_a_seed(self):
        for direction in [Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY]:
            with self.subTest(direction=direction):
                self.assertEqual(self.order(8, direction, seed=1), self.order(8, direction, seed=1))

    def test_chosen_directions_are_a_new_take_each_render_without_a_seed(self):
        for direction in [Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY]:
            with self.subTest(direction=direction):
                self.assertNotEqual(self.order(20, direction), self.order(20, direction))

    def test_chosen_directions_change_with_the_seed(self):
        for direction in [Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY]:
            with self.subTest(direction=direction):
                self.assertNotEqual(self.order(20, direction, seed=1), self.order(20, direction, seed=2))

    def test_chosen_directions_do_not_change_what_probability_rolls(self):
        rows = {Row.PROBABILITY: [50] * 40}
        steps = pat(*[[1, SIXTEENTH]] * 40, **rows)
        plain = [isinstance(n, Note) for n in self.played(1, pattern=steps, seed=1).get_notes()]
        moved = [isinstance(n, Note) for n in self.played(1, Direction.RANDOM, pattern=steps, seed=1).get_notes()]
        self.assertEqual(plain, moved)

    def test_brownian_only_moves_one_step_at_a_time(self):
        found = self.order(40, Direction.BROWNIAN)
        places = [[self.C, self.D, self.E].index(pitch) for pitch in found]
        for before, after in zip(places, places[1:]):
            self.assertIn((after - before) % 3, (0, 1, 2))
        self.assertEqual(places[0], 0)

    def test_eitherway_always_moves(self):
        found = self.order(20, Direction.EITHERWAY)
        for before, after in zip(found, found[1:]):
            self.assertNotEqual(before, after)

    def test_a_pass_always_lasts_as_long_as_the_pattern(self):
        uneven = pat([1, HALF], [2, SIXTEENTH], [3, THREE_SIXTEENTHS])
        for direction in [Direction.FORWARD, Direction.REVERSE_A, Direction.REVERSE_B, Direction.ALTERNATE, Direction.PENDULUM, Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY]:
            with self.subTest(direction=direction):
                self.assertEqual(self.played(5, direction, pattern=uneven).total_length(), Fraction(15, 4))

    def test_a_looping_clip_carries_on_in_its_direction(self):
        data = with_parts(
            patterns={X: {**self.NOTES, PatternSetting.DIRECTION: Direction.ALTERNATE}, LONG: pat([1, 2])},
            scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.LOOP: True}, KICK: {ClipSlotSetting.PATTERN: LONG}}}],
        )
        found = clip(song=render_data(data), scene=1, track=LEAD)
        self.assertEqual(pitches(found)[:6], [self.C, self.D, self.E, self.E, self.D, self.C])

    def test_rests_play_in_order_too(self):
        steps = pat([1, QUARTER], [None, QUARTER], [3, QUARTER])
        found = self.played(1, Direction.REVERSE_B, pattern=steps)
        self.assertEqual(found.get_notes(), [Note(name=NoteName.E, octave_number=4, length=Fraction(1, 4)), Rest(Fraction(1, 4)), Note(name=NoteName.C, octave_number=4, length=Fraction(1, 4))])

    def test_a_morph_target_uses_its_own_direction_and_not_the_clips(self):
        data = with_parts(
            patterns={X: pat([1, HALF], [3, HALF]), Y: {**pat([5, HALF], [6, HALF]), PatternSetting.DIRECTION: Direction.REVERSE_B}},
            scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.DIRECTION: Direction.REVERSE_B, ClipSlotSetting.MORPH_TO: Y, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}}}],
        )
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [52, 48, 57, 55])

    def test_bad_directions_are_refused(self):
        with self.assertRaises(SongFileError):
            self.played(pattern_direction=SIDEWAYS)
        with self.assertRaises(SongFileError):
            self.played(clip_direction=SIDEWAYS)


class TestStepOrder(unittest.TestCase):
    """A pass asks the StepOrder for all of its steps at once, and the next pass carries on from where that one stopped."""

    COUNT = 4
    PASSES = 3
    SEED = 7
    KEY = (X,)
    OTHER_KEY = (Y,)

    def passes(self, direction):
        order = StepOrder(random_source(self.SEED))
        return [order.next_steps(key=self.KEY, count=self.COUNT, direction=direction) for _ in range(self.PASSES)]

    def test_a_direction_that_repeats_carries_on_from_pass_to_pass(self):
        self.assertEqual(self.passes(Direction.FORWARD), [[0, 1, 2, 3]] * self.PASSES)
        self.assertEqual(self.passes(Direction.REVERSE_A), [[0, 3, 2, 1]] * self.PASSES)
        self.assertEqual(self.passes(Direction.REVERSE_B), [[3, 2, 1, 0]] * self.PASSES)
        self.assertEqual(self.passes(Direction.ALTERNATE), [[0, 1, 2, 3], [3, 2, 1, 0], [0, 1, 2, 3]])
        # Pendulum's walk is 0 1 2 3 2 1, which is not a whole number of passes long.
        self.assertEqual(self.passes(Direction.PENDULUM), [[0, 1, 2, 3], [2, 1, 0, 1], [2, 3, 2, 1]])

    def test_each_list_of_steps_and_each_direction_keeps_a_place_of_its_own(self):
        order = StepOrder(random_source(self.SEED))
        self.assertEqual(order.next_steps(key=self.KEY, count=self.COUNT, direction=Direction.ALTERNATE), [0, 1, 2, 3])
        self.assertEqual(order.next_steps(key=self.OTHER_KEY, count=self.COUNT, direction=Direction.ALTERNATE), [0, 1, 2, 3])
        self.assertEqual(order.next_steps(key=self.KEY, count=self.COUNT, direction=Direction.PENDULUM), [0, 1, 2, 3])
        self.assertEqual(order.next_steps(key=self.KEY, count=self.COUNT, direction=Direction.ALTERNATE), [3, 2, 1, 0])

    def test_random_makes_one_choice_for_each_step_of_the_pass(self):
        choices = random_source(self.SEED)
        expected = [[choices.randrange(self.COUNT) for _ in range(self.COUNT)] for _ in range(self.PASSES)]
        self.assertEqual(self.passes(Direction.RANDOM), expected)

    def test_a_direction_that_chooses_starts_on_the_first_step_and_moves_one_step_at_a_time_across_passes(self):
        for direction in (Direction.BROWNIAN, Direction.EITHERWAY):
            with self.subTest(direction=direction):
                steps = [step for one_pass in self.passes(direction) for step in one_pass]
                self.assertEqual(len(steps), self.COUNT * self.PASSES)
                self.assertEqual(steps[0], 0)
                for before, after in zip(steps, steps[1:]):
                    self.assertIn((after - before) % self.COUNT, (0, 1, self.COUNT - 1))
                self.assertEqual(self.passes(direction), self.passes(direction))
