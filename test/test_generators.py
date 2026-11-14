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

from llamatron.music.chord import Chord, ChordType
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.generators.arp import Arp, ChordOrder
from llamatron.generators.base import ClipGenerator
from llamatron.music.note import Note, NoteName, Rest
from llamatron.music.scale import Scale, ScaleType
from llamatron.grid.clip import Clip

QUARTER = 0.25
C4 = Note(name='C', octave_number=4, length=QUARTER)
D4 = Note(name='D', octave_number=4, length=QUARTER)
E4 = Note(name='E', octave_number=4, length=QUARTER)
G4 = Note(name='G', octave_number=4, length=QUARTER)
B4 = Note(name='B', octave_number=4, length=QUARTER)
C_MAJOR = Chord([C4, E4, G4])
C_MAJOR_WHOLE = Note(name='C', octave_number=4, length=1).to_chord(ChordType.MAJOR)
SCALE = Scale(root=Note(name='C', octave_number=0, length=QUARTER), typ=ScaleType.MAJOR)

# Names the tests give to their own things, and other values they use.
R = 'R'
C4_C4 = 'C4 C4'
D4_D4 = 'D4 D4'
C4_C4_E4_E4_G4_G4_C4_C4 = 'C4 C4 E4 E4 G4 G4 C4 C4'
CLIP = 'clip'
RIFF = 'Riff'
C4_E4_G4_C4_E4_G4_C4_E4 = 'C4 E4 G4 C4 E4 G4 C4 E4'
G4_E4_C4_G4_E4_C4_G4_E4 = 'G4 E4 C4 G4 E4 C4 G4 E4'
C4_E4_G4_E4_C4_E4_G4_E4 = 'C4 E4 G4 E4 C4 E4 G4 E4'
G4_E4_C4_E4_G4_E4_C4_E4 = 'G4 E4 C4 E4 G4 E4 C4 E4'
C4_G4_C4_G4 = 'C4 G4 C4 G4'
C4_2 = 'C4'
G4_2 = 'G4'
C4_E4_G4 = 'C4 E4 G4'
C4_E4 = 'C4 E4'
C4_R_C4_E4 = 'C4 R C4 E4'
DB4_F4 = 'Db4 F4'
C4_D4 = 'C4 D4'
C4_D4_R_C4 = 'C4 D4 R C4'
C4_E4_C4_E4 = 'C4 E4 C4 E4'
NOT_AN_ORDER = 'UP'


def names(clip):
    """Return a clip's notes as text, such as 'C4 E4 R'."""
    return ' '.join(
        R if isinstance(position, Rest) else f'{position.get_name()}{position.get_octave_number()}'
        for position in clip.get_notes()
    )


class TestClipGenerator(unittest.TestCase):

    def test_cannot_be_used_directly(self):
        with self.assertRaises(TypeError):
            ClipGenerator()

    def test_subclass_only_needs_to_supply_sounds_and_length(self):
        class Backwards(ClipGenerator):
            def _generate(self, clip):
                return clip.get_sounds()[::-1], clip.get_length()

        result = Backwards().generate(Clip(notes=[C4, D4]))
        self.assertEqual(result.get_notes(), [D4, C4])

    def test_one_generator_can_be_reused(self):
        ratchet = AutoRatchet([2])
        self.assertEqual(names(ratchet.generate(Clip(notes=[C4]))), C4_C4)
        self.assertEqual(names(ratchet.generate(Clip(notes=[D4]))), D4_D4)

    def test_generators_can_be_chained(self):
        clip = Clip(notes=[C_MAJOR_WHOLE])
        result = AutoRatchet([2]).generate(Arp(step=QUARTER).generate(clip))
        self.assertEqual(names(result), C4_C4_E4_E4_G4_G4_C4_C4)

    def test_every_generator_leaves_the_original_unchanged(self):
        for generator in [AutoRatchet([2]), Arp(step=QUARTER)]:
            with self.subTest(generator=type(generator).__name__):
                original = Clip(notes=[C_MAJOR, Rest(QUARTER)], length=1)
                generator.generate(original)
                self.assertEqual(original.get_notes(), [C_MAJOR, Rest(QUARTER)])
                self.assertEqual(original.get_length(), 1)

    def test_every_generator_makes_a_new_clip_and_keeps_the_details(self):
        for generator in [AutoRatchet([2]), Arp(step=QUARTER)]:
            with self.subTest(generator=type(generator).__name__):
                original = Clip(name=RIFF, notes=[C_MAJOR], scale=SCALE, length=1)
                result = generator.generate(original)
                self.assertIsNot(result, original)
                self.assertNotEqual(result.get_id(), original.get_id())
                self.assertEqual(result.get_name(), RIFF)
                self.assertIs(result.get_scale(), SCALE)

    def test_every_generator_rejects_anything_but_a_clip(self):
        for generator in [AutoRatchet([2]), Arp(step=QUARTER)]:
            for value in [None, CLIP, [C4], C4]:
                with self.subTest(generator=type(generator).__name__, value=value):
                    with self.assertRaises(ValueError):
                        generator.generate(value)



