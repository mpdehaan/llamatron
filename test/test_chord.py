import dataclasses
import unittest

from src.chord import Chord, ChordType
from src.note import Note


def notes(text):
    """Turn 'C4 Eb4' into [Note('C', 4), Note('Eb', 4)]."""
    result = []
    for word in text.split():
        # Octave 10 is the only octave with two digits.
        split_at = -2 if word.endswith('10') else -1
        result.append(Note(word[:split_at], int(word[split_at:])))
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
                self.assertEqual(Note('C', 4).to_chord(typ), Chord(notes(expected)))

    def test_other_roots(self):
        cases = [
            ('A', 4, ChordType.MINOR, 'A4 C5 E5'),
            ('F#', 3, ChordType.MAJOR, 'F#3 A#3 C#4'),
            ('Bb', 2, ChordType.MAJOR7, 'Bb2 D3 F3 A3'),
            ('G', 4, ChordType.DOMINANT7, 'G4 B4 D5 F5'),
            ('B', 3, ChordType.DIMINISHED, 'B3 D4 F4'),
            ('E', 2, ChordType.POWER, 'E2 B2'),
        ]
        for name, octave, typ, expected in cases:
            with self.subTest(name=name, octave=octave, typ=typ):
                self.assertEqual(Note(name, octave).to_chord(typ), Chord(notes(expected)))

    def test_returns_a_chord_with_the_root_first(self):
        chord = Note('D', 4).to_chord(ChordType.MINOR)
        self.assertIsInstance(chord, Chord)
        self.assertEqual(chord.notes[0], Note('D', 4))

    def test_notes_are_in_order_from_the_root_up(self):
        chord = Note('C', 4).to_chord(ChordType.MINOR13)
        numbers = [note.midi_number for note in chord.notes]
        self.assertEqual(numbers, sorted(numbers))

    def test_flat_roots_are_spelled_with_flats(self):
        chord = Note('Db', 4).to_chord(ChordType.MAJOR)
        self.assertEqual([note.name for note in chord.notes], ['Db', 'F', 'Ab'])

    def test_other_roots_are_spelled_with_sharps(self):
        chord = Note('C#', 4).to_chord(ChordType.MAJOR)
        self.assertEqual([note.name for note in chord.notes], ['C#', 'F', 'G#'])

    def test_root_keeps_its_spelling(self):
        for name, octave in [('B#', 3), ('Cb', 4), ('E#', 4), ('Fb', 4)]:
            with self.subTest(name=name):
                chord = Note(name, octave).to_chord(ChordType.MAJOR)
                self.assertEqual(chord.notes[0].name, name)
                self.assertEqual(chord.notes[0].octave_number, octave)

    def test_leaves_the_root_note_alone(self):
        note = Note('C', 4)
        note.to_chord(ChordType.MAJOR)
        self.assertEqual(note, Note('C', 4))

    def test_rejects_chords_with_notes_above_the_midi_range(self):
        with self.assertRaises(ValueError):
            Note('G', 10).to_chord(ChordType.MAJOR)

    def test_highest_root_that_fits(self):
        chord = Note('C', 10).to_chord(ChordType.MAJOR)
        self.assertEqual(chord, Chord(notes('C10 E10 G10')))

    def test_rejects_anything_but_a_chord_type(self):
        for typ in ['MAJOR', None, (4, 7), 1]:
            with self.subTest(typ=typ):
                with self.assertRaises(ValueError):
                    Note('C', 4).to_chord(typ)


class TestChord(unittest.TestCase):

    def test_keeps_notes_in_the_order_given(self):
        given = notes('E4 C4 G4')
        self.assertEqual(Chord(given).notes, tuple(given))

    def test_rejects_invalid_notes(self):
        for value in [[], (), 'CEG', None, Note('C', 4), ['C', 'E'], [Note('C', 4), 60]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Chord(value)

    def test_changing_the_original_list_does_not_change_the_chord(self):
        given = notes('C4 E4')
        chord = Chord(given)
        given.append(Note('G', 4))
        self.assertEqual(len(chord.notes), 2)

    def test_cannot_be_changed(self):
        chord = Chord(notes('C4 E4'))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            chord.notes = ()

    def test_order_does_not_affect_equality(self):
        self.assertEqual(Chord(notes('C4 E4 G4')), Chord(notes('G4 C4 E4')))

    def test_enharmonic_chords_are_equal(self):
        self.assertEqual(Chord(notes('C#4 F4')), Chord(notes('Db4 F4')))

    def test_different_chords_are_not_equal(self):
        self.assertNotEqual(Chord(notes('C4 E4 G4')), Chord(notes('C4 Eb4 G4')))
        self.assertNotEqual(Chord(notes('C4 E4 G4')), Chord(notes('E4 G4 C5')))
        self.assertNotEqual(Chord(notes('C4 E4')), Chord(notes('C4 E4 E4')))

    def test_is_not_equal_to_other_types(self):
        self.assertNotEqual(Chord(notes('C4')), Note('C', 4))

    def test_equal_chords_hash_the_same(self):
        self.assertEqual(len({Chord(notes('C4 E4')), Chord(notes('E4 C4'))}), 1)


if __name__ == '__main__':
    unittest.main()
