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

from llamatron.chord import Chord, ChordType
from llamatron.generators.base import ClipGenerator
from llamatron.legacy.generators.transpose import Transpose
from llamatron.note import Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Scene, Song, Track

C4 = Note('C', 4, 0.25)
C_MAJOR = Scale(Note('C', 0, 0.25), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 0, 0.25), ScaleType.MINOR)
C_PENTATONIC = Scale(Note('C', 0, 0.25), ScaleType.MAJOR_PENTATONIC)


def q(name, octave):
    """Return a quarter note."""
    return Note(name, octave, 0.25)


class TestTransposeBasics(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Transpose(half_steps=1), ClipGenerator)

    def test_half_steps(self):
        self.assertEqual(Transpose(half_steps=1).generate(Clip(notes=[C4])).notes, [q('C#', 4)])
        self.assertEqual(Transpose(half_steps=-1).generate(Clip(notes=[C4])).notes, [q('B', 3)])

    def test_whole_steps(self):
        self.assertEqual(Transpose(whole_steps=2).generate(Clip(notes=[C4])).notes, [q('E', 4)])
        self.assertEqual(Transpose(whole_steps=-1).generate(Clip(notes=[C4])).notes, [q('A#', 3)])

    def test_octaves(self):
        self.assertEqual(Transpose(octaves=1).generate(Clip(notes=[C4])).notes, [q('C', 5)])
        self.assertEqual(Transpose(octaves=-2).generate(Clip(notes=[C4])).notes, [q('C', 2)])

    def test_octaves_keep_the_spelling(self):
        result = Transpose(octaves=-1).generate(Clip(notes=[q('Db', 4)]))
        self.assertEqual(result.notes[0].name, 'Db')

    def test_zero_keeps_the_pitch(self):
        for amount in ['half_steps', 'whole_steps', 'octaves']:
            with self.subTest(amount=amount):
                result = Transpose(**{amount: 0}).generate(Clip(notes=[C4]))
                self.assertEqual(result.notes, [C4])

    def test_moves_every_note_and_keeps_lengths(self):
        notes = [Note('C', 4, 0.25), Note('E', 4, 0.5), Note('G', 4, 1)]
        result = Transpose(whole_steps=-1).generate(Clip(notes=notes)).notes
        self.assertEqual(
            result,
            [Note('A#', 3, 0.25), Note('D', 4, 0.5), Note('F', 4, 1)],
        )

    def test_moves_every_note_in_a_chord(self):
        chord = C4.to_chord(ChordType.MAJOR)
        result = Transpose(octaves=-1).generate(Clip(notes=[chord])).notes
        self.assertEqual(result, [Note('C', 3, 0.25).to_chord(ChordType.MAJOR)])

    def test_rests_stay_as_they_are(self):
        result = Transpose(half_steps=1).generate(Clip(notes=[Rest(0.25), C4])).notes
        self.assertEqual(result, [Rest(0.25), q('C#', 4)])

    def test_rejects_moving_outside_the_midi_range(self):
        cases = [
            (Note('C', 0, 0.25), dict(half_steps=-1)),
            (Note('C', 0, 0.25), dict(octaves=-1)),
            (Note('G', 10, 0.25), dict(whole_steps=1)),
            (Note('C', 0, 0.25), dict(scale_notes=-1, scale=C_MAJOR)),
        ]
        for note, amounts in cases:
            with self.subTest(amounts=amounts):
                with self.assertRaises(ValueError):
                    Transpose(**amounts).generate(Clip(notes=[note]))

    def test_empty_clip_stays_empty(self):
        self.assertEqual(Transpose(half_steps=1).generate(Clip()).notes, [])

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[C4], scale=C_MAJOR, length=2)
        result = Transpose(half_steps=1).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.length, 2)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[C4])
        Transpose(octaves=1).generate(original)
        self.assertEqual(original.notes, [C4])


