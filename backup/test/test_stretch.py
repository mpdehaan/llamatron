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

import unittest
from fractions import Fraction

from llamatron.chord import Chord
from llamatron.generators.base import ClipGenerator
from llamatron.legacy.generators.stretch import Stretch
from llamatron.note import Degree, Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

C4 = Note('C', 4, 0.25)
SCALE = Scale(Note('C', 4), ScaleType.MAJOR)


class TestStretch(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Stretch(2), ClipGenerator)

    def test_notes_and_rests_change_by_the_factor(self):
        result = Stretch(2).generate(Clip(notes=[C4, Rest(0.5)]))
        self.assertEqual(result.notes, [Note('C', 4, 0.5), Rest(1)])

    def test_can_shorten(self):
        self.assertEqual(Stretch(0.5).generate(Clip(notes=[C4])).notes, [Note('C', 4, 0.125)])

    def test_six_eight_measure_lasts_as_long_as_four_four(self):
        result = Stretch(Fraction(4, 3)).generate(Clip(notes=[Note('C', 4, Fraction(3, 4))]))
        self.assertEqual(result.total_length(), 1)

    def test_every_chord_note_changes(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)])
        result = Stretch(2).generate(Clip(notes=[chord]))
        self.assertEqual(result.notes, [Chord([Note('C', 4, 1), Note('E', 4, 0.5)])])

    def test_degrees_stay_degrees(self):
        self.assertEqual(Stretch(2).generate(Clip(notes=[Degree(3, 0.25)])).notes, [Degree(3, 0.5)])

    def test_set_length_changes_too(self):
        self.assertEqual(Stretch(2).generate(Clip(notes=[C4], length=1)).length, 2)
        self.assertIsNone(Stretch(2).generate(Clip(notes=[C4])).length)

    def test_uses_note_length(self):
        self.assertEqual(
            Stretch(2).generate(Clip(notes=[1], note_length=0.25)).notes,
            [Degree(1, 0.5)],
        )

    def test_float_factor_stays_exact(self):
        result = Stretch(1 / 3).generate(Clip(notes=[Note('C', 4, 0.75)]))
        self.assertEqual(result.notes[0].length, 0.25)

    def test_keeps_details_and_leaves_the_original_alone(self):
        original = Clip('Riff', notes=[C4], scale=SCALE)
        result = Stretch(2).generate(original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, SCALE)
        self.assertEqual(original.notes, [C4])

    def test_rejects_invalid_factors(self):
        for factor in [0, -1, '2', None, True, float('nan'), float('inf')]:
            with self.subTest(factor=factor):
                with self.assertRaises(ValueError):
                    Stretch(factor)

    def test_factor_can_be_edited_and_is_validated(self):
        generator = Stretch(2)
        generator.factor = 3
        self.assertEqual(generator.factor, 3)
        with self.assertRaises(ValueError):
            generator.factor = 0
        self.assertEqual(generator.factor, 3)


if __name__ == '__main__':
    unittest.main()
