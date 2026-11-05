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

from demo.tunes import RISING_SUN, RISING_SUN_CHORDS, SIMPLE_GIFTS, SIMPLE_GIFTS_CHORDS
from llamatron.analyzers.chord_change_finder import ChordChangeFinder
from llamatron.analyzers.clash_finder import ClashFinder
from llamatron.analyzers.phrase_finder import PhraseFinder
from llamatron.analyzers.scale_detector import ScaleDetector
from llamatron.chord import ChordType
from llamatron.note import Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

QUARTER = 0.25
C4 = Note('C', 4, QUARTER)
C_CHORD = Note('C', 3, 1).to_chord(ChordType.MAJOR)
F_CHORD = Note('F', 3, 1).to_chord(ChordType.MAJOR)


class TestPhraseFinder(unittest.TestCase):

    def test_finds_the_end_of_a_long_note(self):
        clip = Clip(notes=[C4, Note('D', 4, 0.5), C4])
        self.assertEqual(PhraseFinder().analyze(clip), [0.75])

    def test_finds_the_end_of_a_long_rest(self):
        clip = Clip(notes=[C4, Rest(0.5), C4])
        self.assertEqual(PhraseFinder().analyze(clip), [0.75])

    def test_ignores_the_end_of_the_clip(self):
        self.assertEqual(PhraseFinder().analyze(Clip(notes=[C4, Note('D', 4, 1)])), [])

    def test_short_notes_do_not_end_a_phrase(self):
        self.assertEqual(PhraseFinder().analyze(Clip(notes=[C4, C4, C4])), [])

    def test_minimum_length_can_change(self):
        clip = Clip(notes=[C4, C4])
        self.assertEqual(PhraseFinder(minimum_length=QUARTER).analyze(clip), [0.25])

    def test_finds_the_ends_of_simple_gifts_phrases(self):
        points = PhraseFinder().analyze(SIMPLE_GIFTS)
        self.assertIn(9, points)
        self.assertLess(len(points), 6)

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            PhraseFinder(minimum_length=0)
        with self.assertRaises(ValueError):
            PhraseFinder().analyze('clip')


class TestChordChangeFinder(unittest.TestCase):

    def test_finds_changes(self):
        clip = Clip(notes=[C_CHORD, C_CHORD, F_CHORD, C_CHORD])
        self.assertEqual(ChordChangeFinder().analyze(clip), [2, 3])

    def test_no_changes(self):
        self.assertEqual(ChordChangeFinder().analyze(Clip(notes=[C_CHORD, C_CHORD])), [])

    def test_ignores_octaves(self):
        higher = Note('C', 5, 1).to_chord(ChordType.MAJOR)
        self.assertEqual(ChordChangeFinder().analyze(Clip(notes=[C_CHORD, higher])), [])

    def test_ignores_rests(self):
        clip = Clip(notes=[C_CHORD, Rest(1), C_CHORD, Rest(1), F_CHORD])
        self.assertEqual(ChordChangeFinder().analyze(clip), [4])

    def test_finds_the_rising_sun_changes(self):
        chords = RISING_SUN_CHORDS
        self.assertEqual(len(ChordChangeFinder().analyze(chords)), 13)

    def test_rejects_anything_but_a_clip(self):
        with self.assertRaises(ValueError):
            ChordChangeFinder().analyze('clip')


class TestClashFinder(unittest.TestCase):

    def clashes(self, *melody, chord=C_CHORD):
        return ClashFinder().analyze(Clip(notes=list(melody)), Clip(notes=[chord]))

    def test_chord_notes_never_clash(self):
        self.assertEqual(self.clashes(C4, Note('E', 4, QUARTER), Note('G', 4, QUARTER)), [])

    def test_a_note_a_whole_step_away_does_not_clash(self):
        self.assertEqual(self.clashes(Note('D', 4, QUARTER), Note('A', 4, QUARTER)), [])

    def test_a_note_a_half_step_away_clashes(self):
        clashes = self.clashes(Note('F', 4, QUARTER))
        self.assertEqual([(c.time, c.melody_pitch % 12, c.chord_pitch % 12) for c in clashes], [(0, 5, 4)])

    def test_a_note_a_half_step_below_clashes(self):
        clashes = self.clashes(Note('B', 4, QUARTER))
        self.assertEqual([(c.melody_pitch % 12, c.chord_pitch % 12) for c in clashes], [(11, 0)])

    def test_any_octave_counts(self):
        self.assertEqual(len(self.clashes(Note('F', 7, QUARTER))), 1)

    def test_a_short_note_off_the_beat_is_a_passing_note(self):
        passing = Note('F', 4, 0.125)
        self.assertEqual(self.clashes(Note('E', 4, 0.125), passing), [])

    def test_a_short_note_on_the_beat_counts(self):
        self.assertEqual(len(self.clashes(Note('F', 4, 0.125))), 1)

    def test_a_long_note_off_the_beat_counts(self):
        self.assertEqual(len(self.clashes(Note('E', 4, 0.125), Note('F', 4, QUARTER))), 1)

    def test_a_note_stepping_between_its_neighbors_is_a_passing_note(self):
        self.assertEqual(self.clashes(Note('E', 4, QUARTER), Note('F', 4, QUARTER), Note('G', 4, QUARTER)), [])

    def test_a_note_stepping_away_and_back_is_a_passing_note(self):
        self.assertEqual(self.clashes(Note('E', 4, QUARTER), Note('F', 4, QUARTER), Note('E', 4, QUARTER)), [])

    def test_a_note_reached_by_a_leap_still_clashes(self):
        self.assertEqual(len(self.clashes(Note('C', 4, QUARTER), Note('F', 4, QUARTER), Note('E', 4, QUARTER))), 1)

    def test_a_note_longer_than_a_beat_still_clashes_between_steps(self):
        self.assertEqual(len(self.clashes(Note('E', 4, QUARTER), Note('F', 4, 0.5), Note('G', 4, QUARTER))), 1)

    def test_only_chords_at_that_time_count(self):
        melody = Clip(notes=[Rest(1), Note('F', 4, QUARTER)])
        chords = Clip(notes=[C_CHORD, F_CHORD])
        self.assertEqual(ClashFinder().analyze(melody, chords), [])

    def test_degrees_use_the_clip_scale(self):
        scale = Scale(Note('C', 4), ScaleType.MAJOR)
        melody = Clip(notes=[4], note_length=QUARTER, scale=scale)
        self.assertEqual(len(ClashFinder().analyze(melody, Clip(notes=[C_CHORD]))), 1)

    def test_beat_can_change(self):
        passing = Note('F', 4, 0.125)
        melody = Clip(notes=[Note('E', 4, 0.125), passing])
        chords = Clip(notes=[C_CHORD])
        self.assertEqual(len(ClashFinder(beat=0.125).analyze(melody, chords)), 1)

    def test_rising_sun_chart_fits_its_melody(self):
        self.assertEqual(ClashFinder().analyze(RISING_SUN, RISING_SUN_CHORDS), [])

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            ClashFinder(beat=0)
        with self.assertRaises(ValueError):
            ClashFinder().analyze('clip', Clip())
        with self.assertRaises(ValueError):
            ClashFinder().analyze(Clip(), 'clip')


