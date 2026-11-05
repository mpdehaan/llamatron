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

from src.analyzers.clash_finder import ClashFinder
from src.chord import ChordType
from src.generators.base import ClipGenerator
from src.legacy.generators.smoother import Smoother
from src.note import Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

QUARTER = 0.25
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
C_CHORD = Note('C', 3, 4).to_chord(ChordType.MAJOR)
CHORDS = Clip(notes=[C_CHORD])


def q(name, octave=4):
    return Note(name, octave, QUARTER)


def smooth(notes, chords=CHORDS, **options):
    return Smoother(chords, **options).generate(Clip(notes=notes)).notes


class TestClashes(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Smoother(CHORDS), ClipGenerator)

    def test_notes_that_fit_stay_exactly_as_they_are(self):
        notes = [q('C'), q('D'), q('E'), q('G'), q('A')]
        self.assertEqual(smooth(notes), notes)

    def test_a_clashing_note_moves_to_the_nearest_chord_note(self):
        self.assertEqual(smooth([q('F')]), [q('E')])

    def test_a_clashing_note_below_a_chord_note_moves_too(self):
        self.assertEqual(smooth([q('B')]), [q('C', 5)])

    def test_the_result_never_clashes(self):
        notes = [q(name) for name in ['F', 'B', 'F', 'C#', 'F#', 'B']]
        result = smooth(notes)
        self.assertEqual(ClashFinder().analyze(Clip(notes=result), CHORDS), [])

    def test_passing_notes_stay(self):
        notes = [Note('E', 4, 0.125), Note('F', 4, 0.125)]
        self.assertEqual(smooth(notes), notes)
        stepping = [q('E'), q('F'), q('G')]
        self.assertEqual(smooth(stepping), stepping)

    def test_keeps_the_note_length(self):
        self.assertEqual(smooth([Note('F', 4, 0.5)])[0].length, 0.5)


class TestLeaps(unittest.TestCase):

    def test_small_leaps_stay(self):
        notes = [q('C'), q('G')]
        self.assertEqual(smooth(notes), notes)

    def test_a_big_leap_moves_by_an_octave(self):
        self.assertEqual(smooth([q('C'), q('A', 5)]), [q('C'), q('A')])

    def test_a_big_leap_down_moves_too(self):
        self.assertEqual(smooth([q('C', 5), q('D', 3)]), [q('C', 5), q('D', 4)])

    def test_the_note_name_stays_the_same(self):
        result = smooth([q('C'), q('A', 5)])
        self.assertEqual(result[1].name, 'A')

    def test_leaps_are_measured_across_rests(self):
        result = smooth([q('C'), Rest(QUARTER), q('A', 5)])
        self.assertEqual(result, [q('C'), Rest(QUARTER), q('A')])

    def test_max_leap_can_change(self):
        notes = [q('C'), q('A')]
        self.assertEqual(smooth(notes, max_leap=12), notes)
        wide = [q('C'), q('A'), q('A', 3)]
        self.assertEqual(smooth(wide, max_leap=5), [q('C'), q('A', 3), q('A', 3)])

    def test_a_move_cannot_leave_the_original_range(self):
        notes = [q('C'), q('A')]
        self.assertEqual(smooth(notes, max_leap=5), notes)
        lines = [[q('C', 5), q('D', 3), q('C', 4)], [q('C', 3), q('A', 5), q('G', 4)]]
        for line in lines:
            original = [note.midi_number for note in line]
            result = [note.midi_number for note in smooth(line)]
            with self.subTest(line=line):
                self.assertGreaterEqual(min(result), min(original))
                self.assertLessEqual(max(result), max(original))

    def test_first_note_never_moves_for_a_leap(self):
        self.assertEqual(smooth([q('A', 6)])[0], q('A', 6))

    def test_stays_in_the_midi_range(self):
        high = Note('G', 10, QUARTER)
        self.assertEqual(smooth([high])[0].midi_number % 12, 7)


class TestOtherPositions(unittest.TestCase):

    def test_rests_stay(self):
        self.assertEqual(smooth([Rest(1)]), [Rest(1)])

    def test_chords_in_the_melody_stay(self):
        chord = q('F').to_chord(ChordType.MAJOR)
        self.assertEqual(smooth([chord]), [chord])

    def test_empty_clip_stays_empty(self):
        self.assertEqual(smooth([]), [])

    def test_only_chords_at_that_time_count(self):
        chords = Clip(notes=[Rest(1), C_CHORD])
        self.assertEqual(smooth([q('F')], chords), [q('F')])

    def test_keeps_details_and_leaves_the_original_alone(self):
        original = Clip('Riff', notes=[q('F')], scale=C_MAJOR, length=2)
        result = Smoother(CHORDS).generate(original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.length, 2)
        self.assertEqual(original.notes, [q('F')])


class TestFields(unittest.TestCase):

    def test_rejects_invalid_values(self):
        for chords in [None, 'chords', C_CHORD]:
            with self.subTest(chords=chords):
                with self.assertRaises(ValueError):
                    Smoother(chords)
        for max_leap in [0, -1, 1.5, '7', None, True]:
            with self.subTest(max_leap=max_leap):
                with self.assertRaises(ValueError):
                    Smoother(CHORDS, max_leap=max_leap)
        with self.assertRaises(ValueError):
            Smoother(CHORDS).generate('clip')

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Smoother(CHORDS)
        generator.max_leap = 5
        self.assertEqual(generator.max_leap, 5)
        with self.assertRaises(ValueError):
            generator.max_leap = 0
        self.assertEqual(generator.max_leap, 5)


if __name__ == '__main__':
    unittest.main()
