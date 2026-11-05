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

import contextlib
import dataclasses
import io
import os
import tempfile
import unittest

import mido

import demo.mary
import demo.mary_degrees
from src.chord import Chord
from src.generators.arp import Arp
from src.legacy.generators.mix_up import MixUp
from src.generators.repeater import Repeater
from src.legacy.generators.reverse import Reverse
from src.legacy.generators.transpose import Transpose
from src.note import Degree, Note, Rest
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType
from src.song import Clip, Scene, Song, Track

QUARTER = 0.25
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)
C_PENTATONIC = Scale(Note('C', 4), ScaleType.MAJOR_PENTATONIC)


def render_clip(clip, song_scale=None, scene_scale=None):
    """Render one clip, and return its messages as (note, start in beats, end in beats)."""
    song = Song(scale=song_scale)
    track = song.add_track(Track())
    scene = song.add_scene(Scene(scale=scene_scale))
    song.set_clip(scene, track, clip)
    with tempfile.TemporaryDirectory() as directory:
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(directory, song).render()
        midi_file = mido.MidiFile(os.path.join(directory, os.listdir(directory)[0]))
    tick = 0
    started = {}
    result = []
    for message in midi_file.tracks[0]:
        tick += message.time
        if message.type == 'note_on':
            started[message.note] = tick
        elif message.type == 'note_off':
            result.append((message.note, started[message.note] / 480, tick / 480))
    return result


def pitches(clip, **scales):
    return [note for note, _, _ in render_clip(clip, **scales)]


