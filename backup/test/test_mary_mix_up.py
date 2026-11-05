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
from collections import Counter

import mido

import demo.mary
import demo.mary_mix_up
from llamatron.renderers.clip_tree import ClipTree

MELODY_FILES = ['001-001.mid', '002-001.mid']
CHORD_FILES = ['001-002.mid', '002-002.mid']


def render(song, directory):
    ClipTree(directory, song).render()
    return {
        filename: mido.MidiFile(os.path.join(directory, filename))
        for filename in os.listdir(directory)
    }


def played(midi_file):
    return [m.note for m in midi_file.tracks[0] if m.type == 'note_on']


class TestMaryMixUpDemo(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.original = render(demo.mary.build_song(), os.path.join(temporary.name, 'mary'))
        self.mixed = render(demo.mary_mix_up.build_song(), os.path.join(temporary.name, 'new'))

    def test_chords_are_untouched(self):
        for filename in CHORD_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(self.mixed[filename].tracks[0], self.original[filename].tracks[0])

    def test_melody_is_shuffled_but_keeps_the_same_notes(self):
        for filename in MELODY_FILES:
            with self.subTest(filename=filename):
                before, after = played(self.original[filename]), played(self.mixed[filename])
                self.assertNotEqual(after, before)
                self.assertEqual(Counter(after), Counter(before))

    def test_clips_stay_four_measures_long(self):
        for filename, midi_file in self.mixed.items():
            with self.subTest(filename=filename):
                self.assertAlmostEqual(midi_file.length, 8)

    def test_same_result_every_time(self):
        with tempfile.TemporaryDirectory() as directory:
            again = render(demo.mary_mix_up.build_song(), directory)
            for filename in MELODY_FILES:
                with self.subTest(filename=filename):
                    self.assertEqual(again[filename].tracks[0], self.mixed[filename].tracks[0])


if __name__ == '__main__':
    unittest.main()
