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

"""A clip morphing into a second pattern across its repeats."""

import unittest

from llamatron.composition.clip_slot import morph_style_name
from llamatron.generators.blend import BlendMode
from rendering import render_data, song_from_data
from llamatron.composition.file_format import ClipSlotSetting, Direction, PatternSetting, Row, SceneSetting, Section, TrackSetting
from llamatron.exporters.timing import timed_events
from llamatron.composition.song_file_error import SongFileError
from song_testing import LEAD, clip, pat, pitches, with_parts

QUARTER = '1/4'
HALF = '1/2'
NOPE = 'nope'
B = 'b'
PATTERN_D = 'd'
KICK = 'kick'
A = 'a'
PATTERN_C = 'c'
REPEAT_OF_2 = 'repeat of 2'
LONG = 'long'
SHORT = 'short'
C_MINOR = 'C minor'
C_DORIAN = 'C dorian'
RENAMED = 'dark'
# The basic song's default octave is 4, where E is MIDI 52 and E flat 51.
E_IN_OCTAVE_4 = 52
E_FLAT_IN_OCTAVE_4 = 51
SILENT = 'silent'
A_SEED = 3
MOD_WHEEL = 1
# The CC values a pattern with no notes sends, one per step.
CC_VALUES = [10, 20, 30, 40]


