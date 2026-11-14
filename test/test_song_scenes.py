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

"""Scenes and clips in song files: repeats, loops, tempos, scales and what each clip slot plays."""

import unittest
from fractions import Fraction

from llamatron.composition.named_scale import scale_type_name
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from rendering import estimate_data, render_data, song_from_data
from llamatron.composition.file_format import ClipSlotSetting, ScaleSetting, SceneSetting, Section, SetlistSetting, SongSetting
from llamatron.composition.song_file_error import SongFileError
from song_testing import BASIC, LEAD, X, build, clip, pitches, with_parts

YES = 'yes'
C_MINOR = 'C minor'
KICK = 'kick'
EVERY_CLIP_LOOPS = 'every clip loops'
BIG = 'big'
TWO = 'two'
EVERY_CLIP = 'every clip'
A = 'a'
HIT = 'hit'
RIFF = 'riff'
NO_SCALE = 'no scale'
MAIN = 'main'
D_MAJOR = 'D major'
X_1 = 'x 1'
X_2 = 'x 2'
X_3 = 'x 3'
GRANULARITY = 'granularity'
THIRD = '1/3'
DEFAULT_LENGTH = 'default_length'
BAD = 'bad'
WOBBLY = 'wobbly'


class TestClipsInAScene(unittest.TestCase):

    def scene(self, **clip_slots):
        return render_data(with_parts(scenes=[{Section.TRACKS: clip_slots}]))

    def test_a_clip_plays_its_pattern_once_and_ends(self):
        song = self.scene(lead={ClipSlotSetting.PATTERN: A}, kick={ClipSlotSetting.PATTERN: HIT})
        self.assertEqual(clip(song=song, scene=1, track=KICK).total_length(), Fraction(1, 4))
        self.assertEqual(clip(song=song, scene=1, track=LEAD).total_length(), 1)

    def test_a_clip_goes_by_its_own_name_or_its_patterns(self):
        song = self.scene(lead={ClipSlotSetting.PATTERN: A, ClipSlotSetting.NAME: RIFF}, kick={ClipSlotSetting.PATTERN: HIT})
        self.assertEqual(clip(song=song, scene=1, track=LEAD).get_name(), RIFF)
        self.assertEqual(clip(song=song, scene=1, track=KICK).get_name(), HIT)

    def test_repeat_plays_a_pattern_more_times(self):
        song = self.scene(kick={ClipSlotSetting.PATTERN: HIT, ClipSlotSetting.REPEAT: 3})
        self.assertEqual(clip(song=song, scene=1, track=KICK).total_length(), Fraction(3, 4))
        self.assertEqual(len(pitches(clip(song=song, scene=1, track=KICK))), 3)

    def test_loop_plays_until_the_longest_other_clip_ends(self):
        song = self.scene(lead={ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: 2}, kick={ClipSlotSetting.PATTERN: HIT, ClipSlotSetting.LOOP: True})
        self.assertEqual(clip(song=song, scene=1, track=KICK).total_length(), 2)
        self.assertEqual(len(pitches(clip(song=song, scene=1, track=KICK))), 8)

    def test_a_loop_is_cut_at_the_end_of_the_scene(self):
        song = self.scene(lead={ClipSlotSetting.PATTERN: HIT}, kick={ClipSlotSetting.PATTERN: A, ClipSlotSetting.LOOP: True})
        self.assertEqual(clip(song=song, scene=1, track=KICK).total_length(), Fraction(1, 4))

    def test_every_clip_looping_is_an_error(self):
        data = with_parts(scenes=[{SceneSetting.NAME: BIG, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.LOOP: True}, KICK: {ClipSlotSetting.PATTERN: HIT, ClipSlotSetting.LOOP: True}}}])
        with self.assertRaises(SongFileError) as caught:
            render_data(data)
        self.assertIn(EVERY_CLIP_LOOPS, str(caught.exception))
        self.assertIn(BIG, str(caught.exception))

    def test_loop_must_be_true_or_false(self):
        with self.assertRaises(SongFileError):
            self.scene(kick={ClipSlotSetting.PATTERN: HIT, ClipSlotSetting.LOOP: YES})

    def test_repeat_must_be_positive(self):
        for repeat in [0, TWO, True]:
            with self.subTest(repeat=repeat), self.assertRaises(SongFileError):
                self.scene(kick={ClipSlotSetting.PATTERN: HIT, ClipSlotSetting.REPEAT: repeat})

    def test_clips_say_whether_live_should_loop_them(self):
        song = self.scene(lead={ClipSlotSetting.PATTERN: A}, kick={ClipSlotSetting.PATTERN: HIT, ClipSlotSetting.LOOP: True})
        self.assertFalse(clip(song=song, scene=1, track=LEAD).get_loop())
        self.assertTrue(clip(song=song, scene=1, track=KICK).get_loop())

    def test_estimate_gives_seconds_for_scenes_and_clips(self):
        estimates = estimate_data(with_parts(scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: 2}, KICK: {ClipSlotSetting.PATTERN: HIT}}}]))
        number, seconds, clips, problem = estimates[0]
        self.assertEqual((number, seconds, problem), (1, 4, None))
        self.assertEqual(clips, {LEAD: 4, KICK: Fraction(1, 2)})

    def test_estimate_uses_the_scene_tempo(self):
        estimates = estimate_data(with_parts(scenes=[{SceneSetting.TEMPO: 60, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}}]))
        self.assertEqual(estimates[0][1], 4)

    def test_estimate_reports_a_problem_in_only_that_scene(self):
        estimates = estimate_data(with_parts(scenes=[
            {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.LOOP: True}}},
            {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}},
        ]))
        first, second = estimates
        self.assertIn(EVERY_CLIP, first[3])
        self.assertIsNone(first[1])
        self.assertEqual(second[1], 2)


