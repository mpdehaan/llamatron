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
from fractions import Fraction

from src.chord import ChordType
from src.generators.base import ClipGenerator
from src.generators.blend import Blend, BlendMode
from src.legacy.generators.stretch import Stretch
from src.note import Degree, Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

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

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Blend(TARGET, 50), ClipGenerator)

    def test_zero_plays_this_clip(self):
        self.assertEqual(from_target(Blend(TARGET, 0).generate(SOURCE)), [False] * 8)

    def test_one_hundred_plays_the_target(self):
        self.assertEqual(from_target(Blend(TARGET, 100).generate(SOURCE)), [True] * 8)

    def test_in_between_plays_some_of_each(self):
        owners = from_target(Blend(TARGET, 50, seed=1).generate(SOURCE))
        self.assertIn(True, owners)
        self.assertIn(False, owners)

    def test_the_amount_sets_the_share_of_slices_that_change(self):
        for seed in range(20):
            for amount, expected in [(25, 2), (50, 4), (75, 6)]:
                with self.subTest(seed=seed, amount=amount):
                    owners = from_target(Blend(TARGET, amount, seed=seed).generate(SOURCE))
                    self.assertEqual(sum(owners), expected)

    def test_every_step_of_a_morph_changes_something(self):
        for seed in range(30):
            steps = [
                from_target(Blend(TARGET, amount, seed=seed).generate(SOURCE))
                for amount in (0, 25, 50, 75, 100)
            ]
            for before, after in zip(steps, steps[1:]):
                with self.subTest(seed=seed):
                    self.assertNotEqual(after, before)

    def test_a_changed_slice_stays_changed_as_the_amount_rises(self):
        for seed in range(30):
            previous = [False] * 8
            for amount in range(0, 101, 5):
                owners = from_target(Blend(TARGET, amount, seed=seed).generate(SOURCE))
                with self.subTest(seed=seed, amount=amount):
                    self.assertTrue(all(now or not before for before, now in zip(previous, owners)))
                previous = owners

    def test_same_seed_gives_the_same_result(self):
        first = Blend(TARGET, 50, seed=3).generate(SOURCE)
        second = Blend(TARGET, 50, seed=3).generate(SOURCE)
        self.assertEqual(first.notes, second.notes)

    def test_different_seeds_can_choose_different_slices(self):
        results = {tuple(from_target(Blend(TARGET, 50, seed=seed).generate(SOURCE))) for seed in range(10)}
        self.assertGreater(len(results), 1)

    def test_melody_and_chords_change_together_with_the_same_seed(self):
        melody = from_target(Blend(TARGET, 50, seed=4).generate(SOURCE))
        chords = from_target(Blend(TARGET, 50, seed=4).generate(SOURCE))
        self.assertEqual(melody, chords)


class TestSlices(unittest.TestCase):

    def test_slice_length_sets_the_slices(self):
        slices = Blend(TARGET, 50, slice_length=2).slices(Fraction(8))
        self.assertEqual(slices, [(0, 2), (2, 4), (4, 6), (6, 8)])

    def test_last_slice_can_be_shorter(self):
        slices = Blend(TARGET, 50, slice_length=3).slices(Fraction(8))
        self.assertEqual(slices, [(0, 3), (3, 6), (6, 8)])

    def test_points_set_the_slices(self):
        slices = Blend(TARGET, 50, points=[5, 2]).slices(Fraction(8))
        self.assertEqual(slices, [(0, 2), (2, 5), (5, 8)])

    def test_points_past_either_end_and_repeats_are_ignored(self):
        slices = Blend(TARGET, 50, points=[0, 2, 2, 8, 20]).slices(Fraction(8))
        self.assertEqual(slices, [(0, 2), (2, 8)])

    def test_no_points_inside_gives_one_slice(self):
        self.assertEqual(Blend(TARGET, 50, points=[]).slices(Fraction(8)), [(0, 8)])

    def test_every_slice_plays_only_one_clip(self):
        for seed in range(10):
            result = Blend(TARGET, 50, points=[2, 5], seed=seed).generate(SOURCE)
            owners = from_target(result)
            with self.subTest(seed=seed):
                self.assertEqual(len(set(owners[:2])), 1)
                self.assertEqual(len(set(owners[2:5])), 1)
                self.assertEqual(len(set(owners[5:])), 1)

    def test_neighboring_slices_from_one_clip_do_not_cut_a_note(self):
        source = Clip(notes=[Note('C', 4, 8)], scale=C_MAJOR)
        self.assertEqual(Blend(TARGET, 0).generate(source).notes, [Note('C', 4, 8)])

    def test_a_note_crossing_a_change_is_cut(self):
        source = Clip(notes=[Note('C', 4, 2)])
        target = Clip(notes=[Note('A', 4, 2)])
        for seed in range(30):
            result = Blend(target, 50, slice_length=1, seed=seed).generate(source)
            self.assertEqual(sum(note.length for note in result.notes), 2)