class TestClipMorph(unittest.TestCase):

    C_NOTES = [48, 50, 52, 53]
    D_NOTES = [55, 57, 59, 60]

    def morph(self, repeat=3, style=morph_style_name(BlendMode.LEFT), **clip_slot):
        settings = {ClipSlotSetting.PATTERN: PATTERN_C, ClipSlotSetting.REPEAT: repeat, ClipSlotSetting.MORPH_TO: PATTERN_D, ClipSlotSetting.MORPH_STYLE: style, **clip_slot}
        fourths = [QUARTER] * 4
        data = with_parts(
            patterns={
                PATTERN_C: pat(*zip([1, 2, 3, 4], fourths)),
                PATTERN_D: pat(*zip([5, 6, 7, 1], fourths), octave=[4, 4, 4, 5]),
            },
            scenes=[{Section.TRACKS: {LEAD: settings}}],
        )
        return clip(song=render_data(data), scene=1, track=LEAD)

    def pitches_by_repeat(self, found):
        """Return the pitches of each repeat of a four-beat clip, in the order they play."""
        events = sorted(timed_events(clip=found, scale=found.get_scale())[0])
        return [[pitch for time, _, pitch, _ in events if int(time) == repeat] for repeat in range(int(found.total_length()))]

    def test_the_clip_direction_applies_to_the_target_too(self):
        found = self.morph(repeat=2, direction=Direction.REVERSE_B)
        self.assertEqual(self.pitches_by_repeat(found), [self.C_NOTES[::-1], self.D_NOTES[::-1]])

    def test_without_a_clip_direction_the_target_follows_its_own_pattern(self):
        found = self.morph(repeat=2)
        self.assertEqual(self.pitches_by_repeat(found), [self.C_NOTES, self.D_NOTES])

    def test_a_random_clip_direction_draws_the_same_for_the_source_with_or_without_a_morph(self):
        random = Direction.RANDOM
        settings = {ClipSlotSetting.PATTERN: PATTERN_C, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.DIRECTION: random}
        fourths = [QUARTER] * 4
        patterns = {PATTERN_C: pat(*zip([1, 2, 3, 4], fourths)), PATTERN_D: pat(*zip([5, 6, 7, 1], fourths))}
        alone = clip(song=render_data(with_parts(patterns=patterns, seed=A_SEED, scenes=[{Section.TRACKS: {LEAD: settings}}])), scene=1, track=LEAD)
        morphed = clip(song=render_data(with_parts(patterns=patterns, seed=A_SEED, scenes=[{Section.TRACKS: {LEAD: {**settings, ClipSlotSetting.MORPH_TO: PATTERN_D, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.RIGHT)}}}])), scene=1, track=LEAD)
        # The first repeat is all source either way, and must be the same draw.
        self.assertEqual(self.pitches_by_repeat(alone)[0], self.pitches_by_repeat(morphed)[0])

    def test_a_pattern_with_no_notes_morphs_too(self):
        fourths = [QUARTER] * 4
        data = with_parts(
            patterns={
                SILENT: {PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: QUARTER, Row.CC1: CC_VALUES},
                PATTERN_D: pat(*zip([5, 6, 7, 1], fourths), octave=[4, 4, 4, 5]),
            },
            tracks={LEAD: {TrackSetting.CC: [MOD_WHEEL, None, None, None]}},
            scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: SILENT, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: PATTERN_D, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}}}],
        )
        found = clip(song=render_data(data), scene=1, track=LEAD)
        self.assertEqual(self.pitches_by_repeat(found), [[], self.D_NOTES])
        self.assertEqual([control.get_value() for control in found.get_controls() if control.get_time() < 1], CC_VALUES)

    def test_runs_across_the_repeats_of_the_clip(self):
        found = self.morph(repeat=2)
        self.assertEqual(found.total_length(), 2)
        self.assertEqual(pitches(found), self.C_NOTES + self.D_NOTES)

    def test_left_replaces_notes_from_the_left(self):
        found = pitches(self.morph(repeat=5))
        self.assertEqual(found[4:8], self.D_NOTES[:1] + self.C_NOTES[1:])

    def test_right_replaces_notes_from_the_right(self):
        found = pitches(self.morph(repeat=5, style=morph_style_name(BlendMode.RIGHT)))
        self.assertEqual(found[4:8], self.C_NOTES[:3] + self.D_NOTES[3:])

    def test_middle_works(self):
        self.assertEqual(self.morph(style=morph_style_name(BlendMode.MIDDLE)).total_length(), 3)

    def test_a_longer_target_is_cut_and_a_shorter_one_is_looped(self):
        data = with_parts(
            patterns={LONG: pat([1, 2]), SHORT: pat([3, HALF])},
            scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: LONG, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}, KICK: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: SHORT, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}}}],
        )
        song = render_data(data)
        self.assertEqual(clip(song=song, scene=1, track=LEAD).total_length(), 2)
        self.assertEqual(clip(song=song, scene=1, track=KICK).total_length(), 2)

    def test_needs_a_repeat_above_one(self):
        with self.assertRaises(SongFileError) as caught:
            self.morph(repeat=1)
        self.assertIn(REPEAT_OF_2, str(caught.exception))

    def test_needs_both_settings_and_real_values(self):
        good = {ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: B, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}
        bad = [{**good, ClipSlotSetting.MORPH_TO: NOPE}, {**good, ClipSlotSetting.MORPH_STYLE: NOPE}]
        bad += [{k: v for k, v in good.items() if k != missing} for missing in [ClipSlotSetting.MORPH_TO, ClipSlotSetting.MORPH_STYLE]]
        for clip_slot in bad:
            with self.subTest(clip_slot=clip_slot), self.assertRaises(SongFileError):
                song_from_data(with_parts(scenes=[{Section.TRACKS: {LEAD: clip_slot}}]))

    def test_a_clip_slot_names_only_a_scale_the_set_has(self):
        # A clip can set its own scale since 2026-11-11, the user's design, but only one of the set's.
        with self.assertRaises(SongFileError):
            song_from_data(with_parts(scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.SCALE: NOPE}}}]))


class TestClipScale(unittest.TestCase):
    """A clip's own scale wins over its scene's and its song's, and a rename of the scale follows it."""

    def test_a_clips_scale_wins_over_the_scenes_and_the_songs(self):
        # Pattern a plays degrees 1 and 3: E in C major, E flat in C minor.
        scenes = [
            {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A}}},
            {SceneSetting.SCALE: C_DORIAN, Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.SCALE: C_MINOR}}},
            {Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.SCALE: C_MINOR}}},
        ]
        song = render_data(with_parts(scenes=scenes))
        thirds = [pitches(clip(song=song, scene=number, track=LEAD))[1] for number in (1, 2, 3)]
        self.assertEqual(thirds, [E_IN_OCTAVE_4, E_FLAT_IN_OCTAVE_4, E_FLAT_IN_OCTAVE_4])

    def test_renaming_the_scale_renames_the_clips_choice(self):
        song = song_from_data(with_parts(scenes=[{Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.SCALE: C_MINOR}}}]))
        song.get_setlist().rename_item(section=Section.SCALES, old=C_MINOR, new=RENAMED)
        self.assertEqual(song.get_scenes()[0].get_clip_slot(LEAD).get_scale_name(), RENAMED)
