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

from llamatron.music.note import MAX_OCTAVE, MIN_OCTAVE, SEMITONES_ABOVE_C, Note, NoteName, Rest

ALL_NAMES = [
    'C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'Fb', 'E#', 'F', 'F#', 'Gb',
    'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'B#', 'Cb',
]

# Names the tests give to their own things, and other values they use.
DB = 'Db'
NOT_A_NOTE = 'H'
C = 'c'
DBB = 'Dbb'
C4 = 'C4'
C_2 = 'C'
AB = 'Ab'
A = 'A'
BB = 'Bb'
B = 'B'
EB = 'Eb'
GB = 'Gb'
E = 'E'
FB = 'Fb'
F = 'F'


class TestConstruction(unittest.TestCase):

    def test_keeps_name_and_octave(self):
        note = Note(name=NoteName.D_FLAT, octave_number=4, length=0.25)
        self.assertEqual(note.get_name(), DB)
        self.assertEqual(note.get_octave_number(), 4)

    def test_all_names_are_supported(self):
        self.assertCountEqual(ALL_NAMES, SEMITONES_ABOVE_C)
        for name in ALL_NAMES:
            with self.subTest(name=name):
                self.assertEqual(Note(name=name, octave_number=4, length=0.25).get_name(), name)

    def test_all_octaves_from_0_to_10_are_supported(self):
        for octave in range(0, 11):
            with self.subTest(octave=octave):
                self.assertEqual(Note(name=NoteName.C, octave_number=octave, length=0.25).get_octave_number(), octave)

    def test_rejects_invalid_names(self):
        for name in [NOT_A_NOTE, '', C, 'c#', 'C##', DBB, 'C #', '#', C4, None, 1, [C_2]]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Note(name=name, octave_number=4, length=0.25)

    def test_rejects_invalid_octaves(self):
        for octave in [-1, 11, 100, 4.0, 4.5, '4', None, True]:
            with self.subTest(octave=octave):
                with self.assertRaises(ValueError):
                    Note(name=NoteName.C, octave_number=octave, length=0.25)

    def test_cannot_be_changed_into_an_invalid_note(self):
        note = Note(name=NoteName.C, octave_number=4, length=0.25)
        with self.assertRaises(AttributeError):
            note.octave_number = 99


class TestMidiNumber(unittest.TestCase):

    def test_c0_is_the_lowest_midi_number(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=0, length=0.25).get_midi_number(), 0)

    def test_g10_is_the_highest_midi_number(self):
        self.assertEqual(Note(name=NoteName.G, octave_number=10, length=0.25).get_midi_number(), 127)

    def test_each_octave_is_twelve_semitones(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).get_midi_number(), 48)
        self.assertEqual(Note(name=NoteName.C, octave_number=5, length=0.25).get_midi_number(), 60)

    def test_enharmonic_spellings_share_a_midi_number(self):
        self.assertEqual(Note(name=NoteName.C_SHARP, octave_number=4, length=0.25).get_midi_number(), Note(name=NoteName.D_FLAT, octave_number=4, length=0.25).get_midi_number())
        self.assertEqual(Note(name=NoteName.B_SHARP, octave_number=3, length=0.25).get_midi_number(), Note(name=NoteName.C, octave_number=4, length=0.25).get_midi_number())

    def test_rejects_notes_above_the_midi_range(self):
        for name in ['G#', AB, A, 'A#', BB, B, 'B#']:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    Note(name=name, octave_number=10, length=0.25)

    def test_rejects_notes_below_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note(name=NoteName.C_FLAT, octave_number=0, length=0.25)

    def test_all_midi_numbers_can_be_produced(self):
        produced = set()
        for name in ALL_NAMES:
            for octave in range(0, 11):
                try:
                    produced.add(Note(name=name, octave_number=octave, length=0.25).get_midi_number())
                except ValueError:
                    pass
        self.assertEqual(produced, set(range(0, 128)))


