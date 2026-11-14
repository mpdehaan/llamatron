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

import contextlib
import io
import os
import tempfile
import unittest

import mido

from llamatron.music.chord import Chord
from llamatron.generators.arp import Arp
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.music.note import Degree, Note, NoteName, Rest
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.midi_messages import NOTE_OFF_MESSAGE, NOTE_ON_MESSAGE
from llamatron.music.scale import Scale, ScaleType
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn

QUARTER = 0.25
# What the clip files are named under, and the two scenes' files.
EXPORT = 'song'
FIRST_SCENE_CLIP = EXPORT + '_clip_s_001-t_001.mid'
SECOND_SCENE_CLIP = EXPORT + '_clip_s_002-t_001.mid'
C_MAJOR = Scale(root=Note(name='C', octave_number=4), typ=ScaleType.MAJOR)
A_MINOR = Scale(root=Note(name='A', octave_number=3), typ=ScaleType.MINOR)
C_PENTATONIC = Scale(root=Note(name='C', octave_number=4), typ=ScaleType.MAJOR_PENTATONIC)

# Names the tests give to their own things, and other values they use.
E4 = 'E4'
H4 = 'H4'
C4 = 'c4'
E = 'E'
E4X = 'E4x'
E_4 = 'E 4'
E11 = 'E11'
R = 'R'
DB4 = 'Db4'
DB = 'Db'
BB3 = 'Bb3'
BB = 'Bb'
C10 = 'C10'
C = 'C'
C4_2 = 'C4'


def render_clip(*, clip, song_scale=None, scene_scale=None):
    """Render one clip, and return its messages as (note, start in beats, end in beats)."""
    song = ClipGrid(scale=song_scale)
    track = song.add_column(ClipColumn())
    scene = song.add_row(ClipRow(scale=scene_scale))
    song.set_clip(row=scene, column=track, clip=clip)
    with tempfile.TemporaryDirectory() as directory:
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(directory=directory, grid=song).export()
        midi_file = mido.MidiFile(os.path.join(directory, os.listdir(directory)[0]))
    tick = 0
    started = {}
    result = []
    for message in midi_file.tracks[0]:
        tick += message.time
        if message.type == NOTE_ON_MESSAGE:
            started[message.note] = tick
        elif message.type == NOTE_OFF_MESSAGE:
            result.append((message.note, started[message.note] / 480, tick / 480))
    return result


def pitches(clip, **scales):
    return [note for note, _, _ in render_clip(clip=clip, **scales)]


class TestDegree(unittest.TestCase):

    def test_keeps_its_values(self):
        degree = Degree(number=3, length=QUARTER)
        self.assertEqual((degree.get_number(), degree.get_length()), (3, QUARTER))

    def test_length_is_optional(self):
        self.assertIsNone(Degree(number=3).get_length())

    def test_rejects_invalid_numbers(self):
        for number in [0, -1, 1.5, '1', None, True]:
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    Degree(number=number)

    def test_rejects_invalid_lengths_and_amounts(self):
        with self.assertRaises(ValueError):
            Degree(number=1, length=0)
        with self.assertRaises(ValueError):
            Degree(number=1, octave=1.5)
        with self.assertRaises(ValueError):
            Degree(number=1, scale_notes='1')
        with self.assertRaises(ValueError):
            Degree(number=1, half_steps=True)

    def test_cannot_be_changed(self):
        with self.assertRaises(AttributeError):
            Degree(number=1).number = 2

    def test_equality(self):
        self.assertEqual(Degree(number=1, length=QUARTER), Degree(number=1, length=QUARTER))
        self.assertNotEqual(Degree(number=1, length=QUARTER), Degree(number=2, length=QUARTER))
        self.assertNotEqual(Degree(number=1, length=QUARTER), Degree(number=1, length=0.5))


