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
from fractions import Fraction

import mido

from llamatron.music.chord import Chord, ChordType
from llamatron.generators.base import ClipGenerator
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
# What the clip files are named under, and the one clip's file.
EXPORT = 'song'
CLIP_FILE = EXPORT + '_clip_s_001-t_001.mid'
C = Note(name='C', octave_number=4, length=QUARTER)
D = Note(name='D', octave_number=4, length=QUARTER)
E = Note(name='E', octave_number=4, length=QUARTER)
F = Note(name='F', octave_number=4, length=QUARTER)
G = Note(name='G', octave_number=4, length=QUARTER)
A = Note(name='A', octave_number=4, length=QUARTER)
C_MAJOR = Scale(root=Note(name='C', octave_number=4), typ=ScaleType.MAJOR)

# Names the tests give to their own things, and other values they use.
DB = 'Db'
C4 = 'C4'
RIFF = 'Riff'
CLIP = 'clip'


def stutter(counts, notes, **clip_options):
    return AutoRatchet(counts).generate(Clip(notes=notes, **clip_options))


def rendered(clip):
    """Render a clip, and return (type, note, tick) for each note message."""
    song = ClipGrid(scale=C_MAJOR)
    track = song.add_column(ClipColumn())
    scene = song.add_row(ClipRow())
    song.set_clip(row=scene, column=track, clip=clip)
    with tempfile.TemporaryDirectory() as directory:
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(directory=directory, grid=song, name=EXPORT).export()
        midi_file = mido.MidiFile(os.path.join(directory, CLIP_FILE))
    tick = 0
    result = []
    for message in midi_file.tracks[0]:
        tick += message.time
        if message.type in (NOTE_ON_MESSAGE, NOTE_OFF_MESSAGE):
            result.append((message.type, message.note, tick))
    return result


class TestCounts(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(AutoRatchet([1]), ClipGenerator)

    def test_one_leaves_the_note_unchanged(self):
        self.assertEqual(stutter([1], [C, D]).get_notes(), [C, D])

    def test_two_makes_two_notes_of_half_the_length(self):
        half = Note(name=NoteName.C, octave_number=4, length=0.125)
        self.assertEqual(stutter([2], [C]).get_notes(), [half, half])

    def test_three_makes_three_exact_notes(self):
        third = Note(name=NoteName.C, octave_number=4, length=Fraction(1, 12))
        self.assertEqual(stutter([3], [C]).get_notes(), [third, third, third])

    def test_your_example_with_a_cycle(self):
        chopped_e = Note(name=NoteName.E, octave_number=4, length=Fraction(1, 16))
        chopped_a = Note(name=NoteName.A, octave_number=4, length=Fraction(1, 16))
        self.assertEqual(stutter([1, 1, 4], [C, D, E, F, G, A]).get_notes(), [
            C, D, chopped_e, chopped_e, chopped_e, chopped_e,
            F, G, chopped_a, chopped_a, chopped_a, chopped_a,
        ])

    def test_each_generate_starts_the_cycle_again(self):
        generator = AutoRatchet([2, 1])
        first = generator.generate(Clip(notes=[C]))
        second = generator.generate(Clip(notes=[C]))
        self.assertEqual(first.get_notes(), second.get_notes())

    def test_uses_each_note_own_length(self):
        result = stutter([2], [Note(name=NoteName.C, octave_number=4, length=1), Note(name=NoteName.D, octave_number=4, length=0.5)]).get_notes()
        self.assertEqual(result, [
            Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.D, octave_number=4, length=0.25), Note(name=NoteName.D, octave_number=4, length=0.25),
        ])

    def test_keeps_the_spelling(self):
        self.assertEqual(stutter([2], [Note(name=NoteName.D_FLAT, octave_number=4, length=QUARTER)]).get_notes()[0].get_name(), DB)

    def test_inexact_float_lengths_stay_exact(self):
        result = stutter([2], [Note(name=NoteName.C, octave_number=4, length=1 / 12)]).get_notes()
        self.assertEqual(result[0].get_length(), Fraction(1, 24))


class TestRests(unittest.TestCase):

    def test_rests_are_left_alone(self):
        self.assertEqual(stutter([1], [Rest(1)]).get_notes(), [Rest(1)])
        self.assertEqual(stutter([4], [Rest(1)]).get_notes(), [Rest(1)])

    def test_rests_do_not_use_up_a_count(self):
        half = Note(name=NoteName.D, octave_number=4, length=0.125)
        self.assertEqual(stutter([1, 2], [C, Rest(QUARTER), D]).get_notes(), [
            C, Rest(QUARTER), half, half,
        ])

    def test_empty_clip_stays_empty(self):
        self.assertEqual(stutter([2], []).get_notes(), [])


class TestChords(unittest.TestCase):

    def setUp(self):
        self.chord = Note(name=NoteName.C, octave_number=4, length=0.5).to_chord(ChordType.MAJOR)

    def test_chord_repeats_as_a_whole(self):
        half = Note(name=NoteName.C, octave_number=4, length=0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(stutter([2], [self.chord]).get_notes(), [half, half])

    def test_chord_uses_up_one_count(self):
        half = Note(name=NoteName.C, octave_number=4, length=0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(stutter([2, 1], [self.chord, C]).get_notes(), [half, half, C])

    def test_mixed_lengths_keep_their_proportions(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.E, octave_number=4, length=0.25)])
        shorter = Chord([Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.E, octave_number=4, length=0.125)])
        self.assertEqual(stutter([2], [chord]).get_notes(), [shorter, shorter])

    def test_chord_of_one_count_is_unchanged(self):
        self.assertEqual(stutter([1], [self.chord]).get_notes(), [self.chord])


