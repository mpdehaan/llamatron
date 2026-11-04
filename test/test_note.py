import dataclasses
import unittest

from src.note import Note, SEMITONES_ABOVE_C

ALL_NAMES = [
    'C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'Fb', 'E#', 'F', 'F#', 'Gb',
    'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'B#', 'Cb',
]


class TestConstruction(unittest.TestCase):

    def test_keeps_name_and_octave(self):
        note = Note('Db', 4)
        self.assertEqual(note.name, 'Db')
        self.assertEqual(note.octave_number, 4)

    def test_all_names_are_supported(self):
        self.assertCountEqual(ALL_NAMES, SEMITONES_ABOVE_C)
        for name in ALL_NAMES:
            with self.subTest(name=name):
                self.assertEqual(Note(name, 4).name, name)

    def test_all_octaves_from_0_to_10_are_supported(self):
        for octave in range(0, 11):
            with self.subTest(octave=octave):
                self.assertEqual(Note('C', octave).octave_number, octave)

    def test_rejects_invalid_names(self):
        for name in ['H', '', 'c', 'c#', 'C##', 'Dbb', 'C #', '#', 'C4', None, 1, ['C']]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Note(name, 4)

    def test_rejects_invalid_octaves(self):
        for octave in [-1, 11, 100, 4.0, 4.5, '4', None, True]:
            with self.subTest(octave=octave):
                with self.assertRaises(ValueError):
                    Note('C', octave)

    def test_cannot_be_changed_into_an_invalid_note(self):
        note = Note('C', 4)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            note.octave_number = 99


