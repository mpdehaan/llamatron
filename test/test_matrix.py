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

import os
import tempfile
import unittest

import mido

from llamatron.note import Note
from llamatron.renderers.clip_tree import ClipTree
from llamatron.clip_grid import Clip, Scene, ClipGrid, Track


class TestMatrix(unittest.TestCase):

    def test_matrix(self):
        # A song at the default tempo of 120 bpm, with a 3 by 3 grid.
        song = ClipGrid()
        scenes = [song.add_scene(Scene(name)) for name in ['A', 'B', 'C']]
        tracks = [song.add_track(Track(name)) for name in ['T1', 'T2', 'T3']]

        # Every clip plays one octave of C major in quarter notes, from C4 up to C5.
        c_major = [Note(*note, 0.25) for note in zip('CDEFGABC', [4, 4, 4, 4, 4, 4, 4, 5])]
        for scene in scenes:
            for track in tracks:
                song.set_clip(scene, track, Clip(notes=c_major))

        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory, song).render()

            self.assertEqual(sorted(os.listdir(directory)), [
                '001-001.mid', '001-002.mid', '001-003.mid',
                '002-001.mid', '002-002.mid', '002-003.mid',
                '003-001.mid', '003-002.mid', '003-003.mid',
            ])

            for filename in os.listdir(directory):
                with self.subTest(filename=filename):
                    midi_file = mido.MidiFile(os.path.join(directory, filename))
                    played = [
                        message.note
                        for message in midi_file.tracks[0]
                        if message.type == 'note_on'
                    ]
                    self.assertEqual(played, [48, 50, 52, 53, 55, 57, 59, 60])
                    # Eight quarter notes at 120 bpm last four seconds.
                    self.assertAlmostEqual(midi_file.length, 4)


if __name__ == '__main__':
    unittest.main()