class TestTransposeScaleNotes(unittest.TestCase):

    def move(self, note, scale_notes, scale=C_MAJOR):
        clip = Clip(notes=[note], scale=scale)
        return Transpose(scale_notes=scale_notes).generate(clip).notes[0]

    def test_up_a_whole_step_where_the_scale_has_one(self):
        self.assertEqual(self.move(C4, 1), q('D', 4))

    def test_up_a_half_step_where_the_scale_has_one(self):
        self.assertEqual(self.move(q('E', 4), 1), q('F', 4))

    def test_down_uses_the_scale_too(self):
        self.assertEqual(self.move(q('F', 4), -1), q('E', 4))
        self.assertEqual(self.move(q('D', 4), -1), C4)

    def test_crosses_octaves_in_both_directions(self):
        self.assertEqual(self.move(q('B', 4), 1), q('C', 5))
        self.assertEqual(self.move(C4, -1), q('B', 3))

    def test_a_full_scale_length_is_one_octave(self):
        self.assertEqual(self.move(C4, 7), q('C', 5))
        self.assertEqual(self.move(C4, -7), q('C', 3))

    def test_more_than_an_octave(self):
        self.assertEqual(self.move(C4, 9), q('E', 5))
        self.assertEqual(self.move(C4, -9), q('A', 2))

    def test_zero_keeps_the_pitch(self):
        self.assertEqual(self.move(q('E', 4), 0), q('E', 4))

    def test_every_c_major_note_up_by_two(self):
        notes = Scale(C4, ScaleType.MAJOR).count(7)
        result = Transpose(scale_notes=2).generate(Clip(notes=notes, scale=C_MAJOR)).notes
        self.assertEqual(result, [
            q('E', 4), q('F', 4), q('G', 4), q('A', 4), q('B', 4), q('C', 5), q('D', 5),
        ])

    def test_uses_the_shape_of_the_given_scale(self):
        self.assertEqual(self.move(q('C', 4), 1, A_MINOR), q('D', 4))
        self.assertEqual(self.move(q('E', 4), 1, A_MINOR), q('F', 4))
        self.assertEqual(self.move(q('A', 4), -1, A_MINOR), q('G', 4))

    def test_scales_with_fewer_notes_take_bigger_steps(self):
        self.assertEqual(self.move(q('E', 4), 1, C_PENTATONIC), q('G', 4))
        self.assertEqual(self.move(C4, -1, C_PENTATONIC), q('A', 3))
        self.assertEqual(self.move(C4, 5, C_PENTATONIC), q('C', 5))

    def test_only_the_scale_root_note_name_and_type_matter(self):
        high_root = Scale(Note('C', 8, 0.25), ScaleType.MAJOR)
        self.assertEqual(self.move(q('E', 2), 1, high_root), q('F', 2))

    def test_note_outside_the_scale_keeps_its_distance_from_the_note_below(self):
        self.assertEqual(self.move(q('C#', 4), 1), q('D#', 4))
        self.assertEqual(self.move(q('F#', 4), 1), q('G#', 4))
        self.assertEqual(self.move(q('C#', 4), -1), q('C', 4))

    def test_chord_stays_in_the_scale(self):
        c_chord = C4.to_chord(ChordType.MAJOR)
        result = Transpose(scale_notes=1).generate(Clip(notes=[c_chord], scale=C_MAJOR)).notes
        self.assertEqual(result, [q('D', 4).to_chord(ChordType.MINOR)])

    def test_keeps_lengths(self):
        result = self.move(Note('C', 4, 0.5), 1)
        self.assertEqual(result, Note('D', 4, 0.5))


