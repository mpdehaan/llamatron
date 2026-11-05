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
import io
import os
import tempfile
import unittest
from fractions import Fraction

import mido

from src.chord import Chord, ChordType
from src.generators.base import ClipGenerator
from src.generators.stutter import Stutter
from src.note import Degree, Note, Rest
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType
from src.song import Clip, Scene, Song, Track

QUARTER = 0.25
C = Note('C', 4, QUARTER)
D = Note('D', 4, QUARTER)
E = Note('E', 4, QUARTER)
F = Note('F', 4, QUARTER)
G = Note('G', 4, QUARTER)
A = Note('A', 4, QUARTER)
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)


def stutter(counts, notes, **clip_options):
    return Stutter(counts).generate(Clip(notes=notes, **clip_options))


def rendered(clip):
    """Render a clip, and return (type, note, tick) for each note message."""
    song = Song(scale=C_MAJOR)
    track = song.add_track(Track())
    scene = song.add_scene(Scene())
    song.set_clip(scene, track, clip)
    with tempfile.TemporaryDirectory() as directory:
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(directory, song).render()
        midi_file = mido.MidiFile(os.path.join(directory, '000-000.mid'))
    tick = 0
    result = []
    for message in midi_file.tracks[0]:
        tick += message.time
        if message.type in ('note_on', 'note_off'):
            result.append((message.type, message.note, tick))
    return result


class TestCounts(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Stutter([1]), ClipGenerator)

    def test_one_leaves_the_note_unchanged(self):
        self.assertEqual(stutter([1], [C, D]).notes, [C, D])

    def test_two_makes_two_notes_of_half_the_length(self):
        half = Note('C', 4, 0.125)
        self.assertEqual(stutter([2], [C]).notes, [half, half])

    def test_three_makes_three_exact_notes(self):
        third = Note('C', 4, Fraction(1, 12))
        self.assertEqual(stutter([3], [C]).notes, [third, third, third])

    def test_your_example_with_a_cycle(self):
        chopped_e = Note('E', 4, Fraction(1, 16))
        chopped_a = Note('A', 4, Fraction(1, 16))
        self.assertEqual(stutter([1, 1, 4], [C, D, E, F, G, A]).notes, [
            C, D, chopped_e, chopped_e, chopped_e, chopped_e,
            F, G, chopped_a, chopped_a, chopped_a, chopped_a,
        ])

    def test_each_generate_starts_the_cycle_again(self):
        generator = Stutter([2, 1])
        first = generator.generate(Clip(notes=[C]))
        second = generator.generate(Clip(notes=[C]))
        self.assertEqual(first.notes, second.notes)

    def test_uses_each_note_own_length(self):
        result = stutter([2], [Note('C', 4, 1), Note('D', 4, 0.5)]).notes
        self.assertEqual(result, [
            Note('C', 4, 0.5), Note('C', 4, 0.5), Note('D', 4, 0.25), Note('D', 4, 0.25),
        ])

    def test_keeps_the_spelling(self):
        self.assertEqual(stutter([2], [Note('Db', 4, QUARTER)]).notes[0].name, 'Db')

    def test_inexact_float_lengths_stay_exact(self):
        result = stutter([2], [Note('C', 4, 1 / 12)]).notes
        self.assertEqual(result[0].length, Fraction(1, 24))


class TestRests(unittest.TestCase):

    def test_rests_are_left_alone(self):
        self.assertEqual(stutter([1], [Rest(1)]).notes, [Rest(1)])
        self.assertEqual(stutter([4], [Rest(1)]).notes, [Rest(1)])

    def test_rests_do_not_use_up_a_count(self):
        half = Note('D', 4, 0.125)
        self.assertEqual(stutter([1, 2], [C, Rest(QUARTER), D]).notes, [
            C, Rest(QUARTER), half, half,
        ])

    def test_empty_clip_stays_empty(self):
        self.assertEqual(stutter([2], []).notes, [])


class TestChords(unittest.TestCase):

    def setUp(self):
        self.chord = Note('C', 4, 0.5).to_chord(ChordType.MAJOR)

    def test_chord_repeats_as_a_whole(self):
        half = Note('C', 4, 0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(stutter([2], [self.chord]).notes, [half, half])

    def test_chord_uses_up_one_count(self):
        half = Note('C', 4, 0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(stutter([2, 1], [self.chord, C]).notes, [half, half, C])

    def test_mixed_lengths_keep_their_proportions(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)])
        shorter = Chord([Note('C', 4, 0.25), Note('E', 4, 0.125)])
        self.assertEqual(stutter([2], [chord]).notes, [shorter, shorter])

    def test_chord_of_one_count_is_unchanged(self):
        self.assertEqual(stutter([1], [self.chord]).notes, [self.chord])


