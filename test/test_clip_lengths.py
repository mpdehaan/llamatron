# llamatron: a Python language and framework for producing MIDI clips.
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

"""Clip and scene lengths are worked out without playing anything, and agree with a real play.

The first class edits a small song through the Document, as the tracker does, and checks that the
lengths it shows move as expected. The second plays every example in full and checks that every
clip and scene is exactly as long as the arithmetic says, so that a feature that changed a
length without playing would fail here.
"""

import glob
import unittest
from fractions import Fraction

from llamatron.composition.file_format import CellSetting, GeneratorKind, Row, Section
from llamatron.composition.song import Song
from llamatron.playback.pattern_player import MSG_NO_SCALE, WHERE_PATTERN
from llamatron.playback.song_renderer import GRAB_ARROW, QUARTER_NOTES_PER_WHOLE_NOTE, SECONDS_PER_MINUTE, SongRenderer
from llamatron.tui.document import Document

EXAMPLES = sorted(glob.glob('examples/*.yml'))

# A small song: a four-step tune in quarter notes on the lead, and a one-step half-note drone on
# the bass, each in one scene, with a second scene where the lead repeats and the drone loops.
LEAD = 'lead'
BASS = 'bass'
TUNE = 'tune'
DRONE = 'drone'
TUNE_STEPS = 4
QUARTER = '1/4'
EIGHTH = '1/8'
SIXTEENTH = '1/16'
DRONE_STEPS = 1
HALF = '1/2'
TEMPO = 120
SLOW_TEMPO = 60
FAST_TEMPO = 240
FIRST = 0
SECOND = 1
FIRST_SCENE_NAME = 'one'
SECOND_SCENE_NAME = 'two'
LEAD_REPEATS = 2
MORE_REPEATS = 3
MANY_REPEATS = 10
LONGER_TUNE = 8
FIRST_STEP = 0
FIRST_DEGREE = 1
ARP = 'arp'
CHAIN = 'chain'
# Lengths in whole notes.
ONE_PASS = Fraction(1)
DRONE_PASS = Fraction(1, 2)
NO_LENGTH = Fraction(0)
# A scene with nothing in it that doesn't loop lasts no time.


def seconds(whole_notes, tempo=TEMPO):
    """Return how long a length in whole notes lasts at a tempo, as the program works it out."""
    return Fraction(whole_notes) * SECONDS_PER_MINUTE * QUARTER_NOTES_PER_WHOLE_NOTE / tempo


def small_song():
    """Return the small song as a document, built the way the tracker builds one."""
    document = Document()
    document.set_tempo(TEMPO)
    document.add_pattern(TUNE, steps=TUNE_STEPS)
    document.set_step_size(TUNE, QUARTER)
    document.set_step_value(TUNE, Row.DEGREE, FIRST_STEP, FIRST_DEGREE)
    document.add_pattern(DRONE, steps=DRONE_STEPS)
    document.set_step_size(DRONE, HALF)
    document.set_step_value(DRONE, Row.DEGREE, FIRST_STEP, FIRST_DEGREE)
    document.add_track(LEAD)
    document.add_track(BASS)
    document.add_scene(FIRST, FIRST_SCENE_NAME)
    document.add_cell(FIRST, LEAD, TUNE)
    document.add_cell(FIRST, BASS, DRONE)
    document.add_scene(SECOND, SECOND_SCENE_NAME)
    document.add_cell(SECOND, LEAD, TUNE)
    document.set_cell_repeat(SECOND, LEAD, LEAD_REPEATS)
    document.add_cell(SECOND, BASS, DRONE)
    document.set_cell_setting(SECOND, BASS, CellSetting.LOOP, True)
    return document


