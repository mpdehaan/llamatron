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

"""The MacroComposer (internal_tools/macro_composer/): a tune's lines and a drum's hits as patterns and back, velocity shaped by
rhythm, a form laid out as scenes, and existing demos written as inputs that compose back to the same music."""

import unittest
import unittest.mock

from llamatron.composition.setlist import Setlist
from llamatron.macro_composer import composer, decomposer, notation, shaping
from llamatron.support.safe_yaml import load_safely
from llamatron.support.version import VERSION

FILE_ENCODING = 'utf-8'
# Demos of three feels: dance music with a sung lead, a shanty in a minor key, and swung jazz.
DEMOS = ('examples/by_genre/pop/rick_rolling.yml', 'examples/by_genre/tv_theme/three_hour_tour.yml', 'examples/by_genre/tv_theme/aunt_clara.yml')
EIGHTH = '1/8'
TWICE = 2
SIXTEENTH = '1/16'
OCTAVE = 4
VELOCITY = 104
BAR_OF_EIGHTHS = 8
# Three soft pickup notes, the note the line arrives on, the line's highest note an octave up and flattened, an eased ending, a breath.
LINE = [
    {notation.DEGREE: 6, notation.STEPS: 1, notation.STRESS: notation.PICKUP},
    {notation.DEGREE: 6, notation.STEPS: 1, notation.STRESS: notation.PICKUP},
    {notation.DEGREE: 5, notation.STEPS: 2, notation.STRESS: notation.ARRIVAL},
    {notation.DEGREE: 7, notation.STEPS: 1, notation.OCTAVE: 1, notation.ACCIDENTAL: notation.FLAT, notation.STRESS: notation.PEAK},
    {notation.DEGREE: 3, notation.STEPS: 1, notation.STRESS: notation.ENDING},
    {notation.REST: 2},
]
SECOND_LINE = [{notation.DEGREE: 1, notation.STEPS: 6}, {notation.REST: 2}]
HAT = 'hat'
HAT_NOTE = 'F'
LOUD = 72
SOFT = 50
HITS = [notation.LOUD, notation.SOFT, notation.NONE, notation.SOFT] * 4
FOUR_FOUR = 1
KICK_TRACK = 'kick'
HAT_TRACK = 'hat'
BASS_TRACK = 'bass'
LEAD_TRACK = 'lead'
TUNE_PART = 'tune'
HAT_PART = 'hat bar'
SCENE_NAME = 'verse'
SCENE_BARS = 4


def read(path):
    with open(path, encoding=FILE_ENCODING) as file:
        return load_safely(file)


class TestTuneLines(unittest.TestCase):

    def tune(self):
        return notation.tune_rows(lines=[LINE, SECOND_LINE], octave=OCTAVE, velocity=VELOCITY, step_size=EIGHTH)

    def test_a_note_starts_on_its_step_and_is_held_by_ties(self):
        pattern = self.tune()
        self.assertEqual(pattern[notation.STEPS], 2 * BAR_OF_EIGHTHS)
        self.assertEqual(pattern[notation.DEGREE][:BAR_OF_EIGHTHS], [6, 6, 5, None, 7, 3, None, None])
        self.assertEqual(pattern[notation.TIE][:BAR_OF_EIGHTHS], [False, False, False, True, False, False, False, False])

    def test_a_stress_moves_a_note_from_the_parts_velocity(self):
        loud = self.tune()[notation.VELOCITY]
        self.assertEqual(loud[0], VELOCITY + notation.STRESSES[notation.PICKUP])
        self.assertEqual(loud[2], VELOCITY + notation.STRESSES[notation.ARRIVAL])
        self.assertEqual(loud[4], VELOCITY + notation.STRESSES[notation.PEAK])
        self.assertEqual(loud[5], VELOCITY + notation.STRESSES[notation.ENDING])
        self.assertEqual(loud[BAR_OF_EIGHTHS], VELOCITY)

    def test_an_octave_and_an_accidental_are_written_on_the_note(self):
        pattern = self.tune()
        self.assertEqual(pattern[notation.OCTAVE][4], OCTAVE + 1)
        self.assertEqual(pattern[notation.ACCIDENTAL][4], notation.ACCIDENTAL_MARKS[notation.FLAT])

    def test_a_pattern_reads_back_as_the_same_lines(self):
        lines, octave, velocity = notation.tune_lines(pattern=self.tune(), bar=BAR_OF_EIGHTHS)
        self.assertEqual(lines, [LINE, SECOND_LINE])
        self.assertEqual(octave, OCTAVE)
        self.assertEqual(velocity, VELOCITY)

    def test_a_pattern_with_no_notes_cannot_be_written_as_a_tune(self):
        silent = {notation.STEPS: 2, notation.DEGREE: [None, None]}
        with self.assertRaises(notation.NotWritable):
            notation.tune_lines(pattern=silent, bar=BAR_OF_EIGHTHS)


