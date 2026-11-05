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

from src.chord import Chord
from src.generators.base import ClipGenerator
from src.legacy.generators.transpose import Transpose
from src.legacy.generators.transpose_scale import TransposeScale
from src.note import Degree, Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
C_BLUES = Scale(Note('C', 4), ScaleType.BLUES)
C_MINOR = Scale(Note('C', 4), ScaleType.MINOR)
D_MAJOR = Scale(Note('D', 4), ScaleType.MAJOR)
TO_BLUES = TransposeScale(input_scale=C_MAJOR, output_scale=C_BLUES)


def pitches(clip):
    """Return the MIDI numbers that a clip's degrees play in the clip's scale."""
    return [position.to_note(clip.scale).midi_number for position in clip.notes]


class TestDegreeOf(unittest.TestCase):

    def test_scale_notes_get_their_degree(self):
        cases = [('C', 4, 1), ('D', 4, 2), ('E', 4, 3), ('B', 4, 7)]
        for name, octave, number in cases:
            with self.subTest(name=name):
                self.assertEqual(C_MAJOR.degree_of(Note(name, octave)), Degree(number))

    def test_other_octaves(self):
        self.assertEqual(C_MAJOR.degree_of(Note('C', 5)), Degree(1, octave=1))
        self.assertEqual(C_MAJOR.degree_of(Note('B', 3)), Degree(7, octave=-1))

    def test_keeps_the_length(self):
        self.assertEqual(C_MAJOR.degree_of(Note('D', 4, 0.5)), Degree(2, 0.5))

    def test_notes_outside_the_scale_use_half_steps(self):
        self.assertEqual(C_MAJOR.degree_of(Note('C#', 4)), Degree(1, half_steps=1))

    def test_uses_the_root_of_the_scale(self):
        self.assertEqual(D_MAJOR.degree_of(Note('D', 4)), Degree(1))
        self.assertEqual(D_MAJOR.degree_of(Note('C#', 4)), Degree(7, octave=-1))

    def test_every_midi_number_plays_the_same_pitch_again(self):
        for scale in [C_MAJOR, C_BLUES, D_MAJOR]:
            for midi_number in range(0, 128):
                with self.subTest(scale=scale.typ, midi_number=midi_number):
                    note = Note.from_midi_number(midi_number)
                    self.assertEqual(scale.degree_of(note).to_note(scale).midi_number, midi_number)


class TestTransposeScale(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(TO_BLUES, ClipGenerator)

    def test_notes_keep_their_scale_degree(self):
        notes = [Note('E', 4, 0.25), Note('D', 4, 0.25), Note('C', 4, 0.25), Note('G', 4, 0.25)]
        result = TO_BLUES.generate(Clip(notes=notes))
        self.assertEqual(pitches(result), [53, 51, 48, 55])

    def test_notes_become_degrees(self):
        result = TO_BLUES.generate(Clip(notes=[Note('E', 4, 0.25)]))
        self.assertEqual(result.notes, [Degree(3, 0.25)])

    def test_new_clip_uses_the_output_scale(self):
        original = Clip(notes=[Note('C', 4)], scale=C_MAJOR)
        self.assertIs(TO_BLUES.generate(original).scale, C_BLUES)

    def test_changing_the_new_clip_scale_changes_the_notes(self):
        result = TO_BLUES.generate(Clip(notes=[Note('E', 4, 0.25)]))
        result.scale = C_MINOR
        self.assertEqual(pitches(result), [51])

    def test_short_scales_wrap_into_the_next_octave(self):
        result = TO_BLUES.generate(Clip(notes=[Note('B', 4)]))
        self.assertEqual(pitches(result), [60])

    def test_keeps_octaves(self):
        result = TO_BLUES.generate(Clip(notes=[Note('E', 2), Note('E', 6)]))
        self.assertEqual(pitches(result), [29, 77])

    def test_output_root_moves_the_key(self):
        generator = TransposeScale(input_scale=C_MAJOR, output_scale=D_MAJOR)
        result = generator.generate(Clip(notes=[Note('C', 4), Note('E', 4)]))
        self.assertEqual(pitches(result), [50, 54])

    def test_same_scale_keeps_every_pitch(self):
        generator = TransposeScale(input_scale=C_MAJOR, output_scale=C_MAJOR)
        notes = C_MAJOR.octaves(1)
        self.assertEqual(
            pitches(generator.generate(Clip(notes=notes))),
            [note.midi_number for note in notes],
        )

    def test_notes_outside_the_input_scale_keep_their_distance(self):
        result = TO_BLUES.generate(Clip(notes=[Note('C#', 4)]))
        self.assertEqual(pitches(result), [49])

    def test_chords_become_notes_of_the_output_scale(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.5), Note('G', 4, 0.5)])
        result = TO_BLUES.generate(Clip(notes=[chord]))
        self.assertEqual(
            result.notes,
            [Chord([Note('C', 4, 0.5), Note('F', 4, 0.5), Note('G', 4, 0.5)])],
        )

    def test_rests_and_degrees_stay_as_they_are(self):
        result = TO_BLUES.generate(Clip(notes=[Rest(0.25), Degree(2, 0.25)]))
        self.assertEqual(result.notes, [Rest(0.25), Degree(2, 0.25)])

    def test_keeps_lengths_and_clip_details(self):
        original = Clip('Riff', notes=[Note('C', 4)], length=2, note_length=0.5)
        result = TO_BLUES.generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertEqual(result.length, 2)
        self.assertEqual(result.note_length, 0.5)
        self.assertEqual(result.resolved_notes(), [Degree(1, 0.5)])

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[Note('E', 4)], scale=C_MAJOR)
        TO_BLUES.generate(original)
        self.assertEqual(original.notes, [Note('E', 4)])
        self.assertIs(original.scale, C_MAJOR)

    def test_works_with_transpose_afterward(self):
        moved = Transpose(scale_notes=1).generate(TO_BLUES.generate(Clip(notes=[Note('C', 4)])))
        self.assertEqual(pitches(moved), [51])


class TestTransposeScaleFields(unittest.TestCase):

    def test_both_scales_are_required(self):
        with self.assertRaises(TypeError):
            TransposeScale()
        with self.assertRaises(TypeError):
            TransposeScale(input_scale=C_MAJOR)

    def test_rejects_invalid_scales(self):
        for scale in [None, 'C major', ScaleType.MAJOR, Note('C', 4)]:
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    TransposeScale(input_scale=scale, output_scale=C_BLUES)
                with self.assertRaises(ValueError):
                    TransposeScale(input_scale=C_MAJOR, output_scale=scale)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [Note('C', 4)]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    TO_BLUES.generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = TransposeScale(input_scale=C_MAJOR, output_scale=C_BLUES)
        generator.output_scale = C_MINOR
        self.assertIs(generator.generate(Clip()).scale, C_MINOR)
        with self.assertRaises(ValueError):
            generator.input_scale = None
        self.assertIs(generator.input_scale, C_MAJOR)


if __name__ == '__main__':
    unittest.main()
