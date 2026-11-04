import dataclasses
import unittest
from collections.abc import Iterator

from src.note import Note
from src.scale import Scale, ScaleType


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
}


class TestCMajor(unittest.TestCase):

    def test_all_notes_from_c0(self):
        expected = [
            Note(letter, octave, 0.25)
            for octave in range(0, 10)
            for letter in C_MAJOR_LETTERS
        ]
        expected += notes('C10 D10 E10 F10 G10')
        self.assertEqual(Scale(Note('C', 0, 0.25), ScaleType.MAJOR).notes(), expected)

    def test_c0_scale_has_exact_spelling_at_both_ends(self):
        result = Scale(Note('C', 0, 0.25), ScaleType.MAJOR).notes()
        self.assertEqual(len(result), 75)
        self.assertEqual(spelled(result[:8]), 'C0 D0 E0 F0 G0 A0 B0 C1')
        self.assertEqual(spelled(result[-5:]), 'C10 D10 E10 F10 G10')

    def test_partial_scale_from_c4(self):
        expected = [
            Note(letter, octave, 0.25)
            for octave in range(4, 10)
            for letter in C_MAJOR_LETTERS
        ]
        expected += notes('C10 D10 E10 F10 G10')
        self.assertEqual(Scale(Note('C', 4, 0.25), ScaleType.MAJOR).notes(), expected)

    def test_partial_scale_from_c4_has_no_lower_notes(self):
        result = Scale(Note('C', 4, 0.25), ScaleType.MAJOR).notes()
        self.assertEqual(result[0], Note('C', 4, 0.25))
        self.assertEqual(min(note.midi_number for note in result), 48)

    def test_c4_scale_is_the_end_of_the_c0_scale(self):
        full = Scale(Note('C', 0, 0.25), ScaleType.MAJOR).notes()
        partial = Scale(Note('C', 4, 0.25), ScaleType.MAJOR).notes()
        self.assertEqual(full[-len(partial):], partial)


class TestScaleTypes(unittest.TestCase):

    def test_every_scale_type_is_checked_here(self):
        self.assertCountEqual(C4_SCALES, list(ScaleType))

    def test_one_octave_of_every_scale_type_from_c(self):
        for typ, expected in C4_SCALES.items():
            with self.subTest(typ=typ):
                expected_notes = notes(expected)
                result = Scale(Note('C', 4, 0.25), typ).notes()
                self.assertEqual(result[:len(expected_notes)], expected_notes)

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
                result = Scale(Note(name, 4, 0.25), typ).notes()
                self.assertEqual(
                    {note.midi_number % 12 for note in result},
                    c_major_pitches,
                )


class TestOtherRoots(unittest.TestCase):

    def test_d_major_is_spelled_with_sharps(self):
        result = Scale(Note('D', 4, 0.25), ScaleType.MAJOR).notes()
        self.assertEqual(spelled(result[:8]), 'D4 E4 F#4 G4 A4 B4 C#5 D5')

    def test_e_flat_major_is_spelled_with_flats(self):
        result = Scale(Note('Eb', 4, 0.25), ScaleType.MAJOR).notes()
        self.assertEqual(spelled(result[:8]), 'Eb4 F4 G4 Ab4 Bb4 C5 D5 Eb5')

    def test_a_minor_crosses_into_the_next_octave_at_c(self):
        result = Scale(Note('A', 3, 0.25), ScaleType.MINOR).notes()
        self.assertEqual(spelled(result[:8]), 'A3 B3 C4 D4 E4 F4 G4 A4')

    def test_root_keeps_its_spelling(self):
        for name, octave in [('B#', 3), ('Cb', 4), ('E#', 4), ('Fb', 4)]:
            with self.subTest(name=name):
                root = Scale(Note(name, octave, 0.25), ScaleType.MAJOR).notes()[0]
                self.assertEqual(root.name, name)
                self.assertEqual(root.octave_number, octave)


class TestTopOfTheRange(unittest.TestCase):

    def test_stops_at_the_last_scale_note_below_the_limit(self):
        result = Scale(Note('B', 9, 0.25), ScaleType.MAJOR).notes()
        self.assertEqual(spelled(result), 'B9 C#10 D#10 E10 F#10')

    def test_root_at_the_top_gives_one_note(self):
        self.assertEqual(Scale(Note('G', 10, 0.25), ScaleType.MAJOR).notes(), [Note('G', 10, 0.25)])

    def test_no_scale_type_goes_past_the_top(self):
        for typ in ScaleType:
            with self.subTest(typ=typ):
                result = Scale(Note('C', 0, 0.25), typ).notes()
                self.assertLessEqual(result[-1].midi_number, 127)

    def test_chromatic_from_c0_is_every_midi_number(self):
        result = Scale(Note('C', 0, 0.25), ScaleType.CHROMATIC).notes()
        self.assertEqual([note.midi_number for note in result], list(range(0, 128)))


