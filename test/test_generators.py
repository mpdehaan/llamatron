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

from src.chord import Chord, ChordType
from src.generators.arp import Arp, ChordOrder
from src.generators.base import ClipGenerator
from src.generators.repeater import Repeater
from src.note import Note, Rest
from src.scale import Scale, ScaleType
from src.song import Clip

QUARTER = 0.25
C4 = Note('C', 4, QUARTER)
D4 = Note('D', 4, QUARTER)
E4 = Note('E', 4, QUARTER)
G4 = Note('G', 4, QUARTER)
B4 = Note('B', 4, QUARTER)
C_MAJOR = Chord([C4, E4, G4])
C_MAJOR_WHOLE = Note('C', 4, 1).to_chord(ChordType.MAJOR)
SCALE = Scale(Note('C', 0, QUARTER), ScaleType.MAJOR)


def names(clip):
    """Return a clip's notes as text, such as 'C4 E4 R'."""
    return ' '.join(
        'R' if isinstance(position, Rest) else f'{position.name}{position.octave_number}'
        for position in clip.notes
    )


class TestClipGenerator(unittest.TestCase):

    def test_cannot_be_used_directly(self):
        with self.assertRaises(TypeError):
            ClipGenerator()

    def test_subclass_only_needs_to_supply_notes_and_length(self):
        class Backwards(ClipGenerator):
            def _generate(self, clip):
                return clip.notes[::-1], clip.length

        result = Backwards().generate(Clip(notes=[C4, D4]))
        self.assertEqual(result.notes, [D4, C4])

    def test_every_generator_rejects_anything_but_a_clip(self):
        for generator in [Repeater(2), Arp(QUARTER)]:
            for value in [None, 'clip', [C4], C4]:
                with self.subTest(generator=type(generator).__name__, value=value):
                    with self.assertRaises(ValueError):
                        generator.generate(value)

    def test_every_generator_makes_a_new_clip_and_keeps_the_details(self):
        for generator in [Repeater(2), Arp(QUARTER)]:
            with self.subTest(generator=type(generator).__name__):
                original = Clip('Riff', notes=[C_MAJOR], scale=SCALE, length=1)
                result = generator.generate(original)
                self.assertIsNot(result, original)
                self.assertNotEqual(result.id, original.id)
                self.assertEqual(result.name, 'Riff')
                self.assertIs(result.scale, SCALE)

    def test_every_generator_leaves_the_original_unchanged(self):
        for generator in [Repeater(2), Arp(QUARTER)]:
            with self.subTest(generator=type(generator).__name__):
                original = Clip(notes=[C_MAJOR, Rest(QUARTER)], length=1)
                generator.generate(original)
                self.assertEqual(original.notes, [C_MAJOR, Rest(QUARTER)])
                self.assertEqual(original.length, 1)

    def test_generators_can_be_chained(self):
        clip = Clip(notes=[C_MAJOR_WHOLE])
        result = Repeater(2).generate(Arp(QUARTER).generate(clip))
        self.assertEqual(names(result), 'C4 C4 E4 E4 G4 G4 C4 C4')

    def test_one_generator_can_be_reused(self):
        repeater = Repeater(2)
        self.assertEqual(names(repeater.generate(Clip(notes=[C4]))), 'C4 C4')
        self.assertEqual(names(repeater.generate(Clip(notes=[D4]))), 'D4 D4')


