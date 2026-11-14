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

"""Clip and scene lengths are worked out without playing anything, and agree with a real play.

The first class edits a small song through the Document, as the tracker does, and checks that the
lengths it shows move as expected. The second plays every example in full and checks that every
clip and scene is exactly as long as the arithmetic says, so that a feature that changed a
length without playing would fail here.
"""

import unittest
from fractions import Fraction
from unittest import mock

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, Row, Section
from llamatron.playback.song_renderer import GRAB_ARROW, QUARTER_NOTES_PER_WHOLE_NOTE, SECONDS_PER_MINUTE, SongRenderer
from llamatron.strings.errors import ERR_NO_SCALE, ERR_WHERE_PATTERN
from llamatron.tui.lengths import measured
from llamatron.support.example_sets import example_sets
from rendering import bare_document, song_from_file

EXAMPLES = example_sets()

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
# Where the document finds the function that measures a song, which a test wraps to count its calls.
MEASURED_BY_THE_DOCUMENT = 'llamatron.tui.document.measured'
CHAIN = 'chain'
# Lengths in whole notes.
ONE_PASS = Fraction(1)
DRONE_PASS = Fraction(1, 2)
NO_LENGTH = Fraction(0)
# A scene with nothing in it that doesn't loop lasts no time.


def seconds(*, whole_notes, tempo=TEMPO):
    """Return how long a length in whole notes lasts at a tempo, as the program works it out."""
    return Fraction(whole_notes) * SECONDS_PER_MINUTE * QUARTER_NOTES_PER_WHOLE_NOTE / tempo


def small_song():
    """Return the small song as a document, built the way the tracker builds one, from a set with the starter pattern taken out."""
    document = bare_document()
    document.set_tempo(TEMPO)
    document.add_pattern(name=TUNE, steps=TUNE_STEPS)
    document.set_step_size(name=TUNE, step_size=QUARTER)
    document.set_step_value(name=TUNE, row=Row.DEGREE, step=FIRST_STEP, value=FIRST_DEGREE)
    document.add_pattern(name=DRONE, steps=DRONE_STEPS)
    document.set_step_size(name=DRONE, step_size=HALF)
    document.set_step_value(name=DRONE, row=Row.DEGREE, step=FIRST_STEP, value=FIRST_DEGREE)
    document.add_track(LEAD)
    document.add_track(BASS)
    document.add_scene(index=FIRST, name=FIRST_SCENE_NAME)
    document.add_clip_slot(index=FIRST, track=LEAD, pattern=TUNE)
    document.add_clip_slot(index=FIRST, track=BASS, pattern=DRONE)
    document.add_scene(index=SECOND, name=SECOND_SCENE_NAME)
    document.add_clip_slot(index=SECOND, track=LEAD, pattern=TUNE)
    document.set_clip_slot_repeat(index=SECOND, track=LEAD, repeat=LEAD_REPEATS)
    document.add_clip_slot(index=SECOND, track=BASS, pattern=DRONE)
    document.set_clip_slot_setting(index=SECOND, track=BASS, setting=ClipSlotSetting.LOOP, value=True)
    return document


