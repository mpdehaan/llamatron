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

from llamatron.music.chord import Chord
from llamatron.music.note import Degree, Note, NoteName, Rest
from llamatron.music.scale import Scale, ScaleType
from llamatron.grid.clip import Clip

QUARTER = 0.25
C4 = Note(name='C', octave_number=4, length=QUARTER)
D4 = Note(name='D', octave_number=4, length=QUARTER)
E4 = Note(name='E', octave_number=4, length=QUARTER)
F4 = Note(name='F', octave_number=4, length=QUARTER)
C_MAJOR = Scale(root=Note(name='C', octave_number=4), typ=ScaleType.MAJOR)
A_MINOR = Scale(root=Note(name='A', octave_number=3), typ=ScaleType.MINOR)

# Names the tests give to their own things, and other values they use.
RIFF = 'Riff'


class TestTotalLength(unittest.TestCase):

    def test_adds_up_the_notes(self):
        self.assertEqual(Clip(notes=[C4, Rest(0.5), D4]).total_length(), 1)

    def test_set_length_wins(self):
        self.assertEqual(Clip(notes=[C4], length=2).total_length(), 2)

    def test_empty_clip_has_no_length(self):
        self.assertEqual(Clip().total_length(), 0)

    def test_uses_note_length(self):
        self.assertEqual(Clip(notes=[1, 2], note_length=QUARTER).total_length(), 0.5)


class TestPlayedNotes(unittest.TestCase):

    def test_is_the_notes_when_there_is_no_set_length(self):
        self.assertEqual(Clip(notes=[C4, D4]).played_notes(), [C4, D4])

    def test_adds_silence_to_fill_a_set_length(self):
        self.assertEqual(Clip(notes=[C4], length=1).played_notes(), [C4, Rest(0.75)])

    def test_cuts_notes_to_fit_a_set_length(self):
        self.assertEqual(Clip(notes=[C4, D4], length=0.25).played_notes(), [C4])


class TestSection(unittest.TestCase):

    def setUp(self):
        self.clip = Clip(name=RIFF, notes=[C4, D4, E4, F4], scale=C_MAJOR)

    def test_takes_the_notes_in_the_section(self):
        self.assertEqual(self.clip.section(start=0.25, end=0.75).get_notes(), [D4, E4])

    def test_whole_clip(self):
        self.assertEqual(self.clip.section(start=0, end=1).get_notes(), [C4, D4, E4, F4])

    def test_cuts_a_note_at_the_end(self):
        self.assertEqual(self.clip.section(start=0, end=0.375).get_notes(), [C4, Note(name=NoteName.D, octave_number=4, length=0.125)])

    def test_cuts_a_note_at_the_start(self):
        self.assertEqual(self.clip.section(start=0.125, end=0.5).get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.125), D4])

    def test_cuts_a_note_at_both_ends(self):
        clip = Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)])
        self.assertEqual(clip.section(start=0.25, end=0.5).get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.25)])

    def test_cuts_rests(self):
        clip = Clip(notes=[C4, Rest(0.5), D4])
        self.assertEqual(clip.section(start=0.5, end=1).get_notes(), [Rest(0.25), D4])

    def test_past_the_end_becomes_silence(self):
        self.assertEqual(self.clip.section(start=0.75, end=1.5).get_notes(), [F4, Rest(0.5)])
        self.assertEqual(self.clip.section(start=2, end=3).get_notes(), [Rest(1)])

    def test_always_lasts_the_section_length(self):
        for start, end in [(0, 1), (0.1, 0.9), (0.125, 0.375), (0.5, 5)]:
            with self.subTest(start=start, end=end):
                self.assertEqual(
                    self.clip.section(start=start, end=end).total_length(),
                    Fraction(end).limit_denominator(1_000_000) - Fraction(start).limit_denominator(1_000_000),
                )

    def test_chord_notes_are_cut_together(self):
        clip = Clip(notes=[Chord([Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.E, octave_number=4, length=0.25)])])
        self.assertEqual(clip.section(start=0, end=0.125).get_notes(), [Chord([Note(name=NoteName.C, octave_number=4, length=0.125), Note(name=NoteName.E, octave_number=4, length=0.125)])])

    def test_chord_notes_that_have_ended_are_left_out(self):
        clip = Clip(notes=[Chord([Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.E, octave_number=4, length=0.25)])])
        self.assertEqual(clip.section(start=0.25, end=0.5).get_notes(), [Chord([Note(name=NoteName.C, octave_number=4, length=0.25)])])

    def test_degrees_stay_degrees(self):
        clip = Clip(notes=[Degree(number=3, length=0.5)])
        self.assertEqual(clip.section(start=0, end=0.25).get_notes(), [Degree(number=3, length=0.25)])

    def test_uses_note_length(self):
        clip = Clip(notes=[1, 2], note_length=QUARTER)
        self.assertEqual(clip.section(start=0.25, end=0.5).get_notes(), [Degree(number=2, length=QUARTER)])

    def test_respects_a_set_length(self):
        clip = Clip(notes=[C4, D4], length=0.25)
        self.assertEqual(clip.section(start=0, end=0.5).get_notes(), [C4, Rest(0.25)])

    def test_keeps_the_clip_details(self):
        result = self.clip.section(start=0, end=0.25)
        self.assertEqual(result.get_name(), RIFF)
        self.assertIs(result.get_scale(), C_MAJOR)
        self.assertIsNot(result, self.clip)

    def test_leaves_the_original_unchanged(self):
        self.clip.section(start=0, end=0.25)
        self.assertEqual(self.clip.get_notes(), [C4, D4, E4, F4])

    def test_rejects_invalid_sections(self):
        for start, end in [(0.5, 0.25), (0.5, 0.5), (-1, 1)]:
            with self.subTest(start=start, end=end):
                with self.assertRaises(ValueError):
                    self.clip.section(start=start, end=end)



class TestRepeated(unittest.TestCase):

    def test_plays_the_clip_in_a_row_so_it_lasts_longer(self):
        result = Clip(notes=[C4, D4]).repeated(2)
        self.assertEqual(result.get_notes(), [C4, D4, C4, D4])
        self.assertEqual(result.total_length(), 1)

    def test_keeps_silence_from_a_set_length(self):
        result = Clip(notes=[C4], length=0.5).repeated(2)
        self.assertEqual(result.get_notes(), [C4, Rest(0.25), C4, Rest(0.25)])

    def test_keeps_the_clip_details(self):
        result = Clip(name=RIFF, notes=[C4], scale=C_MAJOR).repeated(1)
        self.assertEqual(result.get_name(), RIFF)
        self.assertIs(result.get_scale(), C_MAJOR)

    def test_rejects_invalid_times(self):
        for times in [0, -1, 1.5, '2', None, True]:
            with self.subTest(times=times):
                with self.assertRaises(ValueError):
                    Clip(notes=[C4]).repeated(times)



if __name__ == '__main__':
    unittest.main()