class TestScenes(unittest.TestCase):

    def test_a_scene_scale_overrides_only_that_scene(self):
        data = with_parts(scenes=[
            {SceneSetting.SCALE: C_MINOR, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}},
            {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}},
        ])
        song = render_data(data)
        self.assertEqual(pitches(clip(song=song, scene=1, track=LEAD)), [48, 51])
        self.assertEqual(pitches(clip(song=song, scene=2, track=LEAD)), [48, 52])

    def test_degrees_with_no_scale_anywhere_name_the_problem(self):
        data = with_parts(scale=None, scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}}])
        with self.assertRaises(SongFileError) as caught:
            render_data(data)
        self.assertIn(NO_SCALE, str(caught.exception))

    def test_a_scene_scale_works_when_the_song_has_none(self):
        data = with_parts(scale=None, scenes=[{SceneSetting.SCALE: C_MINOR, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}}])
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [48, 51])

    def test_a_scale_can_have_any_name(self):
        data = with_parts(scales={MAIN: {ScaleSetting.ROOT: NoteName.D, ScaleSetting.TYPE: scale_type_name(ScaleType.MINOR)}}, scale=MAIN)
        self.assertEqual(pitches(clip(song=render_data(data), scene=1, track=LEAD)), [50, 53])

    def test_scales_must_be_in_the_list(self):
        for parts in [{SongSetting.SCALE: D_MAJOR}, {Section.SCENES: [{SceneSetting.SCALE: D_MAJOR, SceneSetting.TRACKS: {}}]}]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                song_from_data(with_parts(**parts))

    def test_scale_list_is_checked(self):
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(scales={BAD: {ScaleSetting.ROOT: NoteName.C, ScaleSetting.TYPE: WOBBLY}}))

    def test_repeat_writes_numbered_scenes(self):
        data = with_parts(scenes=[{SceneSetting.NAME: X, SceneSetting.REPEAT: 3, SceneSetting.TRACKS: {}}])
        self.assertEqual([s.get_name() for s in render_data(data).get_rows()], [X_1, X_2, X_3])

    def test_tempo_ramps_across_a_repeat(self):
        data = with_parts(scenes=[{SceneSetting.REPEAT: 3, SceneSetting.TEMPO_START: 120, SceneSetting.TEMPO_END: 124, SceneSetting.TRACKS: {}}])
        self.assertEqual([s.get_tempo() for s in render_data(data).get_rows()], [120, 122, 124])

    def test_a_scene_can_set_a_tempo(self):
        data = with_parts(scenes=[{SceneSetting.TEMPO: 90, SceneSetting.TRACKS: {}}])
        self.assertEqual(render_data(data).get_rows()[0].get_tempo(), 90)

    def test_no_tempo_uses_the_song_tempo(self):
        self.assertIsNone(build(BASIC).get_rows()[0].get_tempo())
        self.assertEqual(build(BASIC).get_tempo(), 120)

    def test_any_number_of_tracks(self):
        tracks = [f't{n}' for n in range(9)]
        data = with_parts(tracks={name: {} for name in tracks}, scenes=[{Section.TRACKS: {name: {ClipSlotSetting.PATTERN: A} for name in tracks}}])
        self.assertEqual(len(render_data(data).get_columns()), 9)

    def test_a_clip_slot_can_be_empty(self):
        self.assertIsNone(clip(song=render_data(with_parts(scenes=[{Section.TRACKS: {}}])), scene=1, track=LEAD))

    def test_a_song_can_start_with_nothing(self):
        song = render_data({SceneSetting.TEMPO: 120, SceneSetting.TRACKS: {}, Section.SCENES: []})
        self.assertEqual(song.get_rows(), [])

    def test_track_names_must_differ(self):
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(tracks=[A, A]))

    def test_song_settings_are_checked(self):
        for parts in [{GRANULARITY: THIRD}, {DEFAULT_LENGTH: 0}, {SetlistSetting.DEFAULT_OCTAVE: 20}, {SetlistSetting.DEFAULT_DRUM_OCTAVE: X}]:
            with self.subTest(parts=parts), self.assertRaises(SongFileError):
                song_from_data(with_parts(**parts))
