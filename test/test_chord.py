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

from llamatron.music.chord import Chord, ChordType
from llamatron.music.note import Note, NoteName

# Names the tests give to their own things, and other values they use.
MAJOR = 'MAJOR'
A = 'A'
A4_C5_E5 = 'A4 C5 E5'
BB = 'Bb'
BB2_D3_F3_A3 = 'Bb2 D3 F3 A3'
G = 'G'
G4_B4_D5_F5 = 'G4 B4 D5 F5'
B = 'B'
B3_D4_F4 = 'B3 D4 F4'
E = 'E'
E2_B2 = 'E2 B2'
DB = 'Db'
F = 'F'
AB = 'Ab'
CB = 'Cb'
FB = 'Fb'
C10_E10_G10 = 'C10 E10 G10'
E4_C4_G4 = 'E4 C4 G4'
CEG = 'CEG'
C4_E4 = 'C4 E4'
C = 'C'
C4_E4_G4 = 'C4 E4 G4'
G4_C4_E4 = 'G4 C4 E4'
DB4_F4 = 'Db4 F4'
C4_EB4_G4 = 'C4 Eb4 G4'
E4_G4_C5 = 'E4 G4 C5'
C4_E4_E4 = 'C4 E4 E4'
C4 = 'C4'
E4_C4 = 'E4 C4'


def notes(text):
    """Turn 'C4 Eb4' into [Note('C', 4, 0.25), Note('Eb', 4, 0.25)]."""
    result = []
    for word in text.split():
        # Octave 10 is the only octave with two digits.
        split_at = -2 if word.endswith('10') else -1
        result.append(Note(name=word[:split_at], octave_number=int(word[split_at:]), length=0.25))
    return result


# Written out by hand rather than from the intervals, so that a wrong interval
# in ChordType fails here.
C4_CHORDS = {
    ChordType.POWER: 'C4 G4',
    ChordType.MAJOR: 'C4 E4 G4',
    ChordType.MINOR: 'C4 Eb4 G4',
    ChordType.DIMINISHED: 'C4 Eb4 Gb4',
    ChordType.AUGMENTED: 'C4 E4 G#4',
    ChordType.SUS2: 'C4 D4 G4',
    ChordType.SUS4: 'C4 F4 G4',
    ChordType.MAJOR6: 'C4 E4 G4 A4',
    ChordType.MINOR6: 'C4 Eb4 G4 A4',
    ChordType.DOMINANT7: 'C4 E4 G4 Bb4',
    ChordType.MAJOR7: 'C4 E4 G4 B4',
    ChordType.MINOR7: 'C4 Eb4 G4 Bb4',
    ChordType.MINOR_MAJOR7: 'C4 Eb4 G4 B4',
    ChordType.DIMINISHED7: 'C4 Eb4 Gb4 A4',
    ChordType.HALF_DIMINISHED7: 'C4 Eb4 Gb4 Bb4',
    ChordType.AUGMENTED7: 'C4 E4 G#4 Bb4',
    ChordType.AUGMENTED_MAJOR7: 'C4 E4 G#4 B4',
    ChordType.DOMINANT7_SUS4: 'C4 F4 G4 Bb4',
    ChordType.ADD9: 'C4 E4 G4 D5',
    ChordType.MINOR_ADD9: 'C4 Eb4 G4 D5',
    ChordType.DOMINANT9: 'C4 E4 G4 Bb4 D5',
    ChordType.MAJOR9: 'C4 E4 G4 B4 D5',
    ChordType.MINOR9: 'C4 Eb4 G4 Bb4 D5',
    ChordType.DOMINANT11: 'C4 E4 G4 Bb4 D5 F5',
    ChordType.MAJOR11: 'C4 E4 G4 B4 D5 F5',
    ChordType.MINOR11: 'C4 Eb4 G4 Bb4 D5 F5',
    ChordType.DOMINANT13: 'C4 E4 G4 Bb4 D5 F5 A5',
    ChordType.MAJOR13: 'C4 E4 G4 B4 D5 F5 A5',
    ChordType.MINOR13: 'C4 Eb4 G4 Bb4 D5 F5 A5',
}


