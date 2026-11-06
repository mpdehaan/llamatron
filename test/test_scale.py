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

import dataclasses
import unittest

from llamatron.note import Note
from llamatron.scale import Scale, ScaleType


def one_octave(scale):
    """Return a scale's notes the way scale degrees reach them, up to the next root."""
    steps = [*scale.typ.value, 12]
    return [scale.root if step == 0 else scale.root.half_step(step) for step in steps]


def notes(text):
    """Turn 'C4 Eb4' into [Note('C', 4, 0.25), Note('Eb', 4, 0.25)]."""
    result = []
    for word in text.split():
        # Octave 10 is the only octave with two digits.
        split_at = -2 if word.endswith('10') else -1
        result.append(Note(word[:split_at], int(word[split_at:]), 0.25))
    return result


def spelled(scale_notes):
    """Turn notes into 'C4 Eb4' text, so tests can check the exact spelling."""
    return ' '.join(f'{note.name}{note.octave_number}' for note in scale_notes)


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
                self.assertEqual(one_octave(Scale(Note('C', 4, 0.25), typ)), expected_notes)

    def test_other_names_for_the_same_scale(self):
        self.assertIs(ScaleType.IONIAN, ScaleType.MAJOR)
        self.assertIs(ScaleType.AEOLIAN, ScaleType.MINOR)
        self.assertIs(ScaleType.NATURAL_MINOR, ScaleType.MINOR)

    def test_modes_share_the_notes_of_c_major(self):
        cases = [
            ('D', ScaleType.DORIAN),
            ('E', ScaleType.PHRYGIAN),
            ('F', ScaleType.LYDIAN),
            ('G', ScaleType.MIXOLYDIAN),
            ('A', ScaleType.MINOR),
            ('B', ScaleType.LOCRIAN),
        ]
        c_major_pitches = {n % 12 for n in ScaleType.MAJOR.value}
        for name, typ in cases:
            with self.subTest(typ=typ):
                result = one_octave(Scale(Note(name, 4, 0.25), typ))
                self.assertEqual(
                    {note.midi_number % 12 for note in result},
                    c_major_pitches,
                )


class TestOtherRoots(unittest.TestCase):

    def test_d_major_is_spelled_with_sharps(self):
        result = one_octave(Scale(Note('D', 4, 0.25), ScaleType.MAJOR))
        self.assertEqual(spelled(result), 'D4 E4 F#4 G4 A4 B4 C#5 D5')

    def test_e_flat_major_is_spelled_with_flats(self):
        result = one_octave(Scale(Note('Eb', 4, 0.25), ScaleType.MAJOR))
        self.assertEqual(spelled(result), 'Eb4 F4 G4 Ab4 Bb4 C5 D5 Eb5')

    def test_a_minor_crosses_into_the_next_octave_at_c(self):
        result = one_octave(Scale(Note('A', 3, 0.25), ScaleType.MINOR))
        self.assertEqual(spelled(result), 'A3 B3 C4 D4 E4 F4 G4 A4')





class TestScaleLengths(unittest.TestCase):

    def test_root_length_affects_equality(self):
        self.assertNotEqual(
            Scale(Note('C', 4, 0.25), ScaleType.MAJOR),
            Scale(Note('C', 4, 0.5), ScaleType.MAJOR),
        )


class TestScale(unittest.TestCase):

    def test_keeps_root_and_type(self):
        scale = Scale(Note('D', 2, 0.25), ScaleType.DORIAN)
        self.assertEqual(scale.root, Note('D', 2, 0.25))
        self.assertIs(scale.typ, ScaleType.DORIAN)

    def test_rejects_invalid_roots(self):
        for root in ['C', 'C4', None, 60]:
            with self.subTest(root=root):
                with self.assertRaises(ValueError):
                    Scale(root, ScaleType.MAJOR)

    def test_rejects_invalid_types(self):
        for typ in ['MAJOR', None, (0, 2, 4), 1]:
            with self.subTest(typ=typ):
                with self.assertRaises(ValueError):
                    Scale(Note('C', 4, 0.25), typ)

    def test_cannot_be_changed(self):
        scale = Scale(Note('C', 4, 0.25), ScaleType.MAJOR)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            scale.typ = ScaleType.MINOR

    def test_equality(self):
        self.assertEqual(
            Scale(Note('C#', 4, 0.25), ScaleType.MAJOR),
            Scale(Note('Db', 4, 0.25), ScaleType.MAJOR),
        )
        self.assertNotEqual(
            Scale(Note('C', 4, 0.25), ScaleType.MAJOR),
            Scale(Note('C', 4, 0.25), ScaleType.MINOR),
        )
        self.assertNotEqual(
            Scale(Note('C', 4, 0.25), ScaleType.MAJOR),
            Scale(Note('C', 5, 0.25), ScaleType.MAJOR),
        )

    def test_equal_scales_hash_the_same(self):
        scales = {
            Scale(Note('C#', 4, 0.25), ScaleType.MAJOR),
            Scale(Note('Db', 4, 0.25), ScaleType.MAJOR),
        }
        self.assertEqual(len(scales), 1)


if __name__ == '__main__':
    unittest.main()