class TestSetLength(unittest.TestCase):

    def test_length_is_kept(self):
        self.assertEqual(stutter([2], [C], length=1).get_length(), 1)
        self.assertIsNone(stutter([2], [C]).get_length())

    def test_silence_before_the_end_stays(self):
        half = Note(name=NoteName.C, octave_number=4, length=0.125)
        self.assertEqual(stutter([2], [C], length=1).get_notes(), [half, half, Rest(0.75)])

    def test_chops_the_part_of_a_note_that_plays(self):
        quarter = Note(name=NoteName.C, octave_number=4, length=0.25)
        self.assertEqual(stutter([2], [Note(name=NoteName.C, octave_number=4, length=1)], length=0.5).get_notes(), [quarter, quarter])

    def test_notes_past_the_end_do_not_use_up_a_count(self):
        half = Note(name=NoteName.C, octave_number=4, length=0.125)
        self.assertEqual(stutter([2], [C, D], length=0.25).get_notes(), [half, half])


class TestLazyValues(unittest.TestCase):

    def test_degrees_stay_degrees(self):
        half = Degree(number=3, length=0.125)
        self.assertEqual(stutter([2], [Degree(number=3, length=QUARTER)]).get_notes(), [half, half])

    def test_note_length_is_used_and_kept(self):
        result = stutter([2, 1], [1, C4], note_length=QUARTER)
        self.assertEqual(result.get_notes(), [Degree(number=1, length=0.125), Degree(number=1, length=0.125), Note(name=NoteName.C, octave_number=4, length=QUARTER)])
        self.assertEqual(result.get_note_length(), QUARTER)

    def test_needs_a_length_when_it_runs(self):
        with self.assertRaises(ValueError):
            stutter([2], [1])

    def test_degrees_follow_the_scale_at_render(self):
        clip = stutter([2], [Degree(number=3, length=QUARTER)])
        self.assertEqual([m[1] for m in rendered(clip) if m[0] == NOTE_ON_MESSAGE], [52, 52])


class TestRendering(unittest.TestCase):

    def test_chopped_notes_are_adjacent_with_no_rests(self):
        self.assertEqual(rendered(stutter([1, 4], [C, D])), [
            (NOTE_ON_MESSAGE, 48, 0), (NOTE_OFF_MESSAGE, 48, 480),
            (NOTE_ON_MESSAGE, 50, 480), (NOTE_OFF_MESSAGE, 50, 600),
            (NOTE_ON_MESSAGE, 50, 600), (NOTE_OFF_MESSAGE, 50, 720),
            (NOTE_ON_MESSAGE, 50, 720), (NOTE_OFF_MESSAGE, 50, 840),
            (NOTE_ON_MESSAGE, 50, 840), (NOTE_OFF_MESSAGE, 50, 960),
        ])

    def test_next_note_starts_when_it_did_before(self):
        before = [m for m in rendered(Clip(notes=[C, D, E])) if m[1] == 52 and m[0] == NOTE_ON_MESSAGE]
        after = [m for m in rendered(stutter([3, 5, 1], [C, D, E])) if m[1] == 52 and m[0] == NOTE_ON_MESSAGE]
        self.assertEqual(after, before)

    def test_total_duration_stays_the_same(self):
        notes = [C, Rest(0.5), Note(name=NoteName.D, octave_number=4, length=0.5), Note(name=NoteName.C, octave_number=4, length=0.5).to_chord(ChordType.MINOR)]
        result = stutter([2, 3, 5, 7], notes).get_notes()
        self.assertEqual(sum(Fraction(position.get_length()) for position in result), 1.75)

    def test_counts_that_do_not_divide_ticks_evenly_still_end_on_time(self):
        last = rendered(stutter([7], [C]))[-1]
        self.assertEqual(last, (NOTE_OFF_MESSAGE, 48, 480))


class TestClipDetails(unittest.TestCase):

    def test_keeps_the_clip_details(self):
        original = Clip(name=RIFF, notes=[C], scale=C_MAJOR, length=2, note_length=0.5)
        result = AutoRatchet([2]).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.get_name(), RIFF)
        self.assertIs(result.get_scale(), C_MAJOR)
        self.assertEqual(result.get_note_length(), 0.5)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[C, Rest(QUARTER)])
        AutoRatchet([2]).generate(original)
        self.assertEqual(original.get_notes(), [C, Rest(QUARTER)])


class TestAutoRatchetFields(unittest.TestCase):

    def test_counts_are_required(self):
        with self.assertRaises(TypeError):
            AutoRatchet()

    def test_takes_a_list_or_tuple(self):
        self.assertEqual(AutoRatchet([1, 2]).get_counts(), [1, 2])
        self.assertEqual(AutoRatchet((1, 2)).get_counts(), (1, 2))

    def test_rejects_invalid_counts(self):
        invalid = [[], (), None, 2, '2', [0], [-1], [1.5], [2.0], ['2'], [None], [True], [1, 0]]
        for counts in invalid:
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    AutoRatchet(counts)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, CLIP, [C]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    AutoRatchet([1]).generate(value)

    def test_counts_can_be_edited_and_are_validated(self):
        generator = AutoRatchet([1])
        generator.set_counts([2])
        self.assertEqual(len(generator.generate(Clip(notes=[C])).get_notes()), 2)
        with self.assertRaises(ValueError):
            generator.set_counts([])
        self.assertEqual(generator.get_counts(), [2])


if __name__ == '__main__':
    unittest.main()
