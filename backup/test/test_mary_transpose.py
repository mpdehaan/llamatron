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

import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

import mido

import demo.mary_arp
import demo.mary_transpose
from llamatron.renderers.clip_tree import ClipTree

# Each note of C major moves to the same degree of B flat minor.
FIRST_MELODY = [49, 48, 46, 48, 49, 49, 49, 48, 48, 48, 49, 53, 53]
SECOND_MELODY = [49, 48, 46, 48, 49, 49, 49, 49, 48, 48, 49, 48, 46]
C_CHORD_ARP = [34, 37, 41, 37, 34, 37, 41, 37]
G7_CHORD_ARP = [29, 32, 36, 39, 36, 32, 29, 32]
CHORDS = C_CHORD_ARP + C_CHORD_ARP + G7_CHORD_ARP + C_CHORD_ARP


class TestMaryTransposeDemo(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.input_directory = os.path.join(temporary.name, 'input')
        self.output_directory = os.path.join(temporary.name, 'output')
        for name, value in [
            ('INPUT_DIRECTORY', self.input_directory),
            ('OUTPUT_DIRECTORY', self.output_directory),
        ]:
            patcher = mock.patch.object(demo.mary_transpose, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_demo(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            demo.mary_transpose.main()
        return output.getvalue()

    def write_input(self):
        ClipTree(self.input_directory, demo.mary_arp.build_song()).render()

    def read_input_files(self):
        contents = {}
        for name in os.listdir(self.input_directory):
            with open(os.path.join(self.input_directory, name), 'rb') as file:
                contents[name] = file.read()
        return contents

    def played(self, filename):
        midi_file = mido.MidiFile(os.path.join(self.output_directory, filename))
        return [m.note for m in midi_file.tracks[0] if m.type == 'note_on']

    def test_missing_input_prints_a_message_and_writes_nothing(self):
        output = self.run_demo()
        self.assertIn('please run this demo first', output)
        self.assertIn('demo.mary_arp', output)
        self.assertFalse(os.path.exists(self.output_directory))

    def test_writes_one_file_per_clip(self):
        self.write_input()
        self.run_demo()
        self.assertEqual(
            sorted(os.listdir(self.output_directory)),
            ['001-001.mid', '001-002.mid', '002-001.mid', '002-002.mid'],
        )

    def test_melody_moves_to_b_flat_minor(self):
        self.write_input()
        self.run_demo()
        self.assertEqual(self.played('001-001.mid'), FIRST_MELODY)
        self.assertEqual(self.played('002-001.mid'), SECOND_MELODY)

    def test_chords_move_to_b_flat_minor(self):
        self.write_input()
        self.run_demo()
        self.assertEqual(self.played('001-002.mid'), CHORDS)
        self.assertEqual(self.played('002-002.mid'), CHORDS)

    def test_rhythm_and_tempo_stay_the_same(self):
        self.write_input()
        self.run_demo()
        for filename in os.listdir(self.output_directory):
            with self.subTest(filename=filename):
                before = mido.MidiFile(os.path.join(self.input_directory, filename))
                after = mido.MidiFile(os.path.join(self.output_directory, filename))
                self.assertEqual(
                    [(m.type, m.time) for m in before.tracks[0]],
                    [(m.type, m.time) for m in after.tracks[0]],
                )
                self.assertEqual(before.length, after.length)

    def test_input_files_are_left_alone(self):
        self.write_input()
        before = self.read_input_files()
        self.run_demo()
        self.assertEqual(self.read_input_files(), before)


if __name__ == '__main__':
    unittest.main()