class TestToChord(unittest.TestCase):

    def test_every_chord_type_is_checked_here(self):
        self.assertCountEqual(C4_CHORDS, list(ChordType))

    def test_every_chord_type_from_c(self):
        for typ, expected in C4_CHORDS.items():
            with self.subTest(typ=typ):
                self.assertEqual(Note(name=NoteName.C, octave_number=4, length=0.25).to_chord(typ), Chord(notes(expected)))

    def test_other_roots(self):
        cases = [
            (A, 4, ChordType.MINOR, A4_C5_E5),
            ('F#', 3, ChordType.MAJOR, 'F#3 A#3 C#4'),
            (BB, 2, ChordType.MAJOR7, BB2_D3_F3_A3),
            (G, 4, ChordType.DOMINANT7, G4_B4_D5_F5),
            (B, 3, ChordType.DIMINISHED, B3_D4_F4),
            (E, 2, ChordType.POWER, E2_B2),
        ]
        for name, octave, typ, expected in cases:
            with self.subTest(name=name, octave=octave, typ=typ):
                self.assertEqual(Note(name=name, octave_number=octave, length=0.25).to_chord(typ), Chord(notes(expected)))

    def test_returns_a_chord_with_the_root_first(self):
        chord = Note(name=NoteName.D, octave_number=4, length=0.25).to_chord(ChordType.MINOR)
        self.assertIsInstance(chord, Chord)
        self.assertEqual(chord.get_notes()[0], Note(name=NoteName.D, octave_number=4, length=0.25))

    def test_notes_are_in_order_from_the_root_up(self):
        chord = Note(name=NoteName.C, octave_number=4, length=0.25).to_chord(ChordType.MINOR13)
        numbers = [note.get_midi_number() for note in chord.get_notes()]
        self.assertEqual(numbers, sorted(numbers))

    def test_flat_roots_are_spelled_with_flats(self):
        chord = Note(name=NoteName.D_FLAT, octave_number=4, length=0.25).to_chord(ChordType.MAJOR)
        self.assertEqual([note.get_name() for note in chord.get_notes()], [DB, F, AB])

    def test_other_roots_are_spelled_with_sharps(self):
        chord = Note(name=NoteName.C_SHARP, octave_number=4, length=0.25).to_chord(ChordType.MAJOR)
        self.assertEqual([note.get_name() for note in chord.get_notes()], ['C#', F, 'G#'])

    def test_root_keeps_its_spelling(self):
        for name, octave in [('B#', 3), (CB, 4), ('E#', 4), (FB, 4)]:
            with self.subTest(name=name):
                chord = Note(name=name, octave_number=octave, length=0.25).to_chord(ChordType.MAJOR)
                self.assertEqual(chord.get_notes()[0].get_name(), name)
                self.assertEqual(chord.get_notes()[0].get_octave_number(), octave)

    def test_leaves_the_root_note_alone(self):
        note = Note(name=NoteName.C, octave_number=4, length=0.25)
        note.to_chord(ChordType.MAJOR)
        self.assertEqual(note, Note(name=NoteName.C, octave_number=4, length=0.25))

    def test_rejects_chords_with_notes_above_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note(name=NoteName.G, octave_number=10, length=0.25).to_chord(ChordType.MAJOR)

    def test_highest_root_that_fits(self):
        chord = Note(name=NoteName.C, octave_number=10, length=0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(chord, Chord(notes(C10_E10_G10)))

    def test_rejects_anything_but_a_chord_type(self):
        for typ in [MAJOR, None, (4, 7), 1]:
            with self.subTest(typ=typ):
                with self.assertRaises(ValueError):
                    Note(name=NoteName.C, octave_number=4, length=0.25).to_chord(typ)


class TestChordLengths(unittest.TestCase):

    def test_to_chord_gives_every_note_the_root_length(self):
        chord = Note(name=NoteName.C, octave_number=4, length=0.5).to_chord(ChordType.DOMINANT7)
        self.assertEqual([note.get_length() for note in chord.get_notes()], [0.5, 0.5, 0.5, 0.5])

    def test_length_is_the_longest_note(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.E, octave_number=4, length=1), Note(name=NoteName.G, octave_number=4, length=0.5)])
        self.assertEqual(chord.get_length(), 1)

    def test_different_lengths_are_not_equal(self):
        self.assertNotEqual(Chord([Note(name=NoteName.C, octave_number=4, length=0.25)]), Chord([Note(name=NoteName.C, octave_number=4, length=0.5)]))

    def test_order_does_not_affect_equality_with_mixed_lengths(self):
        first = Chord([Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.E, octave_number=4, length=0.5)])
        second = Chord([Note(name=NoteName.E, octave_number=4, length=0.5), Note(name=NoteName.C, octave_number=4, length=0.25)])
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))


class TestChord(unittest.TestCase):

    def test_keeps_notes_in_the_order_given(self):
        given = notes(E4_C4_G4)
        self.assertEqual(Chord(given).get_notes(), tuple(given))

    def test_rejects_invalid_notes(self):
        for value in [[], (), CEG, None, Note(name=NoteName.C, octave_number=4, length=0.25), [C, E], [Note(name=NoteName.C, octave_number=4, length=0.25), 60]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Chord(value)

    def test_changing_the_original_list_does_not_change_the_chord(self):
        given = notes(C4_E4)
        chord = Chord(given)
        given.append(Note(name=NoteName.G, octave_number=4, length=0.25))
        self.assertEqual(len(chord.get_notes()), 2)

    def test_cannot_be_changed(self):
        chord = Chord(notes(C4_E4))
        with self.assertRaises(AttributeError):
            chord.notes = ()

    def test_order_does_not_affect_equality(self):
        self.assertEqual(Chord(notes(C4_E4_G4)), Chord(notes(G4_C4_E4)))

    def test_enharmonic_chords_are_equal(self):
        self.assertEqual(Chord(notes('C#4 F4')), Chord(notes(DB4_F4)))

    def test_different_chords_are_not_equal(self):
        self.assertNotEqual(Chord(notes(C4_E4_G4)), Chord(notes(C4_EB4_G4)))
        self.assertNotEqual(Chord(notes(C4_E4_G4)), Chord(notes(E4_G4_C5)))
        self.assertNotEqual(Chord(notes(C4_E4)), Chord(notes(C4_E4_E4)))

    def test_is_not_equal_to_other_types(self):
        self.assertNotEqual(Chord(notes(C4)), Note(name=NoteName.C, octave_number=4, length=0.25))

    def test_equal_chords_hash_the_same(self):
        self.assertEqual(len({Chord(notes(C4_E4)), Chord(notes(E4_C4))}), 1)


if __name__ == '__main__':
    unittest.main()