class TestRepeater(unittest.TestCase):

    def test_two_turns_a_whole_note_into_two_half_notes(self):
        result = Repeater(2).generate(Clip(notes=[Note('C', 4, 1)]))
        self.assertEqual(result.notes, [Note('C', 4, 0.5), Note('C', 4, 0.5)])

    def test_each_position_repeats_before_the_next(self):
        result = Repeater(2).generate(Clip(notes=[C4, D4]))
        eighth_c, eighth_d = Note('C', 4, 0.125), Note('D', 4, 0.125)
        self.assertEqual(result.notes, [eighth_c, eighth_c, eighth_d, eighth_d])

    def test_three_makes_exact_triplets(self):
        result = Repeater(3).generate(Clip(notes=[Note('C', 4, 1)]))
        self.assertEqual(result.notes, [Note('C', 4, Fraction(1, 3))] * 3)

    def test_chords_are_repeated_with_every_note_shortened(self):
        chord = Note('C', 4, 1).to_chord(ChordType.MAJOR)
        result = Repeater(2).generate(Clip(notes=[chord]))
        half = Note('C', 4, 0.5).to_chord(ChordType.MAJOR)
        self.assertEqual(result.notes, [half, half])

    def test_chords_with_mixed_lengths_keep_their_proportions(self):
        chord = Chord([Note('C', 4, 1), Note('E', 4, 0.5)])
        result = Repeater(2).generate(Clip(notes=[chord]))
        shorter = Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)])
        self.assertEqual(result.notes, [shorter, shorter])

    def test_rests_are_repeated(self):
        result = Repeater(2).generate(Clip(notes=[Rest(1)]))
        self.assertEqual(result.notes, [Rest(0.5), Rest(0.5)])

    def test_keeps_the_note_spelling(self):
        result = Repeater(2).generate(Clip(notes=[Note('Db', 4, 1)]))
        self.assertEqual(names(result), 'Db4 Db4')

    def test_total_duration_stays_the_same(self):
        notes = [Note('C', 4, 0.5), Rest(0.25), C_MAJOR]
        for times in [1, 2, 3, 7]:
            with self.subTest(times=times):
                result = Repeater(times).generate(Clip(notes=notes))
                self.assertEqual(sum(position.length for position in result.notes), 1)

    def test_keeps_the_clip_length(self):
        result = Repeater(2).generate(Clip(notes=[C4], length=1))
        self.assertEqual(result.length, 1)
        self.assertIsNone(Repeater(2).generate(Clip(notes=[C4])).length)

    def test_set_length_keeps_the_silence_after_the_notes(self):
        result = Repeater(2).generate(Clip(notes=[C4], length=1))
        eighth = Note('C', 4, 0.125)
        self.assertEqual(result.notes, [eighth, eighth])

    def test_once_gives_a_copy(self):
        original = Clip(notes=[C4, D4])
        result = Repeater(1).generate(original)
        self.assertEqual(result.notes, original.notes)
        result.notes.append(E4)
        self.assertEqual(len(original.notes), 2)

    def test_empty_clip_stays_empty(self):
        result = Repeater(3).generate(Clip(length=1))
        self.assertEqual(result.notes, [])
        self.assertEqual(result.length, 1)

    def test_inexact_float_lengths_stay_exact(self):
        result = Repeater(2).generate(Clip(notes=[Note('C', 4, 1 / 12)]))
        self.assertEqual(result.notes[0].length, Fraction(1, 24))

    def test_rejects_invalid_item_added_to_a_list(self):
        clip = Clip(notes=[C4])
        clip.notes.append('C4')
        with self.assertRaises(ValueError):
            Repeater(2).generate(clip)

    def test_rejects_invalid_times(self):
        for times in [0, -1, 1.5, 2.0, '2', None, True]:
            with self.subTest(times=times):
                with self.assertRaises(ValueError):
                    Repeater(times)

    def test_times_can_be_edited_and_is_validated(self):
        repeater = Repeater(2)
        repeater.times = 3
        self.assertEqual(repeater.times, 3)
        with self.assertRaises(ValueError):
            repeater.times = 0
        self.assertEqual(repeater.times, 3)


