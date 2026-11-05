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
from collections import Counter

from llamatron.chord import ChordType
from llamatron.generators.base import ClipGenerator
from llamatron.legacy.generators.mix_up2 import MixUp2
from llamatron.note import Degree, Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

QUARTER = 0.25
C = Note('C', 4, QUARTER)
D = Note('D', 4, QUARTER)
E = Note('E', 4, QUARTER)
F = Note('F', 4, QUARTER)
G = Note('G', 4, QUARTER)
SCALE = Scale(Note('C', 4), ScaleType.MAJOR)


def swap(probabilities, notes, seed=None, **clip_options):
    return MixUp2(probabilities, seed=seed).generate(Clip(notes=notes, **clip_options))


class TestSwapping(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(MixUp2([1]), ClipGenerator)

    def test_one_always_swaps_a_note_with_the_next(self):
        for seed in range(20):
            self.assertEqual(swap([1], [C, D], seed=seed).notes, [D, C])

    def test_zero_never_swaps(self):
        for seed in range(20):
            self.assertEqual(swap([0], [C, D, E, F], seed=seed).notes, [C, D, E, F])

    def test_probabilities_choose_the_steps_in_a_cycle(self):
        self.assertEqual(swap([1, 0], [C, D, E, F]).notes, [D, C, F, E])
        self.assertEqual(swap([0, 1], [C, D, E, F]).notes, [C, E, D, F])
        self.assertEqual(swap([0, 0, 1], [C, D, E, F]).notes, [C, D, F, E])

    def test_every_step_can_swap_so_a_note_can_keep_moving(self):
        self.assertEqual(swap([1], [C, D, E, F]).notes, [D, E, F, C])

    def test_half_swaps_about_half_the_time(self):
        swapped = sum(swap([0.5], [C, D], seed=seed).notes == [D, C] for seed in range(400))
        self.assertTrue(150 < swapped < 250, swapped)

    def test_keeps_exactly_the_same_notes(self):
        notes = [C, D, E, F, G]
        result = swap([0.5], notes, seed=1).notes
        self.assertEqual(Counter(result), Counter(notes))

    def test_last_note_has_nothing_to_swap_with(self):
        self.assertEqual(swap([1], [C]).notes, [C])
        self.assertEqual(swap([1], []).notes, [])

    def test_extra_probabilities_are_ignored(self):
        self.assertEqual(swap([1, 0, 0, 0, 0], [C, D]).notes, [D, C])

    def test_notes_keep_their_own_lengths(self):
        long = Note('C', 4, 1)
        self.assertEqual(swap([1], [long, D]).notes, [D, long])


class TestRests(unittest.TestCase):

    def test_rests_stay_where_they_are(self):
        result = swap([1], [C, Rest(0.5), D, Rest(1), E]).notes
        self.assertEqual(result, [D, Rest(0.5), E, Rest(1), C])

    def test_neighbor_is_the_next_note_past_any_rests(self):
        result = swap([1], [C, Rest(0.5), Rest(1), D]).notes
        self.assertEqual(result, [D, Rest(0.5), Rest(1), C])

    def test_rests_do_not_use_up_a_probability(self):
        result = swap([1, 0], [C, Rest(0.5), D, E, F]).notes
        self.assertEqual(result, [D, Rest(0.5), C, F, E])

    def test_rests_at_the_start_and_end_stay(self):
        result = swap([1], [Rest(1), C, D, Rest(0.5)]).notes
        self.assertEqual(result, [Rest(1), D, C, Rest(0.5)])

    def test_clip_of_only_rests_stays_the_same(self):
        self.assertEqual(swap([1], [Rest(1), Rest(0.5)]).notes, [Rest(1), Rest(0.5)])

    def test_same_lengths_keep_the_rhythm(self):
        notes = [C, Rest(0.5), D, E]
        before = [type(position) for position in notes]
        after = [type(position) for position in swap([1], notes).notes]
        self.assertEqual(after, before)


class TestOtherPositions(unittest.TestCase):

    def test_chords_swap_as_one_note(self):
        chord = C.to_chord(ChordType.MAJOR)
        self.assertEqual(swap([1], [chord, D]).notes, [D, chord])

    def test_degrees_stay_degrees(self):
        self.assertEqual(swap([1], [Degree(1), Degree(2)]).notes, [Degree(2), Degree(1)])

    def test_needs_no_lengths_when_it_runs(self):
        result = swap([1], [1, 'C4'])
        self.assertEqual(result.notes, [Note('C', 4), Degree(1)])


class TestSeed(unittest.TestCase):

    def test_same_seed_gives_the_same_result(self):
        generator = MixUp2([0.5], seed=1)
        notes = [C, D, E, F, G] * 4
        self.assertEqual(
            generator.generate(Clip(notes=notes)).notes,
            generator.generate(Clip(notes=notes)).notes,
        )

    def test_different_seeds_can_give_different_results(self):
        notes = [C, D, E, F, G] * 4
        results = {tuple(swap([0.5], notes, seed=seed).notes) for seed in range(10)}
        self.assertGreater(len(results), 1)

    def test_no_seed_still_works(self):
        notes = [C, D, E, F, G]
        self.assertEqual(Counter(swap([0.5], notes).notes), Counter(notes))


class TestClipDetails(unittest.TestCase):

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=[C, D], scale=SCALE, length=2, note_length=0.5)
        result = MixUp2([1]).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, SCALE)
        self.assertEqual(result.length, 2)
        self.assertEqual(result.note_length, 0.5)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=[C, D])
        MixUp2([1]).generate(original)
        self.assertEqual(original.notes, [C, D])


class TestMixUp2Fields(unittest.TestCase):

    def test_probabilities_are_required(self):
        with self.assertRaises(TypeError):
            MixUp2()

    def test_takes_a_list_or_tuple(self):
        self.assertEqual(MixUp2([0, 1]).probabilities, [0, 1])
        self.assertEqual(MixUp2((0, 1)).probabilities, (0, 1))

    def test_rejects_invalid_values(self):
        invalid = [[], (), None, 0.5, '0.5', [-0.1], [1.1], [2], ['1'], [None], [True], [0, 2]]
        for probabilities in invalid:
            with self.subTest(probabilities=probabilities):
                with self.assertRaises(ValueError):
                    MixUp2(probabilities)
        for seed in ['1', 1.5, True]:
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    MixUp2([1], seed=seed)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', [C]]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MixUp2([1]).generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = MixUp2([1])
        generator.probabilities = [0]
        generator.seed = 3
        self.assertEqual((generator.probabilities, generator.seed), ([0], 3))
        with self.assertRaises(ValueError):
            generator.probabilities = []
        self.assertEqual(generator.probabilities, [0])


if __name__ == '__main__':
    unittest.main()
