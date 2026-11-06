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
from fractions import Fraction

from llamatron.generators.base import ClipGenerator
from llamatron.generators.blend import Blend, BlendMode
from llamatron.note import Degree, Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.clip_grid import Clip

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)
WHOLE = 1


def bar(*names):
    """Return a clip with one whole note per measure."""
    return Clip(notes=[Note(name, 4, WHOLE) for name in names], scale=C_MAJOR)


SOURCE = bar('C', 'C', 'C', 'C', 'C', 'C', 'C', 'C')
TARGET = bar('A', 'A', 'A', 'A', 'A', 'A', 'A', 'A')


def from_target(result):
    """Return, measure by measure, whether a result plays the target."""
    now, owners = Fraction(0), {}
    for position in result.notes:
        length = Fraction(position.length).limit_denominator(1_000_000)
        if isinstance(position, Note):
            for measure in range(int(now), int(now + length)):
                owners[measure] = position.name == 'A'
        now += length
    return [owners[measure] for measure in sorted(owners)]


class TestAmounts(unittest.TestCase):

    def test_in_between_plays_some_of_each(self):
        owners = from_target(Blend(TARGET, 50).generate(SOURCE))
        self.assertIn(True, owners)
        self.assertIn(False, owners)

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Blend(TARGET, 50), ClipGenerator)

    def test_zero_plays_this_clip(self):
        self.assertEqual(from_target(Blend(TARGET, 0).generate(SOURCE)), [False] * 8)

    def test_one_hundred_plays_the_target(self):
        self.assertEqual(from_target(Blend(TARGET, 100).generate(SOURCE)), [True] * 8)