class TestLengthsWithoutPlaying(unittest.TestCase):

    def setUp(self):
        self.document = small_song()

    def test_a_clip_lasts_its_pattern_times_its_repeats(self):
        self.assertEqual(self.document.clip_seconds(FIRST, LEAD), seconds(ONE_PASS))
        self.assertEqual(self.document.clip_seconds(SECOND, LEAD), seconds(ONE_PASS * LEAD_REPEATS))
        self.document.set_cell_repeat(FIRST, LEAD, MORE_REPEATS)
        self.assertEqual(self.document.clip_seconds(FIRST, LEAD), seconds(ONE_PASS * MORE_REPEATS))

    def test_a_scene_lasts_its_longest_clip_that_does_not_loop(self):
        self.assertEqual(self.document.scene_seconds(FIRST), seconds(ONE_PASS))
        self.assertEqual(self.document.scene_seconds(SECOND), seconds(ONE_PASS * LEAD_REPEATS))
        self.document.set_cell_repeat(FIRST, BASS, MANY_REPEATS)
        self.assertEqual(self.document.scene_seconds(FIRST), seconds(DRONE_PASS * MANY_REPEATS))

    def test_a_looping_clip_lasts_as_long_as_its_scene(self):
        self.assertEqual(self.document.clip_seconds(SECOND, BASS), self.document.scene_seconds(SECOND))
        self.document.set_cell_repeat(SECOND, LEAD, MORE_REPEATS)
        self.assertEqual(self.document.clip_seconds(SECOND, BASS), seconds(ONE_PASS * MORE_REPEATS))

    def test_the_steps_and_step_size_move_the_lengths(self):
        self.document.set_steps(TUNE, LONGER_TUNE)
        self.assertEqual(self.document.clip_seconds(FIRST, LEAD), seconds(ONE_PASS * 2))
        self.document.set_step_size(TUNE, EIGHTH)
        self.assertEqual(self.document.clip_seconds(FIRST, LEAD), seconds(ONE_PASS))
        self.document.set_step_size(TUNE, None)
        self.document.set_song_step_size(SIXTEENTH)
        self.assertEqual(self.document.pattern_seconds(TUNE), seconds(LONGER_TUNE * Fraction(SIXTEENTH)))
        self.assertEqual(self.document.clip_seconds(FIRST, LEAD), seconds(LONGER_TUNE * Fraction(SIXTEENTH)))

    def test_scene_repeats_and_tempos_move_the_song_length(self):
        both_scenes = ONE_PASS + ONE_PASS * LEAD_REPEATS
        self.assertEqual(self.document.song_seconds(), seconds(both_scenes))
        self.document.set_scene_repeat(FIRST, LEAD_REPEATS)
        self.assertEqual(self.document.scene_seconds(FIRST), seconds(ONE_PASS * LEAD_REPEATS))
        self.assertEqual(self.document.song_seconds(), seconds(both_scenes + ONE_PASS))
        self.document.set_tempo(SLOW_TEMPO)
        self.assertEqual(self.document.song_seconds(), seconds(both_scenes + ONE_PASS, SLOW_TEMPO))
        self.document.set_scene_tempo(SECOND, FAST_TEMPO)
        self.assertEqual(self.document.scene_seconds(SECOND), seconds(ONE_PASS * LEAD_REPEATS, FAST_TEMPO))
        self.assertEqual(self.document.song_seconds(), seconds(ONE_PASS * LEAD_REPEATS, SLOW_TEMPO) + seconds(ONE_PASS * LEAD_REPEATS, FAST_TEMPO))

    def test_a_morph_and_a_chain_leave_the_lengths_alone(self):
        self.document.set_cell_morph_target(SECOND, LEAD, DRONE)
        self.document.add_generator(Section.ARPS, ARP)
        self.document.add_chain(CHAIN)
        self.document.add_chain_step(CHAIN, GeneratorKind.ARP, ARP)
        self.document.set_cell_setting(SECOND, LEAD, CellSetting.CHAIN, CHAIN)
        self.assertEqual(self.document.clip_seconds(SECOND, LEAD), seconds(ONE_PASS * LEAD_REPEATS))
        self.assertEqual(self.document.scene_seconds(SECOND), seconds(ONE_PASS * LEAD_REPEATS))

    def test_a_scene_with_nothing_that_does_not_loop_is_a_problem(self):
        self.document.set_cell_setting(SECOND, LEAD, CellSetting.LOOP, True)
        self.assertIsNone(self.document.scene_seconds(SECOND))
        self.assertIsNotNone(self.document.scene_problem(SECOND))
        self.assertEqual(self.document.scene_seconds(FIRST), seconds(ONE_PASS))

    def test_degrees_with_no_scale_are_a_problem_without_playing(self):
        self.document.set_scale_name(None)
        where = WHERE_PATTERN.format(name=TUNE)
        self.assertEqual(self.document.scene_problem(FIRST), MSG_NO_SCALE.format(where=where, scene=FIRST + 1))
        self.assertIsNone(self.document.scene_seconds(FIRST))
        self.document.set_drum(TUNE, True)
        self.document.set_drum(DRONE, True)
        self.assertIsNone(self.document.scene_problem(FIRST))
        self.assertEqual(self.document.scene_seconds(FIRST), seconds(ONE_PASS))

    def test_grabs_in_a_circle_are_a_problem_without_playing(self):
        self.document.set_cell_setting(FIRST, LEAD, CellSetting.GRAB_TRACK, BASS)
        self.document.set_cell_setting(FIRST, BASS, CellSetting.GRAB_TRACK, LEAD)
        self.assertIn(GRAB_ARROW.join([LEAD, BASS, LEAD]), self.document.scene_problem(FIRST))
        self.assertIsNone(self.document.scene_problem(SECOND))


class TestLengthsAgreeWithPlaying(unittest.TestCase):
    """Every example, played in full, is exactly as long as the arithmetic says, clip by clip and scene by scene."""

    def test_every_example(self):
        self.assertTrue(EXAMPLES)
        for path in EXAMPLES:
            renderer = SongRenderer(Song.read_file(path))
            for scene in renderer.get_scenes():
                played = {track: renderer.get_clip(scene, track).total_length() for track in scene.get_track_names()}
                for track, length in played.items():
                    with self.subTest(path=path, scene=scene.describe(), track=track):
                        self.assertEqual(renderer.get_clip_length(scene, track), length)
                with self.subTest(path=path, scene=scene.describe()):
                    self.assertEqual(renderer.get_scene_length(scene), longest_without_looping(scene, played))


def longest_without_looping(scene, played):
    """Return the longest of a scene's played clips that doesn't loop, or no length if none."""
    lengths = [length for track, length in played.items() if not scene.get_cell(track).loops()]
    return max(lengths, default=NO_LENGTH)