class TestMidiNumber(unittest.TestCase):

    def test_c0_is_the_lowest_midi_number(self):
        self.assertEqual(Note('C', 0).midi_number, 0)

    def test_g10_is_the_highest_midi_number(self):
        self.assertEqual(Note('G', 10).midi_number, 127)

    def test_each_octave_is_twelve_semitones(self):
        self.assertEqual(Note('C', 4).midi_number, 48)
        self.assertEqual(Note('C', 5).midi_number, 60)

    def test_enharmonic_spellings_share_a_midi_number(self):
        self.assertEqual(Note('C#', 4).midi_number, Note('Db', 4).midi_number)
        self.assertEqual(Note('B#', 3).midi_number, Note('C', 4).midi_number)

    def test_rejects_notes_above_the_midi_range(self):
        for name in ['G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'B#']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Note(name, 10)

    def test_rejects_notes_below_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note('Cb', 0)

    def test_all_midi_numbers_can_be_produced(self):
        produced = set()
        for name in ALL_NAMES:
            for octave in range(0, 11):
                try:
                    produced.add(Note(name, octave).midi_number)
                except ValueError:
                    pass
        self.assertEqual(produced, set(range(0, 128)))


class TestHalfStep(unittest.TestCase):

    def test_moves_up(self):
        self.assertEqual(Note('C', 4).half_step(1), Note('C#', 4))
        self.assertEqual(Note('C', 4).half_step(7), Note('G', 4))

    def test_moves_down(self):
        self.assertEqual(Note('D', 4).half_step(-1), Note('C#', 4))

    def test_zero_gives_the_same_pitch(self):
        self.assertEqual(Note('C', 4).half_step(0), Note('C', 4))

    def test_crosses_octaves(self):
        self.assertEqual(Note('B', 3).half_step(1), Note('C', 4))
        self.assertEqual(Note('C', 4).half_step(-1), Note('B', 3))
        self.assertEqual(Note('C', 4).half_step(25), Note('C#', 6))

    def test_returns_a_new_note_and_leaves_the_original_alone(self):
        note = Note('C', 4)
        result = note.half_step(0)
        self.assertIsNot(result, note)
        note.half_step(2)
        self.assertEqual(note, Note('C', 4))

    def test_sharps_and_naturals_are_spelled_with_sharps(self):
        self.assertEqual(Note('C', 4).half_step(1).name, 'C#')
        self.assertEqual(Note('C#', 4).half_step(2).name, 'D#')

    def test_flats_are_spelled_with_flats(self):
        self.assertEqual(Note('Db', 4).half_step(2).name, 'Eb')
        self.assertEqual(Note('Bb', 4).half_step(-2).name, 'Ab')

    def test_cannot_leave_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note('G', 10).half_step(1)
        with self.assertRaises(ValueError):
            Note('C', 0).half_step(-1)


class TestWholeStep(unittest.TestCase):

    def test_moves_up_two_half_steps_each(self):
        self.assertEqual(Note('C', 4).whole_step(1), Note('D', 4))
        self.assertEqual(Note('C', 4).whole_step(3), Note('F#', 4))

    def test_moves_down_two_half_steps_each(self):
        self.assertEqual(Note('D', 4).whole_step(-1), Note('C', 4))
        self.assertEqual(Note('C', 4).whole_step(-1), Note('A#', 3))

    def test_returns_a_new_note(self):
        note = Note('C', 4)
        self.assertIsNot(note.whole_step(0), note)

    def test_cannot_leave_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note('F', 10).whole_step(2)
        with self.assertRaises(ValueError):
            Note('C#', 0).whole_step(-1)


class TestOctave(unittest.TestCase):

    def test_moves_up_and_down(self):
        self.assertEqual(Note('C', 4).octave(1), Note('C', 5))
        self.assertEqual(Note('C', 4).octave(-2), Note('C', 2))

    def test_keeps_the_spelling(self):
        self.assertEqual(Note('Db', 4).octave(1).name, 'Db')
        self.assertEqual(Note('C#', 4).octave(1).name, 'C#')

    def test_returns_a_new_note(self):
        note = Note('C', 4)
        self.assertIsNot(note.octave(0), note)

    def test_cannot_leave_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note('A', 9).octave(1)
        with self.assertRaises(ValueError):
            Note('C', 0).octave(-1)
        with self.assertRaises(ValueError):
            Note('Cb', 1).octave(-1)


class TestStepCountValidation(unittest.TestCase):

    def test_methods_reject_non_integers(self):
        note = Note('C', 4)
        methods = [note.half_step, note.whole_step, note.octave]
        for method in methods:
            for n in [1.5, 1.0, '1', None, True]:
                with self.subTest(method=method.__name__, n=n):
                    with self.assertRaises(ValueError):
                        method(n)


class TestEquality(unittest.TestCase):

    def test_enharmonic_spellings_are_equal(self):
        pairs = [
            ('C#', 'Db'), ('D#', 'Eb'), ('F#', 'Gb'), ('G#', 'Ab'), ('A#', 'Bb'),
            ('E', 'Fb'), ('E#', 'F'),
        ]
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                self.assertEqual(Note(first, 4), Note(second, 4))

    def test_enharmonic_spellings_that_cross_an_octave_are_equal(self):
        self.assertEqual(Note('B#', 3), Note('C', 4))
        self.assertEqual(Note('Cb', 4), Note('B', 3))

    def test_same_octave_number_does_not_make_b_sharp_equal_c(self):
        self.assertNotEqual(Note('B#', 4), Note('C', 4))
        self.assertNotEqual(Note('Cb', 4), Note('B', 4))

    def test_different_pitches_are_not_equal(self):
        self.assertNotEqual(Note('C', 4), Note('D', 4))
        self.assertNotEqual(Note('C', 4), Note('C', 5))

    def test_is_not_equal_to_other_types(self):
        self.assertNotEqual(Note('C', 4), 'C')

    def test_enharmonic_notes_hash_the_same(self):
        self.assertEqual(len({Note('C#', 4), Note('Db', 4)}), 1)
        self.assertEqual(len({Note('B#', 3), Note('C', 4)}), 1)


if __name__ == '__main__':
    unittest.main()