class TestArpOrders(unittest.TestCase):

    def arp(self, *, order, chord=C_MAJOR_WHOLE, step=0.125):
        return names(Arp(step=step, order=order).generate(Clip(notes=[chord])))

    def test_up(self):
        self.assertEqual(self.arp(order=ChordOrder.UP), C4_E4_G4_C4_E4_G4_C4_E4)

    def test_down(self):
        self.assertEqual(self.arp(order=ChordOrder.DOWN), G4_E4_C4_G4_E4_C4_G4_E4)

    def test_up_down_does_not_repeat_the_turning_points(self):
        self.assertEqual(self.arp(order=ChordOrder.UP_DOWN), C4_E4_G4_E4_C4_E4_G4_E4)

    def test_down_up_does_not_repeat_the_turning_points(self):
        self.assertEqual(self.arp(order=ChordOrder.DOWN_UP), G4_E4_C4_E4_G4_E4_C4_E4)

    def test_up_down_with_four_notes(self):
        chord = Note(name=NoteName.C, octave_number=4, length=1).to_chord(ChordType.DOMINANT7)
        self.assertEqual(self.arp(order=ChordOrder.UP_DOWN, chord=chord), 'C4 E4 G4 A#4 G4 E4 C4 E4')

    def test_up_down_with_two_notes(self):
        chord = Note(name=NoteName.C, octave_number=4, length=0.5).to_chord(ChordType.POWER)
        self.assertEqual(self.arp(order=ChordOrder.UP_DOWN, chord=chord), C4_G4_C4_G4)

    def test_single_note_chord_works_in_every_order(self):
        for order in ChordOrder:
            with self.subTest(order=order):
                self.assertEqual(self.arp(order=order, chord=Chord([Note(name=NoteName.C, octave_number=4, length=0.25)])), C4_C4)

    def test_up_uses_pitch_not_the_order_the_chord_was_built_in(self):
        chord = Chord([Note(name=NoteName.G, octave_number=4, length=0.25), Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.E, octave_number=4, length=0.25)])
        self.assertEqual(self.arp(order=ChordOrder.UP, chord=chord, step=0.25), C4_2)
        self.assertEqual(self.arp(order=ChordOrder.DOWN, chord=chord, step=0.25), G4_2)

    def test_inexact_float_step_does_not_add_a_tiny_extra_note(self):
        self.assertEqual(self.arp(order=ChordOrder.UP, chord=C_MAJOR, step=1 / 12), C4_E4_G4)

    def test_repeated_pitch_in_a_chord_is_played_once_per_cycle(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=0.25), Note(name=NoteName.B_SHARP, octave_number=3, length=0.25), Note(name=NoteName.E, octave_number=4, length=0.25)])
        self.assertEqual(self.arp(order=ChordOrder.UP, chord=chord), C4_E4)

    def test_defaults_to_up(self):
        self.assertIs(Arp(step=QUARTER).get_order(), ChordOrder.UP)


class TestArpRandom(unittest.TestCase):

    def clip(self):
        return Clip(notes=[Note(name=NoteName.C, octave_number=5, length=8).to_chord(ChordType.MAJOR7)])

    def test_uses_only_the_chord_notes(self):
        result = Arp(step=0.125, order=ChordOrder.RANDOM, seed=1).generate(self.clip())
        self.assertEqual(len(result.get_notes()), 64)
        self.assertEqual(
            {note.get_midi_number() for note in result.get_notes()},
            {note.get_midi_number() for note in self.clip().get_notes()[0].get_notes()},
        )

    def test_same_seed_gives_the_same_result_every_time(self):
        arp = Arp(step=0.125, order=ChordOrder.RANDOM, seed=1)
        self.assertEqual(arp.generate(self.clip()).get_notes(), arp.generate(self.clip()).get_notes())

    def test_different_seeds_give_different_results(self):
        first = Arp(step=0.125, order=ChordOrder.RANDOM, seed=1).generate(self.clip())
        second = Arp(step=0.125, order=ChordOrder.RANDOM, seed=2).generate(self.clip())
        self.assertNotEqual(first.get_notes(), second.get_notes())

    def test_no_seed_still_works(self):
        result = Arp(step=0.125, order=ChordOrder.RANDOM).generate(self.clip())
        self.assertEqual(len(result.get_notes()), 64)


