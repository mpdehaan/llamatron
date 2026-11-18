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

"""Follow Chords: a clip's notes, written over chord I, are moved to the chord another track plays in the same scene, after that track's own chains."""

import unittest

from llamatron.composition.file_format import Accidental, ChordSymbol, ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, TrackSetting
from llamatron.composition.generator_settings import FollowChordsSetting, ProgressionSetting
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import timed_events
from llamatron.music.note import NoteName
from llamatron.strings import errors
from tests.playback.test_registers import OCTAVE, STEP_SIZE, pattern, song
from tests.support.rendering import render_data, setlist_from_data
from tests.support.ui_testing import fixed_text

CHORDS = 'Chords'
SYNTH = 'synth'
PAD = 'pad'
CHORDS_PATTERN = 'chords'
FIGURE = 'figure'
FOLLOW = 'follow chords'
CHAIN = 'following'
PAD_FOLLOW = 'follow the synth'
PAD_CHAIN = 'following the synth'
MADE = 'one four five six'
MADE_CHAIN = 'making chords'
NO_SUCH_TRACK = 'nobody'
RENAMED = 'Harmony'
# A triad built on a step's degree from the notes of the scale.
TRIAD = 3
# MIDI numbers of C major's notes from C in octave 5, the octave every pattern here is written in.
C = 60
D = 62
E = 64
F = 65
G = 67
G_SHARP = 68
A = 69
B_FLAT = 70
B = 71
OCTAVE_UP = 12
# The figure every test moves, C, E, G and C, and the chords I, IV, V and vi, a step each.
FIGURE_DEGREES = [1, 3, 5, 1]
CHORD_DEGREES = [1, 4, 5, 6]
FOLLOWED = [C, A, D + OCTAVE_UP, A]
ONE_STEP_EACH = '1/4'


def following_data(*, chords=None, chord_rows=None, figure=None, figure_rows=None, chords_from=CHORDS, scenes=1):
    """Return a song's data: the Chords track plays a chord a step, a triad on each degree given, None a rest, and the synth runs Follow Chords over a figure."""
    chords = CHORD_DEGREES if chords is None else chords
    figure = FIGURE_DEGREES if figure is None else figure
    rows = {Row.DEGREE: chords, Row.CHORD: [None if degree is None else TRIAD for degree in chords], **(chord_rows or {})}
    patterns = {CHORDS_PATTERN: pattern(len(chords), **rows), FIGURE: pattern(len(figure), **{Row.DEGREE: figure, **(figure_rows or {})})}
    clips = {CHORDS: {ClipSlotSetting.PATTERN: CHORDS_PATTERN}, SYNTH: {ClipSlotSetting.PATTERN: FIGURE, ClipSlotSetting.CHAINS: [CHAIN]}}
    data = song(patterns=patterns, scenes=[{SceneSetting.TRACKS: {name: dict(clip) for name, clip in clips.items()}} for _ in range(scenes)], tracks=[CHORDS, SYNTH])
    data[Section.FOLLOW_CHORDS] = {FOLLOW: {} if chords_from is None else {FollowChordsSetting.CHORDS_FROM: chords_from}}
    data[Section.CHAINS] = {CHAIN: [{GeneratorKind.FOLLOW_CHORDS: FOLLOW}]}
    return data


def pitches(data, *, scene=0):
    """Return the MIDI numbers each track plays in a scene, in time order, by the track, chords as sorted lists."""
    grid = render_data(data)
    row = grid.get_rows()[scene]
    played = {}
    for column in grid.get_columns():
        clip = grid.get_clip(row=row, column=column)
        if clip is None:
            continue
        starts = {}
        for start, _, midi, _ in sorted(timed_events(clip=clip, scale=clip.get_scale())[0]):
            starts.setdefault(start, []).append(midi)
        played[column.get_name()] = [notes[0] if len(notes) == 1 else sorted(notes) for notes in starts.values()]
    return played