class TestDrumHits(unittest.TestCase):

    def bar(self):
        return notation.drum_rows(drum=HAT, hits=HITS, loud=LOUD, soft=SOFT, step_size=SIXTEENTH)

    def test_each_hit_is_the_drums_note_at_its_velocity(self):
        pattern = self.bar()
        self.assertTrue(pattern[notation.DRUM])
        self.assertEqual(pattern[notation.DEGREE][:4], [HAT_NOTE, HAT_NOTE, None, HAT_NOTE])
        self.assertEqual(pattern[notation.VELOCITY][:4], [LOUD, SOFT, None, SOFT])

    def test_a_pattern_reads_back_as_the_same_hits(self):
        self.assertEqual(notation.drum_hits(pattern=self.bar()), (HAT, HITS, LOUD, SOFT))

    def test_a_pattern_of_three_velocities_cannot_be_written_as_hits(self):
        pattern = self.bar()
        pattern[notation.VELOCITY][0] = LOUD + 1
        with self.assertRaises(notation.NotWritable):
            notation.drum_hits(pattern=pattern)


class TestShaping(unittest.TestCase):

    def shaped(self, *, feel, role):
        pattern = notation.drum_rows(drum=HAT, hits=[notation.LOUD] * 16, loud=LOUD, soft=LOUD, step_size=SIXTEENTH)
        return shaping.shaped(pattern=pattern, role=role, feel=feel, signature=FOUR_FOUR, compound=False)

    def test_no_note_moves_further_than_the_reach_under_any_feel(self):
        for feel in shaping.FEELS:
            for role in (shaping.PERCUSSION, shaping.BASS, shaping.COMPING, shaping.TUNE):
                with self.subTest(feel=feel, role=role):
                    self.assertLessEqual(max(abs(value - LOUD) for value in self.shaped(feel=feel, role=role)), shaping.REACH)

    def test_the_moves_of_a_rhythm_are_kept_and_are_the_moves_worked_out_anew(self):
        for feel in shaping.FEELS:
            for role in (shaping.PERCUSSION, shaping.BASS, shaping.COMPING, shaping.TUNE):
                with self.subTest(feel=feel, role=role):
                    kept = self.shaped(feel=feel, role=role)
                    shaping.MOVES_KEPT.clear()
                    self.assertEqual(self.shaped(feel=feel, role=role), kept)

    def test_another_rhythm_has_moves_of_its_own(self):
        every_step = notation.drum_rows(drum=HAT, hits=[notation.LOUD] * 16, loud=LOUD, soft=LOUD, step_size=SIXTEENTH)
        offbeats = notation.drum_rows(drum=HAT, hits=[notation.NONE, notation.LOUD] * 8, loud=LOUD, soft=LOUD, step_size=SIXTEENTH)
        given = dict(role=shaping.BASS, feel=shaping.FEELS[0], signature=FOUR_FOUR, compound=False)
        self.assertNotEqual(shaping.moves(pattern=every_step, **given), shaping.moves(pattern=offbeats, **given))
        self.assertEqual(shaping.moves(pattern=every_step, **given), shaping.moves(pattern=every_step, **given))

    def test_a_note_before_a_beat_nothing_lands_on_is_pushed_and_one_before_a_note_is_not(self):
        alone = notation.drum_rows(drum=HAT, hits=[notation.NONE, notation.NONE, notation.LOUD, notation.NONE] + [notation.NONE] * 12, loud=LOUD, soft=LOUD, step_size=SIXTEENTH)
        followed = notation.drum_rows(drum=HAT, hits=[notation.NONE, notation.NONE, notation.LOUD, notation.LOUD] + [notation.NONE] * 12, loud=LOUD, soft=LOUD, step_size=SIXTEENTH)
        given = dict(role=shaping.BASS, feel=shaping.FEELS[0], signature=FOUR_FOUR, compound=False)
        self.assertEqual(shaping.moves(pattern=alone, **given)[2], shaping.PUSH)
        self.assertNotEqual(shaping.moves(pattern=followed, **given)[2], shaping.PUSH)

    def test_the_moves_kept_are_forgotten_when_there_are_too_many(self):
        shaping.MOVES_KEPT.clear()
        kept = self.shaped(feel=shaping.FEELS[0], role=shaping.BASS)
        with unittest.mock.patch.object(shaping, 'MOST_MOVES_KEPT', len(shaping.MOVES_KEPT)):
            self.shaped(feel=shaping.FEELS[0], role=shaping.TUNE)
            self.assertEqual(len(shaping.MOVES_KEPT), 1)
        self.assertEqual(self.shaped(feel=shaping.FEELS[0], role=shaping.BASS), kept)

    def test_dance_music_leans_on_the_offbeats_and_a_march_on_the_downbeat(self):
        four = self.shaped(feel=shaping.FOUR, role=shaping.PERCUSSION)
        self.assertGreater(four[2], four[0])
        down = self.shaped(feel=shaping.DOWN, role=shaping.PERCUSSION)
        self.assertEqual(max(down), down[0])

    def test_a_note_off_the_beat_held_over_the_next_beat_is_a_push(self):
        pushed = notation.tune_rows(lines=[[{notation.REST: 1}, {notation.DEGREE: 1, notation.STEPS: 7}]], octave=OCTAVE, velocity=VELOCITY, step_size=EIGHTH)
        loud = shaping.shaped(pattern=pushed, role=shaping.TUNE, feel=shaping.BACKBEAT, signature=FOUR_FOUR, compound=False)
        self.assertEqual(loud[1], VELOCITY + shaping.PUSH)

    def test_the_drummers_drums_are_left_alone_and_a_bass_is_a_bass(self):
        bar = notation.drum_rows(drum=HAT, hits=HITS, loud=LOUD, soft=SOFT, step_size=SIXTEENTH)
        self.assertIsNone(shaping.role_of(pattern=bar, tracks=[KICK_TRACK]))
        self.assertEqual(shaping.role_of(pattern=bar, tracks=[HAT_TRACK]), shaping.PERCUSSION)
        tune = notation.tune_rows(lines=[SECOND_LINE], octave=OCTAVE, velocity=VELOCITY, step_size=EIGHTH)
        self.assertEqual(shaping.role_of(pattern=tune, tracks=[BASS_TRACK]), shaping.BASS)
        self.assertEqual(shaping.role_of(pattern=tune, tracks=[LEAD_TRACK]), shaping.TUNE)

    def test_what_was_shaped_can_be_told_again(self):
        tune = notation.tune_rows(lines=[LINE, SECOND_LINE], octave=OCTAVE, velocity=VELOCITY, step_size=EIGHTH)
        again = dict(tune)
        again[notation.VELOCITY] = shaping.shaped(pattern=tune, role=shaping.TUNE, feel=shaping.SWING, signature=FOUR_FOUR, compound=False)
        self.assertEqual(shaping.unshaped(pattern=again, role=shaping.TUNE, feel=shaping.SWING, signature=FOUR_FOUR, compound=False), tune[notation.VELOCITY])


