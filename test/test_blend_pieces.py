# noose6: a Python language and framework for producing MIDI clips.
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

"""Checks that every song built with BlendPiece must pass, whatever its tunes are.

If one of these fails for a new pair of tunes, fix the library, not the demo or this test.
"""

import contextlib
import gzip
import io
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from unittest import mock

import demo.blend_base as base
import demo.gifts_to_sun as gifts_to_sun
import demo.tunes as tunes
from src.analyzers.clash_finder import ClashFinder
from src.note import Rest
from src.renderers.timing import timed_notes


def pitches(clip):
    return [pitch for _, _, pitch in timed_notes(clip, clip.scale)[0]]


class BlendPieceChecks:

    module = None
    first_scale = None
    second_scale = None

    def setUp(self):
        self.song = self.module.build_song()
        self.melody_track, self.chord_track, self.bass_track, self.kick_track, self.snare_track = self.song.tracks
        self.parts = list(zip(self.song.scenes[1:-1], self.module.PROGRESSION))

    def clip(self, scene, track):
        return self.song.get_clip(scene, track)

    def test_the_tune_ahead_sets_the_scale(self):
        scales = {
            part.amount: self.clip(scene, self.melody_track).scale for scene, part in self.parts
        }
        for amount, scale in scales.items():
            expected = self.first_scale if amount <= 50 else self.second_scale
            with self.subTest(amount=amount):
                self.assertEqual((scale.root.name, scale.typ), expected)

    def test_every_morph_note_is_in_the_scale_of_the_tune_ahead(self):
        for scene, part in self.parts:
            melody = self.clip(scene, self.melody_track)
            allowed = {(melody.scale.root.midi_number + step) % 12 for step in melody.scale.typ.value}
            with self.subTest(scene=scene.name):
                self.assertLessEqual({pitch % 12 for pitch in pitches(melody)}, allowed)
                self.assertLessEqual({pitch % 12 for pitch in pitches(self.clip(scene, self.chord_track))}, allowed)

    def test_chords_never_clash_with_the_melody(self):
        for scene in self.song.scenes:
            melody, chords = self.clip(scene, self.melody_track), self.clip(scene, self.chord_track)
            with self.subTest(scene=scene.name):
                self.assertEqual(ClashFinder().analyze(melody, chords), [])

    def test_bass_never_clashes_with_the_chords(self):
        for scene in self.song.scenes[1:]:
            bass, chords = self.clip(scene, self.bass_track), self.clip(scene, self.chord_track)
            with self.subTest(scene=scene.name):
                self.assertEqual(ClashFinder().analyze(bass, chords), [])

    def test_every_part_stays_in_its_own_space(self):
        for scene in self.song.scenes:
            melody, chords = pitches(self.clip(scene, self.melody_track)), pitches(self.clip(scene, self.chord_track))
            with self.subTest(scene=scene.name):
                self.assertLess(max(chords), min(melody))
                bass = self.clip(scene, self.bass_track)
                if bass is not None:
                    self.assertLess(max(pitches(bass)), min(chords))

    def test_every_note_is_on_a_piano(self):
        for scene in self.song.scenes:
            for track in self.song.tracks:
                clip = self.clip(scene, track)
                if clip is not None:
                    with self.subTest(scene=scene.name, track=track.name):
                        self.assertGreaterEqual(min(pitches(clip)), 21)
                        self.assertLessEqual(max(pitches(clip)), 108)

    def test_every_blend_mode_is_shown(self):
        self.assertEqual(
            {part.blend_mode for part in self.module.PROGRESSION},
            {base.BlendMode.STRONG_BEATS, base.BlendMode.CONTOUR, base.BlendMode.SLICES},
        )

    def test_every_track_in_a_scene_lasts_the_same_time(self):
        for scene in self.song.scenes:
            lengths = {
                self.clip(scene, track).total_length() for track in self.song.tracks
                if self.clip(scene, track) is not None
            }
            with self.subTest(scene=scene.name):
                self.assertEqual(len(lengths), 1)

    def test_drums_play_on_the_right_beats(self):
        for scene in self.song.scenes:
            measures = int(self.clip(scene, self.melody_track).total_length())
            kick = timed_notes(self.clip(scene, self.kick_track), None)[0]
            snare = timed_notes(self.clip(scene, self.snare_track), None)[0]
            with self.subTest(scene=scene.name):
                self.assertEqual(sorted(start for start, _, _ in kick), list(range(measures)))
                self.assertEqual(
                    sorted(start for start, _, _ in snare),
                    [measure + Fraction(beat, 4) for measure in range(measures) for beat in (1, 2, 3)],
                )

    def test_every_run_gives_the_same_song(self):
        again = self.module.build_song()
        for first, second in zip(self.song.scenes, again.scenes):
            for track, other in zip(self.song.tracks, again.tracks):
                before, after = self.clip(first, track), again.get_clip(second, other)
                if before is not None:
                    with self.subTest(scene=first.name, track=track.name):
                        self.assertEqual(before.played_notes(), after.played_notes())

    def test_renders_to_ableton_with_both_views(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, 'piece')
            with mock.patch.object(self.module, 'OUTPUT_DIRECTORY', directory):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main()
            with open(os.path.join(directory, 'piece.als'), 'rb') as file:
                live_set = ET.fromstring(gzip.decompress(file.read())).find('LiveSet')
        tracks = live_set.find('Tracks').findall('MidiTrack')
        self.assertEqual(len(tracks), 5)
        self.assertEqual(len(live_set.find('Scenes')), len(self.song.scenes))
        for track in tracks:
            arrangement = track.find('DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events')
            self.assertGreaterEqual(len(arrangement), len(self.song.scenes) - 1)

    def test_renders_to_midi_files(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, 'piece')
            with mock.patch.object(self.module, 'OUTPUT_DIRECTORY', directory):
                with mock.patch.object(self.module, 'USE_ABLETON', False):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main()
            self.assertEqual(len(os.listdir(directory)), len(self.song.scenes) * 5 - 1)


class TestGiftsToSun(BlendPieceChecks, unittest.TestCase):

    module = gifts_to_sun
    first_scale = ('C', tunes.C_MAJOR.typ)
    second_scale = ('A', tunes.A_MINOR.typ)


class TestCharts(unittest.TestCase):

    def test_charts_can_use_chords_outside_the_scale_and_two_in_a_measure(self):
        chart = tunes.chart('C:1/2 E7:1/2 A7 Dm', 1, tunes.C_MAJOR)
        self.assertEqual(chart.total_length(), 3)
        self.assertEqual(
            sorted(note.midi_number % 12 for note in chart.notes[1].notes),
            sorted(pitch % 12 for pitch in (40, 44, 47, 50)),
        )


class TestChecksCatchProblems(unittest.TestCase):

    def test_blend_piece_rejects_tunes_of_different_lengths(self):
        with self.assertRaises(ValueError):
            base.BlendPiece(
                'A', tunes.SIMPLE_GIFTS, tunes.SIMPLE_GIFTS_CHORDS,
                'B', tunes.RISING_SUN, tunes.RISING_SUN_CHORDS,
                [], 9, arp_step=Fraction(1, 8), flowing_step=Fraction(1, 8),
            )


if __name__ == '__main__':
    unittest.main()
