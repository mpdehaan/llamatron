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

import unittest

from src.chord import ChordType
from src.note import Note
from src.score import Score, ramp
from src.song import Clip

MELODY = Clip(notes=[Note('C', 4, 1)])
CHORDS = Clip(notes=[Note('C', 3, 1).to_chord(ChordType.MAJOR)])


class TestRamp(unittest.TestCase):

    def test_includes_both_ends(self):
        self.assertEqual(ramp(0, 100, 5), [0, 25, 50, 75, 100])

    def test_two_steps(self):
        self.assertEqual(ramp(0, 100, 2), [0, 100])

    def test_can_go_down(self):
        self.assertEqual(ramp(100, 0, 3), [100, 50, 0])

    def test_rejects_invalid_steps(self):
        for steps in [1, 0, 2.5, '3', None, True]:
            with self.subTest(steps=steps):
                with self.assertRaises(ValueError):
                    ramp(0, 100, steps)


class TestScore(unittest.TestCase):

    def setUp(self):
        self.score = Score(tempo=90)

    def test_has_a_tempo_and_named_tracks(self):
        self.assertEqual(self.score.song.tempo, 90)
        self.assertEqual([track.name for track in self.score.song.tracks], ['Melody', 'Chords', 'Bass', 'kick', 'snare'])

    def test_drums_go_on_their_tracks_and_are_optional(self):
        scene = self.score.play('First', MELODY, kick=MELODY, snare=CHORDS)
        self.assertEqual(self.score.song.get_clip(scene, self.score.kick_track).notes, MELODY.notes)
        self.assertEqual(self.score.song.get_clip(scene, self.score.snare_track).notes, CHORDS.notes)
        without = self.score.play('Second', MELODY)
        self.assertIsNone(self.score.song.get_clip(without, self.score.kick_track))
        self.assertIsNone(self.score.song.get_clip(without, self.score.snare_track))

    def test_bass_goes_on_its_track_and_is_optional(self):
        with_bass = self.score.play('First', MELODY, CHORDS, MELODY)
        without = self.score.play('Second', MELODY, CHORDS)
        self.assertEqual(self.score.song.get_clip(with_bass, self.score.bass_track).name, 'First')
        self.assertIsNone(self.score.song.get_clip(without, self.score.bass_track))

    def test_default_tempo(self):
        self.assertEqual(Score().song.tempo, 120)

    def test_adds_scenes_in_order_with_names(self):
        self.score.play('First', MELODY)
        self.score.play('Second', MELODY)
        self.assertEqual([scene.name for scene in self.score.song.scenes], ['First', 'Second'])

    def test_clips_go_on_their_tracks_with_the_scene_name(self):
        scene = self.score.play('Verse', MELODY, CHORDS)
        melody = self.score.song.get_clip(scene, self.score.melody_track)
        chords = self.score.song.get_clip(scene, self.score.chord_track)
        self.assertEqual(melody.notes, MELODY.notes)
        self.assertEqual(chords.notes, CHORDS.notes)
        self.assertEqual((melody.name, chords.name), ('Verse', 'Verse'))

    def test_chords_are_optional(self):
        scene = self.score.play('Verse', MELODY)
        self.assertIsNone(self.score.song.get_clip(scene, self.score.chord_track))

    def test_leaves_the_clips_given_alone(self):
        self.score.play('Verse', MELODY, CHORDS)
        self.assertIsNone(MELODY.name)


if __name__ == '__main__':
    unittest.main()
