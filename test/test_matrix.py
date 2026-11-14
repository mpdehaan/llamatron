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

import os
import tempfile
import unittest

import mido

from llamatron.music.note import Note
from llamatron.exporters.clip_tree import ClipTree
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn
from llamatron.exporters.midi_messages import NOTE_ON_MESSAGE

# Names the tests give to their own things, and other values they use.
A = 'A'
B = 'B'
C = 'C'
T1 = 'T1'
T2 = 'T2'
T3 = 'T3'
# What the clip files are named under, and how each is named after its scene and track.
EXPORT = 'song'
CLIP_FILE = EXPORT + '_clip_s_{scene:03d}-{scene_name}-t_{track:03d}-{track_name}.mid'
CDEFGABC = 'CDEFGABC'


class TestMatrix(unittest.TestCase):

    def test_matrix(self):
        # A song at the default tempo of 120 bpm, with a 3 by 3 grid.
        song = ClipGrid()
        scenes = [song.add_row(ClipRow(name=name)) for name in [A, B, C]]
        tracks = [song.add_column(ClipColumn(name=name)) for name in [T1, T2, T3]]

        # Every clip plays one octave of C major in quarter notes, from C4 up to C5.
        c_major = [Note(name=name, octave_number=octave, length=0.25) for name, octave in zip(CDEFGABC, [4, 4, 4, 4, 4, 4, 4, 5])]
        for scene in scenes:
            for track in tracks:
                song.set_clip(row=scene, column=track, clip=Clip(notes=c_major))

        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory=directory, grid=song, name=EXPORT).export()

            self.assertEqual(sorted(os.listdir(directory)), [
                CLIP_FILE.format(scene=scene + 1, scene_name=scene_name, track=track + 1, track_name=track_name)
                for scene, scene_name in enumerate([A, B, C]) for track, track_name in enumerate([T1, T2, T3])
            ])

            for filename in os.listdir(directory):
                with self.subTest(filename=filename):
                    midi_file = mido.MidiFile(os.path.join(directory, filename))
                    played = [
                        message.note
                        for message in midi_file.tracks[0]
                        if message.type == NOTE_ON_MESSAGE
                    ]
                    self.assertEqual(played, [48, 50, 52, 53, 55, 57, 59, 60])
                    # Eight quarter notes at 120 bpm last four seconds.
                    self.assertAlmostEqual(midi_file.length, 4)


if __name__ == '__main__':
    unittest.main()
