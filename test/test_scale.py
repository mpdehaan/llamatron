# llamatron: a music program
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

from llamatron.music.note import FIRST_DEGREE, MAX_OCTAVE, Note, NoteName
from llamatron.strings.errors import ERR_BAD_DEGREE
from llamatron.music.scale import Scale, ScaleType

# Names the tests give to their own things, and other values they use.
D = 'D'
E = 'E'
F = 'F'
G = 'G'
A = 'A'
B = 'B'
A3_B3_C4_D4_E4_F4_G4_A4 = 'A3 B3 C4 D4 E4 F4 G4 A4'
C = 'C'
C4 = 'C4'
MAJOR = 'MAJOR'


def one_octave(scale):
    """Return a scale's notes the way scale degrees reach them, up to the next root."""
    steps = [*scale.get_type().value, 12]
    return [scale.get_root() if step == 0 else scale.get_root().half_step(step) for step in steps]


def notes(text):
    """Turn 'C4 Eb4' into [Note('C', 4, 0.25), Note('Eb', 4, 0.25)]."""
    result = []
    for word in text.split():
        # Octave 10 is the only octave with two digits.
        split_at = -2 if word.endswith('10') else -1
        result.append(Note(name=word[:split_at], octave_number=int(word[split_at:]), length=0.25))
    return result


def spelled(scale_notes):
    """Turn notes into 'C4 Eb4' text, so tests can check the exact spelling."""
    return ' '.join(f'{note.get_name()}{note.get_octave_number()}' for note in scale_notes)


C_MAJOR_LETTERS = ['C', 'D', 'E', 'F', 'G', 'A', 'B']

