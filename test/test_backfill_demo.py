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

from demo.backfill import build_song
from src.renderers.clip_tree import ClipTree

TICKS_PER_SIXTEENTH = 120

# (MIDI number, position in sixteenth notes) for each clip.
RUN_0 = [(48, 0), (60, 4), (48, 8), (55, 12)]
RUN_1 = [(48, 0), (53, 2), (60, 4), (53, 6), (48, 8), (52, 10), (55, 12)]
RUN_2 = [
    (48, 0), (50, 1), (53, 2), (57, 3), (60, 4), (57, 5), (53, 6), (50, 7),
    (48, 8), (50, 9), (52, 10), (53, 11), (55, 12),
]


class TestBackfillDemo(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name
        ClipTree(self.directory, build_song()).render()

    def midi_file(self, filename):
        return mido.MidiFile(os.path.join(self.directory, filename))

    def played(self, filename):
        tick = 0
        result = []
        for message in self.midi_file(filename).tracks[0]:
            tick += message.time
            if message.type == 'note_on':
                result.append((message.note, tick // TICKS_PER_SIXTEENTH))
        return result

    def test_writes_one_named_file_per_scene(self):
        self.assertEqual(sorted(os.listdir(self.directory)), [
            '001-001-Run_0.mid', '002-001-Run_1.mid', '003-001-Run_2.mid',
        ])

    def test_each_scene_fills_in_more_of_the_pattern(self):
        self.assertEqual(self.played('001-001-Run_0.mid'), RUN_0)
        self.assertEqual(self.played('002-001-Run_1.mid'), RUN_1)
        self.assertEqual(self.played('003-001-Run_2.mid'), RUN_2)

    def test_every_clip_lasts_two_seconds(self):
        for filename in os.listdir(self.directory):
            with self.subTest(filename=filename):
                self.assertAlmostEqual(self.midi_file(filename).length, 2)

    def test_original_notes_stay_on_their_times(self):
        for filename in ['002-001-Run_1.mid', '003-001-Run_2.mid']:
            with self.subTest(filename=filename):
                self.assertLessEqual(set(RUN_0), set(self.played(filename)))


if __name__ == '__main__':
    unittest.main()