class TestScaleDetector(unittest.TestCase):

    def detect(self, clip):
        scale = ScaleDetector().analyze(clip)
        return scale.root.name, scale.typ

    def test_finds_both_tunes(self):
        self.assertEqual(self.detect(SIMPLE_GIFTS), ('C', ScaleType.MAJOR))
        self.assertEqual(self.detect(RISING_SUN), ('A', ScaleType.MINOR))

    def test_the_last_note_decides_between_relative_keys(self):
        long_a_ends_on_c = [Note('A', 4, 2), Note('E', 4, 0.25), Note('C', 4, 0.25)]
        self.assertEqual(self.detect(Clip(notes=long_a_ends_on_c)), ('C', ScaleType.MAJOR))
        long_c_ends_on_a = [Note('C', 4, 2), Note('E', 4, 0.25), Note('A', 3, 0.25)]
        self.assertEqual(self.detect(Clip(notes=long_c_ends_on_a)), ('A', ScaleType.MINOR))

    def test_finds_a_tune_with_many_notes_outside_its_scale(self):
        names = ['A', 'E', 'G', 'A', 'F', 'D', 'C#', 'G#', 'B', 'C']
        notes = [Note(name, 4, 0.25) for name in names]
        self.assertEqual(self.detect(Clip(notes=notes)), ('C', ScaleType.MAJOR))

    def test_relative_keys_are_told_apart_by_their_home_note(self):
        c_major = Scale(Note('C', 4, 0.25), ScaleType.MAJOR).octaves(1)
        a_minor = Scale(Note('A', 3, 0.25), ScaleType.MINOR).octaves(1)
        self.assertEqual(self.detect(Clip(notes=c_major)), ('C', ScaleType.MAJOR))
        self.assertEqual(self.detect(Clip(notes=a_minor)), ('A', ScaleType.MINOR))

    def test_finds_other_keys(self):
        d_major = Scale(Note('D', 4, 0.25), ScaleType.MAJOR).octaves(1)
        self.assertEqual(self.detect(Clip(notes=d_major)), ('D', ScaleType.MAJOR))

    def test_root_is_at_or_below_the_lowest_note(self):
        self.assertEqual(ScaleDetector().analyze(SIMPLE_GIFTS).root.midi_number, 48)
        self.assertEqual(ScaleDetector().analyze(RISING_SUN).root.midi_number, 45)

    def test_types_can_change(self):
        notes = Scale(Note('D', 4, 0.25), ScaleType.DORIAN).octaves(1)
        scale = ScaleDetector(types=[ScaleType.DORIAN]).analyze(Clip(notes=notes))
        self.assertEqual((scale.root.name, scale.typ), ('D', ScaleType.DORIAN))

    def test_rejects_invalid_values(self):
        for types in [[], None, ['MAJOR']]:
            with self.subTest(types=types):
                with self.assertRaises(ValueError):
                    ScaleDetector(types=types)
        with self.assertRaises(ValueError):
            ScaleDetector().analyze('clip')
        with self.assertRaises(ValueError):
            ScaleDetector().analyze(Clip(notes=[Rest(1)]))


class TestSimpleGiftsChart(unittest.TestCase):

    def test_chart_has_a_few_places_for_harmonize_to_fix(self):
        clashes = ClashFinder().analyze(SIMPLE_GIFTS, SIMPLE_GIFTS_CHORDS)
        self.assertLess(len(clashes), 5)


if __name__ == '__main__':
    unittest.main()