class TestTransposeFindingTheScale(unittest.TestCase):

    def test_uses_the_clip_scale(self):
        result = Transpose(scale_notes=1).generate(Clip(notes=[q('G', 4)], scale=A_MINOR))
        self.assertEqual(result.notes, [q('A', 4)])

    def test_given_scale_is_used_over_the_clip_scale(self):
        clip = Clip(notes=[q('E', 4)], scale=C_PENTATONIC)
        result = Transpose(scale_notes=1, scale=C_MAJOR).generate(clip)
        self.assertEqual(result.notes, [q('F', 4)])

    def test_given_scale_does_not_change_the_new_clip_scale(self):
        clip = Clip(notes=[C4], scale=C_PENTATONIC)
        result = Transpose(scale_notes=1, scale=C_MAJOR).generate(clip)
        self.assertIs(result.scale, C_PENTATONIC)

    def test_rejects_scale_notes_with_no_scale(self):
        with self.assertRaises(ValueError):
            Transpose(scale_notes=1).generate(Clip(notes=[C4]))

    def test_other_amounts_do_not_need_a_scale(self):
        for amount in ['half_steps', 'whole_steps', 'octaves']:
            with self.subTest(amount=amount):
                Transpose(**{amount: 1}).generate(Clip(notes=[C4]))

    def test_can_use_a_scene_or_song_scale_through_scale_at(self):
        song = Song(scale=C_MAJOR)
        track = song.add_track(Track())
        major_scene = song.add_scene(Scene())
        minor_scene = song.add_scene(Scene(scale=A_MINOR))
        clip = Clip(notes=[q('G', 4)])
        self.assertEqual(
            Transpose(scale_notes=-1, scale=song.scale_at(major_scene, track)).generate(clip).notes,
            [q('F', 4)],
        )
        self.assertEqual(
            Transpose(scale_notes=1, scale=song.scale_at(minor_scene, track)).generate(clip).notes,
            [q('A', 4)],
        )


class TestTransposeFields(unittest.TestCase):

    def test_needs_exactly_one_amount(self):
        with self.assertRaises(ValueError):
            Transpose()
        with self.assertRaises(ValueError):
            Transpose(scale=C_MAJOR)
        with self.assertRaises(ValueError):
            Transpose(half_steps=1, octaves=1)

    def test_amounts_must_be_named(self):
        with self.assertRaises(TypeError):
            Transpose(1)

    def test_rejects_invalid_amounts(self):
        for amount in ['half_steps', 'whole_steps', 'octaves', 'scale_notes']:
            for value in [1.5, 1.0, '1', True]:
                with self.subTest(amount=amount, value=value):
                    with self.assertRaises(ValueError):
                        Transpose(**{amount: value})

    def test_rejects_invalid_scales(self):
        for scale in ['C major', ScaleType.MAJOR, C4]:
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    Transpose(scale_notes=1, scale=scale)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [C4]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Transpose(half_steps=1).generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        transpose = Transpose(half_steps=1)
        transpose.half_steps = 2
        self.assertEqual(transpose.generate(Clip(notes=[C4])).notes, [q('D', 4)])
        with self.assertRaises(ValueError):
            transpose.half_steps = 1.5
        self.assertEqual(transpose.half_steps, 2)

    def test_can_be_edited_to_use_a_different_amount(self):
        transpose = Transpose(half_steps=1)
        transpose.half_steps = None
        transpose.octaves = 1
        self.assertEqual(transpose.generate(Clip(notes=[C4])).notes, [q('C', 5)])

    def test_edits_that_leave_the_wrong_number_of_amounts_are_rejected_when_generating(self):
        transpose = Transpose(half_steps=1)
        transpose.octaves = 1
        with self.assertRaises(ValueError):
            transpose.generate(Clip(notes=[C4]))
        transpose.octaves = None
        transpose.half_steps = None
        with self.assertRaises(ValueError):
            transpose.generate(Clip(notes=[C4]))

    def test_rejects_invalid_item_added_to_a_list(self):
        clip = Clip(notes=[C4])
        clip.notes.append('C4')
        with self.assertRaises(ValueError):
            Transpose(half_steps=1).generate(clip)


if __name__ == '__main__':
    unittest.main()
