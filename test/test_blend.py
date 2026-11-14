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

import unittest
from fractions import Fraction

from llamatron.generators.base import ClipGenerator
from llamatron.generators.blend import Blend, BlendMode
from llamatron.music.note import Degree, Note, NoteName, Rest
from llamatron.music.scale import Scale, ScaleType
from llamatron.grid.clip import Clip

C_MAJOR = Scale(root=Note(name='C', octave_number=4), typ=ScaleType.MAJOR)
A_MINOR = Scale(root=Note(name='A', octave_number=3), typ=ScaleType.MINOR)
WHOLE = 1

# Names the tests give to their own things, and other values they use.
A = 'A'
RIFF = 'Riff'
C = 'C'
CLIP = 'clip'
NAN = 'nan'
NOT_A_MODE = 'LEFT'


def bar(*names):
    """Return a clip with one whole note per measure."""
    return Clip(notes=[Note(name=name, octave_number=4, length=WHOLE) for name in names], scale=C_MAJOR)


SOURCE = bar('C', 'C', 'C', 'C', 'C', 'C', 'C', 'C')
TARGET = bar('A', 'A', 'A', 'A', 'A', 'A', 'A', 'A')


def from_target(result):
    """Return, measure by measure, whether a result plays the target."""
    now = Fraction(0)
    owners = {}
    for position in result.get_notes():
        length = Fraction(position.get_length()).limit_denominator(1_000_000)
        if isinstance(position, Note):
            for measure in range(int(now), int(now + length)):
                owners[measure] = position.get_name() == A
        now += length
    return [owners[measure] for measure in sorted(owners)]


class TestAmounts(unittest.TestCase):

    def test_in_between_plays_some_of_each(self):
        owners = from_target(Blend(target=TARGET, amount=50).generate(SOURCE))
        self.assertIn(True, owners)
        self.assertIn(False, owners)

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Blend(target=TARGET, amount=50), ClipGenerator)

    def test_zero_plays_this_clip(self):
        self.assertEqual(from_target(Blend(target=TARGET, amount=0).generate(SOURCE)), [False] * 8)

    def test_one_hundred_plays_the_target(self):
        self.assertEqual(from_target(Blend(target=TARGET, amount=100).generate(SOURCE)), [True] * 8)


class TestClips(unittest.TestCase):

    def test_rests_are_blended_too(self):
        source = Clip(notes=[Rest(1)])
        target = Clip(notes=[Note(name=NoteName.A, octave_number=4, length=1)])
        self.assertEqual(Blend(target=target, amount=100).generate(source).get_notes(), [Note(name=NoteName.A, octave_number=4, length=1)])
        self.assertEqual(Blend(target=target, amount=0).generate(source).get_notes(), [Rest(1)])

    def test_rejects_clips_of_different_lengths(self):
        with self.assertRaises(ValueError):
            Blend(target=bar(A), amount=50).generate(bar(C, C))

    def test_degrees_use_their_own_clip_scale(self):
        source = Clip(notes=[Degree(number=1, length=1)], scale=C_MAJOR)
        target = Clip(notes=[Degree(number=1, length=1)], scale=A_MINOR)
        self.assertEqual(Blend(target=target, amount=0).generate(source).get_notes(), [Note(name=NoteName.C, octave_number=4, length=1)])
        self.assertEqual(Blend(target=target, amount=100).generate(source).get_notes(), [Note(name=NoteName.A, octave_number=3, length=1)])

    def test_degrees_need_a_scale(self):
        with self.assertRaises(ValueError):
            Blend(target=TARGET, amount=0).generate(Clip(notes=[Degree(number=1, length=8)]))

    def test_empty_clips_stay_empty(self):
        self.assertEqual(Blend(target=Clip(), amount=50).generate(Clip()).get_notes(), [])

    def test_keeps_details_and_leaves_the_originals_alone(self):
        original = Clip(name=RIFF, notes=[Note(name=NoteName.C, octave_number=4, length=1)], scale=C_MAJOR)
        target = Clip(notes=[Note(name=NoteName.A, octave_number=4, length=1)], scale=A_MINOR)
        result = Blend(target=target, amount=100).generate(original)
        self.assertEqual(result.get_name(), RIFF)
        self.assertIs(result.get_scale(), C_MAJOR)
        self.assertEqual(original.get_notes(), [Note(name=NoteName.C, octave_number=4, length=1)])
        self.assertEqual(target.get_notes(), [Note(name=NoteName.A, octave_number=4, length=1)])


MELODY = Clip(notes=[
    Note(name='C', octave_number=4, length=0.25), Note(name='D', octave_number=4, length=0.25), Note(name='E', octave_number=4, length=0.25), Note(name='F', octave_number=4, length=0.25),
    Note(name='G', octave_number=4, length=0.25), Note(name='A', octave_number=4, length=0.25), Note(name='G', octave_number=4, length=0.25), Note(name='F', octave_number=4, length=0.25),
], scale=C_MAJOR)
GOAL = Clip(notes=[Note(name='C', octave_number=5, length=0.5), Note(name='A', octave_number=4, length=0.5), Note(name='F', octave_number=5, length=0.5), Note(name='D', octave_number=5, length=0.5)], scale=C_MAJOR)