class TestIteration(unittest.TestCase):

    def test_iterating_gives_the_same_notes_as_the_list(self):
        scale = Scale(Note('C', 4, 0.25), ScaleType.MINOR)
        self.assertEqual(list(scale), scale.notes())

    def test_returns_an_iterator_that_gives_notes_one_at_a_time(self):
        iterator = iter(Scale(Note('C', 4, 0.25), ScaleType.MAJOR))
        self.assertIsInstance(iterator, Iterator)
        self.assertEqual(next(iterator), Note('C', 4, 0.25))
        self.assertEqual(next(iterator), Note('D', 4, 0.25))

    def test_can_be_used_in_a_for_loop_and_stopped_early(self):
        result = []
        for index, note in enumerate(Scale(Note('C', 4, 0.25), ScaleType.MAJOR)):
            if index == 3:
                break
            result.append(note)
        self.assertEqual(result, notes('C4 D4 E4'))

    def test_can_be_iterated_more_than_once(self):
        scale = Scale(Note('C', 4, 0.25), ScaleType.MAJOR)
        self.assertEqual(list(scale), list(scale))

    def test_notes_returns_a_new_list_each_time(self):
        scale = Scale(Note('C', 4, 0.25), ScaleType.MAJOR)
        scale.notes().clear()
        self.assertEqual(scale.notes()[0], Note('C', 4, 0.25))


class TestCount(unittest.TestCase):

    def test_returns_the_first_notes_as_a_list(self):
        result = Scale(Note('C', 4, 0.25), ScaleType.MAJOR).count(3)
        self.assertIsInstance(result, list)
        self.assertEqual(spelled(result), 'C4 D4 E4')

    def test_can_go_past_one_octave(self):
        result = Scale(Note('C', 4, 0.25), ScaleType.MAJOR_PENTATONIC).count(7)
        self.assertEqual(spelled(result), 'C4 D4 E4 G4 A4 C5 D5')

    def test_can_reach_the_last_note(self):
        scale = Scale(Note('C', 0, 0.25), ScaleType.MAJOR)
        self.assertEqual(scale.count(75), scale.notes())

    def test_rejects_more_notes_than_the_scale_has(self):
        with self.assertRaises(ValueError):
            Scale(Note('C', 0, 0.25), ScaleType.MAJOR).count(76)

    def test_rejects_invalid_counts(self):
        for n in [0, -1, 1.5, 1.0, '1', None, True]:
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    Scale(Note('C', 4, 0.25), ScaleType.MAJOR).count(n)


class TestOctaves(unittest.TestCase):

    def test_one_octave_includes_the_root_at_both_ends(self):
        result = Scale(Note('C', 4, 0.25), ScaleType.MAJOR).octaves(1)
        self.assertIsInstance(result, list)
        self.assertEqual(spelled(result), 'C4 D4 E4 F4 G4 A4 B4 C5')

    def test_two_octaves(self):
        result = Scale(Note('A', 3, 0.25), ScaleType.MINOR_PENTATONIC).octaves(2)
        self.assertEqual(spelled(result), 'A3 C4 D4 E4 G4 A4 C5 D5 E5 G5 A5')

    def test_every_scale_type_ends_on_the_root(self):
        for typ in ScaleType:
            with self.subTest(typ=typ):
                result = Scale(Note('C', 4, 0.25), typ).octaves(1)
                self.assertEqual(result[-1], Note('C', 5, 0.25))
                self.assertEqual(len(result), len(typ.value) + 1)

    def test_can_reach_the_top_of_the_midi_range(self):
        result = Scale(Note('G', 9, 0.25), ScaleType.MAJOR).octaves(1)
        self.assertEqual(result[-1], Note('G', 10, 0.25))

    def test_rejects_going_past_the_top_of_the_midi_range(self):
        with self.assertRaises(ValueError):
            Scale(Note('A', 9, 0.25), ScaleType.MAJOR).octaves(1)

    def test_rejects_invalid_counts(self):
        for n in [0, -1, 1.5, 1.0, '1', None, True]:
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    Scale(Note('C', 4, 0.25), ScaleType.MAJOR).octaves(n)


class TestScaleLengths(unittest.TestCase):

    def test_every_note_has_the_root_length(self):
        scale = Scale(Note('C', 4, 0.125), ScaleType.MAJOR)
        for notes_list in [scale.notes(), scale.count(3), scale.octaves(1)]:
            self.assertEqual({note.length for note in notes_list}, {0.125})

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