class TestForm(unittest.TestCase):

    def patterns(self):
        return {TUNE_PART: notation.tune_rows(lines=[LINE, SECOND_LINE], octave=OCTAVE, velocity=VELOCITY, step_size=EIGHTH),
                HAT_PART: notation.drum_rows(drum=HAT, hits=HITS, loud=LOUD, soft=SOFT, step_size=SIXTEENTH)}

    def scene(self, entry):
        return composer.scene_of(entry=entry, bands={}, patterns=self.patterns(), signature=FOUR_FOUR)[composer.TRACKS]

    def test_the_first_part_that_divides_the_bars_times_the_scene_and_the_others_loop(self):
        clips = self.scene({composer.SCENE: SCENE_NAME, composer.BARS: SCENE_BARS, composer.PLAY: {HAT_TRACK: HAT_PART, LEAD_TRACK: TUNE_PART}})
        self.assertEqual(clips[HAT_TRACK], {composer.PATTERN: HAT_PART, composer.REPEAT: SCENE_BARS})
        self.assertEqual(clips[LEAD_TRACK], {composer.PATTERN: TUNE_PART, composer.LOOP: True})

    def test_a_part_may_say_its_own_chains_and_timing(self):
        played = {composer.PART: TUNE_PART, composer.CHAINS: [SCENE_NAME], composer.REPEAT: 2}
        clips = self.scene({composer.SCENE: SCENE_NAME, composer.PLAY: {LEAD_TRACK: played, HAT_TRACK: {composer.PART: HAT_PART, composer.ONCE: True}}})
        self.assertEqual(clips[LEAD_TRACK], {composer.PATTERN: TUNE_PART, composer.REPEAT: 2, composer.CHAINS: [SCENE_NAME]})
        self.assertEqual(clips[HAT_TRACK], {composer.PATTERN: HAT_PART})

    def test_a_scene_no_part_divides_is_refused(self):
        with self.assertRaises(ValueError):
            self.scene({composer.SCENE: SCENE_NAME, composer.BARS: 3, composer.PLAY: {LEAD_TRACK: TUNE_PART}})