class TestDegreeToNote(unittest.TestCase):

    def test_every_degree_of_c_major(self):
        played = [self.note(degree=Degree(number=n)).get_midi_number() for n in range(1, 8)]
        self.assertEqual(played, [48, 50, 52, 53, 55, 57, 59])

    def note(self, *, degree, scale=C_MAJOR):
        return degree.to_note(scale)

    def test_one_is_the_root(self):
        self.assertEqual(self.note(degree=Degree(number=1)), Note(name=NoteName.C, octave_number=4))

    def test_continues_past_the_top_of_the_scale(self):
        self.assertEqual(self.note(degree=Degree(number=8)), Note(name=NoteName.C, octave_number=5))
        self.assertEqual(self.note(degree=Degree(number=10)), Note(name=NoteName.E, octave_number=5))

    def test_scale_size_decides_where_the_octave_is(self):
        self.assertEqual(self.note(degree=Degree(number=6), scale=C_PENTATONIC), Note(name=NoteName.C, octave_number=5))

    def test_uses_the_shape_and_root_of_the_scale(self):
        self.assertEqual(self.note(degree=Degree(number=1), scale=A_MINOR), Note(name=NoteName.A, octave_number=3))
        self.assertEqual(self.note(degree=Degree(number=3), scale=A_MINOR), Note(name=NoteName.C, octave_number=4))

    def test_octave_moves_it_below_the_root(self):
        self.assertEqual(self.note(degree=Degree(number=7, octave=-1)), Note(name=NoteName.B, octave_number=3))

    def test_half_steps_make_notes_outside_the_scale(self):
        self.assertEqual(self.note(degree=Degree(number=4, half_steps=1)), Note(name=NoteName.F_SHARP, octave_number=4))

    def test_keeps_its_length(self):
        self.assertEqual(self.note(degree=Degree(number=1, length=0.5)).get_length(), 0.5)

    def test_rejects_notes_outside_the_midi_range(self):
        with self.assertRaises(ValueError):
            Degree(number=1, octave=-10).to_note(C_MAJOR)
        with self.assertRaises(ValueError):
            Degree(number=1, octave=10).to_note(C_MAJOR)



class TestLengthsFromTheClip(unittest.TestCase):

    def test_note_without_a_length(self):
        self.assertIsNone(Note(name=NoteName.C, octave_number=4).get_length())

    def test_notes_without_lengths_use_note_length(self):
        clip = Clip(notes=[Note(name=NoteName.C, octave_number=4), Degree(number=2)], note_length=0.5)
        self.assertEqual(clip.resolved_notes(), [Note(name=NoteName.C, octave_number=4, length=0.5), Degree(number=2, length=0.5)])

    def test_own_length_wins_over_note_length(self):
        clip = Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1), Degree(number=2, length=1), Rest(1)], note_length=0.5)
        self.assertEqual(clip.resolved_notes(), [Note(name=NoteName.C, octave_number=4, length=1), Degree(number=2, length=1), Rest(1)])

    def test_chord_notes_use_note_length(self):
        clip = Clip(notes=[Chord([Note(name=NoteName.C, octave_number=4), Note(name=NoteName.E, octave_number=4, length=1)])], note_length=0.5)
        self.assertEqual(clip.resolved_notes(), [Chord([Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.E, octave_number=4, length=1)])])

    def test_chord_length_is_none_until_it_has_lengths(self):
        self.assertIsNone(Chord([Note(name=NoteName.C, octave_number=4), Note(name=NoteName.E, octave_number=4, length=1)]).get_length())

    def test_chords_without_lengths_can_be_compared(self):
        self.assertEqual(Chord([Note(name=NoteName.C, octave_number=4), Note(name=NoteName.E, octave_number=4)]), Chord([Note(name=NoteName.E, octave_number=4), Note(name=NoteName.C, octave_number=4)]))
        self.assertEqual(
            len({Chord([Note(name=NoteName.C, octave_number=4), Note(name=NoteName.B_SHARP, octave_number=3, length=0.5)]), Chord([Note(name=NoteName.B_SHARP, octave_number=3, length=0.5), Note(name=NoteName.C, octave_number=4)])}),
            1,
        )

    def test_keeps_the_stored_notes_without_lengths(self):
        clip = Clip(notes=[Degree(number=1)], note_length=0.5)
        clip.resolved_notes()
        self.assertEqual(clip.get_notes(), [Degree(number=1)])

    def test_note_length_can_be_set_later(self):
        clip = Clip(notes=[Degree(number=1)])
        clip.set_note_length(0.5)
        self.assertEqual(clip.resolved_notes(), [Degree(number=1, length=0.5)])

    def test_editing_note_length_affects_notes_already_in_the_clip(self):
        clip = Clip(notes=[Degree(number=1)], note_length=0.5)
        clip.set_note_length(1)
        self.assertEqual(clip.resolved_notes(), [Degree(number=1, length=1)])

    def test_missing_length_is_only_a_problem_when_it_is_needed(self):
        clip = Clip(notes=[Degree(number=1), Note(name=NoteName.C, octave_number=4)])
        with self.assertRaises(ValueError):
            clip.resolved_notes()

    def test_rejects_invalid_note_lengths(self):
        for note_length in [0, -1, '1', True]:
            with self.subTest(note_length=note_length):
                with self.assertRaises(ValueError):
                    Clip(note_length=note_length)


