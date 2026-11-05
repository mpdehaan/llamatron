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

import demo.mary
import demo.mary_arp
import demo.mary_repeat
from src.renderers.clip_tree import ClipTree

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


class TestMaryGenerators(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.original = render(demo.mary.build_song(), os.path.join(temporary.name, 'mary'))
        self.repeated = render(demo.mary_repeat.build_song(), os.path.join(temporary.name, 'repeat'))
        self.arpeggiated = render(demo.mary_arp.build_song(), os.path.join(temporary.name, 'arp'))

    def test_melody_is_untouched(self):
        for filename in MELODY_FILES:
            with self.subTest(filename=filename):
                original = self.original[filename].tracks[0]
                self.assertEqual(self.repeated[filename].tracks[0], original)
                self.assertEqual(self.arpeggiated[filename].tracks[0], original)

    def test_original_chords_are_whole_notes(self):
        c_chord, g7_chord = [36, 40, 43], [31, 35, 38, 41]
        for filename in CHORD_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(
                    played(self.original[filename]),
                    c_chord + c_chord + g7_chord + c_chord,
                )
                self.assertAlmostEqual(self.original[filename].length, 8)

    def test_repeat_plays_each_chord_as_two_half_notes(self):
        c_chord, g7_chord = [36, 40, 43], [31, 35, 38, 41]
        for filename in CHORD_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(
                    played(self.repeated[filename]),
                    c_chord * 2 + c_chord * 2 + g7_chord * 2 + c_chord * 2,
                )
                self.assertEqual(
                    {m.time for m in self.repeated[filename].tracks[0] if m.type == 'note_off'},
                    {0, 960},
                )
                self.assertAlmostEqual(self.repeated[filename].length, 8)

    def test_arp_plays_the_expected_notes_at_the_same_total_length(self):
        c_chord = [36, 40, 43, 40, 36, 40, 43, 40]
        g7_chord = [31, 35, 38, 41, 38, 35, 31, 35]
        for filename in CHORD_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(
                    played(self.arpeggiated[filename]),
                    c_chord + c_chord + g7_chord + c_chord,
                )
                self.assertAlmostEqual(self.arpeggiated[filename].length, 8)


if __name__ == '__main__':
    unittest.main()