class TestAClipsTiming(unittest.TestCase):

    def test_a_repeat_is_kept_a_loop_adds_nothing_and_a_clip_played_once_says_so(self):
        played = {composer.PART: TUNE_PART}
        self.assertEqual(decomposer.timed(played=played, clip={composer.REPEAT: TWICE}), {composer.PART: TUNE_PART, composer.REPEAT: TWICE})
        self.assertEqual(decomposer.timed(played=played, clip={composer.LOOP: True}), played)
        self.assertEqual(decomposer.timed(played=played, clip={}), {composer.PART: TUNE_PART, composer.ONCE: True})


class TestDemosAsInputs(unittest.TestCase):

    def test_a_demo_written_as_an_input_composes_back_to_the_same_music(self):
        for path in DEMOS:
            with self.subTest(path=path):
                given = decomposer.decomposed(read(path))
                made = Setlist.from_data(data=composer.composed(given=given, version=VERSION)).to_data()
                self.assertTrue(decomposer.same_music(one=made, other=Setlist.read_file(path).to_data()))

    def test_a_demos_parts_are_tunes_and_hits_and_none_is_left_as_written(self):
        for path in DEMOS:
            with self.subTest(path=path):
                given = decomposer.decomposed(read(path))
                self.assertFalse([name for name, part in given[composer.PARTS].items() if composer.RAW in part])

    def test_the_parts_the_feel_shapes_are_listed_with_the_feel(self):
        given = decomposer.decomposed(read(DEMOS[0]))
        self.assertEqual(given[composer.FEEL], shaping.FOUR)
        self.assertIn(HAT_TRACK, given[composer.SHAPED])


if __name__ == '__main__':
    unittest.main()