class TestArpTiming(unittest.TestCase):

    def test_every_step_has_the_step_length(self):
        result = Arp(step=0.125).generate(Clip(notes=[C_MAJOR_WHOLE]))
        self.assertEqual({note.get_length() for note in result.get_notes()}, {0.125})

    def test_chord_keeps_its_total_length(self):
        result = Arp(step=0.125).generate(Clip(notes=[C_MAJOR_WHOLE, C4]))
        self.assertEqual(sum(position.get_length() for position in result.get_notes()), 1.25)

    def test_last_step_is_cut_to_fit_the_chord(self):
        step = Fraction(1, 12)
        result = Arp(step=step).generate(Clip(notes=[Note(name=NoteName.C, octave_number=4, length=0.125).to_chord(ChordType.MAJOR)]))
        self.assertEqual(
            [note.get_length() for note in result.get_notes()],
            [step, Fraction(1, 24)],
        )

    def test_step_longer_than_the_chord_plays_one_shortened_note(self):
        result = Arp(step=1).generate(Clip(notes=[C_MAJOR]))
        self.assertEqual(result.get_notes(), [C4])

    def test_chord_with_mixed_lengths_uses_its_longest_note(self):
        chord = Chord([Note(name=NoteName.C, octave_number=4, length=0.5), Note(name=NoteName.E, octave_number=4, length=0.25)])
        result = Arp(step=0.25).generate(Clip(notes=[chord]))
        self.assertEqual(names(result), C4_E4)

    def test_notes_and_rests_are_left_alone(self):
        result = Arp(step=0.125).generate(Clip(notes=[C4, Rest(QUARTER), C_MAJOR]))
        self.assertEqual(result.get_notes()[:2], [C4, Rest(QUARTER)])
        self.assertEqual(names(result), C4_R_C4_E4)

    def test_keeps_note_spelling(self):
        chord = Chord([Note(name=NoteName.D_FLAT, octave_number=4, length=0.25), Note(name=NoteName.F, octave_number=4, length=0.25)])
        result = Arp(step=0.125).generate(Clip(notes=[chord]))
        self.assertEqual(names(result), DB4_F4)

    def test_no_set_length_plays_through_once(self):
        result = Arp(step=QUARTER).generate(Clip(notes=[C4, D4]))
        self.assertEqual(names(result), C4_D4)
        self.assertIsNone(result.get_length())

    def test_set_length_starts_again_until_it_is_filled(self):
        result = Arp(step=QUARTER).generate(Clip(notes=[C4, D4, Rest(QUARTER)], length=1))
        self.assertEqual(names(result), C4_D4_R_C4)
        self.assertEqual(result.get_length(), 1)

    def test_set_length_cuts_off_the_end(self):
        result = Arp(step=QUARTER).generate(Clip(notes=[C4, D4, E4], length=0.375))
        self.assertEqual(result.get_notes(), [C4, Note(name=NoteName.D, octave_number=4, length=0.125)])
        self.assertEqual(result.get_length(), 0.375)

    def test_set_length_restarts_the_chord_pattern(self):
        chord = Note(name=NoteName.C, octave_number=4, length=0.5).to_chord(ChordType.MAJOR)
        result = Arp(step=QUARTER).generate(Clip(notes=[chord], length=1))
        self.assertEqual(names(result), C4_E4_C4_E4)

    def test_empty_clip_with_a_set_length_is_silent(self):
        result = Arp(step=QUARTER).generate(Clip(length=1))
        self.assertEqual(result.get_notes(), [Rest(1)])

    def test_empty_clip_stays_empty(self):
        self.assertEqual(Arp(step=QUARTER).generate(Clip()).get_notes(), [])


class TestArpFields(unittest.TestCase):

    def test_step_is_required(self):
        with self.assertRaises(TypeError):
            Arp()

    def test_rejects_invalid_values(self):
        for step in [0, -0.25, '0.25', None, True]:
            with self.subTest(step=step):
                with self.assertRaises(ValueError):
                    Arp(step=step)
        for order in [NOT_AN_ORDER, None, 1]:
            with self.subTest(order=order):
                with self.assertRaises(ValueError):
                    Arp(step=QUARTER, order=order)
        for seed in ['1', 1.5, True]:
            with self.subTest(seed=seed):
                with self.assertRaises(ValueError):
                    Arp(step=QUARTER, seed=seed)

    def test_fields_can_be_edited_and_are_validated(self):
        arp = Arp(step=QUARTER)
        arp.set_step(0.5)
        arp.set_order(ChordOrder.DOWN)
        arp.set_seed(3)
        self.assertEqual((arp.get_step(), arp.get_order(), arp.get_seed()), (0.5, ChordOrder.DOWN, 3))
        with self.assertRaises(ValueError):
            arp.set_step(0)
        with self.assertRaises(ValueError):
            arp.set_order(NOT_AN_ORDER)
        self.assertEqual((arp.get_step(), arp.get_order()), (0.5, ChordOrder.DOWN))


if __name__ == '__main__':
    unittest.main()