class TestShorthand(unittest.TestCase):

    def test_text_becomes_a_note_without_a_length(self):
        self.assertEqual(Clip(notes=[E4]).get_notes(), [Note(name=NoteName.E, octave_number=4)])

    def test_text_can_use_any_note_name(self):
        cases = [('C#4', 'C#', 4), (DB4, DB, 4), (BB3, BB, 3), ('B#3', 'B#', 3), (C10, C, 10)]
        for text, name, octave in cases:
            with self.subTest(text=text):
                note = Clip(notes=[text]).get_notes()[0]
                self.assertEqual((note.get_name(), note.get_octave_number()), (name, octave))

    def test_numbers_become_degrees(self):
        self.assertEqual(Clip(notes=[3]).get_notes(), [Degree(number=3)])

    def test_dashes_become_rests_of_quarter_notes(self):
        cases = [('-', 0.25), ('--', 0.5), ('---', 0.75), ('----', 1), ('--------', 2)]
        for text, length in cases:
            with self.subTest(text=text):
                self.assertEqual(Clip(notes=[text]).get_notes(), [Rest(length)])

    def test_dashes_ignore_note_length(self):
        clip = Clip(notes=['-'], note_length=1)
        self.assertEqual(clip.resolved_notes(), [Rest(0.25)])

    def test_objects_are_kept_as_they_are(self):
        degree = Degree(number=1, length=0.5)
        note = Note(name=NoteName.C, octave_number=4, length=0.5)
        rest = Rest(0.5)
        self.assertEqual(Clip(notes=[degree, note, rest]).get_notes(), [degree, note, rest])

    def test_everything_can_be_mixed(self):
        clip = Clip(notes=[E4, 2, Rest(0.5), '-', Degree(number=1, length=1)], note_length=QUARTER)
        self.assertEqual(clip.resolved_notes(), [
            Note(name=NoteName.E, octave_number=4, length=QUARTER), Degree(number=2, length=QUARTER), Rest(0.5), Rest(0.25), Degree(number=1, length=1),
        ])

    def test_setting_notes_later_also_understands_shorthand(self):
        clip = Clip()
        clip.set_notes([E4, 2, '-'])
        self.assertEqual(clip.get_notes(), [Note(name=NoteName.E, octave_number=4), Degree(number=2), Rest(0.25)])

    def test_rejects_invalid_shorthand(self):
        invalid = [H4, C4, E, '4', E4X, E_4, 'C##4', E11, 'G#10', '', ' ', '-x', '- -', R,
                   0, -1, 1.5, True, None]
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Clip(notes=[value])


