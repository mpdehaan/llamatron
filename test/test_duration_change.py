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
import random
import tempfile
import unittest
from fractions import Fraction

import mido

from src.chord import Chord, ChordType
from src.generators.base import ClipGenerator
from src.legacy.generators.duration_change import DurationChange
from src.note import Degree, Note, Rest
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType
from src.song import Clip, Scene, Song, Track

QUARTER = 0.25
C = Note('C', 4, QUARTER)
D = Note('D', 4, QUARTER)
E = Note('E', 4, QUARTER)
F = Note('F', 4, QUARTER)
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)


def change(factors, notes, **clip_options):
    return DurationChange(factors).generate(Clip(notes=notes, **clip_options))


def starts(positions):
    """Return when each non-rest position starts, and the total length of them all."""
    now = Fraction(0)
    result = []
    for position in positions:
        if not isinstance(position, Rest):
            result.append(now)
        now += Fraction(position.length).limit_denominator(1_000_000)
    return result, now


def rendered(clip):
    """Render a clip, and return (type, note, tick) for each note message."""
    song = Song(scale=C_MAJOR)
    track = song.add_track(Track())
    scene = song.add_scene(Scene())
    song.set_clip(scene, track, clip)
    with tempfile.TemporaryDirectory() as directory:
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(directory, song).render()
        midi_file = mido.MidiFile(os.path.join(directory, '001-001.mid'))
    tick = 0
    result = []
    for message in midi_file.tracks[0]:
        tick += message.time
        if message.type in ('note_on', 'note_off'):
            result.append((message.type, message.note, tick))
    return result


class TestFactors(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(DurationChange([1]), ClipGenerator)

    def test_half_makes_every_note_half_as_long_and_keeps_its_start(self):
        self.assertEqual(change([0.5], [C, D]).notes, [
            Note('C', 4, 0.125), Rest(0.125),
            Note('D', 4, 0.125), Rest(0.125),
        ])

    def test_one_keeps_every_note(self):
        self.assertEqual(change([1], [C, Rest(QUARTER), D]).notes, [C, Rest(QUARTER), D])

    def test_factors_cycle(self):
        notes = [Note('C', 4, 1)] * 4
        result = change([0.25, 0.5], notes).notes
        self.assertEqual([p.length for p in result if not isinstance(p, Rest)], [0.25, 0.5, 0.25, 0.5])

    def test_your_example_with_a_cycle_of_three(self):
        self.assertEqual(change([0.25, 1, 2], [C, D, E, F]).notes, [
            Note('C', 4, Fraction(1, 16)), Rest(Fraction(3, 16)),
            D,
            E,
            Note('F', 4, Fraction(1, 16)), Rest(Fraction(3, 16)),
        ])

    def test_each_generate_starts_the_cycle_again(self):
        generator = DurationChange([0.5, 1])
        first = generator.generate(Clip(notes=[C]))
        second = generator.generate(Clip(notes=[C]))
        self.assertEqual(first.notes, second.notes)

    def test_inexact_float_factors_stay_exact(self):
        result = change([1 / 3], [Note('C', 4, 0.75)]).notes
        self.assertEqual(result, [Note('C', 4, 0.25), Rest(0.5)])


class TestRests(unittest.TestCase):

    def test_rests_do_not_use_up_a_factor(self):
        result = change([0.5, 1], [C, Rest(QUARTER), D]).notes
        self.assertEqual(result, [Note('C', 4, 0.125), Rest(0.125), Rest(QUARTER), D])

    def test_rests_are_kept_when_nothing_grows_into_them(self):
        result = change([0.5], [Rest(1), C]).notes
        self.assertEqual(result[0], Rest(1))

    def test_clip_of_only_rests_stays_the_same(self):
        self.assertEqual(change([2], [Rest(1), Rest(0.5)]).notes, [Rest(1), Rest(0.5)])

    def test_empty_clip_stays_empty(self):
        self.assertEqual(change([2], []).notes, [])


class TestGrowing(unittest.TestCase):

    def test_stops_at_the_very_next_note(self):
        self.assertEqual(change([2], [C, D]).notes, [C, D])

    def test_uses_part_of_a_longer_rest(self):
        result = change([2], [C, Rest(0.5), D]).notes
        self.assertEqual(result, [Note('C', 4, 0.5), Rest(0.25), D])

    def test_uses_all_of_a_rest_of_the_same_size(self):
        result = change([2], [C, Rest(QUARTER), D]).notes
        self.assertEqual(result, [Note('C', 4, 0.5), D])

    def test_stops_at_the_next_note_after_a_short_rest(self):
        result = change([8], [C, Rest(QUARTER), D]).notes
        self.assertEqual(result, [Note('C', 4, 0.5), D])

    def test_plays_through_several_rests(self):
        result = change([4], [C, Rest(0.25), Rest(0.25), Rest(0.5), D]).notes
        self.assertEqual(result, [Note('C', 4, 1), Rest(0.25), D])

    def test_stops_at_the_end_of_a_clip_without_a_set_length(self):
        self.assertEqual(change([2], [C]).notes, [C])

    def test_same_pitch_ends_and_triggers_again(self):
        self.assertEqual(rendered(change([2], [C, C])), [
            ('note_on', 48, 0), ('note_off', 48, 480),
            ('note_on', 48, 480), ('note_off', 48, 960),
        ])


class TestChords(unittest.TestCase):

    def setUp(self):
        self.chord = Note('C', 4, 0.5).to_chord(ChordType.MAJOR)

    def test_all_notes_use_the_same_factor(self):
        result = change([0.5], [self.chord]).notes
        self.assertEqual(result, [Note('C', 4, 0.25).to_chord(ChordType.MAJOR), Rest(0.25)])

    def test_chord_uses_up_one_factor(self):
        result = change([0.5, 1], [self.chord, C]).notes
        self.assertEqual(result, [
            Note('C', 4, 0.25).to_chord(ChordType.MAJOR), Rest(0.25), C,
        ])

    def test_mixed_lengths_keep_their_proportions(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)])
        result = change([0.5], [chord]).notes
        self.assertEqual(result, [Chord([Note('C', 4, 0.25), Note('E', 4, 0.125)]), Rest(0.25)])

    def test_growing_chord_plays_through_a_rest(self):
        result = change([2], [self.chord, Rest(1), C]).notes
        self.assertEqual(result, [Note('C', 4, 1).to_chord(ChordType.MAJOR), Rest(0.5), C])

    def test_growing_chord_stops_at_the_next_note(self):
        self.assertEqual(change([2], [self.chord, C]).notes, [self.chord, C])

    def test_growing_mixed_chord_cuts_only_notes_that_are_too_long(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.125)])
        result = change([2], [chord, C]).notes
        self.assertEqual(result, [Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)]), C])