class TestClips(unittest.TestCase):

    def test_keeps_the_total_length(self):
        for amount in [0, 30, 70, 100]:
            with self.subTest(amount=amount):
                result = Blend(TARGET, amount, seed=2).generate(SOURCE)
                self.assertEqual(result.total_length(), 8)

    def test_rests_are_blended_too(self):
        source = Clip(notes=[Rest(1)])
        target = Clip(notes=[Note('A', 4, 1)])
        self.assertEqual(Blend(target, 100).generate(source).notes, [Note('A', 4, 1)])
        self.assertEqual(Blend(target, 0).generate(source).notes, [Rest(1)])

    def test_rejects_clips_of_different_lengths(self):
        with self.assertRaises(ValueError):
            Blend(bar('A'), 50).generate(bar('C', 'C'))

    def test_stretch_makes_lengths_match(self):
        target = Stretch(Fraction(4, 3)).generate(Clip(notes=[Note('A', 4, Fraction(3, 4))]))
        result = Blend(target, 100).generate(bar('C'))
        self.assertEqual(result.notes, [Note('A', 4, 1)])

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
EIGHTHS = Clip(notes=[Note.from_midi_number(p, 0.125) for p in SOURCE_PITCHES], scale=C_MAJOR)
GOAL_EIGHTHS = Clip(notes=[Note.from_midi_number(p, 0.125) for p in GOAL_PITCHES], scale=C_MAJOR)


class TestStrongBeats(unittest.TestCase):

    def blend(self, amount, **options):
        return Blend(GOAL, amount, mode=BlendMode.STRONG_BEATS, **options).generate(MELODY)

    def test_zero_keeps_the_clip(self):
        self.assertEqual(self.blend(0).notes, MELODY.notes)

    def test_one_hundred_changes_strong_beats_and_nothing_between(self):
        self.assertEqual(pitches_of(self.blend(100)), [60, 50, 57, 53, 65, 57, 62, 53])

    def test_keeps_the_rhythm(self):
        result = self.blend(100)
        self.assertEqual([p.length for p in result.notes], [p.length for p in MELODY.notes])

    def test_the_amount_sets_the_share_of_strong_beats(self):
        for amount, expected in [(25, 1), (50, 2), (75, 3)]:
            for seed in range(10):
                result = pitches_of(self.blend(amount, seed=seed))
                changed = sum(a != b for a, b in zip(result[::2], pitches_of(MELODY)[::2]))
                with self.subTest(amount=amount, seed=seed):
                    self.assertEqual(changed, expected)

    def test_a_changed_beat_stays_changed_as_the_amount_rises(self):
        for seed in range(20):
            previous = pitches_of(MELODY)
            for amount in [0, 25, 50, 75, 100]:
                now = pitches_of(self.blend(amount, seed=seed))
                for before, after, original in zip(previous, now, pitches_of(MELODY)):
                    with self.subTest(seed=seed, amount=amount):
                        self.assertTrue(before == original or after == before)
                previous = now

    def test_strong_beat_can_change(self):
        result = pitches_of(self.blend(100, strong_beat=1))
        self.assertEqual(result, [60, 50, 52, 53, 65, 57, 55, 53])

    def test_rests_stay_and_a_silent_target_changes_nothing(self):
        source = Clip(notes=[Rest(0.5), Note('C', 4, 0.5)], scale=C_MAJOR)
        target = Clip(notes=[Rest(1)], scale=C_MAJOR)
        self.assertEqual(Blend(target, 100, mode=BlendMode.STRONG_BEATS).generate(source).notes, source.notes)
        with_notes = Clip(notes=[Note('A', 4, 1)], scale=C_MAJOR)
        result = Blend(with_notes, 100, mode=BlendMode.STRONG_BEATS).generate(source)
        self.assertEqual(result.notes, [Rest(0.5), Note('A', 4, 0.5)])

    def test_chords_move_together(self):
        chord = Note('C', 4, 1).to_chord(ChordType.MAJOR)
        target = Clip(notes=[Note('A', 4, 1)], scale=C_MAJOR)
        result = Blend(target, 100, mode=BlendMode.STRONG_BEATS).generate(Clip(notes=[chord], scale=C_MAJOR))
        self.assertEqual(
            sorted(note.midi_number for note in result.notes[0].notes),
            [50, 54, 57],
        )

    def test_needs_clips_of_the_same_length(self):
        with self.assertRaises(ValueError):
            Blend(bar('A'), 50, mode=BlendMode.STRONG_BEATS).generate(bar('C', 'C'))