class TestRendering(unittest.TestCase):

    def test_degrees_use_the_song_scale(self):
        clip = Clip(notes=[1, 2, 3], note_length=QUARTER)
        self.assertEqual(pitches(clip, song_scale=C_MAJOR), [48, 50, 52])

    def test_scene_scale_overrides_the_song(self):
        clip = Clip(notes=[1, 2, 3], note_length=QUARTER)
        self.assertEqual(pitches(clip, song_scale=C_MAJOR, scene_scale=A_MINOR), [45, 47, 48])

    def test_clip_scale_overrides_the_scene(self):
        clip = Clip(notes=[1, 2, 3], note_length=QUARTER, scale=C_PENTATONIC)
        self.assertEqual(pitches(clip, scene_scale=A_MINOR), [48, 50, 52])

    def test_one_clip_can_play_in_two_scenes_with_different_scales(self):
        song = ClipGrid()
        track = song.add_column(ClipColumn())
        clip = Clip(notes=[1, 3], note_length=QUARTER)
        major_scene = song.add_row(ClipRow(scale=C_MAJOR))
        minor_scene = song.add_row(ClipRow(scale=Scale(root=Note(name=NoteName.C, octave_number=4), typ=ScaleType.MINOR)))
        song.set_clip(row=major_scene, column=track, clip=clip)
        song.set_clip(row=minor_scene, column=track, clip=clip)
        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory=directory, grid=song, name=EXPORT).export()
            played = [
                [m.note for m in mido.MidiFile(os.path.join(directory, name)).tracks[0]
                 if m.type == NOTE_ON_MESSAGE]
                for name in [FIRST_SCENE_CLIP, SECOND_SCENE_CLIP]
            ]
        self.assertEqual(played, [[48, 52], [48, 51]])

    def test_changing_the_scale_after_writing_the_clip_changes_the_result(self):
        clip = Clip(notes=[1, 3], note_length=QUARTER, scale=C_MAJOR)
        clip.set_scale(Scale(root=Note(name=NoteName.D, octave_number=4), typ=ScaleType.MAJOR))
        self.assertEqual(pitches(clip), [50, 54])

    def test_literal_notes_ignore_the_scale(self):
        clip = Clip(notes=[E4, 2], note_length=QUARTER)
        self.assertEqual(pitches(clip, song_scale=A_MINOR), [52, 47])

    def test_lengths_and_rests_are_rendered(self):
        clip = Clip(notes=[1, '-', Degree(number=2, length=0.5), C4_2], note_length=QUARTER)
        self.assertEqual(render_clip(clip=clip, song_scale=C_MAJOR), [
            (48, 0, 1), (50, 2, 4), (48, 4, 5),
        ])

    def test_missing_scale_stops_before_writing_anything(self):
        song = ClipGrid()
        track = song.add_column(ClipColumn())
        scene = song.add_row(ClipRow())
        other_track = song.add_column(ClipColumn())
        song.set_clip(row=scene, column=track, clip=Clip(notes=[C4_2], note_length=QUARTER))
        song.set_clip(row=scene, column=other_track, clip=Clip(notes=[1], note_length=QUARTER))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                ClipTree(directory=directory, grid=song).export()
            self.assertEqual(os.listdir(directory), [])

    def test_missing_length_stops_before_writing_anything(self):
        song = ClipGrid(scale=C_MAJOR)
        track = song.add_column(ClipColumn())
        scene = song.add_row(ClipRow())
        song.set_clip(row=scene, column=track, clip=Clip(notes=[1]))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                ClipTree(directory=directory, grid=song).export()
            self.assertEqual(os.listdir(directory), [])

    def test_clips_of_literal_notes_do_not_need_a_scale(self):
        self.assertEqual(pitches(Clip(notes=[C4_2], note_length=QUARTER)), [48])


class TestGeneratorsWithDegrees(unittest.TestCase):

    def test_every_generator_keeps_degrees_as_degrees(self):
        clip = Clip(notes=[1, 2, 3], note_length=QUARTER)
        for generator in [AutoRatchet([2]), Arp(step=QUARTER)]:
            with self.subTest(generator=type(generator).__name__):
                result = generator.generate(clip)
                self.assertTrue(all(isinstance(p, Degree) for p in result.get_notes()))

    def test_every_generator_keeps_note_length(self):
        clip = Clip(notes=[1], note_length=QUARTER)
        for generator in [AutoRatchet([2]), Arp(step=QUARTER)]:
            with self.subTest(generator=type(generator).__name__):
                self.assertEqual(generator.generate(clip).get_note_length(), QUARTER)

    def test_generators_reject_invalid_items_added_to_a_list(self):
        for generator in [AutoRatchet([2]), Arp(step=QUARTER)]:
            clip = Clip(notes=[1], note_length=QUARTER)
            clip.get_notes().append(C4_2)
            with self.subTest(generator=type(generator).__name__):
                with self.assertRaises(ValueError):
                    generator.generate(clip)

    def test_arp_leaves_degrees_alone_and_fills_chords(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4), Note(name=NoteName.E, octave_number=4)])
        result = Arp(step=0.125).generate(Clip(notes=[1, chord], note_length=QUARTER))
        self.assertEqual(result.get_notes(), [Degree(number=1, length=QUARTER), Note(name=NoteName.C, octave_number=4, length=0.125), Note(name=NoteName.E, octave_number=4, length=0.125)])


if __name__ == '__main__':
    unittest.main()