# Written out by hand rather than from the intervals, so that a wrong interval
# in ScaleType fails here. Each one runs from C4 up to C5.
C4_SCALES = {
    ScaleType.MAJOR: 'C4 D4 E4 F4 G4 A4 B4 C5',
    ScaleType.DORIAN: 'C4 D4 Eb4 F4 G4 A4 Bb4 C5',
    ScaleType.PHRYGIAN: 'C4 Db4 Eb4 F4 G4 Ab4 Bb4 C5',
    ScaleType.LYDIAN: 'C4 D4 E4 F#4 G4 A4 B4 C5',
    ScaleType.MIXOLYDIAN: 'C4 D4 E4 F4 G4 A4 Bb4 C5',
    ScaleType.MINOR: 'C4 D4 Eb4 F4 G4 Ab4 Bb4 C5',
    ScaleType.LOCRIAN: 'C4 Db4 Eb4 F4 Gb4 Ab4 Bb4 C5',
    ScaleType.HARMONIC_MINOR: 'C4 D4 Eb4 F4 G4 Ab4 B4 C5',
    ScaleType.MELODIC_MINOR: 'C4 D4 Eb4 F4 G4 A4 B4 C5',
    ScaleType.HARMONIC_MAJOR: 'C4 D4 E4 F4 G4 Ab4 B4 C5',
    ScaleType.MAJOR_PENTATONIC: 'C4 D4 E4 G4 A4 C5',
    ScaleType.MINOR_PENTATONIC: 'C4 Eb4 F4 G4 Bb4 C5',
    ScaleType.BLUES: 'C4 Eb4 F4 F#4 G4 Bb4 C5',
    ScaleType.MAJOR_BLUES: 'C4 D4 Eb4 E4 G4 A4 C5',
    ScaleType.CHROMATIC: 'C4 C#4 D4 D#4 E4 F4 F#4 G4 G#4 A4 A#4 B4 C5',
    ScaleType.WHOLE_TONE: 'C4 D4 E4 F#4 G#4 A#4 C5',
    ScaleType.WHOLE_HALF_DIMINISHED: 'C4 D4 Eb4 F4 Gb4 Ab4 A4 B4 C5',
    ScaleType.HALF_WHOLE_DIMINISHED: 'C4 Db4 Eb4 E4 F#4 G4 A4 Bb4 C5',
    ScaleType.LYDIAN_DOMINANT: 'C4 D4 E4 F#4 G4 A4 Bb4 C5',
    ScaleType.ALTERED: 'C4 Db4 Eb4 E4 Gb4 Ab4 Bb4 C5',
    ScaleType.BEBOP_DOMINANT: 'C4 D4 E4 F4 G4 A4 Bb4 B4 C5',
    ScaleType.PHRYGIAN_DOMINANT: 'C4 Db4 E4 F4 G4 Ab4 Bb4 C5',
    ScaleType.HUNGARIAN_MINOR: 'C4 D4 Eb4 F#4 G4 Ab4 B4 C5',
    ScaleType.DOUBLE_HARMONIC: 'C4 Db4 E4 F4 G4 Ab4 B4 C5',
    ScaleType.AUGMENTED: 'C4 Eb4 E4 G4 Ab4 B4 C5',
    ScaleType.DORIAN_FLAT2: 'C4 Db4 Eb4 F4 G4 A4 Bb4 C5',
    ScaleType.LYDIAN_AUGMENTED: 'C4 D4 E4 F#4 G#4 A4 B4 C5',
    ScaleType.MIXOLYDIAN_FLAT6: 'C4 D4 E4 F4 G4 Ab4 Bb4 C5',
    ScaleType.LOCRIAN_NATURAL2: 'C4 D4 Eb4 F4 Gb4 Ab4 Bb4 C5',
    ScaleType.BEBOP_MAJOR: 'C4 D4 E4 F4 G4 Ab4 A4 B4 C5',
    ScaleType.PROMETHEUS: 'C4 D4 E4 F#4 A4 Bb4 C5',
    ScaleType.HUNGARIAN_MAJOR: 'C4 D#4 E4 F#4 G4 A4 Bb4 C5',
    ScaleType.UKRAINIAN_DORIAN: 'C4 D4 Eb4 F#4 G4 A4 Bb4 C5',
    ScaleType.PERSIAN: 'C4 Db4 E4 F4 Gb4 Ab4 B4 C5',
    ScaleType.NEAPOLITAN_MINOR: 'C4 Db4 Eb4 F4 G4 Ab4 B4 C5',
    ScaleType.NEAPOLITAN_MAJOR: 'C4 Db4 Eb4 F4 G4 A4 B4 C5',
    ScaleType.ENIGMATIC: 'C4 Db4 E4 F#4 G#4 A#4 B4 C5',
    ScaleType.EGYPTIAN: 'C4 D4 F4 G4 Bb4 C5',
    ScaleType.HIRAJOSHI: 'C4 D4 Eb4 G4 Ab4 C5',
    ScaleType.IN_SEN: 'C4 Db4 F4 G4 Bb4 C5',
    ScaleType.IWATO: 'C4 Db4 F4 Gb4 Bb4 C5',
    ScaleType.KUMOI: 'C4 D4 Eb4 G4 A4 C5',
    ScaleType.YO: 'C4 D4 F4 G4 A4 C5',
    ScaleType.RYUKYU: 'C4 E4 F4 G4 B4 C5',
    ScaleType.TODI: 'C4 Db4 Eb4 F#4 G4 Ab4 B4 C5',
    ScaleType.MARWA: 'C4 Db4 E4 F#4 G4 A4 B4 C5',
    ScaleType.PURVI: 'C4 Db4 E4 F#4 G4 Ab4 B4 C5',
}



