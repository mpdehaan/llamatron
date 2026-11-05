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

from demo.mary import MELODY
from llamatron.chord import Chord
from llamatron.legacy.generators.accompany import Accompany
from llamatron.generators.base import ClipGenerator
from llamatron.note import Degree, Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

WHOLE = 1
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)
PENTATONIC = Scale(Note('C', 4), ScaleType.MAJOR_PENTATONIC)


def chord(*names, length=WHOLE):
    """Return a chord from names like 'C3'."""
    return Chord([Note(name[:-1], int(name[-1]), length) for name in names])


C_CHORD = chord('C3', 'E3', 'G3')
F_CHORD = chord('F3', 'A3', 'C4')
G_CHORD = chord('G3', 'B3', 'D4')
D_MINOR_CHORD = chord('D3', 'F3', 'A3')


def accompany(notes, **clip_options):
    clip_options.setdefault('scale', C_MAJOR)
    return Accompany().generate(Clip(notes=notes, **clip_options))


class TestChoosingChords(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Accompany(), ClipGenerator)

    def test_finds_the_chords_for_mary(self):
        melody = [note for section in MELODY for note in section]
        self.assertEqual(accompany(melody).notes, [
            C_CHORD, C_CHORD, G_CHORD, C_CHORD, C_CHORD, C_CHORD, G_CHORD, C_CHORD,
        ])

    def test_picks_the_chord_that_holds_the_notes(self):
        notes = [Note('F', 4, 0.5), Note('A', 4, 0.5)]
        self.assertEqual(accompany(notes).notes, [F_CHORD])

    def test_longer_notes_count_for_more(self):
        notes = [Note('D', 4, 0.75), Note('C', 4, 0.25)]
        self.assertIn(accompany(notes).notes[0], [G_CHORD, D_MINOR_CHORD])

    def test_ties_go_to_the_first_then_fifth_then_fourth(self):
        self.assertEqual(accompany([Note('C', 4, WHOLE)]).notes, [C_CHORD])
        self.assertEqual(accompany([Note('G', 4, WHOLE)]).notes, [C_CHORD])
        self.assertEqual(accompany([Note('D', 4, WHOLE)]).notes, [G_CHORD])
        self.assertEqual(accompany([Note('F', 4, WHOLE)]).notes, [F_CHORD])

    def test_any_octave_of_a_note_counts(self):
        self.assertEqual(accompany([Note('F', 2, WHOLE)]).notes, [F_CHORD])

    def test_notes_outside_the_scale_do_not_help_a_chord(self):
        notes = [Note('C#', 4, 0.5), Note('F', 4, 0.5)]
        self.assertEqual(accompany(notes).notes, [F_CHORD])

    def test_uses_the_shape_of_the_scale(self):
        notes = [Note('A', 4, 0.5), Note('C', 5, 0.5)]
        result = accompany(notes, scale=A_MINOR).notes
        self.assertEqual(result, [chord('A2', 'C3', 'E3')])

    def test_scales_with_fewer_notes_still_work(self):
        result = accompany([Note('C', 4, WHOLE)], scale=PENTATONIC).notes
        self.assertEqual(result, [chord('C3', 'E3', 'A3')])

    def test_chords_in_the_melody_count(self):
        melody_chord = Chord([Note('F', 4, WHOLE), Note('A', 4, WHOLE)])
        self.assertEqual(accompany([melody_chord]).notes, [F_CHORD])

    def test_degrees_in_the_melody_use_the_scale(self):
        self.assertEqual(accompany([Degree(4, WHOLE)]).notes, [F_CHORD])

    def test_note_length_is_used(self):
        result = accompany([4, 6, 4, 6], note_length=0.25)
        self.assertEqual(result.notes, [F_CHORD])