class TestHalfStep(unittest.TestCase):

    def test_moves_up(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).half_step(1), Note(name=NoteName.C_SHARP, octave_number=4, length=0.25))
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).half_step(7), Note(name=NoteName.G, octave_number=4, length=0.25))

    def test_moves_down(self):
        self.assertEqual(Note(name=NoteName.D, octave_number=4, length=0.25).half_step(-1), Note(name=NoteName.C_SHARP, octave_number=4, length=0.25))

    def test_zero_gives_the_same_pitch(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).half_step(0), Note(name=NoteName.C, octave_number=4, length=0.25))

    def test_crosses_octaves(self):
        self.assertEqual(Note(name=NoteName.B, octave_number=3, length=0.25).half_step(1), Note(name=NoteName.C, octave_number=4, length=0.25))
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).half_step(-1), Note(name=NoteName.B, octave_number=3, length=0.25))
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).half_step(25), Note(name=NoteName.C_SHARP, octave_number=6, length=0.25))

    def test_returns_a_new_note_and_leaves_the_original_alone(self):
        note = Note(name=NoteName.C, octave_number=4, length=0.25)
        result = note.half_step(0)
        self.assertIsNot(result, note)
        note.half_step(2)
        self.assertEqual(note, Note(name=NoteName.C, octave_number=4, length=0.25))

    def test_sharps_and_naturals_are_spelled_with_sharps(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).half_step(1).get_name(), 'C#')
        self.assertEqual(Note(name=NoteName.C_SHARP, octave_number=4, length=0.25).half_step(2).get_name(), 'D#')

    def test_flats_are_spelled_with_flats(self):
        self.assertEqual(Note(name=NoteName.D_FLAT, octave_number=4, length=0.25).half_step(2).get_name(), EB)
        self.assertEqual(Note(name=NoteName.B_FLAT, octave_number=4, length=0.25).half_step(-2).get_name(), AB)

    def test_cannot_leave_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note(name=NoteName.G, octave_number=10, length=0.25).half_step(1)
        with self.assertRaises(ValueError):
            Note(name=NoteName.C, octave_number=0, length=0.25).half_step(-1)





INVALID_LENGTHS = [0, -0.25, '0.25', None, True, float('nan'), float('inf')]


class TestNoteLength(unittest.TestCase):

    def test_length_is_optional(self):
        self.assertIsNone(Note(name=NoteName.C, octave_number=4).get_length())

    def test_half_step_keeps_the_length(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.5).half_step(1).get_length(), 0.5)

    def test_keeps_its_length(self):
        for length in [1, 0.5, 0.25, 0.125, Fraction(1, 12), 2]:
            with self.subTest(length=length):
                self.assertEqual(Note(name=NoteName.C, octave_number=4, length=length).get_length(), length)

    def test_rejects_invalid_lengths(self):
        for length in INVALID_LENGTHS:
            if length is not None:
                with self.subTest(length=length):
                    with self.assertRaises(ValueError):
                        Note(name=NoteName.C, octave_number=4, length=length)

    def test_different_lengths_are_not_equal(self):
        self.assertNotEqual(Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.C, octave_number=4, length=0.5))

    def test_equal_lengths_can_be_written_differently(self):
        self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.C, octave_number=4, length=Fraction(1, 4)))
        self.assertEqual(len({Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.C, octave_number=4, length=Fraction(1, 4))}), 1)

    def test_enharmonic_notes_need_the_same_length_to_be_equal(self):
        self.assertEqual(Note(name=NoteName.C_SHARP, octave_number=4, length=0.5), Note(name=NoteName.D_FLAT, octave_number=4, length=0.5))
        self.assertNotEqual(Note(name=NoteName.C_SHARP, octave_number=4, length=0.5), Note(name=NoteName.D_FLAT, octave_number=4, length=0.25))


class TestRest(unittest.TestCase):

    def test_length_is_required(self):
        with self.assertRaises(TypeError):
            Rest()

    def test_keeps_its_length(self):
        self.assertEqual(Rest(0.25).get_length(), 0.25)

    def test_rejects_invalid_lengths(self):
        for length in INVALID_LENGTHS:
            with self.subTest(length=length):
                with self.assertRaises(ValueError):
                    Rest(length)

    def test_equality(self):
        self.assertEqual(Rest(0.25), Rest(0.25))
        self.assertNotEqual(Rest(0.25), Rest(0.5))
        self.assertNotEqual(Rest(0.25), Note(name=NoteName.C, octave_number=4, length=0.25))

    def test_cannot_be_changed(self):
        with self.assertRaises(AttributeError):
            Rest(0.25).length = 0.5


class TestEquality(unittest.TestCase):

    def test_enharmonic_spellings_are_equal(self):
        pairs = [
            ('C#', DB), ('D#', EB), ('F#', GB), ('G#', AB), ('A#', BB),
            (E, FB), ('E#', F),
        ]
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                self.assertEqual(Note(name=first, octave_number=4, length=0.25), Note(name=second, octave_number=4, length=0.25))

    def test_enharmonic_spellings_that_cross_an_octave_are_equal(self):
        self.assertEqual(Note(name=NoteName.B_SHARP, octave_number=3, length=0.25), Note(name=NoteName.C, octave_number=4, length=0.25))
        self.assertEqual(Note(name=NoteName.C_FLAT, octave_number=4, length=0.25), Note(name=NoteName.B, octave_number=3, length=0.25))

    def test_same_octave_number_does_not_make_b_sharp_equal_c(self):
        self.assertNotEqual(Note(name=NoteName.B_SHARP, octave_number=4, length=0.25), Note(name=NoteName.C, octave_number=4, length=0.25))
        self.assertNotEqual(Note(name=NoteName.C_FLAT, octave_number=4, length=0.25), Note(name=NoteName.B, octave_number=4, length=0.25))

    def test_different_pitches_are_not_equal(self):
        self.assertNotEqual(Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.D, octave_number=4, length=0.25))
        self.assertNotEqual(Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.C, octave_number=5, length=0.25))

    def test_is_not_equal_to_other_types(self):
        self.assertNotEqual(Note(name=NoteName.C, octave_number=4, length=0.25), C_2)

    def test_enharmonic_notes_hash_the_same(self):
        self.assertEqual(len({Note(name=NoteName.C_SHARP, octave_number=4, length=0.25), Note(name=NoteName.D_FLAT, octave_number=4, length=0.25)}), 1)
        self.assertEqual(len({Note(name=NoteName.B_SHARP, octave_number=3, length=0.25), Note(name=NoteName.C, octave_number=4, length=0.25)}), 1)


