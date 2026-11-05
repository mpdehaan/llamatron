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

import os
import tempfile
import unittest

import mido

from demo.scales import build_song
from src.note import Note
from src.renderers.clip_tree import ClipTree
from src.scale import ScaleType


class TestScalesDemo(unittest.TestCase):

    def setUp(self):
        self.song = build_song()
        self.track = self.song.tracks[0]
        self.clips = [self.song.get_clip(scene, self.track) for scene in self.song.scenes]

    def played(self, clip):
        return [note.midi_number for note in clip.notes]

    def test_has_one_track(self):
        self.assertEqual(len(self.song.tracks), 1)

    def test_has_one_scene_and_clip_for_every_scale_type(self):
        self.assertEqual(len(self.song.scenes), len(ScaleType))
        self.assertEqual([clip.scale.typ for clip in self.clips], list(ScaleType))

    def test_every_clip_is_quarter_notes_starting_on_c(self):
        for clip in self.clips:
            with self.subTest(clip=clip.name):
                self.assertEqual(clip.notes[0], Note('C', 4, 0.25))
                self.assertEqual({note.length for note in clip.notes}, {0.25})

    def test_every_clip_plays_its_own_scale(self):
        expected = {
            ScaleType.MAJOR: [48, 50, 52, 53, 55, 57, 59, 60],
            ScaleType.MINOR: [48, 50, 51, 53, 55, 56, 58, 60],
            ScaleType.MAJOR_PENTATONIC: [48, 50, 52, 55, 57, 60],
            ScaleType.WHOLE_TONE: [48, 50, 52, 54, 56, 58, 60],
            ScaleType.MIXOLYDIAN: [48, 50, 52, 53, 55, 57, 58, 60],
            ScaleType.CHROMATIC: [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60],
            ScaleType.BEBOP_DOMINANT: [48, 50, 52, 53, 55, 57, 58, 59, 60],
        }
        for clip in self.clips:
            if clip.scale.typ in expected:
                with self.subTest(clip=clip.name):
                    self.assertEqual(self.played(clip), expected[clip.scale.typ])

    def test_every_clip_plays_its_whole_scale_and_ends_an_octave_above_the_root(self):
        for clip in self.clips:
            with self.subTest(clip=clip.name):
                self.assertEqual(len(clip.notes), len(clip.scale.typ.value) + 1)
                self.assertEqual(clip.notes[-1].midi_number, 60)

    def test_every_clip_sounds_different(self):
        played = {tuple(self.played(clip)) for clip in self.clips}
        self.assertEqual(len(played), len(self.clips))

    def test_renders_one_file_per_scale_type_named_after_it(self):
        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory, self.song).render()
            self.assertEqual(
                sorted(os.listdir(directory)),
                sorted(
                    f'{index:03d}-000-{scale_type.name}.mid'
                    for index, scale_type in enumerate(ScaleType)
                ),
            )


if __name__ == '__main__':
    unittest.main()