class TestArpOrders(unittest.TestCase):

    def arp(self, order, chord=C_MAJOR_WHOLE, step=0.125):
        return names(Arp(step, order).generate(Clip(notes=[chord])))

    def test_up(self):
        self.assertEqual(self.arp(ChordOrder.UP), 'C4 E4 G4 C4 E4 G4 C4 E4')

    def test_down(self):
        self.assertEqual(self.arp(ChordOrder.DOWN), 'G4 E4 C4 G4 E4 C4 G4 E4')

    def test_up_down_does_not_repeat_the_turning_points(self):
        self.assertEqual(self.arp(ChordOrder.UP_DOWN), 'C4 E4 G4 E4 C4 E4 G4 E4')

    def test_down_up_does_not_repeat_the_turning_points(self):
        self.assertEqual(self.arp(ChordOrder.DOWN_UP), 'G4 E4 C4 E4 G4 E4 C4 E4')

    def test_up_down_with_four_notes(self):
        chord = Note('C', 4, 1).to_chord(ChordType.DOMINANT7)
        self.assertEqual(self.arp(ChordOrder.UP_DOWN, chord), 'C4 E4 G4 A#4 G4 E4 C4 E4')

    def test_up_down_with_two_notes(self):
        chord = Note('C', 4, 0.5).to_chord(ChordType.POWER)
        self.assertEqual(self.arp(ChordOrder.UP_DOWN, chord), 'C4 G4 C4 G4')

    def test_single_note_chord_works_in_every_order(self):
        for order in ChordOrder:
            with self.subTest(order=order):
                self.assertEqual(self.arp(order, Chord([Note('C', 4, 0.25)])), 'C4 C4')

    def test_up_uses_pitch_not_the_order_the_chord_was_built_in(self):
        chord = Chord([Note('G', 4, 0.25), Note('C', 4, 0.25), Note('E', 4, 0.25)])
        self.assertEqual(self.arp(ChordOrder.UP, chord, 0.25), 'C4')
        self.assertEqual(self.arp(ChordOrder.DOWN, chord, 0.25), 'G4')

    def test_inexact_float_step_does_not_add_a_tiny_extra_note(self):
        self.assertEqual(self.arp(ChordOrder.UP, C_MAJOR, 1 / 12), 'C4 E4 G4')

    def test_repeated_pitch_in_a_chord_is_played_once_per_cycle(self):
        chord = Chord([Note('C', 4, 0.25), Note('B#', 3, 0.25), Note('E', 4, 0.25)])
        self.assertEqual(self.arp(ChordOrder.UP, chord), 'C4 E4')

    def test_defaults_to_up(self):
        self.assertIs(Arp(QUARTER).order, ChordOrder.UP)


class TestArpRandom(unittest.TestCase):

    def clip(self):
        return Clip(notes=[Note('C', 5, 8).to_chord(ChordType.MAJOR7)])

    def test_uses_only_the_chord_notes(self):
        result = Arp(0.125, ChordOrder.RANDOM, seed=1).generate(self.clip())
        self.assertEqual(len(result.notes), 64)
        self.assertEqual(
            {note.midi_number for note in result.notes},
            {note.midi_number for note in self.clip().notes[0].notes},
        )

    def test_same_seed_gives_the_same_result_every_time(self):
        arp = Arp(0.125, ChordOrder.RANDOM, seed=1)
        self.assertEqual(arp.generate(self.clip()).notes, arp.generate(self.clip()).notes)

    def test_different_seeds_give_different_results(self):
        first = Arp(0.125, ChordOrder.RANDOM, seed=1).generate(self.clip())
        second = Arp(0.125, ChordOrder.RANDOM, seed=2).generate(self.clip())
        self.assertNotEqual(first.notes, second.notes)

    def test_no_seed_still_works(self):
        result = Arp(0.125, ChordOrder.RANDOM).generate(self.clip())
        self.assertEqual(len(result.notes), 64)


