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
from src.note import Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

C4 = Note('C', 4, 0.25)
SCALE = Scale(Note('C', 0, 0.25), ScaleType.MAJOR)
NOTES = Scale(C4, ScaleType.CHROMATIC).count(12)


class TestMixUp(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(MixUp(1), ClipGenerator)

    def test_one_swap_changes_exactly_two_positions(self):
        for seed in range(20):
            with self.subTest(seed=seed):
                result = MixUp(1, seed=seed).generate(Clip(notes=NOTES)).notes
                moved = [i for i in range(len(NOTES)) if result[i] != NOTES[i]]
                self.assertEqual(len(moved), 2)
                first, second = moved
                self.assertEqual(result[first], NOTES[second])
                self.assertEqual(result[second], NOTES[first])

    def test_zero_swaps_changes_nothing(self):
        self.assertEqual(MixUp(0).generate(Clip(notes=NOTES)).notes, NOTES)

    def test_keeps_exactly_the_same_notes(self):
        result = MixUp(50, seed=1).generate(Clip(notes=NOTES)).notes
        self.assertEqual(Counter(result), Counter(NOTES))
        self.assertNotEqual(result, NOTES)

    def test_can_swap_rests_and_chords(self):
        chord = C4.to_chord(ChordType.MAJOR)
        notes = [C4, Rest(0.25), chord, Note('D', 4, 0.25)]
        results = [
            MixUp(3, seed=seed).generate(Clip(notes=notes)).notes
            for seed in range(30)
        ]
        for result in results:
            self.assertEqual(Counter(result), Counter(notes))
        self.assertGreater(len({result.index(Rest(0.25)) for result in results}), 1)
        self.assertGreater(len({result.index(chord) for result in results}), 1)

    def test_total_duration_stays_the_same(self):
        notes = [Note('C', 4, 1), Rest(0.5), Note('D', 4, 0.25)]
        result = MixUp(5, seed=1).generate(Clip(notes=notes)).notes
        self.assertEqual(sum(position.length for position in result), 1.75)

    def test_clips_too_short_to_swap_stay_the_same(self):
        self.assertEqual(MixUp(5).generate(Clip()).notes, [])
        self.assertEqual(MixUp(5).generate(Clip(notes=[C4])).notes, [C4])

    def test_keeps_the_clip_details(self):
        original = Clip('Riff', notes=NOTES, scale=SCALE, length=2)
        result = MixUp(1).generate(original)
        self.assertIsNot(result, original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, SCALE)
        self.assertEqual(result.length, 2)

    def test_leaves_the_original_unchanged(self):
        original = Clip(notes=NOTES)
        MixUp(10, seed=1).generate(original)
        self.assertEqual(original.notes, NOTES)


class TestMixUpSeed(unittest.TestCase):

    def test_same_seed_gives_the_same_result_every_time(self):
        mix_up = MixUp(5, seed=1)
        self.assertEqual(
            mix_up.generate(Clip(notes=NOTES)).notes,
            mix_up.generate(Clip(notes=NOTES)).notes,
        )

    def test_different_seeds_give_different_results(self):
        self.assertNotEqual(
            MixUp(5, seed=1).generate(Clip(notes=NOTES)).notes,
            MixUp(5, seed=2).generate(Clip(notes=NOTES)).notes,
        )

    def test_no_seed_still_works(self):
        result = MixUp(5).generate(Clip(notes=NOTES)).notes
        self.assertEqual(Counter(result), Counter(NOTES))


class TestMixUpFields(unittest.TestCase):

    def test_swaps_is_required(self):
        with self.assertRaises(TypeError):
            MixUp()

    def test_rejects_invalid_values(self):
        for swaps in [-1, 1.5, 2.0, '2', None, True]:
            with self.subTest(swaps=swaps):
                with self.assertRaises(ValueError):
                    MixUp(swaps)
        for seed in ['1', 1.5, True]:
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    MixUp(1, seed=seed)

    def test_rejects_anything_but_a_clip(self):
        for value in [None, 'clip', NOTES]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MixUp(1).generate(value)

    def test_fields_can_be_edited_and_are_validated(self):
        mix_up = MixUp(1)
        mix_up.swaps = 2
        mix_up.seed = 3
        self.assertEqual((mix_up.swaps, mix_up.seed), (2, 3))
        with self.assertRaises(ValueError):
            mix_up.swaps = -1
        self.assertEqual(mix_up.swaps, 2)


if __name__ == '__main__':
    unittest.main()
