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
from src.generators.reverse import Reverse
from src.note import Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

C4 = Note('C', 4, 0.25)
D4 = Note('D', 4, 0.5)
E4 = Note('E', 4, 0.125)
SCALE = Scale(Note('C', 0, 0.25), ScaleType.MAJOR)


class TestReverse(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Reverse(), ClipGenerator)

    def test_reverses_the_notes(self):
        self.assertEqual(Reverse().generate(Clip(notes=[C4, D4, E4])).notes, [E4, D4, C4])

    def test_notes_keep_their_own_lengths(self):
        result = Reverse().generate(Clip(notes=[C4, D4, E4])).notes
        self.assertEqual([note.length for note in result], [0.125, 0.5, 0.25])

    def test_reverses_rests_and_chords(self):
        chord = C4.to_chord(ChordType.MAJOR)
        result = Reverse().generate(Clip(notes=[C4, Rest(0.25), chord])).notes
        self.assertEqual(result, [chord, Rest(0.25), C4])

    def test_chord_notes_stay_together(self):
        chord = Chord([Note('C', 4, 1), Note('E', 4, 0.5)])
        self.assertEqual(Reverse().generate(Clip(notes=[chord])).notes, [chord])

    def test_twice_gives_the_original(self):
        original = Clip(notes=[C4, Rest(0.25), D4])
        result = Reverse().generate(Reverse().generate(original))
        self.assertEqual(result.notes, original.notes)

    def test_empty_clip_stays_empty(self):
        self.assertEqual(Reverse().generate(Clip()).notes, [])

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[C4], scale=SCALE)
        result = Reverse().generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, SCALE)
        self.assertIsNone(result.length)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[C4, D4])
        Reverse().generate(original)
        self.assertEqual(original.notes, [C4, D4])

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [C4]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Reverse().generate(value)


class TestReverseWithSetLength(unittest.TestCase):

    def test_silence_at_the_end_moves_to_the_start(self):
        result = Reverse().generate(Clip(notes=[C4], length=1))
        self.assertEqual(result.notes, [Rest(0.75), C4])
        self.assertEqual(result.length, 1)

    def test_only_the_part_that_plays_is_reversed(self):
        result = Reverse().generate(Clip(notes=[C4, D4, E4], length=0.5))
        self.assertEqual(result.notes, [Note('D', 4, 0.25), C4])
        self.assertEqual(result.length, 0.5)

    def test_empty_clip_is_silent(self):
        result = Reverse().generate(Clip(length=1))
        self.assertEqual(result.notes, [Rest(1)])

    def test_twice_keeps_the_timing(self):
        result = Reverse().generate(Reverse().generate(Clip(notes=[C4], length=1)))
        self.assertEqual(result.notes, [C4, Rest(0.75)])


if __name__ == '__main__':
    unittest.main()
