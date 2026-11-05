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

from src.chord import Chord, ChordType
from src.generators.base import ClipGenerator
from src.legacy.generators.register import Register
from src.note import Degree, Note, Rest
from src.song import Clip

LOW, HIGH = Note('C', 3), Note('B', 3)


def fold(*notes):
    return Register(LOW, HIGH).generate(Clip(notes=list(notes))).notes


class TestRegister(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Register(LOW, HIGH), ClipGenerator)

    def test_notes_inside_stay(self):
        self.assertEqual(fold(Note('E', 3, 1)), [Note('E', 3, 1)])

    def test_notes_above_come_down_by_octaves(self):
        self.assertEqual(fold(Note('E', 6, 1)), [Note('E', 3, 1)])

    def test_notes_below_go_up_by_octaves(self):
        self.assertEqual(fold(Note('E', 1, 1)), [Note('E', 3, 1)])

    def test_edges_are_allowed(self):
        self.assertEqual(fold(Note('C', 3, 1), Note('B', 3, 1)), [Note('C', 3, 1), Note('B', 3, 1)])

    def test_chord_notes_move_separately_and_stay_the_same_notes(self):
        chord = Note('G', 3, 1).to_chord(ChordType.MAJOR)
        result = fold(chord)[0]
        self.assertIsInstance(result, Chord)
        self.assertEqual(sorted(note.midi_number for note in result.notes), [38, 43, 47])

    def test_rests_and_degrees_stay(self):
        self.assertEqual(fold(Rest(1), Degree(2, 1)), [Rest(1), Degree(2, 1)])

    def test_keeps_details_and_leaves_the_original_alone(self):
        original = Clip('Riff', notes=[Note('E', 6, 1)], length=2)
        result = Register(LOW, HIGH).generate(original)
        self.assertEqual((result.name, result.length), ('Riff', 2))
        self.assertEqual(original.notes, [Note('E', 6, 1)])

    def test_rejects_a_range_smaller_than_an_octave(self):
        with self.assertRaises(ValueError):
            Register(Note('C', 3), Note('A', 3)).generate(Clip())

    def test_rejects_invalid_values(self):
        for value in [None, 36, 'C3']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Register(value, HIGH)
                with self.assertRaises(ValueError):
                    Register(LOW, value)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Register(LOW, HIGH)
        generator.low = Note('D', 3)
        self.assertEqual(generator.low, Note('D', 3))
        with self.assertRaises(ValueError):
            generator.low = None
        self.assertEqual(generator.low, Note('D', 3))


if __name__ == '__main__':
    unittest.main()