class TestSetLength(unittest.TestCase):

    def test_length_is_kept(self):
        self.assertEqual(stutter([2], [C], length=1).length, 1)
        self.assertIsNone(stutter([2], [C]).length)

    def test_silence_before_the_end_stays(self):
        half = Note('C', 4, 0.125)
        self.assertEqual(stutter([2], [C], length=1).notes, [half, half, Rest(0.75)])

    def test_chops_the_part_of_a_note_that_plays(self):
        quarter = Note('C', 4, 0.25)
        self.assertEqual(stutter([2], [Note('C', 4, 1)], length=0.5).notes, [quarter, quarter])

    def test_notes_past_the_end_do_not_use_up_a_count(self):
        half = Note('C', 4, 0.125)
        self.assertEqual(stutter([2], [C, D], length=0.25).notes, [half, half])


class TestLazyValues(unittest.TestCase):

    def test_degrees_stay_degrees(self):
        half = Degree(3, 0.125)
        self.assertEqual(stutter([2], [Degree(3, QUARTER)]).notes, [half, half])

    def test_note_length_is_used_and_kept(self):
        result = stutter([2, 1], [1, 'C4'], note_length=QUARTER)
        self.assertEqual(result.notes, [Degree(1, 0.125), Degree(1, 0.125), Note('C', 4, QUARTER)])
        self.assertEqual(result.note_length, QUARTER)

    def test_needs_a_length_when_it_runs(self):
        with self.assertRaises(ValueError):
            stutter([2], [1])

    def test_degrees_follow_the_scale_at_render(self):
        clip = stutter([2], [Degree(3, QUARTER)])
        self.assertEqual([m[1] for m in rendered(clip) if m[0] == 'note_on'], [52, 52])


class TestRendering(unittest.TestCase):

    def test_chopped_notes_are_adjacent_with_no_rests(self):
        self.assertEqual(rendered(stutter([1, 4], [C, D])), [
            ('note_on', 48, 0), ('note_off', 48, 480),
            ('note_on', 50, 480), ('note_off', 50, 600),
            ('note_on', 50, 600), ('note_off', 50, 720),
            ('note_on', 50, 720), ('note_off', 50, 840),
            ('note_on', 50, 840), ('note_off', 50, 960),
        ])

    def test_next_note_starts_when_it_did_before(self):
        before = [m for m in rendered(Clip(notes=[C, D, E])) if m[1] == 52 and m[0] == 'note_on']
        after = [m for m in rendered(stutter([3, 5, 1], [C, D, E])) if m[1] == 52 and m[0] == 'note_on']
        self.assertEqual(after, before)

    def test_total_duration_stays_the_same(self):
        notes = [C, Rest(0.5), Note('D', 4, 0.5), Note('C', 4, 0.5).to_chord(ChordType.MINOR)]
        result = stutter([2, 3, 5, 7], notes).notes
        self.assertEqual(sum(Fraction(position.length) for position in result), 1.75)

    def test_counts_that_do_not_divide_ticks_evenly_still_end_on_time(self):
        last = rendered(stutter([7], [C]))[-1]
        self.assertEqual(last, ('note_off', 48, 480))


class TestClipDetails(unittest.TestCase):

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[C], scale=C_MAJOR, length=2, note_length=0.5)
        result = Stutter([2]).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.note_length, 0.5)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[C, Rest(QUARTER)])
        Stutter([2]).generate(original)
        self.assertEqual(original.notes, [C, Rest(QUARTER)])


class TestStutterFields(unittest.TestCase):

    def test_counts_are_required(self):
        with self.assertRaises(TypeError):
            Stutter()

    def test_takes_a_list_or_tuple(self):
        self.assertEqual(Stutter([1, 2]).counts, [1, 2])
        self.assertEqual(Stutter((1, 2)).counts, (1, 2))

    def test_rejects_invalid_counts(self):
        invalid = [[], (), None, 2, '2', [0], [-1], [1.5], [2.0], ['2'], [None], [True], [1, 0]]
        for counts in invalid:
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    Stutter(counts)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [C]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Stutter([1]).generate(value)

    def test_counts_can_be_edited_and_are_validated(self):
        generator = Stutter([1])
        generator.counts = [2]
        self.assertEqual(len(generator.generate(Clip(notes=[C])).notes), 2)
        with self.assertRaises(ValueError):
            generator.counts = []
        self.assertEqual(generator.counts, [2])


if __name__ == '__main__':
    unittest.main()
