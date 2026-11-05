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

import contextlib
import io
import os
import tempfile
import unittest
from fractions import Fraction

import mido

from llamatron.chord import Chord, ChordType
from llamatron.legacy.generators.backfill import Backfill
from llamatron.generators.base import ClipGenerator
from llamatron.note import Degree, Note, Rest
from llamatron.renderers.clip_tree import ClipTree
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Scene, Song, Track

SIXTEENTH = 0.0625
QUARTER = 0.25
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)
E_FLAT_MAJOR = Scale(Note('Eb', 4), ScaleType.MAJOR)


def q(name, octave=4):
    """Return a quarter note."""
    return Note(name, octave, QUARTER)


def fill(notes, probabilities=(1,), scale=C_MAJOR, seed=None, **clip_options):
    generator = Backfill(list(probabilities), scale=scale, seed=seed)
    return generator.generate(Clip(notes=notes, **clip_options))


def played(clip):
    """Return (name and octave, start) for each non-rest position in a clip."""
    result = []
    now = Fraction(0)
    for position in clip.notes:
        if not isinstance(position, Rest):
            result.append((f'{position.name}{position.octave_number}', now))
        now += Fraction(position.length).limit_denominator(1_000_000)
    return result


class TestFillingAGap(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Backfill([1]), ClipGenerator)

    def test_adds_the_scale_note_nearest_the_middle_at_the_halfway_time(self):
        result = fill([q('C'), Rest(0.75), q('G')])
        self.assertEqual(result.notes, [q('C'), Rest(0.25), q('E'), Rest(0.25), q('G')])

    def test_new_note_lasts_as_long_as_the_first_note(self):
        result = fill([Note('C', 4, SIXTEENTH), Rest(0.9375), q('G')])
        self.assertEqual(result.notes[2], Note('E', 4, SIXTEENTH))

    def test_works_going_down(self):
        result = fill([q('G'), Rest(0.75), q('C')])
        self.assertEqual(result.notes[2], q('E'))

    def test_ties_go_to_the_lower_note(self):
        result = fill([q('C'), Rest(0.75), q('A')])
        self.assertEqual(result.notes[2], q('E'))

    def test_uses_the_shape_of_the_scale(self):
        result = fill([q('A', 3), Rest(0.75), q('E')], scale=A_MINOR)
        self.assertEqual(result.notes[2], q('C'))

    def test_uses_the_spelling_of_the_scale(self):
        result = fill([q('Eb'), Rest(0.75), q('Db', 5)], scale=E_FLAT_MAJOR)
        self.assertEqual(result.notes[2].name, 'Ab')

    def test_repeated_runs_get_smoother_and_then_stop(self):
        clip = Clip(notes=[Note('C', 4, SIXTEENTH), Rest(0.4375), Note('G', 4, SIXTEENTH)])
        generator = Backfill([1, 1, 1, 1], scale=C_MAJOR)
        expected = ['C E G', 'C D E F G', 'C D E F G']
        for names in expected:
            clip = generator.generate(clip)
            self.assertEqual(' '.join(p.name for p in clip.notes if not isinstance(p, Rest)), names)

    def test_repeated_runs_keep_notes_on_their_times(self):
        clip = Clip(notes=[Note('C', 4, SIXTEENTH), Rest(0.4375), Note('G', 4, SIXTEENTH)])
        generator = Backfill([1], scale=C_MAJOR)
        clip = generator.generate(generator.generate(clip))
        self.assertEqual(played(clip), [
            ('C4', Fraction(0)), ('D4', Fraction(1, 8)), ('E4', Fraction(1, 4)),
            ('F4', Fraction(3, 8)), ('G4', Fraction(1, 2)),
        ])


