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

from demo.tunes import C_MAJOR, SIMPLE_GIFTS, SIMPLE_GIFTS_CHORDS
from src.analyzers.clash_finder import ClashFinder
from src.chord import Chord, ChordType
from src.legacy.generators.accompany import Accompany
from src.generators.base import ClipGenerator
from src.legacy.generators.harmonize import Harmonize
from src.note import Note, Rest
from src.song import Clip

C_CHORD = Note('C', 3, 1).to_chord(ChordType.MAJOR)
F_CHORD = Note('F', 3, 1).to_chord(ChordType.MAJOR)
G_CHORD = Note('G', 3, 1).to_chord(ChordType.MAJOR)


def melody(*names):
    return Clip(notes=[Note(name, 4, 1) for name in names], scale=C_MAJOR)


def chart(*chords):
    return Clip(notes=list(chords), scale=C_MAJOR)


class TestHarmonize(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Harmonize([chart(C_CHORD)]), ClipGenerator)

    def test_plays_the_real_chord_when_it_does_not_clash(self):
        result = Harmonize([chart(C_CHORD, F_CHORD)]).generate(melody('C', 'F'))
        self.assertEqual(result.notes, [C_CHORD, F_CHORD])

    def test_plays_a_real_chord_that_is_not_in_the_scale(self):
        d_major = Note('D', 3, 1).to_chord(ChordType.MAJOR)
        result = Harmonize([chart(d_major)]).generate(melody('D'))
        self.assertEqual(result.notes, [d_major])

    def test_tries_the_next_chart_when_a_chord_clashes(self):
        result = Harmonize([chart(C_CHORD), chart(F_CHORD)]).generate(melody('F'))
        self.assertEqual(result.notes, [F_CHORD])

    def test_chooses_from_the_scale_when_every_chart_clashes(self):
        result = Harmonize([chart(C_CHORD), chart(C_CHORD)]).generate(melody('F'))
        self.assertEqual(ClashFinder().analyze(melody('F'), Clip(notes=result.notes)), [])
        self.assertNotEqual(result.notes, [C_CHORD])

    def test_keeps_the_chart_slots(self):
        short = [
            Chord([Note('C', 3, 0.5), Note('E', 3, 0.5)]),
            Chord([Note('F', 3, 1.5), Note('A', 3, 1.5)]),
        ]
        result = Harmonize([Clip(notes=short, scale=C_MAJOR)]).generate(melody('C', 'A'))
        self.assertEqual(result.notes, short)

    def test_a_rest_in_a_chart_falls_through_to_the_next(self):
        result = Harmonize([chart(Rest(1)), chart(C_CHORD)]).generate(melody('C'))
        self.assertEqual(result.notes, [C_CHORD])

    def test_uses_the_scale_given_or_else_the_melody_clip_scale(self):
        clip = Clip(notes=[Note('F', 4, 1)])
        with self.assertRaises(ValueError):
            Harmonize([Clip(notes=[C_CHORD])]).generate(clip)
        Harmonize([Clip(notes=[C_CHORD])], scale=C_MAJOR).generate(clip)

    def test_never_clashes_on_all_of_simple_gifts(self):
        result = Harmonize([SIMPLE_GIFTS_CHORDS], scale=C_MAJOR).generate(SIMPLE_GIFTS)
        self.assertEqual(ClashFinder().analyze(SIMPLE_GIFTS, result), [])

    def test_keeps_most_of_the_real_chords(self):
        chart_chords = SIMPLE_GIFTS_CHORDS.resolved_notes()
        result = Harmonize([SIMPLE_GIFTS_CHORDS], scale=C_MAJOR).generate(SIMPLE_GIFTS).notes
        same = sum(chord == real for chord, real in zip(result, chart_chords))
        self.assertGreaterEqual(same, len(chart_chords) - 2)

    def test_does_not_change_the_melody(self):
        clip = melody('C')
        Harmonize([chart(C_CHORD)]).generate(clip)
        self.assertEqual(clip.notes, [Note('C', 4, 1)])

    def test_keeps_the_clip_details(self):
        clip = Clip('Riff', notes=[Note('C', 4, 1)], scale=C_MAJOR)
        result = Harmonize([chart(C_CHORD)]).generate(clip)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)

    def test_rejects_charts_of_a_different_length(self):
        with self.assertRaises(ValueError):
            Harmonize([chart(C_CHORD)]).generate(melody('C', 'C'))

    def test_rejects_invalid_values(self):
        for charts in [[], None, chart(C_CHORD), ['chart']]:
            with self.subTest(charts=charts):
                with self.assertRaises(ValueError):
                    Harmonize(charts)
        with self.assertRaises(ValueError):
            Harmonize([chart(C_CHORD)], scale='C major')
        with self.assertRaises(ValueError):
            Harmonize([chart(C_CHORD)]).generate('clip')

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Harmonize([chart(C_CHORD)])
        generator.scale = C_MAJOR
        self.assertIs(generator.scale, C_MAJOR)
        with self.assertRaises(ValueError):
            generator.charts = []
        self.assertEqual(len(generator.charts), 1)


class TestConnectingChords(unittest.TestCase):

    def test_prefers_a_chord_that_shares_a_note_with_the_one_before(self):
        generator = Harmonize([chart(C_CHORD, C_CHORD)], scale=C_MAJOR)
        result = generator.generate(melody('C', 'F')).notes
        self.assertEqual(result[0], C_CHORD)
        shared = {note.midi_number % 12 for note in C_CHORD.notes}
        self.assertTrue(any(note.midi_number % 12 in shared for note in result[1].notes))


class TestRankedChords(unittest.TestCase):

    def test_best_fit_comes_first(self):
        chords = Accompany(scale=C_MAJOR).ranked_chords(melody('F'))
        self.assertEqual(chords[0], F_CHORD)

    def test_every_chord_in_the_scale_is_offered(self):
        self.assertEqual(len(Accompany(scale=C_MAJOR).ranked_chords(melody('C'))), 7)

    def test_needs_a_scale(self):
        with self.assertRaises(ValueError):
            Accompany().ranked_chords(Clip(notes=[Note('C', 4, 1)]))


if __name__ == '__main__':
    unittest.main()
