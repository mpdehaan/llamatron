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

from llamatron.chord import Chord, ChordType
from llamatron.generators.base import ClipGenerator
from llamatron.legacy.generators.force_scale import ForceScale, nearest_in_scale
from llamatron.note import Degree, Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)
E_FLAT_MAJOR = Scale(Note('Eb', 4), ScaleType.MAJOR)


def q(name, octave=4):
    return Note(name, octave, 0.25)


class TestForceScale(unittest.TestCase):

    def force(self, *notes, scale=C_MAJOR):
        return ForceScale(scale).generate(Clip(notes=list(notes)))

    def test_is_a_clip_generator(self):
        self.assertIsInstance(ForceScale(C_MAJOR), ClipGenerator)

    def test_notes_in_the_scale_stay(self):
        notes = [q(name) for name in 'CDEFGAB']
        self.assertEqual(self.force(*notes).notes, notes)

    def test_notes_outside_move_to_the_closest_with_ties_going_lower(self):
        self.assertEqual(self.force(q('F#')).notes, [q('F')])
        self.assertEqual(self.force(q('C#')).notes, [q('C')])
        self.assertEqual(self.force(q('G#')).notes, [q('G')])

    def test_uses_the_shape_of_the_scale(self):
        pentatonic = Scale(Note('C', 4), ScaleType.MAJOR_PENTATONIC)
        self.assertEqual(self.force(q('F'), scale=pentatonic).notes, [q('E')])
        self.assertEqual(self.force(q('B'), scale=pentatonic).notes, [q('C', 5)])

    def test_chords_become_chords_of_the_scale(self):
        d_major = Note('D', 3, 1).to_chord(ChordType.MAJOR)
        d_minor = Note('D', 3, 1).to_chord(ChordType.MINOR)
        self.assertEqual(self.force(d_major).notes, [d_minor])

    def test_e_major_becomes_e_minor_in_a_minor(self):
        e_major = Note('E', 3, 1).to_chord(ChordType.MAJOR)
        e_minor = Note('E', 3, 1).to_chord(ChordType.MINOR)
        self.assertEqual(self.force(e_major, scale=A_MINOR).notes, [e_minor])

    def test_rests_and_degrees_stay(self):
        self.assertEqual(self.force(Rest(1), Degree(2, 1)).notes, [Rest(1), Degree(2, 1)])

    def test_keeps_lengths(self):
        self.assertEqual(self.force(Note('F#', 4, 0.5)).notes[0].length, 0.5)

    def test_uses_the_spelling_of_the_scale(self):
        self.assertEqual(self.force(q('A'), scale=E_FLAT_MAJOR).notes[0].name, 'Ab')

    def test_new_clip_uses_the_scale_and_keeps_its_details(self):
        original = Clip('Riff', notes=[q('C')], scale=A_MINOR, length=2)
        result = ForceScale(C_MAJOR).generate(original)
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.name, 'Riff')
        self.assertEqual(result.length, 2)
        self.assertIs(original.scale, A_MINOR)

    def test_nearest_in_scale_stays_in_the_midi_range(self):
        self.assertEqual(nearest_in_scale(0, C_MAJOR), 0)
        self.assertLessEqual(nearest_in_scale(127, C_MAJOR), 127)

    def test_rejects_invalid_values(self):
        for scale in [None, 'C major', ScaleType.MAJOR]:
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    ForceScale(scale)
        with self.assertRaises(ValueError):
            ForceScale(C_MAJOR).generate('clip')

    def test_scale_can_be_edited_and_is_validated(self):
        generator = ForceScale(C_MAJOR)
        generator.scale = A_MINOR
        self.assertIs(generator.scale, A_MINOR)
        with self.assertRaises(ValueError):
            generator.scale = None
        self.assertIs(generator.scale, A_MINOR)


if __name__ == '__main__':
    unittest.main()