class TestMeasures(unittest.TestCase):

    def test_one_chord_per_measure(self):
        notes = [Note('C', 4, WHOLE), Note('F', 4, WHOLE), Note('D', 4, WHOLE)]
        self.assertEqual(accompany(notes).notes, [C_CHORD, F_CHORD, G_CHORD])

    def test_a_note_counts_in_every_measure_it_crosses(self):
        notes = [Rest(0.5), Note('F', 4, WHOLE), Rest(0.5)]
        self.assertEqual(accompany(notes).notes, [F_CHORD, F_CHORD])

    def test_last_chord_stops_at_the_end_of_the_melody(self):
        notes = [Note('C', 4, WHOLE), Note('F', 4, 0.5)]
        self.assertEqual(accompany(notes).notes, [C_CHORD, chord('F3', 'A3', 'C4', length=0.5)])

    def test_measure_with_no_notes_repeats_the_chord_before_it(self):
        notes = [Note('F', 4, WHOLE), Rest(WHOLE), Note('D', 4, WHOLE)]
        self.assertEqual(accompany(notes).notes, [F_CHORD, F_CHORD, G_CHORD])

    def test_first_measure_with_no_notes_uses_the_first_chord(self):
        notes = [Rest(WHOLE), Note('F', 4, WHOLE)]
        self.assertEqual(accompany(notes).notes, [C_CHORD, F_CHORD])

    def test_only_rests_uses_the_first_chord(self):
        self.assertEqual(accompany([Rest(WHOLE)]).notes, [C_CHORD])

    def test_empty_clip_has_no_chords(self):
        self.assertEqual(accompany([]).notes, [])

    def test_measure_length_can_change(self):
        notes = [Note('C', 4, 0.5), Note('F', 4, 0.5)]
        result = Accompany(measure_length=0.5).generate(Clip(notes=notes, scale=C_MAJOR))
        self.assertEqual(result.notes, [
            chord('C3', 'E3', 'G3', length=0.5), chord('F3', 'A3', 'C4', length=0.5),
        ])

    def test_set_length_is_kept_and_filled(self):
        result = accompany([Note('F', 4, 0.25)], length=2)
        self.assertEqual(result.length, 2)
        self.assertEqual(result.notes, [F_CHORD, F_CHORD])

    def test_set_length_ignores_notes_past_the_end(self):
        notes = [Note('F', 4, WHOLE), Note('D', 4, WHOLE)]
        self.assertEqual(accompany(notes, length=1).notes, [F_CHORD])


class TestOptions(unittest.TestCase):

    def test_octave_moves_the_chords(self):
        generator = Accompany(octave=0)
        result = generator.generate(Clip(notes=[Note('C', 4, WHOLE)], scale=C_MAJOR))
        self.assertEqual(result.notes, [chord('C4', 'E4', 'G4')])

    def test_uses_the_clip_scale(self):
        generator = Accompany()
        clip = Clip(notes=[Note('A', 4, WHOLE)], scale=A_MINOR)
        self.assertEqual(generator.generate(clip).notes, [chord('A2', 'C3', 'E3')])

    def test_given_scale_is_used_over_the_clip_scale(self):
        generator = Accompany(scale=C_MAJOR)
        clip = Clip(notes=[Note('C', 4, WHOLE)], scale=A_MINOR)
        result = generator.generate(clip)
        self.assertEqual(result.notes, [C_CHORD])
        self.assertIs(result.scale, A_MINOR)

    def test_rejects_having_no_scale(self):
        with self.assertRaises(ValueError):
            Accompany().generate(Clip(notes=[Note('C', 4, WHOLE)]))

    def test_needs_a_length_when_it_runs(self):
        with self.assertRaises(ValueError):
            accompany([1])

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[Note('C', 4, WHOLE)], scale=C_MAJOR, note_length=0.5)
        result = Accompany().generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.note_length, 0.5)

    def test_leaves_the_original_unchanged(self):
        notes = [Note('C', 4, WHOLE)]
        original = Clip(notes=notes, scale=C_MAJOR)
        Accompany().generate(original)
        self.assertEqual(original.notes, notes)


class TestAccompanyFields(unittest.TestCase):

    def test_rejects_invalid_values(self):
        for scale in ['C major', ScaleType.MAJOR, Note('C', 4)]:
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    Accompany(scale=scale)
        for measure_length in [0, -1, '1', None, True]:
            with self.subTest(measure_length=measure_length):
                with self.assertRaises(ValueError):
                    Accompany(measure_length=measure_length)
        for octave in [1.5, '1', None, True]:
            with self.subTest(octave=octave):
                with self.assertRaises(ValueError):
                    Accompany(octave=octave)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [Note('C', 4, WHOLE)]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Accompany().generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Accompany()
        generator.scale = A_MINOR
        generator.measure_length = 0.5
        generator.octave = 0
        self.assertEqual(
            (generator.scale, generator.measure_length, generator.octave),
            (A_MINOR, 0.5, 0),
        )
        with self.assertRaises(ValueError):
            generator.measure_length = 0
        self.assertEqual(generator.measure_length, 0.5)


if __name__ == '__main__':
    unittest.main()