class TestSkipping(unittest.TestCase):

    def test_nothing_between_neighboring_scale_notes(self):
        notes = [q('C'), Rest(0.75), q('D')]
        self.assertEqual(fill(notes).notes, notes)

    def test_nothing_between_two_of_the_same_pitch(self):
        notes = [q('C'), Rest(0.75), q('C')]
        self.assertEqual(fill(notes).notes, notes)

    def test_notes_outside_the_scale_can_have_nothing_between(self):
        notes = [q('C#'), Rest(0.75), q('D')]
        self.assertEqual(fill(notes).notes, notes)

    def test_notes_outside_the_scale_can_have_a_scale_note_between(self):
        self.assertEqual(fill([q('C#'), Rest(0.75), q('D#')]).notes[2], q('D'))

    def test_no_room_without_a_rest(self):
        notes = [q('C'), q('G')]
        self.assertEqual(fill(notes).notes, notes)

    def test_no_room_when_the_first_note_runs_past_the_middle(self):
        notes = [Note('C', 4, 0.75), Rest(0.25), q('G')]
        self.assertEqual(fill(notes).notes, notes)

    def test_no_room_when_the_silence_is_shorter_than_the_new_note(self):
        notes = [q('C'), Rest(0.125), q('G')]
        self.assertEqual(fill(notes).notes, notes)

    def test_new_note_can_exactly_fill_the_silence(self):
        result = fill([Note('C', 4, SIXTEENTH), Rest(SIXTEENTH), Note('G', 4, SIXTEENTH)])
        self.assertEqual(result.notes, [
            Note('C', 4, SIXTEENTH), Note('E', 4, SIXTEENTH), Note('G', 4, SIXTEENTH),
        ])

    def test_gap_after_the_last_note_is_never_filled(self):
        notes = [q('C'), Rest(1)]
        self.assertEqual(fill(notes).notes, notes)

    def test_single_note_and_empty_clips_stay_the_same(self):
        self.assertEqual(fill([q('C')]).notes, [q('C')])
        self.assertEqual(fill([]).notes, [])

    def test_gap_before_the_first_note_is_never_filled(self):
        notes = [Rest(1), q('C')]
        self.assertEqual(fill(notes).notes, notes)

    def test_existing_rests_are_kept_when_nothing_is_added(self):
        notes = [q('C'), Rest(0.25), Rest(0.25), q('D')]
        self.assertEqual(fill(notes).notes, notes)


class TestProbabilities(unittest.TestCase):

    def setUp(self):
        self.gap = [q('C'), Rest(0.75), q('G')]

    def test_zero_never_fills(self):
        for seed in range(50):
            self.assertEqual(fill(self.gap, [0], seed=seed).notes, self.gap)

    def test_one_always_fills(self):
        for seed in range(50):
            self.assertEqual(len(fill(self.gap, [1], seed=seed).notes), 5)

    def test_half_fills_about_half_the_time(self):
        filled = sum(len(fill(self.gap, [0.5], seed=seed).notes) == 5 for seed in range(400))
        self.assertTrue(150 < filled < 250, filled)

    def test_each_gap_uses_the_next_probability_in_a_cycle(self):
        notes = [q('C'), Rest(0.75), q('G'), Rest(0.75), q('C'), Rest(0.75), q('G')]
        result = fill(notes, [0, 1])
        self.assertEqual(played(result), [
            ('C4', Fraction(0)), ('G4', Fraction(1)), ('E4', Fraction(3, 2)),
            ('C4', Fraction(2)), ('G4', Fraction(3)),
        ])

    def test_your_example_only_rolls_once_per_gap(self):
        notes = []
        for name in 'CGCGC':
            notes += [q(name), Rest(0.75)]
        result = fill(notes[:-1], [0, 0, 0.5, 1], seed=1)
        added_at = {start for _, start in played(result)} - {Fraction(n) for n in range(5)}
        self.assertTrue(added_at <= {Fraction(5, 2), Fraction(7, 2)})
        self.assertIn(Fraction(7, 2), added_at)

    def test_a_gap_with_no_room_still_uses_up_a_probability(self):
        notes = [q('C'), q('G'), Rest(0.75), q('C')]
        result = fill(notes, [1, 0])
        self.assertEqual(result.notes, notes)

    def test_same_seed_gives_the_same_result(self):
        notes = []
        for name in 'CGCGCGCG':
            notes += [q(name), Rest(0.75)]
        first = fill(notes[:-1], [0.5], seed=3)
        second = fill(notes[:-1], [0.5], seed=3)
        self.assertEqual(first.notes, second.notes)

    def test_different_seeds_can_give_different_results(self):
        notes = []
        for name in 'CGCGCGCG':
            notes += [q(name), Rest(0.75)]
        results = {tuple(fill(notes[:-1], [0.5], seed=seed).notes) for seed in range(10)}
        self.assertGreater(len(results), 1)


class TestChords(unittest.TestCase):

    def test_chord_lowest_note_is_its_pitch(self):
        chord = q('C').to_chord(ChordType.MAJOR)
        result = fill([chord, Rest(0.75), q('G')])
        self.assertEqual(result.notes, [chord, Rest(0.25), q('E'), Rest(0.25), q('G')])

    def test_next_chord_uses_its_lowest_note(self):
        chord = q('G').to_chord(ChordType.MAJOR)
        result = fill([q('C'), Rest(0.75), chord])
        self.assertEqual(result.notes[2], q('E'))

    def test_new_note_lasts_as_long_as_the_longest_chord_note(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)])
        result = fill([chord, Rest(1.5), q('G')])
        self.assertEqual(result.notes[2], Note('E', 4, 0.5))