class TestScaleTypes(unittest.TestCase):

    def test_every_scale_type_is_checked_here(self):
        self.assertCountEqual(C4_SCALES, list(ScaleType))

    def test_one_octave_of_every_scale_type_from_c(self):
        for typ, expected in C4_SCALES.items():
            with self.subTest(typ=typ):
                expected_notes = notes(expected)
                self.assertEqual(one_octave(Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=typ)), expected_notes)

    def test_other_names_for_the_same_scale(self):
        self.assertIs(ScaleType.IONIAN, ScaleType.MAJOR)
        self.assertIs(ScaleType.AEOLIAN, ScaleType.MINOR)
        self.assertIs(ScaleType.NATURAL_MINOR, ScaleType.MINOR)

    def test_modes_share_the_notes_of_c_major(self):
        cases = [
            (D, ScaleType.DORIAN),
            (E, ScaleType.PHRYGIAN),
            (F, ScaleType.LYDIAN),
            (G, ScaleType.MIXOLYDIAN),
            (A, ScaleType.MINOR),
            (B, ScaleType.LOCRIAN),
        ]
        c_major_pitches = {n % 12 for n in ScaleType.MAJOR.value}
        for name, typ in cases:
            with self.subTest(typ=typ):
                result = one_octave(Scale(root=Note(name=name, octave_number=4, length=0.25), typ=typ))
                self.assertEqual(
                    {note.get_midi_number() % 12 for note in result},
                    c_major_pitches,
                )


class TestOtherRoots(unittest.TestCase):

    def test_d_major_is_spelled_with_sharps(self):
        result = one_octave(Scale(root=Note(name=NoteName.D, octave_number=4, length=0.25), typ=ScaleType.MAJOR))
        self.assertEqual(spelled(result), 'D4 E4 F#4 G4 A4 B4 C#5 D5')

    def test_e_flat_major_is_spelled_with_flats(self):
        result = one_octave(Scale(root=Note(name=NoteName.E_FLAT, octave_number=4, length=0.25), typ=ScaleType.MAJOR))
        self.assertEqual(spelled(result), 'Eb4 F4 G4 Ab4 Bb4 C5 D5 Eb5')

    def test_a_minor_crosses_into_the_next_octave_at_c(self):
        result = one_octave(Scale(root=Note(name=NoteName.A, octave_number=3, length=0.25), typ=ScaleType.MINOR))
        self.assertEqual(spelled(result), A3_B3_C4_D4_E4_F4_G4_A4)





class TestScaleLengths(unittest.TestCase):

    def test_root_length_affects_equality(self):
        self.assertNotEqual(
            Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
            Scale(root=Note(name=NoteName.C, octave_number=4, length=0.5), typ=ScaleType.MAJOR),
        )