class TestFollowing(unittest.TestCase):

    def test_each_note_moves_to_the_chord_playing_on_the_track_followed(self):
        self.assertEqual(pitches(following_data())[SYNTH], FOLLOWED)

    def test_the_track_followed_plays_its_own_chords_as_ever(self):
        self.assertEqual(pitches(following_data())[CHORDS][0], [C, E, G])

    def test_chords_made_by_a_progression_on_the_track_followed_are_followed_the_same(self):
        data = following_data(chords=[1, 1, 1, 1])
        data[Section.PROGRESSIONS] = {MADE: {ProgressionSetting.CHORDS: CHORD_DEGREES, ProgressionSetting.EVERY: ONE_STEP_EACH}}
        data[Section.CHAINS][MADE_CHAIN] = [{GeneratorKind.PROGRESSION: MADE}]
        data[Section.SCENES][0][SceneSetting.TRACKS][CHORDS][ClipSlotSetting.CHAINS] = [MADE_CHAIN]
        self.assertEqual(pitches(data)[SYNTH], FOLLOWED)

    def test_a_chord_goes_on_through_the_rests_after_it_and_nothing_moves_before_the_first(self):
        self.assertEqual(pitches(following_data(chords=[None, 4, None, None]))[SYNTH], [C, A, C + OCTAVE_UP, F])

    def test_a_chord_of_the_figure_moves_whole(self):
        played = pitches(following_data(chords=[4], figure=[1], figure_rows={Row.CHORD: [TRIAD]}))
        self.assertEqual(played[SYNTH], [[F, A, C + OCTAVE_UP]])

    def test_a_major_chord_from_outside_the_scale_gives_the_figure_its_own_third(self):
        played = pitches(following_data(chords=[3, None, None, None], chord_rows={Row.CHORD: [ChordSymbol.MAJOR, None, None, None]}))
        self.assertEqual(played[SYNTH], [E, G_SHARP, B, E])

    def test_a_triad_says_nothing_of_a_seventh_so_the_figures_seventh_stays_in_the_scale(self):
        played = pitches(following_data(chords=[1, 4], figure=[7, 7]))
        self.assertEqual(played[SYNTH], [B, E + OCTAVE_UP])

    def test_a_seventh_chord_gives_the_figure_its_own_seventh(self):
        played = pitches(following_data(chords=[1], chord_rows={Row.CHORD: [ChordSymbol.DOMINANT7]}, figure=[7]))
        self.assertEqual(played[SYNTH], [B_FLAT])

    def test_a_root_between_two_notes_of_the_scale_moves_the_figure_by_exact_half_steps(self):
        rows = {Row.CHORD: [ChordSymbol.MAJOR, None, None, None], Row.ACCIDENTAL: [Accidental.FLAT, None, None, None]}
        played = pitches(following_data(chords=[7, None, None, None], chord_rows=rows))
        self.assertEqual(played[SYNTH], [B_FLAT, D + OCTAVE_UP, F + OCTAVE_UP, B_FLAT])

    def test_each_scene_follows_its_own_chords(self):
        data = following_data(scenes=2)
        other = 'other chords'
        data[Section.PATTERNS][other] = pattern(1, **{Row.DEGREE: [5], Row.CHORD: [TRIAD]})
        data[Section.SCENES][1][SceneSetting.TRACKS][CHORDS][ClipSlotSetting.PATTERN] = other
        self.assertEqual(pitches(data, scene=1)[SYNTH], [G, B, D + OCTAVE_UP, G])

    def test_a_muted_track_is_still_followed(self):
        data = following_data()
        data[Section.TRACKS][CHORDS] = {TrackSetting.MUTE: True}
        self.assertEqual(pitches(data)[SYNTH], FOLLOWED)


class TestNothingToFollow(unittest.TestCase):

    def unmoved(self):
        return [C, E, G, C]

    def test_no_track_named_moves_nothing(self):
        self.assertEqual(pitches(following_data(chords_from=None))[SYNTH], self.unmoved())

    def test_a_track_the_song_lacks_moves_nothing(self):
        self.assertEqual(pitches(following_data(chords_from=NO_SUCH_TRACK))[SYNTH], self.unmoved())

    def test_a_track_with_no_clip_in_the_scene_moves_nothing(self):
        data = following_data()
        del data[Section.SCENES][0][SceneSetting.TRACKS][CHORDS]
        self.assertEqual(pitches(data)[SYNTH], self.unmoved())

    def test_a_clip_that_follows_its_own_track_is_left_alone(self):
        self.assertEqual(pitches(following_data(chords_from=SYNTH))[SYNTH], self.unmoved())

    def test_a_drum_pattern_is_left_alone(self):
        data = following_data()
        data[Section.PATTERNS][FIGURE].update({PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C, NoteName.E, NoteName.G, NoteName.C]})
        with_drums = pitches(data)[SYNTH]
        data[Section.SCENES][0][SceneSetting.TRACKS][SYNTH].pop(ClipSlotSetting.CHAINS)
        self.assertEqual(with_drums, pitches(data)[SYNTH])


class TestFollowChordsSettings(unittest.TestCase):

    def test_tracks_that_follow_each_other_in_a_circle_are_refused(self):
        data = following_data()
        data[Section.FOLLOW_CHORDS][PAD_FOLLOW] = {FollowChordsSetting.CHORDS_FROM: SYNTH}
        data[Section.CHAINS][PAD_CHAIN] = [{GeneratorKind.FOLLOW_CHORDS: PAD_FOLLOW}]
        data[Section.SCENES][0][SceneSetting.TRACKS][CHORDS][ClipSlotSetting.CHAINS] = [PAD_CHAIN]
        with self.assertRaises(SongFileError) as refused:
            render_data(data)
        self.assertIn(fixed_text(errors.ERR_CIRCULAR_FOLLOW), str(refused.exception))

    def test_a_track_can_follow_a_track_that_follows_another(self):
        data = following_data()
        data[Section.TRACKS][PAD] = {}
        data[Section.FOLLOW_CHORDS][PAD_FOLLOW] = {FollowChordsSetting.CHORDS_FROM: SYNTH}
        data[Section.CHAINS][PAD_CHAIN] = [{GeneratorKind.FOLLOW_CHORDS: PAD_FOLLOW}]
        data[Section.SCENES][0][SceneSetting.TRACKS][PAD] = {ClipSlotSetting.PATTERN: FIGURE, ClipSlotSetting.CHAINS: [PAD_CHAIN]}
        self.assertEqual(len(pitches(data)[PAD]), len(FIGURE_DEGREES))

    def test_renaming_the_track_followed_renames_it_in_the_settings(self):
        setlist = setlist_from_data(following_data())
        setlist.get_songs()[0].rename_item(section=Section.TRACKS, old=CHORDS, new=RENAMED)
        self.assertEqual(setlist.get_generator_settings(kind=GeneratorKind.FOLLOW_CHORDS, name=FOLLOW).get_chords_from(), RENAMED)

    def test_a_track_that_is_not_text_is_refused(self):
        data = following_data()
        data[Section.FOLLOW_CHORDS][FOLLOW] = {FollowChordsSetting.CHORDS_FROM: OCTAVE}
        with self.assertRaises(SongFileError):
            setlist_from_data(data)

    def test_the_steps_here_are_a_quarter_each(self):
        self.assertEqual(STEP_SIZE, ONE_STEP_EACH)


if __name__ == '__main__':
    unittest.main()
