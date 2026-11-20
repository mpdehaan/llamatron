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

"""The draws as a song plays: each direction, blank slots passed over, a value added or subtracted on the note or the velocity,
a step's and a scene's resets, and every track drawing from one draw in track order."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, Direction, DrawDirection, DrawName, DrawSetting, Operator, PatternSetting, RegisterName, RegisterUse, Row, ScaleSetting, SceneSetting, Section, SongSetting, StatementPart
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.realtime.score import Score
from llamatron.strings import errors
from tests.support import song_testing
from tests.support.rendering import render_data, song_from_data
from tests.support.song_testing import clip

CHROMATIC = 'chromatic'
TUNE = 'tune'
LEAD = song_testing.LEAD
OTHER = 'other'
# The pitch a step written as degree 1 plays in C chromatic, before anything is added.
MIDDLE_C = 60
STEPS = 4
ONE = 1
QUIET = 60
COUNT_IN = [0, 1, 2, 3]
TWELVE_TONES = list(range(12))
BEATS_A_MINUTE = 60
HALF_A_SECOND = 0.5
QUARTER = '1/4'


def song_data(*, draws, rows, repeat=1, steps=STEPS, scenes=None, tracks=(LEAD,)):
    """Return a song in C chromatic whose one pattern of steps, each written as degree 1, carries the rows given."""
    pattern = {PatternSetting.STEPS: steps, Row.DEGREE: [ONE] * steps, **rows}
    played = {track: {ClipSlotSetting.PATTERN: TUNE} for track in tracks}
    return {
        Section.SCALES: {CHROMATIC: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: scale_type_name(ScaleType.CHROMATIC)}}, SongSetting.SCALE: CHROMATIC,
        Section.DRAWS: draws, Section.PATTERNS: {TUNE: pattern}, Section.TRACKS: {track: {} for track in tracks},
        Section.SCENES: scenes or [{SceneSetting.REPEAT: repeat, SceneSetting.TRACKS: played}],
    }


def heard(*, song, scene, track=LEAD):
    """Return the pitch and velocity of every note a track's clip plays in a scene, in time order."""
    played = clip(song=song, scene=scene, track=track)
    return [(pitch, velocity) for _, _, pitch, velocity in sorted(timed_events(clip=played, scale=played.get_scale())[0])]


def pitches_of(*, song, scenes, track=LEAD):
    """Return each scene's pitches, a list a scene."""
    return [[pitch for pitch, _ in heard(song=song, scene=scene, track=track)] for scene in range(1, scenes + 1)]


def every_step(*, use=RegisterUse.ADD, steps=STEPS):
    return [use] * steps


def a_draw(*, slots, direction=None):
    return {DrawSetting.SLOTS: slots, **({DrawSetting.DIRECTION: direction} if direction else {})}


class TestDirections(unittest.TestCase):

    def test_a_forward_draw_on_the_first_step_counts_in_one_pass_after_another(self):
        song = render_data(song_data(draws={DrawName.DD: a_draw(slots=COUNT_IN)}, rows={Row.DD_NOTE: [RegisterUse.ADD, 0, 0, 0]}, repeat=len(COUNT_IN)))
        firsts = [scene[0] for scene in pitches_of(song=song, scenes=len(COUNT_IN))]
        self.assertEqual(firsts, [MIDDLE_C + value for value in COUNT_IN])

    def test_each_direction_that_repeats_takes_its_slots_in_the_pattern_directions_order(self):
        slots = [0, 1, 2, 3]
        expected = {
            Direction.FORWARD: [0, 1, 2, 3, 0, 1, 2, 3], Direction.REVERSE_B: [3, 2, 1, 0, 3, 2, 1, 0],
            Direction.PENDULUM: [0, 1, 2, 3, 2, 1, 0, 1], Direction.ALTERNATE: [0, 1, 2, 3, 3, 2, 1, 0],
        }
        for direction, values in expected.items():
            with self.subTest(direction=direction):
                song = render_data(song_data(draws={DrawName.AD: a_draw(slots=slots, direction=direction)}, rows={Row.AD_NOTE: every_step()}, repeat=2))
                played = [pitch - MIDDLE_C for scene in pitches_of(song=song, scenes=2) for pitch in scene]
                self.assertEqual(played, values)

    def test_serial_deals_every_slot_once_a_round(self):
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=TWELVE_TONES, direction=DrawDirection.SERIAL)}, rows={Row.AD_NOTE: every_step()}, repeat=6))
        played = [pitch - MIDDLE_C for scene in pitches_of(song=song, scenes=6) for pitch in scene]
        rounds = [played[start:start + len(TWELVE_TONES)] for start in range(0, len(played), len(TWELVE_TONES))]
        for each in rounds:
            self.assertEqual(sorted(each), TWELVE_TONES)

    def test_any_and_random_take_only_values_the_slots_hold(self):
        slots = [1, 1, 2, 3, 5]
        for direction in (DrawDirection.ANY, Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY):
            with self.subTest(direction=direction):
                song = render_data(song_data(draws={DrawName.AD: a_draw(slots=slots, direction=direction)}, rows={Row.AD_NOTE: every_step()}, repeat=4))
                played = {pitch - MIDDLE_C for scene in pitches_of(song=song, scenes=4) for pitch in scene}
                self.assertLessEqual(played, set(slots))

    def test_a_blank_slot_is_passed_over_without_using_up_a_draw(self):
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=[0, None, 5])}, rows={Row.AD_NOTE: every_step()}))
        self.assertEqual(pitches_of(song=song, scenes=1), [[MIDDLE_C, MIDDLE_C + 5, MIDDLE_C, MIDDLE_C + 5]])

    def test_a_draw_with_no_value_adds_nothing(self):
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=[None, None])}, rows={Row.AD_NOTE: every_step()}))
        self.assertEqual(pitches_of(song=song, scenes=1), [[MIDDLE_C] * STEPS])

    def test_a_step_with_no_use_draws_nothing(self):
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=COUNT_IN)}, rows={Row.AD_NOTE: [RegisterUse.ADD, 0, RegisterUse.ADD, 0]}))
        self.assertEqual(pitches_of(song=song, scenes=1), [[MIDDLE_C, MIDDLE_C, MIDDLE_C + 1, MIDDLE_C]])