class TestSetLength(unittest.TestCase):

    def test_length_is_kept(self):
        self.assertEqual(change([2], [C], length=1).length, 1)
        self.assertIsNone(change([2], [C]).length)

    def test_can_grow_into_the_silence_before_the_end(self):
        result = change([2], [C], length=1).notes
        self.assertEqual(result, [Note('C', 4, 0.5), Rest(0.5)])

    def test_stops_at_the_end_of_the_clip(self):
        result = change([100], [C], length=1).notes
        self.assertEqual(result, [Note('C', 4, 1)])

    def test_note_cut_by_the_length_is_scaled_from_what_plays(self):
        result = change([0.5], [Note('C', 4, 1)], length=0.5).notes
        self.assertEqual(result, [Note('C', 4, 0.25), Rest(0.25)])


class TestLazyValues(unittest.TestCase):

    def test_degrees_stay_degrees(self):
        result = change([0.5], [Degree(3, QUARTER)]).notes
        self.assertEqual(result, [Degree(3, 0.125), Rest(0.125)])

    def test_note_length_is_used_and_kept(self):
        result = change([0.5], [1, 'C4'], note_length=QUARTER)
        self.assertEqual(result.notes, [
            Degree(1, 0.125), Rest(0.125), Note('C', 4, 0.125), Rest(0.125),
        ])
        self.assertEqual(result.note_length, QUARTER)

    def test_needs_a_length_when_it_runs(self):
        with self.assertRaises(ValueError):
            change([0.5], [1])


class TestTiming(unittest.TestCase):

    def test_every_note_starts_when_it_did_before_with_random_clips(self):
        generator = random.Random(1)
        lengths = [0.125, 0.25, 0.5, 1]
        factors = [0.25, 0.5, 1, 1.5, 2, 4]
        for _ in range(200):
            notes = []
            for _ in range(generator.randint(1, 10)):
                length = generator.choice(lengths)
                kind = generator.choice(['note', 'rest', 'chord'])
                if kind == 'note':
                    notes.append(Note('C', 4, length))
                elif kind == 'rest':
                    notes.append(Rest(length))
                else:
                    notes.append(Note('C', 4, length).to_chord(ChordType.MAJOR))
            chosen = [generator.choice(factors) for _ in range(generator.randint(1, 4))]
            result = change(chosen, notes).notes
            with self.subTest(notes=notes, factors=chosen):
                self.assertEqual(starts(result), starts(notes))

    def test_render_starts_notes_on_the_same_ticks(self):
        notes = [C, Rest(0.5), D, E, Rest(QUARTER), F]
        before = [m for m in rendered(Clip(notes=notes)) if m[0] == 'note_on']
        after = [m for m in rendered(change([0.25, 1, 2, 4], notes)) if m[0] == 'note_on']
        self.assertEqual(after, before)


class TestClipDetails(unittest.TestCase):

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[C], scale=C_MAJOR, length=2, note_length=0.5)
        result = DurationChange([0.5]).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.note_length, 0.5)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[C, Rest(QUARTER)])
        DurationChange([0.5]).generate(original)
        self.assertEqual(original.notes, [C, Rest(QUARTER)])


class TestDurationChangeFields(unittest.TestCase):

    def test_factors_are_required(self):
        with self.assertRaises(TypeError):
            DurationChange()

    def test_takes_a_list_or_tuple(self):
        self.assertEqual(DurationChange([1, 2]).factors, [1, 2])
        self.assertEqual(DurationChange((1, 2)).factors, (1, 2))

    def test_rejects_invalid_factors(self):
        invalid = [
            [], (), None, 0.5, '0.5', [0], [-1], ['1'], [None], [True],
            [float('nan')], [float('inf')], [1, 0],
        ]
        for factors in invalid:
            with self.subTest(factors=factors):
                with self.assertRaises(ValueError):
                    DurationChange(factors)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [C]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    DurationChange([1]).generate(value)

    def test_factors_can_be_edited_and_are_validated(self):
        generator = DurationChange([1])
        generator.factors = [0.5]
        self.assertEqual(generator.generate(Clip(notes=[C])).notes[0].length, 0.125)
        with self.assertRaises(ValueError):
            generator.factors = []
        self.assertEqual(generator.factors, [0.5])


if __name__ == '__main__':
    unittest.main()