class TestRestsAndLengths(unittest.TestCase):

    def test_rests_around_the_new_note_add_up_to_the_same_time(self):
        result = fill([q('C'), Rest(0.25), Rest(0.5), q('G')])
        self.assertEqual(result.notes, [q('C'), Rest(0.25), q('E'), Rest(0.25), q('G')])

    def test_rest_at_the_start_and_end_are_kept(self):
        result = fill([Rest(1), q('C'), Rest(0.75), q('G'), Rest(1)])
        self.assertEqual(result.notes, [
            Rest(1), q('C'), Rest(0.25), q('E'), Rest(0.25), q('G'), Rest(1),
        ])

    def test_set_length_is_kept_and_silence_stays(self):
        result = fill([q('C'), Rest(0.75), q('G')], length=2)
        self.assertEqual(result.length, 2)
        self.assertEqual(result.notes[-1], Rest(0.75))

    def test_notes_past_a_set_length_do_not_make_a_gap(self):
        notes = [q('C'), Rest(0.75), q('G')]
        self.assertEqual(fill(notes, length=1).notes, notes)

    def test_notes_past_a_set_length_are_cut_when_a_note_is_added(self):
        notes = [q('C'), Rest(0.75), q('G'), Rest(1), q('C')]
        result = fill(notes, length=1.5)
        self.assertEqual(result.notes, [q('C'), Rest(0.25), q('E'), Rest(0.25), q('G'), Rest(0.25)])
        self.assertEqual(result.length, 1.5)

    def test_total_duration_stays_the_same(self):
        notes = [q('C'), Rest(0.75), q('G'), Rest(0.5), q('C'), Rest(0.75), q('E')]
        before = sum(Fraction(p.length) for p in notes)
        after = sum(Fraction(p.length) for p in fill(notes).notes)
        self.assertEqual(after, before)


class TestFindingTheScale(unittest.TestCase):

    def setUp(self):
        self.notes = [q('C'), Rest(0.75), q('A')]

    def test_uses_the_clip_scale(self):
        generator = Backfill([1])
        result = generator.generate(Clip(notes=self.notes, scale=A_MINOR))
        self.assertEqual(result.notes[2], q('E'))

    def test_given_scale_is_used_over_the_clip_scale(self):
        pentatonic = Scale(Note('C', 4), ScaleType.MAJOR_PENTATONIC)
        generator = Backfill([1], scale=pentatonic)
        result = generator.generate(Clip(notes=self.notes, scale=A_MINOR))
        self.assertEqual(result.notes[2], q('E'))
        self.assertIs(result.scale, A_MINOR)

    def test_can_use_a_scene_or_song_scale_through_scale_at(self):
        song = Song(scale=C_MAJOR)
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        generator = Backfill([1], scale=song.scale_at(scene, track))
        result = generator.generate(Clip(notes=[q('C'), Rest(0.75), q('G')]))
        self.assertEqual(result.notes[2], q('E'))

    def test_rejects_filling_a_gap_with_no_scale(self):
        with self.assertRaises(ValueError):
            Backfill([1]).generate(Clip(notes=self.notes))

    def test_no_scale_is_needed_when_nothing_would_be_filled(self):
        Backfill([0]).generate(Clip(notes=self.notes))
        Backfill([1]).generate(Clip(notes=[q('C'), q('A')]))
        Backfill([1]).generate(Clip(notes=[q('C')]))