class TestUses(unittest.TestCase):

    def test_subtract_takes_the_value_away(self):
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=[1, 2])}, rows={Row.AD_NOTE: every_step(use=RegisterUse.SUBTRACT)}))
        self.assertEqual(pitches_of(song=song, scenes=1), [[MIDDLE_C - 1, MIDDLE_C - 2, MIDDLE_C - 1, MIDDLE_C - 2]])

    def test_a_step_that_uses_a_draw_on_the_note_and_the_velocity_draws_once(self):
        rows = {Row.VELOCITY: [QUIET] * STEPS, Row.AD_NOTE: every_step(), Row.AD_VELOCITY: every_step()}
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=[0, 1, 2, 3])}, rows=rows))
        self.assertEqual(heard(song=song, scene=1), [(MIDDLE_C + value, QUIET + value) for value in COUNT_IN])

    def test_two_draws_on_one_step_add_together_and_can_pull_against_each_other(self):
        rows = {Row.BD_NOTE: every_step(), Row.DD_NOTE: every_step(use=RegisterUse.SUBTRACT)}
        song = render_data(song_data(draws={DrawName.BD: a_draw(slots=[4]), DrawName.DD: a_draw(slots=COUNT_IN)}, rows=rows))
        self.assertEqual(pitches_of(song=song, scenes=1), [[MIDDLE_C + 4 - value for value in COUNT_IN]])

    def test_a_drum_pattern_cannot_move_its_note_by_a_draw(self):
        data = song_data(draws={DrawName.AD: a_draw(slots=COUNT_IN)}, rows={PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C] * STEPS, Row.AD_NOTE: every_step()})
        with self.assertRaises(SongFileError) as refused:
            render_data(data)
        self.assertIn(errors.ERR_REGISTER_NOTE_ON_DRUMS, str(refused.exception))


class TestResets(unittest.TestCase):

    def test_a_steps_reset_sends_the_draw_back_before_it_draws(self):
        rows = {Row.AD_NOTE: every_step(), Row.AD_RESET: [False, False, True, False]}
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=[0, 1, 2, 3, 4, 5])}, rows=rows, repeat=2))
        played = [pitch - MIDDLE_C for scene in pitches_of(song=song, scenes=2) for pitch in scene]
        self.assertEqual(played, [0, 1, 0, 1, 2, 3, 0, 1])

    def test_a_reset_comes_before_the_draw_a_redrawing_condition_takes(self):
        draw = {**a_draw(slots=[1, 2, 3]), DrawSetting.CONDITIONS_REDRAW: True}
        rows = {Row.AD_NOTE: every_step(), Row.AD_RESET: [False, False, True, False], **muted_when_equal(draw=DrawName.AD, value=1)}
        song = render_data(song_data(draws={DrawName.AD: draw}, rows=rows))
        # Step 1 draws 1 and is muted, step 2 draws 2; step 3 resets AD before its condition draws, so it draws 1 and is muted; step 4 draws 2.
        self.assertEqual([pitch - MIDDLE_C for pitch in pitches_of(song=song, scenes=1)[0]], [2, 2])

    def test_a_serial_reset_starts_a_new_round(self):
        rows = {Row.AD_NOTE: every_step(), Row.AD_RESET: [True, False, False, False]}
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=COUNT_IN, direction=DrawDirection.SERIAL)}, rows=rows, repeat=3))
        for scene in pitches_of(song=song, scenes=3):
            self.assertEqual(sorted(pitch - MIDDLE_C for pitch in scene), COUNT_IN)

    def test_a_scene_resets_its_draws_as_it_first_starts_and_draws_carry_on_from_scene_to_scene_otherwise(self):
        played = {LEAD: {ClipSlotSetting.PATTERN: TUNE}}
        scenes = [{SceneSetting.TRACKS: played}, {SceneSetting.TRACKS: played}, {SceneSetting.RESET_DRAWS: [DrawName.AD], SceneSetting.TRACKS: played}]
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=list(range(8)))}, rows={Row.AD_NOTE: every_step(steps=2)}, steps=2, scenes=scenes))
        self.assertEqual(pitches_of(song=song, scenes=3), [[MIDDLE_C, MIDDLE_C + 1], [MIDDLE_C + 2, MIDDLE_C + 3], [MIDDLE_C, MIDDLE_C + 1]])