def pitches_of(clip):
    return [position.get_midi_number() for position in clip.get_notes() if isinstance(position, Note)]


SOURCE_PITCHES = [48, 50, 52, 53, 55, 57, 59, 60]
GOAL_PITCHES = [72, 74, 76, 77, 79, 81, 83, 84]
EIGHTHS = Clip(notes=[Note(name=name, octave_number=octave, length=0.125) for name, octave in [('C', 4), ('D', 4), ('E', 4), ('F', 4), ('G', 4), ('A', 4), ('B', 4), ('C', 5)]], scale=C_MAJOR)
GOAL_EIGHTHS = Clip(notes=[Note(name=name, octave_number=octave, length=0.125) for name, octave in [('C', 6), ('D', 6), ('E', 6), ('F', 6), ('G', 6), ('A', 6), ('B', 6), ('C', 7)]], scale=C_MAJOR)


class TestSweeps(unittest.TestCase):

    def blend(self, *, amount, mode):
        return pitches_of(Blend(target=GOAL_EIGHTHS, amount=amount, mode=mode).generate(EIGHTHS))

    def test_zero_keeps_the_clip_and_one_hundred_plays_the_target(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            with self.subTest(mode=mode):
                self.assertEqual(self.blend(amount=0, mode=mode), SOURCE_PITCHES)
                self.assertEqual(self.blend(amount=100, mode=mode), GOAL_PITCHES)

    def test_left_comes_in_from_the_start(self):
        self.assertEqual(self.blend(amount=25, mode=BlendMode.LEFT), GOAL_PITCHES[:2] + SOURCE_PITCHES[2:])

    def test_right_comes_in_from_the_end(self):
        self.assertEqual(self.blend(amount=25, mode=BlendMode.RIGHT), SOURCE_PITCHES[:6] + GOAL_PITCHES[6:])

    def test_middle_grows_from_the_center(self):
        self.assertEqual(
            self.blend(amount=50, mode=BlendMode.MIDDLE),
            SOURCE_PITCHES[:2] + GOAL_PITCHES[2:6] + SOURCE_PITCHES[6:],
        )

    def test_a_rising_amount_only_ever_adds(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            changed = [
                {i for i, (a, b) in enumerate(zip(self.blend(amount=amount, mode=mode), SOURCE_PITCHES)) if a != b}
                for amount in range(0, 101, 10)
            ]
            for before, after in zip(changed, changed[1:]):
                with self.subTest(mode=mode):
                    self.assertLessEqual(before, after)

    def test_keeps_the_total_length(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            for amount in [0, 13, 50, 87, 100]:
                result = Blend(target=GOAL_EIGHTHS, amount=amount, mode=mode).generate(EIGHTHS)
                with self.subTest(mode=mode, amount=amount):
                    self.assertEqual(result.total_length(), 1)

    def test_source_notes_are_not_cut(self):
        source = Clip(notes=[Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.D, octave_number=4, length=0.5)], scale=C_MAJOR)
        target = Clip(notes=[Note(name=NoteName.A, octave_number=4, length=1)], scale=C_MAJOR)
        result = Blend(target=target, amount=40, mode=BlendMode.LEFT).generate(source)
        self.assertEqual(result.get_notes(), [Note(name=NoteName.A, octave_number=4, length=0.5), Note(name=NoteName.D, octave_number=4, length=0.5)])


class TestModes(unittest.TestCase):

    def test_every_mode_keeps_the_total_length_and_clip_details(self):
        original = Clip(name=RIFF, notes=list(MELODY.get_notes()), scale=C_MAJOR)
        for mode in BlendMode:
            with self.subTest(mode=mode):
                result = Blend(target=GOAL, amount=50, mode=mode).generate(original)
                self.assertEqual(result.total_length(), 2)
                self.assertEqual(result.get_name(), RIFF)
                self.assertIs(result.get_scale(), C_MAJOR)
                self.assertEqual(original.get_notes(), MELODY.get_notes())

    def test_every_mode_respects_a_set_length(self):
        source = Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)], scale=C_MAJOR, length=2)
        target = Clip(notes=[Note(name=NoteName.A, octave_number=4, length=2)], scale=C_MAJOR)
        for mode in BlendMode:
            with self.subTest(mode=mode):
                self.assertEqual(Blend(target=target, amount=100, mode=mode).generate(source).total_length(), 2)


class TestFields(unittest.TestCase):

    def test_rejects_invalid_values(self):
        for target in [None, CLIP, Note(name=NoteName.C, octave_number=4, length=1)]:
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    Blend(target=target, amount=50)
        for amount in [-1, 101, '50', None, True, float(NAN)]:
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    Blend(target=TARGET, amount=amount)
        with self.assertRaises(ValueError):
            Blend(target=TARGET, amount=50, mode=NOT_A_MODE)

    def test_rejects_anything_but_a_clip(self):
        with self.assertRaises(ValueError):
            Blend(target=TARGET, amount=50).generate([Note(name=NoteName.C, octave_number=4, length=1)])

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Blend(target=TARGET, amount=50)
        generator.set_amount(75)
        self.assertEqual(generator.get_amount(), 75)
        with self.assertRaises(ValueError):
            generator.set_amount(200)
        self.assertEqual(generator.get_amount(), 75)


if __name__ == '__main__':
    unittest.main()