class TestDegrees(unittest.TestCase):

    def test_middle_degree_needs_no_scale(self):
        result = Backfill([1]).generate(Clip(notes=[Degree(1, QUARTER), Rest(0.75), Degree(5, QUARTER)]))
        self.assertEqual(result.notes[2], Degree(3, QUARTER))

    def test_ties_go_to_the_lower_degree(self):
        result = Backfill([1]).generate(Clip(notes=[Degree(1, QUARTER), Rest(0.75), Degree(4, QUARTER)]))
        self.assertEqual(result.notes[2], Degree(2, QUARTER))

    def test_neighboring_degrees_have_nothing_between(self):
        notes = [Degree(1, QUARTER), Rest(0.75), Degree(2, QUARTER)]
        self.assertEqual(Backfill([1]).generate(Clip(notes=notes)).notes, notes)

    def test_degrees_can_be_filled_going_down(self):
        result = Backfill([1]).generate(Clip(notes=[Degree(5, QUARTER), Rest(0.75), Degree(1, QUARTER)]))
        self.assertEqual(result.notes[2], Degree(3, QUARTER))

    def test_keeps_the_octave(self):
        notes = [Degree(1, QUARTER, octave=1), Rest(0.75), Degree(5, QUARTER, octave=1)]
        result = Backfill([1]).generate(Clip(notes=notes))
        self.assertEqual(result.notes[2], Degree(3, QUARTER, octave=1))

    def test_note_length_is_used_and_kept(self):
        result = Backfill([1]).generate(Clip(notes=[1, Rest(0.75), 5], note_length=QUARTER))
        self.assertEqual(result.notes[0], Degree(1, QUARTER))
        self.assertEqual(result.notes[2], Degree(3, QUARTER))
        self.assertEqual(result.note_length, QUARTER)

    def test_moved_degrees_count_where_they_end_up(self):
        notes = [Degree(1, QUARTER, scale_notes=-2), Rest(0.75), Degree(1, QUARTER, scale_notes=2)]
        result = Backfill([1]).generate(Clip(notes=notes))
        self.assertEqual(result.notes[2], Degree(1, QUARTER))

    def test_middle_degree_below_the_root_stays_valid(self):
        notes = [Degree(1, QUARTER, scale_notes=-4), Rest(0.75), Degree(1, QUARTER, scale_notes=-2)]
        result = Backfill([1]).generate(Clip(notes=notes))
        self.assertEqual(result.notes[2].to_note(C_MAJOR), Degree(1, QUARTER, scale_notes=-3).to_note(C_MAJOR))

    def test_different_octaves_need_a_scale(self):
        notes = [Degree(1, QUARTER), Rest(0.75), Degree(1, QUARTER, octave=1)]
        with self.assertRaises(ValueError):
            Backfill([1]).generate(Clip(notes=notes))
        result = Backfill([1], scale=C_MAJOR).generate(Clip(notes=notes))
        self.assertEqual(result.notes[2], q('F'))

    def test_mixing_a_degree_and_a_note_needs_a_scale(self):
        notes = [Degree(1, QUARTER), Rest(0.75), q('G')]
        with self.assertRaises(ValueError):
            Backfill([1]).generate(Clip(notes=notes))
        result = Backfill([1], scale=C_MAJOR).generate(Clip(notes=notes))
        self.assertEqual(result.notes[2], q('E'))

    def test_needs_a_length_when_it_runs(self):
        with self.assertRaises(ValueError):
            Backfill([1]).generate(Clip(notes=[1, 5]))


class TestRendering(unittest.TestCase):

    def test_new_notes_render_at_the_right_time(self):
        clip = fill([q('C'), Rest(0.75), q('G')])
        song = Song()
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        song.set_clip(scene, track, clip)
        with tempfile.TemporaryDirectory() as directory:
            with contextlib.redirect_stdout(io.StringIO()):
                ClipTree(directory, song).render()
            midi_file = mido.MidiFile(os.path.join(directory, '001-001.mid'))
        tick = 0
        starts = []
        for message in midi_file.tracks[0]:
            tick += message.time
            if message.type == 'note_on':
                starts.append((message.note, tick / 480))
        self.assertEqual(starts, [(48, 0), (52, 2), (55, 4)])


class TestClipDetails(unittest.TestCase):

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[q('C'), Rest(0.75), q('G')], scale=C_MAJOR, length=2, note_length=0.5)
        result = Backfill([1]).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(result.length, 2)
        self.assertEqual(result.note_length, 0.5)

    def test_leaves_the_original_unchanged(self):
        notes = [q('C'), Rest(0.75), q('G')]
        original = Clip(notes=notes, scale=C_MAJOR)
        Backfill([1]).generate(original)
        self.assertEqual(original.notes, notes)


class TestBackfillFields(unittest.TestCase):

    def test_probabilities_are_required(self):
        with self.assertRaises(TypeError):
            Backfill()

    def test_takes_a_list_or_tuple(self):
        self.assertEqual(Backfill([0, 0.5, 1]).probabilities, [0, 0.5, 1])
        self.assertEqual(Backfill((0, 1)).probabilities, (0, 1))

    def test_rejects_invalid_probabilities(self):
        invalid = [
            [], (), None, 0.5, '0.5', [-0.1], [1.1], [2], ['1'], [None], [True],
            [float('nan')], [float('inf')], [0, 2],
        ]
        for probabilities in invalid:
            with self.subTest(probabilities=probabilities):
                with self.assertRaises(ValueError):
                    Backfill(probabilities)

    def test_rejects_invalid_scales_and_seeds(self):
        for scale in ['C major', ScaleType.MAJOR, q('C')]:
            with self.subTest(scale=scale):
                with self.assertRaises(ValueError):
                    Backfill([1], scale=scale)
        for seed in ['1', 1.5, True]:
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    Backfill([1], seed=seed)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [q('C')]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Backfill([1]).generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Backfill([1])
        generator.probabilities = [0]
        generator.scale = C_MAJOR
        generator.seed = 3
        self.assertEqual(
            (generator.probabilities, generator.scale, generator.seed),
            ([0], C_MAJOR, 3),
        )
        with self.assertRaises(ValueError):
            generator.probabilities = []
        self.assertEqual(generator.probabilities, [0])


if __name__ == '__main__':
    unittest.main()