class TestLengthsWithoutPlaying(unittest.TestCase):

    def setUp(self):
        self.document = small_song()

    def test_a_clip_lasts_its_pattern_times_its_repeats(self):
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=ONE_PASS))
        self.assertEqual(self.document.lengths().clip_seconds(index=SECOND, track=LEAD), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.document.set_clip_slot_repeat(index=FIRST, track=LEAD, repeat=MORE_REPEATS)
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=ONE_PASS * MORE_REPEATS))

    def test_a_scene_lasts_its_longest_clip_that_does_not_loop(self):
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS))
        self.assertEqual(self.document.lengths().scene_seconds(SECOND), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.document.set_clip_slot_repeat(index=FIRST, track=BASS, repeat=MANY_REPEATS)
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=DRONE_PASS * MANY_REPEATS))

    def test_a_looping_clip_lasts_as_long_as_its_scene(self):
        self.assertEqual(self.document.lengths().clip_seconds(index=SECOND, track=BASS), self.document.lengths().scene_seconds(SECOND))
        self.document.set_clip_slot_repeat(index=SECOND, track=LEAD, repeat=MORE_REPEATS)
        self.assertEqual(self.document.lengths().clip_seconds(index=SECOND, track=BASS), seconds(whole_notes=ONE_PASS * MORE_REPEATS))

    def test_the_steps_and_step_size_move_the_lengths(self):
        self.document.set_steps(name=TUNE, steps=LONGER_TUNE)
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=ONE_PASS * 2))
        self.document.set_step_size(name=TUNE, step_size=EIGHTH)
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=ONE_PASS))
        self.document.set_step_size(name=TUNE, step_size=None)
        self.document.set_default_step_size(SIXTEENTH)
        self.assertEqual(self.document.lengths().pattern_seconds(TUNE), seconds(whole_notes=LONGER_TUNE * Fraction(SIXTEENTH)))
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=LONGER_TUNE * Fraction(SIXTEENTH)))

    def test_scene_repeats_and_tempos_move_the_song_length(self):
        both_scenes = ONE_PASS + ONE_PASS * LEAD_REPEATS
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=both_scenes))
        self.document.set_scene_repeat(index=FIRST, repeat=LEAD_REPEATS)
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=both_scenes + ONE_PASS))
        self.document.set_tempo(SLOW_TEMPO)
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=both_scenes + ONE_PASS, tempo=SLOW_TEMPO))
        self.document.set_scene_tempo(index=SECOND, tempo=FAST_TEMPO)
        self.assertEqual(self.document.lengths().scene_seconds(SECOND), seconds(whole_notes=ONE_PASS * LEAD_REPEATS, tempo=FAST_TEMPO))
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=ONE_PASS * LEAD_REPEATS, tempo=SLOW_TEMPO) + seconds(whole_notes=ONE_PASS * LEAD_REPEATS, tempo=FAST_TEMPO))

    def test_the_longest_scene_counts_every_repeat_and_leaves_out_a_scene_with_a_problem(self):
        self.assertEqual(self.document.lengths().longest_scene_seconds(), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.document.set_scene_repeat(index=FIRST, repeat=MANY_REPEATS)
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS * MANY_REPEATS))
        self.assertEqual(self.document.lengths().scene_play_seconds(FIRST), seconds(whole_notes=ONE_PASS))
        self.assertEqual(self.document.lengths().longest_scene_seconds(), seconds(whole_notes=ONE_PASS * MANY_REPEATS))
        # The second scene's clips are still found after the first scene's ten plays.
        self.assertEqual(self.document.lengths().clip_seconds(index=SECOND, track=LEAD), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.document.set_clip_slot_setting(index=FIRST, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.LOOP, value=True)
        self.assertIsNone(self.document.lengths().scene_seconds(FIRST))
        self.assertIsNone(self.document.lengths().song_seconds())
        self.assertEqual(self.document.lengths().longest_scene_seconds(), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))

    def test_a_patterns_own_length_takes_no_estimate_of_the_song(self):
        # The pattern editor shows only the pattern's own length, and every edit there changes the song, so asking for it must not measure the song.
        with mock.patch(MEASURED_BY_THE_DOCUMENT, wraps=measured) as measuring:
            self.assertEqual(self.document.lengths().pattern_seconds(TUNE), seconds(whole_notes=ONE_PASS))
            self.assertEqual(self.document.lengths().step_size(TUNE), Fraction(QUARTER))
            self.assertEqual(self.document.lengths().pattern_length(TUNE), ONE_PASS)
            measuring.assert_not_called()

    def test_a_scenes_length_measures_the_song_once_until_the_song_changes(self):
        with mock.patch(MEASURED_BY_THE_DOCUMENT, wraps=measured) as measuring:
            self.document.lengths().scene_seconds(FIRST)
            self.document.lengths().clip_seconds(index=SECOND, track=LEAD)
            self.document.lengths().song_seconds()
            self.assertEqual(measuring.call_count, 1)
            self.document.set_tempo(SLOW_TEMPO)
            self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=ONE_PASS + ONE_PASS * LEAD_REPEATS, tempo=SLOW_TEMPO))
            self.assertEqual(measuring.call_count, 2)

    def test_a_morph_and_a_chain_leave_the_lengths_alone(self):
        self.document.set_clip_slot_morph_target(index=SECOND, track=LEAD, pattern=DRONE)
        self.document.add_generator(section=Section.ARPS, name=ARP)
        self.document.add_chain(CHAIN)
        self.document.add_chain_step(chain=CHAIN, kind=GeneratorKind.ARP, name=ARP)
        self.document.set_clip_slot_setting(index=SECOND, track=LEAD, setting=ClipSlotSetting.CHAIN, value=CHAIN)
        self.assertEqual(self.document.lengths().clip_seconds(index=SECOND, track=LEAD), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.assertEqual(self.document.lengths().scene_seconds(SECOND), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))

    def test_a_scene_with_nothing_that_does_not_loop_is_a_problem(self):
        self.document.set_clip_slot_setting(index=SECOND, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.assertIsNone(self.document.lengths().scene_seconds(SECOND))
        self.assertIsNotNone(self.document.lengths().scene_problem(SECOND))
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS))

    def test_degrees_with_no_scale_are_a_problem_without_playing(self):
        self.document.set_scale_name(None)
        where = ERR_WHERE_PATTERN.format(name=TUNE)
        self.assertEqual(self.document.lengths().scene_problem(FIRST), ERR_NO_SCALE.format(where=where, scene=FIRST + 1))
        self.assertIsNone(self.document.lengths().scene_seconds(FIRST))
        self.document.set_drum(name=TUNE, drum=True)
        self.document.set_drum(name=DRONE, drum=True)
        self.assertIsNone(self.document.lengths().scene_problem(FIRST))
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS))

    def test_grabs_in_a_circle_are_a_problem_without_playing(self):
        self.document.set_clip_slot_setting(index=FIRST, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=BASS)
        self.document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        self.assertIn(GRAB_ARROW.join([LEAD, BASS, LEAD]), self.document.lengths().scene_problem(FIRST))
        self.assertIsNone(self.document.lengths().scene_problem(SECOND))


class TestLengthsAgreeWithPlaying(unittest.TestCase):
    """Every example, played in full, is exactly as long as the arithmetic says, clip by clip and scene by scene."""

    def test_every_example(self):
        self.assertTrue(EXAMPLES)
        for path in EXAMPLES:
            renderer = SongRenderer(song_from_file(path))
            for scene in renderer.get_scenes():
                played = {track: renderer.get_clip(scene=scene, track=track).total_length() for track in scene.get_track_names()}
                for track, length in played.items():
                    with self.subTest(path=path, scene=scene.describe(), track=track):
                        self.assertEqual(renderer.get_clip_length(scene=scene, track=track), length)
                with self.subTest(path=path, scene=scene.describe()):
                    self.assertEqual(renderer.get_scene_length(scene), longest_without_looping(scene=scene, played=played))


def longest_without_looping(*, scene, played):
    """Return the longest of a scene's played clips that doesn't loop, or no length if none."""
    lengths = [length for track, length in played.items() if not scene.get_clip_slot(track).loops()]
    return max(lengths, default=NO_LENGTH)