class TestContour(unittest.TestCase):

    def blend(self, amount, **options):
        return Blend(GOAL, amount, mode=BlendMode.CONTOUR, **options).generate(MELODY)

    def test_zero_keeps_the_clip(self):
        self.assertEqual(self.blend(0).notes, MELODY.notes)

    def test_one_hundred_plays_the_target_in_this_rhythm(self):
        self.assertEqual(pitches_of(self.blend(100)), [60, 60, 57, 57, 65, 65, 62, 62])
        self.assertEqual([p.length for p in self.blend(100).notes], [p.length for p in MELODY.notes])

    def test_fifty_is_halfway_along_the_scale(self):
        # C4 to C5 is seven scale notes, so halfway rounds to the fourth or fifth note of the scale.
        self.assertIn(pitches_of(self.blend(50))[0], [53, 55])

    def test_every_note_stays_in_the_scale(self):
        allowed = {0, 2, 4, 5, 7, 9, 11}
        for amount in range(0, 101, 10):
            with self.subTest(amount=amount):
                self.assertLessEqual({pitch % 12 for pitch in pitches_of(self.blend(amount))}, allowed)

    def test_every_note_moves_steadily_towards_the_goal(self):
        goal = [60, 60, 57, 57, 65, 65, 62, 62]
        for index, (start, end) in enumerate(zip(pitches_of(MELODY), goal)):
            path = [pitches_of(self.blend(amount))[index] for amount in range(0, 101, 10)]
            with self.subTest(index=index):
                self.assertEqual(path, sorted(path, reverse=start > end))

    def test_makes_notes_that_belong_to_neither_clip(self):
        source, target = set(pitches_of(MELODY)), set(pitches_of(GOAL))
        self.assertTrue(set(pitches_of(self.blend(50))) - source - target)

    def test_does_not_depend_on_the_seed(self):
        self.assertEqual(self.blend(50, seed=1).notes, self.blend(50, seed=2).notes)

    def test_uses_the_scale_given_or_else_the_clip_scale(self):
        pentatonic = Scale(Note('C', 4), ScaleType.MAJOR_PENTATONIC)
        allowed = {0, 2, 4, 7, 9}
        result = pitches_of(self.blend(50, scale=pentatonic))
        self.assertLessEqual({pitch % 12 for pitch in result}, allowed)

    def test_needs_a_scale(self):
        source = Clip(notes=[Note('C', 4, 1)])
        with self.assertRaises(ValueError):
            Blend(Clip(notes=[Note('A', 4, 1)]), 50, mode=BlendMode.CONTOUR).generate(source)

    def test_rests_stay(self):
        source = Clip(notes=[Rest(0.5), Note('C', 4, 0.5)], scale=C_MAJOR)
        target = Clip(notes=[Note('A', 4, 1)], scale=C_MAJOR)
        result = Blend(target, 100, mode=BlendMode.CONTOUR).generate(source)
        self.assertEqual(result.notes, [Rest(0.5), Note('A', 4, 0.5)])

    def test_silent_target_changes_nothing(self):
        source = Clip(notes=[Note('C', 4, 1)], scale=C_MAJOR)
        self.assertEqual(Blend(Clip(notes=[Rest(1)]), 100, mode=BlendMode.CONTOUR).generate(source).notes, source.notes)

    def test_chords_keep_their_shape(self):
        chord = Note('C', 4, 1).to_chord(ChordType.MAJOR)
        target = Clip(notes=[Note('A', 5, 1)], scale=C_MAJOR)
        result = Blend(target, 100, mode=BlendMode.CONTOUR).generate(Clip(notes=[chord], scale=C_MAJOR))
        pitches = sorted(note.midi_number for note in result.notes[0].notes)
        self.assertEqual([pitches[1] - pitches[0], pitches[2] - pitches[1]], [4, 3])
        self.assertEqual(pitches[2], 69)

    def test_needs_clips_of_the_same_length(self):
        with self.assertRaises(ValueError):
            Blend(bar('A'), 50, mode=BlendMode.CONTOUR).generate(bar('C', 'C'))


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

    def test_does_not_use_chance(self):
        for mode in [BlendMode.LEFT, BlendMode.RIGHT, BlendMode.MIDDLE]:
            first = Blend(GOAL_EIGHTHS, 40, mode=mode, seed=1).generate(EIGHTHS).notes
            second = Blend(GOAL_EIGHTHS, 40, mode=mode, seed=2).generate(EIGHTHS).notes
            with self.subTest(mode=mode):
                self.assertEqual(first, second)

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

    def test_slices_is_the_default(self):
        self.assertIs(Blend(TARGET, 50).mode, BlendMode.SLICES)

    def test_each_mode_gives_a_different_result(self):
        modes = [BlendMode.SLICES, BlendMode.STRONG_BEATS, BlendMode.CONTOUR]
        results = {tuple(Blend(GOAL, 50, mode=mode, seed=1).generate(MELODY).notes) for mode in modes}
        self.assertEqual(len(results), len(modes))

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
        for points in ['2', 2, ['2'], [-1], [float('inf')], [None]]:
            with self.subTest(points=points):
                with self.assertRaises(ValueError):
                    Blend(TARGET, 50, points=points)
        with self.assertRaises(ValueError):
            Blend(TARGET, 50, slice_length=0)
        with self.assertRaises(ValueError):
            Blend(TARGET, 50, seed='1')
        with self.assertRaises(ValueError):
            Blend(TARGET, 50, mode='CONTOUR')
        with self.assertRaises(ValueError):
            Blend(TARGET, 50, strong_beat=0)
        with self.assertRaises(ValueError):
            Blend(TARGET, 50, scale='C major')

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