class TestCopies(unittest.TestCase):
    """with_length, with_velocity, with_glide and half_step make a new note without checking again what the copy keeps.

    So each copy is compared, field by field, with the note the constructor makes from the same
    values, and each is given what the constructor refuses, which the copy refuses in the same words.
    """

    OCTAVE = 4
    QUARTER = Fraction(1, 4)
    EIGHTH = Fraction(1, 8)
    QUIET = 40
    LOUD = 120
    BAD_LENGTHS = [0, -1, True, 'long', float('inf')]
    BAD_VELOCITIES = [0, 128, 1.5, True, 'loud']

    def note(self, **changes):
        """Return the note the copies are made from, a quiet D flat, or the constructor's note with some of its values changed."""
        values = dict(name=NoteName.D_FLAT, octave_number=self.OCTAVE, length=self.QUARTER, velocity=self.QUIET, glide=False)
        return Note(**{**values, **changes})

    def fields(self, note):
        return (note.get_name(), note.get_octave_number(), note.get_midi_number(), note.get_length(), note.get_velocity(), note.get_glide())

    def refusal(self, make):
        """Return the words a note is refused in."""
        with self.assertRaises(ValueError) as refused:
            make()
        return str(refused.exception)

    def test_another_length_keeps_everything_else_and_leaves_the_original_alone(self):
        original = self.note()
        self.assertEqual(self.fields(original.with_length(self.EIGHTH)), self.fields(self.note(length=self.EIGHTH)))
        self.assertEqual(self.fields(original), self.fields(self.note()))

    def test_a_copy_can_have_no_length_for_its_clip_to_fill_in(self):
        self.assertEqual(self.fields(self.note().with_length(None)), self.fields(self.note(length=None)))

    def test_a_bad_length_is_refused_in_the_constructors_words(self):
        for bad in self.BAD_LENGTHS:
            with self.subTest(length=bad):
                self.assertEqual(self.refusal(lambda: self.note().with_length(bad)), self.refusal(lambda: self.note(length=bad)))

    def test_another_velocity_keeps_everything_else(self):
        self.assertEqual(self.fields(self.note().with_velocity(self.LOUD)), self.fields(self.note(velocity=self.LOUD)))
        self.assertEqual(self.fields(self.note().with_velocity(None)), self.fields(self.note(velocity=None)))

    def test_a_bad_velocity_is_refused_in_the_constructors_words(self):
        for bad in self.BAD_VELOCITIES:
            with self.subTest(velocity=bad):
                self.assertEqual(self.refusal(lambda: self.note().with_velocity(bad)), self.refusal(lambda: self.note(velocity=bad)))

    def test_gliding_keeps_everything_else(self):
        self.assertEqual(self.fields(self.note().with_glide()), self.fields(self.note(glide=True)))
        self.assertEqual(self.fields(self.note(glide=True).with_glide()), self.fields(self.note(glide=True)))

    def test_a_half_step_keeps_the_length_the_velocity_and_the_glide(self):
        moved = self.note(glide=True).half_step(2)
        self.assertEqual(self.fields(moved), self.fields(self.note(name=NoteName.E_FLAT, glide=True)))

    def test_a_half_step_out_of_the_midi_range_is_refused_in_the_constructors_words(self):
        top = self.note(name=NoteName.G, octave_number=MAX_OCTAVE)
        self.assertEqual(self.refusal(lambda: top.half_step(1)), self.refusal(lambda: self.note(name=NoteName.G_SHARP, octave_number=MAX_OCTAVE)))
        bottom = self.note(name=NoteName.C, octave_number=MIN_OCTAVE)
        self.assertEqual(self.refusal(lambda: bottom.half_step(-1)), self.refusal(lambda: self.note(name=NoteName.B, octave_number=MIN_OCTAVE - 1)))

    def test_the_lowest_and_highest_notes_can_be_reached_by_half_steps(self):
        self.assertEqual(self.fields(self.note(name=NoteName.F_SHARP, octave_number=MAX_OCTAVE).half_step(1)), self.fields(self.note(name=NoteName.G, octave_number=MAX_OCTAVE)))
        self.assertEqual(self.fields(self.note(name=NoteName.D_FLAT, octave_number=MIN_OCTAVE).half_step(-1)), self.fields(self.note(name=NoteName.C, octave_number=MIN_OCTAVE)))


if __name__ == '__main__':
    unittest.main()