class TestDegree(unittest.TestCase):

    def test_keeps_its_values(self):
        degree = Degree(3, QUARTER)
        self.assertEqual((degree.number, degree.length), (3, QUARTER))

    def test_length_is_optional(self):
        self.assertIsNone(Degree(3).length)

    def test_rejects_invalid_numbers(self):
        for number in [0, -1, 1.5, '1', None, True]:
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    Degree(number)

    def test_rejects_invalid_lengths_and_amounts(self):
        with self.assertRaises(ValueError):
            Degree(1, 0)
        with self.assertRaises(ValueError):
            Degree(1, octave=1.5)
        with self.assertRaises(ValueError):
            Degree(1, scale_notes='1')
        with self.assertRaises(ValueError):
            Degree(1, half_steps=True)

    def test_cannot_be_changed(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            Degree(1).number = 2

    def test_equality(self):
        self.assertEqual(Degree(1, QUARTER), Degree(1, QUARTER))
        self.assertNotEqual(Degree(1, QUARTER), Degree(2, QUARTER))
        self.assertNotEqual(Degree(1, QUARTER), Degree(1, 0.5))


class TestDegreeToNote(unittest.TestCase):

    def note(self, degree, scale=C_MAJOR):
        return degree.to_note(scale)

    def test_one_is_the_root(self):
        self.assertEqual(self.note(Degree(1)), Note('C', 4))

    def test_every_degree_of_c_major(self):
        played = [self.note(Degree(n)).midi_number for n in range(1, 8)]
        self.assertEqual(played, [48, 50, 52, 53, 55, 57, 59])

    def test_continues_past_the_top_of_the_scale(self):
        self.assertEqual(self.note(Degree(8)), Note('C', 5))
        self.assertEqual(self.note(Degree(10)), Note('E', 5))

    def test_scale_size_decides_where_the_octave_is(self):
        self.assertEqual(self.note(Degree(6), C_PENTATONIC), Note('C', 5))

    def test_uses_the_shape_and_root_of_the_scale(self):
        self.assertEqual(self.note(Degree(1), A_MINOR), Note('A', 3))
        self.assertEqual(self.note(Degree(3), A_MINOR), Note('C', 4))

    def test_octave_moves_it_below_the_root(self):
        self.assertEqual(self.note(Degree(7, octave=-1)), Note('B', 3))

    def test_half_steps_make_notes_outside_the_scale(self):
        self.assertEqual(self.note(Degree(4, half_steps=1)), Note('F#', 4))

    def test_keeps_its_length(self):
        self.assertEqual(self.note(Degree(1, 0.5)).length, 0.5)

    def test_rejects_notes_outside_the_midi_range(self):
        with self.assertRaises(ValueError):
            Degree(1, octave=-10).to_note(C_MAJOR)
        with self.assertRaises(ValueError):
            Degree(1, octave=10).to_note(C_MAJOR)


class TestDegreeMoved(unittest.TestCase):

    def test_returns_a_new_degree(self):
        original = Degree(3, QUARTER)
        self.assertIsNot(original.moved(octaves=1), original)
        self.assertEqual(original.octave, 0)

    def test_moves_add_up(self):
        moved = Degree(1).moved(octaves=1).moved(octaves=1, half_steps=1)
        self.assertEqual((moved.octave, moved.half_steps), (2, 1))

    def test_scale_notes_can_go_below_the_root(self):
        self.assertEqual(Degree(1).moved(scale_notes=-1).to_note(C_MAJOR), Note('B', 3))
        self.assertEqual(Degree(1).moved(scale_notes=-8).to_note(C_MAJOR), Note('B', 2))


class TestLengthsFromTheClip(unittest.TestCase):

    def test_note_without_a_length(self):
        self.assertIsNone(Note('C', 4).length)

    def test_notes_without_lengths_use_note_length(self):
        clip = Clip(notes=[Note('C', 4), Degree(2)], note_length=0.5)
        self.assertEqual(clip.resolved_notes(), [Note('C', 4, 0.5), Degree(2, 0.5)])

    def test_own_length_wins_over_note_length(self):
        clip = Clip(notes=[Note('C', 4, 1), Degree(2, 1), Rest(1)], note_length=0.5)
        self.assertEqual(clip.resolved_notes(), [Note('C', 4, 1), Degree(2, 1), Rest(1)])

    def test_chord_notes_use_note_length(self):
        clip = Clip(notes=[Chord([Note('C', 4), Note('E', 4, 1)])], note_length=0.5)
        self.assertEqual(clip.resolved_notes(), [Chord([Note('C', 4, 0.5), Note('E', 4, 1)])])

    def test_chord_length_is_none_until_it_has_lengths(self):
        self.assertIsNone(Chord([Note('C', 4), Note('E', 4, 1)]).length)

    def test_chords_without_lengths_can_be_compared(self):
        self.assertEqual(Chord([Note('C', 4), Note('E', 4)]), Chord([Note('E', 4), Note('C', 4)]))
        self.assertEqual(
            len({Chord([Note('C', 4), Note('B#', 3, 0.5)]), Chord([Note('B#', 3, 0.5), Note('C', 4)])}),
            1,
        )

    def test_keeps_the_stored_notes_without_lengths(self):
        clip = Clip(notes=[Degree(1)], note_length=0.5)
        clip.resolved_notes()
        self.assertEqual(clip.notes, [Degree(1)])

    def test_note_length_can_be_set_later(self):
        clip = Clip(notes=[Degree(1)])
        clip.note_length = 0.5
        self.assertEqual(clip.resolved_notes(), [Degree(1, 0.5)])

    def test_editing_note_length_affects_notes_already_in_the_clip(self):
        clip = Clip(notes=[Degree(1)], note_length=0.5)
        clip.note_length = 1
        self.assertEqual(clip.resolved_notes(), [Degree(1, 1)])

    def test_missing_length_is_only_a_problem_when_it_is_needed(self):
        clip = Clip(notes=[Degree(1), Note('C', 4)])
        with self.assertRaises(ValueError):
            clip.resolved_notes()

    def test_rejects_invalid_note_lengths(self):
        for note_length in [0, -1, '1', True]:
            with self.subTest(note_length=note_length):
                with self.assertRaises(ValueError):
                    Clip(note_length=note_length)

    def test_scale_can_produce_notes_without_lengths(self):
        notes = C_MAJOR.count(3)
        self.assertEqual({note.length for note in notes}, {None})
        clip = Clip(notes=notes, note_length=QUARTER)
        self.assertEqual(clip.resolved_notes()[0], Note('C', 4, QUARTER))


class TestShorthand(unittest.TestCase):

    def test_text_becomes_a_note_without_a_length(self):
        self.assertEqual(Clip(notes=['E4']).notes, [Note('E', 4)])

    def test_text_can_use_any_note_name(self):
        cases = [('C#4', 'C#', 4), ('Db4', 'Db', 4), ('Bb3', 'Bb', 3), ('B#3', 'B#', 3), ('C10', 'C', 10)]
        for text, name, octave in cases:
            with self.subTest(text=text):
                note = Clip(notes=[text]).notes[0]
                self.assertEqual((note.name, note.octave_number), (name, octave))

    def test_numbers_become_degrees(self):
        self.assertEqual(Clip(notes=[3]).notes, [Degree(3)])

    def test_dashes_become_rests_of_quarter_notes(self):
        cases = [('-', 0.25), ('--', 0.5), ('---', 0.75), ('----', 1), ('--------', 2)]
        for text, length in cases:
            with self.subTest(text=text):
                self.assertEqual(Clip(notes=[text]).notes, [Rest(length)])

    def test_dashes_ignore_note_length(self):
        clip = Clip(notes=['-'], note_length=1)
        self.assertEqual(clip.resolved_notes(), [Rest(0.25)])

    def test_objects_are_kept_as_they_are(self):
        degree, note, rest = Degree(1, 0.5), Note('C', 4, 0.5), Rest(0.5)
        self.assertEqual(Clip(notes=[degree, note, rest]).notes, [degree, note, rest])

    def test_everything_can_be_mixed(self):
        clip = Clip(notes=['E4', 2, Rest(0.5), '-', Degree(1, 1)], note_length=QUARTER)
        self.assertEqual(clip.resolved_notes(), [
            Note('E', 4, QUARTER), Degree(2, QUARTER), Rest(0.5), Rest(0.25), Degree(1, 1),
        ])

    def test_setting_notes_later_also_understands_shorthand(self):
        clip = Clip()
        clip.notes = ['E4', 2, '-']
        self.assertEqual(clip.notes, [Note('E', 4), Degree(2), Rest(0.25)])

    def test_rejects_invalid_shorthand(self):
        invalid = ['H4', 'c4', 'E', '4', 'E4x', 'E 4', 'C##4', 'E11', 'G#10', '', ' ', '-x', '- -', 'R',
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
        song = Song()
        track = song.add_track(Track())
        clip = Clip(notes=[1, 3], note_length=QUARTER)
        major_scene = song.add_scene(Scene(scale=C_MAJOR))
        minor_scene = song.add_scene(Scene(scale=Scale(Note('C', 4), ScaleType.MINOR)))
        song.set_clip(major_scene, track, clip)
        song.set_clip(minor_scene, track, clip)
        with tempfile.TemporaryDirectory() as directory:
            ClipTree(directory, song).render()
            played = [
                [m.note for m in mido.MidiFile(os.path.join(directory, name)).tracks[0]
                 if m.type == 'note_on']
                for name in ['001-001.mid', '002-001.mid']
            ]
        self.assertEqual(played, [[48, 52], [48, 51]])

    def test_changing_the_scale_after_writing_the_clip_changes_the_result(self):
        clip = Clip(notes=[1, 3], note_length=QUARTER, scale=C_MAJOR)
        clip.scale = Scale(Note('D', 4), ScaleType.MAJOR)
        self.assertEqual(pitches(clip), [50, 54])

    def test_literal_notes_ignore_the_scale(self):
        clip = Clip(notes=['E4', 2], note_length=QUARTER)
        self.assertEqual(pitches(clip, song_scale=A_MINOR), [52, 47])

    def test_lengths_and_rests_are_rendered(self):
        clip = Clip(notes=[1, '-', Degree(2, 0.5), 'C4'], note_length=QUARTER)
        self.assertEqual(render_clip(clip, song_scale=C_MAJOR), [
            (48, 0, 1), (50, 2, 4), (48, 4, 5),
        ])

    def test_missing_scale_stops_before_writing_anything(self):
        song = Song()
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        other_track = song.add_track(Track())
        song.set_clip(scene, track, Clip(notes=['C4'], note_length=QUARTER))
        song.set_clip(scene, other_track, Clip(notes=[1], note_length=QUARTER))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                ClipTree(directory, song).render()
            self.assertEqual(os.listdir(directory), [])

    def test_missing_length_stops_before_writing_anything(self):
        song = Song(scale=C_MAJOR)
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        song.set_clip(scene, track, Clip(notes=[1]))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                ClipTree(directory, song).render()
            self.assertEqual(os.listdir(directory), [])

    def test_clips_of_literal_notes_do_not_need_a_scale(self):
        self.assertEqual(pitches(Clip(notes=['C4'], note_length=QUARTER)), [48])


class TestGeneratorsWithDegrees(unittest.TestCase):

    def test_every_generator_keeps_degrees_as_degrees(self):
        clip = Clip(notes=[1, 2, 3], note_length=QUARTER)
        generators = [
            Repeater(2), Arp(QUARTER), MixUp([1], seed=1), Reverse(), Transpose(scale_notes=1),
        ]
        for generator in generators:
            with self.subTest(generator=type(generator).__name__):
                result = generator.generate(clip)
                self.assertTrue(all(isinstance(p, Degree) for p in result.notes))

    def test_every_generator_keeps_note_length(self):
        clip = Clip(notes=[1], note_length=QUARTER)
        for generator in [Repeater(2), Arp(QUARTER), MixUp([1]), Reverse(), Transpose(octaves=1)]:
            with self.subTest(generator=type(generator).__name__):
                self.assertEqual(generator.generate(clip).note_length, QUARTER)

    def test_repeater_divides_lengths_taken_from_the_clip(self):
        result = Repeater(2).generate(Clip(notes=[1], note_length=0.5))
        self.assertEqual(result.notes, [Degree(1, 0.25), Degree(1, 0.25)])

    def test_repeater_needs_a_length(self):
        with self.assertRaises(ValueError):
            Repeater(2).generate(Clip(notes=[1]))

    def test_reverse_stays_lazy_without_a_set_length(self):
        result = Reverse().generate(Clip(notes=[1, 2]))
        self.assertEqual(result.notes, [Degree(2), Degree(1)])

    def test_reverse_with_a_set_length_uses_the_clip_note_length(self):
        result = Reverse().generate(Clip(notes=[1], note_length=QUARTER, length=1))
        self.assertEqual(result.notes, [Rest(0.75), Degree(1, QUARTER)])

    def test_mix_up_stays_lazy(self):
        result = MixUp([1, 0], seed=1).generate(Clip(notes=[1, 2]))
        self.assertEqual(result.notes, [Degree(2), Degree(1)])

    def test_transpose_scale_notes_needs_no_scale_for_degrees(self):
        result = Transpose(scale_notes=2).generate(Clip(notes=[1]))
        self.assertEqual(result.notes, [Degree(1, scale_notes=2)])

    def test_transpose_follows_the_scale_at_render(self):
        clip = Transpose(scale_notes=-1).generate(Clip(notes=[1, 2], note_length=QUARTER))
        self.assertEqual(pitches(clip, song_scale=C_MAJOR), [47, 48])
        self.assertEqual(pitches(clip, song_scale=A_MINOR), [43, 45])

    def test_transpose_half_whole_and_octaves_at_render(self):
        clip = Clip(notes=[1], note_length=QUARTER)
        cases = [(dict(half_steps=1), 49), (dict(whole_steps=-1), 46), (dict(octaves=-1), 36)]
        for amounts, expected in cases:
            with self.subTest(amounts=amounts):
                result = Transpose(**amounts).generate(clip)
                self.assertEqual(pitches(result, song_scale=C_MAJOR), [expected])

    def test_transpose_still_needs_a_scale_for_literal_notes(self):
        with self.assertRaises(ValueError):
            Transpose(scale_notes=1).generate(Clip(notes=['C4']))

    def test_transpose_keeps_notes_without_lengths_lazy(self):
        result = Transpose(octaves=1).generate(Clip(notes=['C4']))
        self.assertEqual(result.notes, [Note('C', 5)])
        self.assertIsNone(result.notes[0].length)

    def test_arp_leaves_degrees_alone_and_fills_chords(self):
        chord = Chord([Note('C', 4), Note('E', 4)])
        result = Arp(0.125).generate(Clip(notes=[1, chord], note_length=QUARTER))
        self.assertEqual(result.notes, [Degree(1, QUARTER), Note('C', 4, 0.125), Note('E', 4, 0.125)])

    def test_generators_reject_invalid_items_added_to_a_list(self):
        for generator in [Repeater(2), Arp(QUARTER), MixUp([1]), Reverse(), Transpose(octaves=1)]:
            clip = Clip(notes=[1], note_length=QUARTER)
            clip.notes.append('C4')
            with self.subTest(generator=type(generator).__name__):
                with self.assertRaises(ValueError):
                    generator.generate(clip)


class TestMaryDegreesDemo(unittest.TestCase):

    def test_melody_sounds_exactly_like_the_literal_version(self):
        with tempfile.TemporaryDirectory() as directory:
            literal_directory = os.path.join(directory, 'literal')
            degrees_directory = os.path.join(directory, 'degrees')
            ClipTree(literal_directory, demo.mary.build_song()).render()
            ClipTree(degrees_directory, demo.mary_degrees.build_song()).render()
            self.assertEqual(sorted(os.listdir(degrees_directory)), ['001-001.mid', '002-001.mid'])
            for filename in os.listdir(degrees_directory):
                with self.subTest(filename=filename):
                    self.assertEqual(
                        mido.MidiFile(os.path.join(degrees_directory, filename)).tracks[0],
                        mido.MidiFile(os.path.join(literal_directory, filename)).tracks[0],
                    )


if __name__ == '__main__':
    unittest.main()