class TestClips(unittest.TestCase):

    def test_rests_are_blended_too(self):
        source = Clip(notes=[Rest(1)])
        target = Clip(notes=[Note('A', 4, 1)])
        self.assertEqual(Blend(target, 100).generate(source).notes, [Note('A', 4, 1)])
        self.assertEqual(Blend(target, 0).generate(source).notes, [Rest(1)])

    def test_rejects_clips_of_different_lengths(self):
        with self.assertRaises(ValueError):
            Blend(bar('A'), 50).generate(bar('C', 'C'))

    def test_degrees_use_their_own_clip_scale(self):
        source = Clip(notes=[Degree(1, 1)], scale=C_MAJOR)
        target = Clip(notes=[Degree(1, 1)], scale=A_MINOR)
        self.assertEqual(Blend(target, 0).generate(source).notes, [Note('C', 4, 1)])
        self.assertEqual(Blend(target, 100).generate(source).notes, [Note('A', 3, 1)])

    def test_degrees_need_a_scale(self):
        with self.assertRaises(ValueError):
            Blend(TARGET, 0).generate(Clip(notes=[Degree(1, 8)]))

    def test_empty_clips_stay_empty(self):
        self.assertEqual(Blend(Clip(), 50).generate(Clip()).notes, [])

    def test_keeps_details_and_leaves_the_originals_alone(self):
        original = Clip('Riff', notes=[Note('C', 4, 1)], scale=C_MAJOR)
        target = Clip(notes=[Note('A', 4, 1)], scale=A_MINOR)
        result = Blend(target, 100).generate(original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(original.notes, [Note('C', 4, 1)])
        self.assertEqual(target.notes, [Note('A', 4, 1)])


MELODY = Clip(notes=[
    Note('C', 4, 0.25), Note('D', 4, 0.25), Note('E', 4, 0.25), Note('F', 4, 0.25),
    Note('G', 4, 0.25), Note('A', 4, 0.25), Note('G', 4, 0.25), Note('F', 4, 0.25),
], scale=C_MAJOR)
GOAL = Clip(notes=[Note('C', 5, 0.5), Note('A', 4, 0.5), Note('F', 5, 0.5), Note('D', 5, 0.5)], scale=C_MAJOR)


def pitches_of(clip):
    return [position.midi_number for position in clip.notes if isinstance(position, Note)]


SOURCE_PITCHES = [48, 50, 52, 53, 55, 57, 59, 60]
GOAL_PITCHES = [72, 74, 76, 77, 79, 81, 83, 84]
EIGHTHS = Clip(notes=[Note(*n, 0.125) for n in [('C', 4), ('D', 4), ('E', 4), ('F', 4), ('G', 4), ('A', 4), ('B', 4), ('C', 5)]], scale=C_MAJOR)
GOAL_EIGHTHS = Clip(notes=[Note(*n, 0.125) for n in [('C', 6), ('D', 6), ('E', 6), ('F', 6), ('G', 6), ('A', 6), ('B', 6), ('C', 7)]], scale=C_MAJOR)


class TestSweeps(unittest.TestCase):

    def blend(self, amount, mode):
        return pitches_of(Blend(GOAL_EIGHTHS, amount, mode=mode).generate(EIGHTHS))

    def test_zero_keeps_the_clip_and_one_hundred_plays_the_target(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            with self.subTest(mode=mode):
                self.assertEqual(self.blend(0, mode), SOURCE_PITCHES)
                self.assertEqual(self.blend(100, mode), GOAL_PITCHES)

    def test_left_comes_in_from_the_start(self):
        self.assertEqual(self.blend(25, BlendMode.LEFT), GOAL_PITCHES[:2] + SOURCE_PITCHES[2:])

    def test_right_comes_in_from_the_end(self):
        self.assertEqual(self.blend(25, BlendMode.RIGHT), SOURCE_PITCHES[:6] + GOAL_PITCHES[6:])

    def test_middle_grows_from_the_center(self):
        self.assertEqual(
            self.blend(50, BlendMode.MIDDLE),
            SOURCE_PITCHES[:2] + GOAL_PITCHES[2:6] + SOURCE_PITCHES[6:],
        )

    def test_a_rising_amount_only_ever_adds(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            changed = [
                {i for i, (a, b) in enumerate(zip(self.blend(amount, mode), SOURCE_PITCHES)) if a != b}
                for amount in range(0, 101, 10)
            ]
            for before, after in zip(changed, changed[1:]):
                with self.subTest(mode=mode):
                    self.assertLessEqual(before, after)

    def test_keeps_the_total_length(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            for amount in [0, 13, 50, 87, 100]:
                result = Blend(GOAL_EIGHTHS, amount, mode=mode).generate(EIGHTHS)
                with self.subTest(mode=mode, amount=amount):
                    self.assertEqual(result.total_length(), 1)

    def test_source_notes_are_not_cut(self):
        source = Clip(notes=[Note('C', 4, 0.5), Note('D', 4, 0.5)], scale=C_MAJOR)
        target = Clip(notes=[Note('A', 4, 1)], scale=C_MAJOR)
        result = Blend(target, 40, mode=BlendMode.LEFT).generate(source)
        self.assertEqual(result.notes, [Note('A', 4, 0.5), Note('D', 4, 0.5)])


class TestModes(unittest.TestCase):

    def test_every_mode_keeps_the_total_length_and_clip_details(self):
        original = Clip('Riff', notes=list(MELODY.notes), scale=C_MAJOR)
        for mode in BlendMode:
            with self.subTest(mode=mode):
                result = Blend(GOAL, 50, mode=mode).generate(original)
                self.assertEqual(result.total_length(), 2)
                self.assertEqual(result.name, 'Riff')
                self.assertIs(result.scale, C_MAJOR)
                self.assertEqual(original.notes, MELODY.notes)

    def test_every_mode_respects_a_set_length(self):
        source = Clip(notes=[Note('C', 4, 1)], scale=C_MAJOR, length=2)
        target = Clip(notes=[Note('A', 4, 2)], scale=C_MAJOR)
        for mode in BlendMode:
            with self.subTest(mode=mode):
                self.assertEqual(Blend(target, 100, mode=mode).generate(source).total_length(), 2)


class TestFields(unittest.TestCase):

    def test_rejects_invalid_values(self):
        for target in [None, 'clip', Note('C', 4, 1)]:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    Blend(target, 50)
        for amount in [-1, 101, '50', None, True, float('nan')]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    Blend(TARGET, amount)
        with self.assertRaises(ValueError):
            Blend(TARGET, 50, mode='LEFT')

    def test_rejects_anything_but_a_clip(self):
        with self.assertRaises(ValueError):
            Blend(TARGET, 50).generate([Note('C', 4, 1)])

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Blend(TARGET, 50)
        generator.amount = 75
        self.assertEqual(generator.amount, 75)
        with self.assertRaises(ValueError):
            generator.amount = 200
        self.assertEqual(generator.amount, 75)


if __name__ == '__main__':
    unittest.main()