def muted_when_equal(*, draw, value, steps=STEPS):
    """Return a pattern's Mute When rows for every step: muted when a draw equals a value."""
    return {Row.MUTE_C1: [draw] * steps, Row.MUTE_C2: [Operator.SAME] * steps, Row.MUTE_C3: [value] * steps}


class TestConditions(unittest.TestCase):
    """A statement reads a draw as it reads a register: only looking at it, or, where the draw redraws in conditions, drawing from it."""

    def test_a_step_that_draws_reads_its_own_draw_and_a_step_that_does_not_only_looks(self):
        rows = {Row.AD_NOTE: [RegisterUse.ADD, 0, 0, 0], **muted_when_equal(draw=DrawName.AD, value=2)}
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=COUNT_IN)}, rows=rows, repeat=4))
        # The first step draws 0, 1, 2, 3 pass by pass before its condition reads AD, and the other steps look at what it drew: the whole third pass is muted.
        self.assertEqual([len(scene) for scene in pitches_of(song=song, scenes=4)], [4, 4, 0, 4])

    def test_a_draw_that_redraws_in_conditions_is_drawn_by_each_statement_that_reads_it_once_a_step(self):
        draw = {**a_draw(slots=COUNT_IN), DrawSetting.CONDITIONS_REDRAW: True}
        rows = {Row.AD_NOTE: [RegisterUse.ADD, 0, 0, 0], **muted_when_equal(draw=DrawName.AD, value=2)}
        song = render_data(song_data(draws={DrawName.AD: draw}, rows=rows, repeat=2))
        # Each step draws 0, 1, 2, 3 in turn, so the third step of every pass is muted; the first step's Note+=AD hears the 0 its statement drew.
        self.assertEqual(pitches_of(song=song, scenes=2), [[MIDDLE_C, MIDDLE_C, MIDDLE_C]] * 2)

    def test_a_statement_compares_a_register_with_a_draw(self):
        rows = {Row.AD_NOTE: every_step(), Row.MUTE_C1: [RegisterName.AX] * STEPS, Row.MUTE_C2: [Operator.LESS] * STEPS, Row.MUTE_C3: [DrawName.AD] * STEPS}
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=COUNT_IN)}, rows=rows))
        # AX stays 0, and each step draws AD before its condition compares: 0, 1, 2, 3, so only the first step sounds.
        self.assertEqual(pitches_of(song=song, scenes=1), [[MIDDLE_C]])

    def test_a_table_reads_a_draw_as_a_pass_starts(self):
        played = {LEAD: {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.REPEAT: 4, ClipSlotSetting.SKIP_WHEN: [{StatementPart.REGISTER: DrawName.AD, StatementPart.OPERATOR: Operator.SAME, StatementPart.VALUE: 1}]}}
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=COUNT_IN)}, rows={Row.AD_NOTE: [RegisterUse.ADD, 0, 0, 0]}, scenes=[{SceneSetting.TRACKS: played}]))
        # Each pass's first step draws the next value; the second pass starts with AD at 0, the third with AD at 1, which sits the third pass out.
        self.assertEqual(len(pitches_of(song=song, scenes=1)[0]), 3 * STEPS)


class TestLights(unittest.TestCase):
    """What the Draws page lights while a song plays: the slot each draw last took its value from, by the second."""

    def test_the_score_says_which_slot_each_draw_stands_on_by_the_second(self):
        data = song_data(draws={DrawName.DD: a_draw(slots=COUNT_IN)}, rows={Row.DD_NOTE: every_step(), PatternSetting.STEP_SIZE: QUARTER}, steps=STEPS)
        data[SongSetting.TEMPO] = BEATS_A_MINUTE
        score = Score(song=song_from_data(data), routes={})
        # Four quarter notes at 60 beats a minute: a second a step, each step drawing the next slot.
        found = [score.draw_places_at(scene=0, seconds=second + HALF_A_SECOND) for second in range(STEPS)]
        self.assertEqual(found, [{DrawName.DD: place} for place in range(STEPS)])
        self.assertEqual(score.draw_places_at(scene=0, seconds=-HALF_A_SECOND), {})


class TestShared(unittest.TestCase):

    def test_tracks_drawing_at_one_moment_draw_in_track_order(self):
        song = render_data(song_data(draws={DrawName.AD: a_draw(slots=list(range(8)))}, rows={Row.AD_NOTE: every_step(steps=2)}, steps=2, tracks=(LEAD, OTHER)))
        self.assertEqual(pitches_of(song=song, scenes=1, track=LEAD), [[MIDDLE_C, MIDDLE_C + 2]])
        self.assertEqual(pitches_of(song=song, scenes=1, track=OTHER), [[MIDDLE_C + 1, MIDDLE_C + 3]])


if __name__ == '__main__':
    unittest.main()
