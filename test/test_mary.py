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

from demo.mary import CHORDS, MELODY, build_song
from src.renderers.clip_tree import ClipTree

WHOLE_NOTES_PER_SCENE = 4


class TestMary(unittest.TestCase):

    def test_melody_has_the_expected_notes(self):
        played = [
            f'{note.name}{note.octave_number}'
            for scene in MELODY
            for note in scene
        ]
        self.assertEqual(' '.join(played), (
            'E4 D4 C4 D4 E4 E4 E4 D4 D4 D4 E4 G4 G4 '
            'E4 D4 C4 D4 E4 E4 E4 E4 D4 D4 E4 D4 C4'
        ))

    def test_every_clip_is_four_measures_long(self):
        for scene in [*MELODY, *CHORDS]:
            self.assertEqual(sum(position.length for position in scene), WHOLE_NOTES_PER_SCENE)

    def test_renders_two_scenes_of_two_tracks(self):
        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory, build_song()).render()
            self.assertEqual(
                sorted(os.listdir(directory)),
                ['001-001.mid', '001-002.mid', '002-001.mid', '002-002.mid'],
            )
            for filename in os.listdir(directory):
                with self.subTest(filename=filename):
                    midi_file = mido.MidiFile(os.path.join(directory, filename))
                    # Four measures of four quarter notes at 120 bpm last eight seconds.
                    self.assertAlmostEqual(midi_file.length, 8)


if __name__ == '__main__':
    unittest.main()