class TestScale(unittest.TestCase):

    def test_keeps_root_and_type(self):
        scale = Scale(root=Note(name=NoteName.D, octave_number=2, length=0.25), typ=ScaleType.DORIAN)
        self.assertEqual(scale.get_root(), Note(name=NoteName.D, octave_number=2, length=0.25))
        self.assertIs(scale.get_type(), ScaleType.DORIAN)

    def test_rejects_invalid_roots(self):
        for root in [C, C4, None, 60]:
            with self.subTest(root=root):
                with self.assertRaises(ValueError):
                    Scale(root=root, typ=ScaleType.MAJOR)

    def test_rejects_invalid_types(self):
        for typ in [MAJOR, None, (0, 2, 4), 1]:
            with self.subTest(typ=typ):
                with self.assertRaises(ValueError):
                    Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=typ)

    def test_cannot_be_changed(self):
        scale = Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=ScaleType.MAJOR)
        with self.assertRaises(AttributeError):
            scale.typ = ScaleType.MINOR

    def test_equality(self):
        self.assertEqual(
            Scale(root=Note(name=NoteName.C_SHARP, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
            Scale(root=Note(name=NoteName.D_FLAT, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
        )
        self.assertNotEqual(
            Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
            Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=ScaleType.MINOR),
        )
        self.assertNotEqual(
            Scale(root=Note(name=NoteName.C, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
            Scale(root=Note(name=NoteName.C, octave_number=5, length=0.25), typ=ScaleType.MAJOR),
        )

    def test_equal_scales_hash_the_same(self):
        scales = {
            Scale(root=Note(name=NoteName.C_SHARP, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
            Scale(root=Note(name=NoteName.D_FLAT, octave_number=4, length=0.25), typ=ScaleType.MAJOR),
        }
        self.assertEqual(len(scales), 1)


class TestTheNoteADegreePlays(unittest.TestCase):
    """note_at is where a degree becomes a note, made once with its length, velocity and glide.

    test_degrees.py checks the notes of every degree through Degree.to_note, which asks note_at.
    These check what playing a pattern asks for directly, without a Degree.
    """

    QUARTER = Fraction(1, 4)
    LOUD = 110
    C_MAJOR = Scale(root=Note(name=NoteName.C, octave_number=4), typ=ScaleType.MAJOR)
    E_FLAT_MINOR = Scale(root=Note(name=NoteName.E_FLAT, octave_number=3), typ=ScaleType.MINOR)
    NOT_DEGREES = [0, -1, True, 1.0, None]

    def at(self, scale, *, degree, scale_notes=0, half_steps=0):
        """Return the name and octave of what a degree plays, like C4."""
        note = scale.note_at(degree=degree, scale_notes=scale_notes, half_steps=half_steps, length=self.QUARTER)
        return f'{note.get_name()}{note.get_octave_number()}'

    def test_degrees_count_from_the_root_and_carry_on_into_the_next_octave(self):
        self.assertEqual([self.at(self.C_MAJOR, degree=degree) for degree in (1, 3, 7, 8, 10)], ['C4', 'E4', 'B4', 'C5', 'E5'])

    def test_scale_notes_move_along_the_scale_and_half_steps_move_after(self):
        self.assertEqual(self.at(self.C_MAJOR, degree=3, scale_notes=-2), 'C4')
        self.assertEqual(self.at(self.C_MAJOR, degree=1, scale_notes=-1), 'B3')
        self.assertEqual(self.at(self.C_MAJOR, degree=1, scale_notes=9), 'E5')
        self.assertEqual(self.at(self.C_MAJOR, degree=1, half_steps=1), 'C#4')
        self.assertEqual(self.at(self.C_MAJOR, degree=2, scale_notes=1, half_steps=-1), 'D#4')

    def test_a_scale_on_a_flat_spells_its_notes_with_flats(self):
        self.assertEqual([self.at(self.E_FLAT_MINOR, degree=degree) for degree in (1, 2, 3)], ['Eb3', 'F3', 'Gb3'])

    def test_the_note_is_made_with_its_length_velocity_and_glide(self):
        note = self.C_MAJOR.note_at(degree=1, scale_notes=0, half_steps=0, length=self.QUARTER, velocity=self.LOUD, glide=True)
        self.assertEqual((note.get_length(), note.get_velocity(), note.get_glide()), (self.QUARTER, self.LOUD, True))
        plain = self.C_MAJOR.note_at(degree=1, scale_notes=0, half_steps=0, length=None)
        self.assertEqual((plain.get_length(), plain.get_velocity(), plain.get_glide()), (None, None, False))

    def test_what_is_not_a_degree_is_refused(self):
        for bad in self.NOT_DEGREES:
            with self.subTest(degree=bad):
                with self.assertRaises(ValueError) as refused:
                    self.C_MAJOR.note_at(degree=bad, scale_notes=0, half_steps=0, length=self.QUARTER)
                self.assertEqual(str(refused.exception), ERR_BAD_DEGREE.format(value=bad, lowest=FIRST_DEGREE))

    def test_a_note_outside_the_midi_range_is_refused(self):
        high = Scale(root=Note(name=NoteName.C, octave_number=MAX_OCTAVE), typ=ScaleType.MAJOR)
        self.assertEqual(self.at(high, degree=5), f'G{MAX_OCTAVE}')
        with self.assertRaises(ValueError):
            high.note_at(degree=6, scale_notes=0, half_steps=0, length=self.QUARTER)


if __name__ == '__main__':
    unittest.main()
