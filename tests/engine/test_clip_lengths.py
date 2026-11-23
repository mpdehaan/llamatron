# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Clip and scene lengths are worked out without playing anything, and agree with a real play.

The first class edits a small song through the Document, as the tracker does, and checks that the
lengths it shows move as expected. The second plays every example in full and checks that every
clip and scene is exactly as long as the arithmetic says, so that a feature that changed a
length without playing would fail here.
"""

from fractions import Fraction
import unittest
from unittest import mock

from llamatron.engine.generators import arp as arp_plugin
from llamatron.engine.realizer import song_realizer
from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.interface.tracker.lengths import measured
from llamatron.model.file.example_sets import example_sets
from llamatron.model.schema.file_format import ClipSlotSetting, Row
from llamatron.user_strings import errors, marks
from tests.support.rendering import bare_document, song_from_file

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
# A scene's percentage of the song's tempo that doubles it, and the slow song's tempo doubled.
DOUBLING = 200
FAST_TEMPO = SLOW_TEMPO * 2
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
MEASURED_BY_THE_DOCUMENT = 'llamatron.interface.tracker.document.measured'
CHAIN = 'chain'
# Lengths in whole notes.
ONE_PASS = Fraction(1)
DRONE_PASS = Fraction(1, 2)
NO_LENGTH = Fraction(0)
# A scene with nothing in it that doesn't loop lasts no time.


def seconds(*, whole_notes, tempo=TEMPO):
    """Return how long a length in whole notes lasts at a tempo, as the program works it out."""
    return Fraction(whole_notes) * song_realizer.SECONDS_PER_MINUTE * song_realizer.QUARTER_NOTES_PER_WHOLE_NOTE / tempo


def small_song():
    """Return the small song as a document, built the way the tracker builds one, from a set with the starter pattern taken out."""
    document = bare_document()
    document.change_set(document.song().set_tempo, TEMPO)
    document.add_pattern(name=TUNE, steps=TUNE_STEPS)
    document.change_pattern(document.pattern(TUNE).set_step_size, QUARTER)
    document.change_pattern(document.pattern(TUNE).set_value, row=Row.DEGREE, step=FIRST_STEP, value=FIRST_DEGREE)
    document.add_pattern(name=DRONE, steps=DRONE_STEPS)
    document.change_pattern(document.pattern(DRONE).set_step_size, HALF)
    document.change_pattern(document.pattern(DRONE).set_value, row=Row.DEGREE, step=FIRST_STEP, value=FIRST_DEGREE)
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
        self.document.change_pattern(self.document.pattern(TUNE).set_steps, LONGER_TUNE)
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=ONE_PASS * 2))
        self.document.change_pattern(self.document.pattern(TUNE).set_step_size, EIGHTH)
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=ONE_PASS))
        self.document.change_pattern(self.document.pattern(TUNE).set_step_size, None)
        self.document.change_set(self.document.get_setlist().set_step_size, SIXTEENTH)
        self.assertEqual(self.document.lengths().pattern_seconds(TUNE), seconds(whole_notes=LONGER_TUNE * Fraction(SIXTEENTH)))
        self.assertEqual(self.document.lengths().clip_seconds(index=FIRST, track=LEAD), seconds(whole_notes=LONGER_TUNE * Fraction(SIXTEENTH)))

    def test_scene_repeats_and_tempos_move_the_song_length(self):
        both_scenes = ONE_PASS + ONE_PASS * LEAD_REPEATS
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=both_scenes))
        self.document.change_set(self.document.song().get_scene(FIRST).set_repeat, LEAD_REPEATS)
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=both_scenes + ONE_PASS))
        self.document.change_set(self.document.song().set_tempo, SLOW_TEMPO)
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=both_scenes + ONE_PASS, tempo=SLOW_TEMPO))
        self.document.change_set(self.document.song().get_scene(SECOND).set_tempo, DOUBLING)
        self.assertEqual(self.document.lengths().scene_seconds(SECOND), seconds(whole_notes=ONE_PASS * LEAD_REPEATS, tempo=FAST_TEMPO))
        self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=ONE_PASS * LEAD_REPEATS, tempo=SLOW_TEMPO) + seconds(whole_notes=ONE_PASS * LEAD_REPEATS, tempo=FAST_TEMPO))

    def test_the_longest_scene_counts_every_repeat_and_leaves_out_a_scene_with_a_problem(self):
        self.assertEqual(self.document.lengths().longest_scene_seconds(), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.document.change_set(self.document.song().get_scene(FIRST).set_repeat, MANY_REPEATS)
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
            self.document.change_set(self.document.song().set_tempo, SLOW_TEMPO)
            self.assertEqual(self.document.lengths().song_seconds(), seconds(whole_notes=ONE_PASS + ONE_PASS * LEAD_REPEATS, tempo=SLOW_TEMPO))
            self.assertEqual(measuring.call_count, 2)

    def test_a_morph_and_a_chain_leave_the_lengths_alone(self):
        self.document.set_clip_slot_morph_target(index=SECOND, track=LEAD, pattern=DRONE)
        self.document.add_generator(section=arp_plugin.SECTION, name=ARP)
        self.document.add_chain(CHAIN)
        self.document.change_set(self.document.get_setlist().get_chain(CHAIN).add_step, kind=arp_plugin.NAME, name=ARP, setlist=self.document.get_setlist())
        self.document.set_clip_slot_setting(index=SECOND, track=LEAD, setting=ClipSlotSetting.CHAINS, value=[CHAIN])
        self.assertEqual(self.document.lengths().clip_seconds(index=SECOND, track=LEAD), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))
        self.assertEqual(self.document.lengths().scene_seconds(SECOND), seconds(whole_notes=ONE_PASS * LEAD_REPEATS))

    def test_a_scene_with_nothing_that_does_not_loop_is_a_problem(self):
        self.document.set_clip_slot_setting(index=SECOND, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.assertIsNone(self.document.lengths().scene_seconds(SECOND))
        self.assertIsNotNone(self.document.lengths().scene_problem(SECOND))
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS))

    def test_degrees_with_no_scale_are_a_problem_without_playing(self):
        self.document.change_set(self.document.song().set_scale_name, None)
        where = errors.ERR_WHERE_PATTERN.format(name=TUNE)
        self.assertEqual(self.document.lengths().scene_problem(FIRST), errors.ERR_NO_SCALE.format(where=where, scene=FIRST + 1))
        self.assertIsNone(self.document.lengths().scene_seconds(FIRST))
        self.document.change_pattern(self.document.pattern(TUNE).set_drum, True)
        self.document.change_pattern(self.document.pattern(DRONE).set_drum, True)
        self.assertIsNone(self.document.lengths().scene_problem(FIRST))
        self.assertEqual(self.document.lengths().scene_seconds(FIRST), seconds(whole_notes=ONE_PASS))

    def test_grabs_in_a_circle_are_a_problem_without_playing(self):
        self.document.set_clip_slot_setting(index=FIRST, track=LEAD, setting=ClipSlotSetting.GRAB_TRACK, value=BASS)
        self.document.set_clip_slot_setting(index=FIRST, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        self.assertIn(marks.MSG_CIRCLE_ARROW.join([LEAD, BASS, LEAD]), self.document.lengths().scene_problem(FIRST))
        self.assertIsNone(self.document.lengths().scene_problem(SECOND))


def longest_without_looping(*, realizer, scene, played):
    """Return the longest of a scene's played clips that doesn't loop for as long as its scene lasts, or no length if none."""
    lengths = [length for track, length in played.items() if not realizer.fills_its_scene(scene=scene, track=track)]
    return max(lengths, default=NO_LENGTH)


def check_lengths_agree(*, test, path):
    """An example, played in full, is exactly as long as the arithmetic says, clip by clip and scene by scene."""
    realizer = SongRealizer(song_from_file(path))
    for scene in realizer.get_scenes():
        played = {track: realizer.get_clip(scene=scene, track=track).total_length() for track in scene.get_track_names()}
        for track, length in played.items():
            with test.subTest(scene=scene.describe(), track=track):
                test.assertEqual(realizer.get_clip_length(scene=scene, track=track), length)
        with test.subTest(scene=scene.describe()):
            test.assertEqual(realizer.get_scene_length(scene), longest_without_looping(realizer=realizer, scene=scene, played=played))

