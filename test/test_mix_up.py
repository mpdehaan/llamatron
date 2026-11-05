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
from collections import Counter

from src.chord import ChordType
from src.generators.base import ClipGenerator
from src.generators.mix_up import MixUp
from src.note import Degree, Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

QUARTER = 0.25
C = Note('C', 4, QUARTER)
D = Note('D', 4, QUARTER)
E = Note('E', 4, QUARTER)
SCALE = Scale(Note('C', 0, QUARTER), ScaleType.MAJOR)
NOTES = Scale(C, ScaleType.CHROMATIC).count(12)


def mix(probabilities, notes, seed=None, **clip_options):
    return MixUp(probabilities, seed=seed).generate(Clip(notes=notes, **clip_options))


class TestMixUp(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(MixUp([1]), ClipGenerator)

    def test_zero_changes_nothing(self):
        for seed in range(20):
            self.assertEqual(mix([0], NOTES, seed=seed).notes, NOTES)

    def test_one_makes_a_certain_swap_at_that_step(self):
        for seed in range(20):
            self.assertEqual(mix([1, 0], [C, D], seed=seed).notes, [D, C])

    def test_a_later_swap_can_undo_an_earlier_one(self):
        for seed in range(20):
            self.assertEqual(mix([1, 1], [C, D], seed=seed).notes, [C, D])

    def test_keeps_exactly_the_same_notes(self):
        for seed in range(20):
            self.assertEqual(Counter(mix([0.5], NOTES, seed=seed).notes), Counter(NOTES))

    def test_swaps_with_notes_that_are_not_neighbors(self):
        partners = {mix([1, 0, 0], [C, D, E], seed=seed).notes.index(C) for seed in range(30)}
        self.assertEqual(partners, {1, 2})

    def test_each_note_uses_the_next_probability_in_a_cycle(self):
        notes = [C, D, E]
        for seed in range(20):
            result = mix([0, 0, 1], notes, seed=seed).notes
            self.assertNotEqual(result[2], E)

    def test_only_the_chosen_step_starts_a_swap(self):
        for seed in range(20):
            result = mix([1, 0, 0, 0], NOTES[:4], seed=seed).notes
            moved = [place for place in range(4) if result[place] != NOTES[place]]
            self.assertEqual(len(moved), 2)
            self.assertIn(0, moved)

    def test_cycle_repeats_for_later_notes(self):
        results = [mix([0, 0, 1], NOTES[:6], seed=seed).notes for seed in range(30)]
        self.assertTrue(any(result[5] != NOTES[5] for result in results))
        self.assertTrue(any(result[2] != NOTES[2] for result in results))

    def test_half_swaps_about_half_the_time(self):
        changed = sum(mix([0.5, 0], [C, D], seed=seed).notes != [C, D] for seed in range(400))
        self.assertTrue(150 < changed < 250, changed)

    def test_notes_keep_their_own_lengths(self):
        long = Note('C', 4, 1)
        self.assertEqual(mix([1, 0], [long, D]).notes, [D, long])

    def test_too_few_notes_stay_the_same(self):
        self.assertEqual(mix([1], []).notes, [])
        self.assertEqual(mix([1], [C]).notes, [C])

    def test_chords_swap_as_one_note(self):
        chord = C.to_chord(ChordType.MAJOR)
        self.assertEqual(mix([1, 0], [chord, D]).notes, [D, chord])

    def test_degrees_stay_degrees(self):
        self.assertEqual(mix([1, 0], [Degree(1), Degree(2)]).notes, [Degree(2), Degree(1)])

    def test_needs_no_lengths_when_it_runs(self):
        self.assertEqual(mix([1, 0], [1, 'C4']).notes, [Note('C', 4), Degree(1)])


class TestRests(unittest.TestCase):

    def test_rests_stay_where_they_are(self):
        notes = [C, Rest(0.5), D, Rest(1), E, Rest(0.125)]
        for seed in range(30):
            result = mix([1], notes, seed=seed).notes
            self.assertEqual(result[1], Rest(0.5))
            self.assertEqual(result[3], Rest(1))
            self.assertEqual(result[5], Rest(0.125))

    def test_rest_is_never_chosen_as_a_partner(self):
        for seed in range(30):
            self.assertEqual(mix([1, 0], [C, Rest(0.5), D], seed=seed).notes, [D, Rest(0.5), C])

    def test_rests_do_not_use_up_a_probability(self):
        for seed in range(20):
            result = mix([0, 1], [C, Rest(0.5), D], seed=seed).notes
            self.assertEqual(result, [D, Rest(0.5), C])

    def test_clip_of_only_rests_stays_the_same(self):
        self.assertEqual(mix([1], [Rest(1), Rest(0.5)]).notes, [Rest(1), Rest(0.5)])

    def test_single_note_with_rests_stays_the_same(self):
        self.assertEqual(mix([1], [Rest(1), C, Rest(0.5)]).notes, [Rest(1), C, Rest(0.5)])


class TestClipDetails(unittest.TestCase):

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=NOTES, scale=SCALE, length=2, note_length=0.5)
        result = MixUp([1]).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, SCALE)
        self.assertEqual(result.length, 2)
        self.assertEqual(result.note_length, 0.5)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=NOTES)
        MixUp([1], seed=1).generate(original)
        self.assertEqual(original.notes, NOTES)


class TestMixUpSeed(unittest.TestCase):

    def test_same_seed_gives_the_same_result_every_time(self):
        generator = MixUp([0.5], seed=1)
        self.assertEqual(
            generator.generate(Clip(notes=NOTES)).notes,
            generator.generate(Clip(notes=NOTES)).notes,
        )

    def test_different_seeds_give_different_results(self):
        self.assertNotEqual(mix([1], NOTES, seed=1).notes, mix([1], NOTES, seed=2).notes)

    def test_no_seed_still_works(self):
        self.assertEqual(Counter(mix([1], NOTES).notes), Counter(NOTES))


class TestMixUpFields(unittest.TestCase):

    def test_probabilities_are_required(self):
        with self.assertRaises(TypeError):
            MixUp()

    def test_takes_a_list_or_tuple(self):
        self.assertEqual(MixUp([0, 1]).probabilities, [0, 1])
        self.assertEqual(MixUp((0, 1)).probabilities, (0, 1))

    def test_no_longer_takes_a_number_of_swaps(self):
        for value in [0, 1, 5]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MixUp(value)

    def test_rejects_invalid_values(self):
        invalid = [[], (), None, 0.5, '0.5', [-0.1], [1.1], [2], ['1'], [None], [True], [0, 2]]
        for probabilities in invalid:
            with self.subTest(probabilities=probabilities):
                with self.assertRaises(ValueError):
                    MixUp(probabilities)
        for seed in ['1', 1.5, True]:
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    MixUp([1], seed=seed)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', NOTES]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MixUp([1]).generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = MixUp([1])
        generator.probabilities = [0]
        generator.seed = 3
        self.assertEqual((generator.probabilities, generator.seed), ([0], 3))
        with self.assertRaises(ValueError):
            generator.probabilities = []
        self.assertEqual(generator.probabilities, [0])


if __name__ == '__main__':
    unittest.main()