class TestArpTiming(unittest.TestCase):

    def test_every_step_has_the_step_length(self):
        result = Arp(0.125).generate(Clip(notes=[C_MAJOR_WHOLE]))
        self.assertEqual({note.length for note in result.notes}, {0.125})

    def test_chord_keeps_its_total_length(self):
        result = Arp(0.125).generate(Clip(notes=[C_MAJOR_WHOLE, C4]))
        self.assertEqual(sum(position.length for position in result.notes), 1.25)

    def test_last_step_is_cut_to_fit_the_chord(self):
        step = Fraction(1, 12)
        result = Arp(step).generate(Clip(notes=[Note('C', 4, 0.125).to_chord(ChordType.MAJOR)]))
        self.assertEqual(
            [note.length for note in result.notes],
            [step, Fraction(1, 24)],
        )

    def test_step_longer_than_the_chord_plays_one_shortened_note(self):
        result = Arp(1).generate(Clip(notes=[C_MAJOR]))
        self.assertEqual(result.notes, [C4])

    def test_chord_with_mixed_lengths_uses_its_longest_note(self):
        chord = Chord([Note('C', 4, 0.5), Note('E', 4, 0.25)])
        result = Arp(0.25).generate(Clip(notes=[chord]))
        self.assertEqual(names(result), 'C4 E4')

    def test_notes_and_rests_are_left_alone(self):
        result = Arp(0.125).generate(Clip(notes=[C4, Rest(QUARTER), C_MAJOR]))
        self.assertEqual(result.notes[:2], [C4, Rest(QUARTER)])
        self.assertEqual(names(result), 'C4 R C4 E4')

    def test_keeps_note_spelling(self):
        chord = Chord([Note('Db', 4, 0.25), Note('F', 4, 0.25)])
        result = Arp(0.125).generate(Clip(notes=[chord]))
        self.assertEqual(names(result), 'Db4 F4')

    def test_no_set_length_plays_through_once(self):
        result = Arp(QUARTER).generate(Clip(notes=[C4, D4]))
        self.assertEqual(names(result), 'C4 D4')
        self.assertIsNone(result.length)

    def test_set_length_starts_again_until_it_is_filled(self):
        result = Arp(QUARTER).generate(Clip(notes=[C4, D4, Rest(QUARTER)], length=1))
        self.assertEqual(names(result), 'C4 D4 R C4')
        self.assertEqual(result.length, 1)

    def test_set_length_cuts_off_the_end(self):
        result = Arp(QUARTER).generate(Clip(notes=[C4, D4, E4], length=0.375))
        self.assertEqual(result.notes, [C4, Note('D', 4, 0.125)])
        self.assertEqual(result.length, 0.375)

    def test_set_length_restarts_the_chord_pattern(self):
        chord = Note('C', 4, 0.5).to_chord(ChordType.MAJOR)
        result = Arp(QUARTER).generate(Clip(notes=[chord], length=1))
        self.assertEqual(names(result), 'C4 E4 C4 E4')

    def test_empty_clip_with_a_set_length_is_silent(self):
        result = Arp(QUARTER).generate(Clip(length=1))
        self.assertEqual(result.notes, [Rest(1)])

    def test_empty_clip_stays_empty(self):
        self.assertEqual(Arp(QUARTER).generate(Clip()).notes, [])


class TestArpFields(unittest.TestCase):

    def test_step_is_required(self):
        with self.assertRaises(TypeError):
            Arp()

    def test_rejects_invalid_values(self):
        for step in [0, -0.25, '0.25', None, True]:
            with self.subTest(step=step):
                with self.assertRaises(ValueError):
                    Arp(step)
        for order in ['UP', None, 1]:
            with self.subTest(order=order):
                with self.assertRaises(ValueError):
                    Arp(QUARTER, order)
        for seed in ['1', 1.5, True]:
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    Arp(QUARTER, seed=seed)

    def test_fields_can_be_edited_and_are_validated(self):
        arp = Arp(QUARTER)
        arp.step = 0.5
        arp.order = ChordOrder.DOWN
        arp.seed = 3
        self.assertEqual((arp.step, arp.order, arp.seed), (0.5, ChordOrder.DOWN, 3))
        with self.assertRaises(ValueError):
            arp.step = 0
        with self.assertRaises(ValueError):
            arp.order = 'UP'
        self.assertEqual((arp.step, arp.order), (0.5, ChordOrder.DOWN))


if __name__ == '__main__':
    unittest.main()
