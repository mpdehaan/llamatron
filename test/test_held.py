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

"""Held: a sound that keeps sounding while the positions after it start, as a long gate does."""

import unittest
from fractions import Fraction

from llamatron.music.chord import Chord
from llamatron.grid.clip import Clip
from llamatron.generators.arp import Arp
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.music.held import Held, phrase
from llamatron.music.note import Note, NoteName, Rest
from llamatron.exporters.timing import timed_events

C = Note(name='C', octave_number=5, length=Fraction(1, 2))
D = Note(name='D', octave_number=5, length=Fraction(1, 8))
E = Note(name='E', octave_number=5, length=Fraction(1, 8))

# Text where a sound should be, which a Held refuses.
NOT_A_SOUND = 'C'


def events(clip):
    """Return a clip's notes as (start, end, MIDI number), in time order."""
    return sorted((start, end, number) for start, end, number, _ in timed_events(clip=clip, scale=None)[0])


class TestHeld(unittest.TestCase):

    def test_the_next_position_starts_after_its_length_while_its_sound_carries_on(self):
        clip = Clip(notes=[Held(sound=C, length=Fraction(1, 8)), D, Rest(Fraction(1, 4))])
        self.assertEqual(events(clip), [(0, Fraction(1, 2), C.get_midi_number()), (Fraction(1, 8), Fraction(1, 4), D.get_midi_number())])
        self.assertEqual(clip.total_length(), Fraction(1, 2))

    def test_the_end_of_the_clip_cuts_its_sound(self):
        clip = Clip(notes=[Held(sound=C, length=Fraction(1, 8)), D], length=Fraction(3, 8))
        self.assertEqual(events(clip)[0], (0, Fraction(3, 8), C.get_midi_number()))

    def test_a_held_phrase_plays_its_parts_one_after_another(self):
        held = Held(sound=phrase([D, Rest(Fraction(1, 8)), E]), length=Fraction(1, 8))
        self.assertEqual(events(Clip(notes=[held, Rest(Fraction(1, 4))])), [
            (0, Fraction(1, 8), D.get_midi_number()), (Fraction(1, 4), Fraction(3, 8), E.get_midi_number()),
        ])

    def test_a_section_that_starts_part_way_through_keeps_the_rest_of_its_sound(self):
        clip = Clip(notes=[Held(sound=C, length=Fraction(1, 4)), D, Rest(Fraction(1, 2))])
        self.assertEqual(events(clip.section(start=Fraction(1, 8), end=Fraction(1, 2))), [
            (0, Fraction(3, 8), C.get_midi_number()), (Fraction(1, 8), Fraction(1, 4), D.get_midi_number()),
        ])

    def test_an_arpeggiator_fills_a_held_chord_without_moving_what_follows(self):
        chord = Chord([Note(name=NoteName.C, octave_number=5, length=Fraction(1, 4)), Note(name=NoteName.E, octave_number=5, length=Fraction(1, 4))])
        clip = Arp(step=Fraction(1, 8)).generate(Clip(notes=[Held(sound=chord, length=Fraction(1, 16)), D, Rest(Fraction(1, 16))]))
        self.assertEqual(events(clip), [
            (0, Fraction(1, 8), Note(name=NoteName.C, octave_number=5).get_midi_number()),
            (Fraction(1, 16), Fraction(3, 16), D.get_midi_number()),
            (Fraction(1, 8), Fraction(1, 4), Note(name=NoteName.E, octave_number=5).get_midi_number()),
        ])
        self.assertEqual(clip.total_length(), Fraction(1, 4))

    def test_an_auto_ratchet_chops_a_held_sound_in_place(self):
        clip = AutoRatchet([1, 2]).generate(Clip(notes=[Held(sound=C, length=Fraction(1, 8)), D, Rest(Fraction(3, 8))]))
        self.assertEqual(events(clip), [
            (0, Fraction(1, 2), C.get_midi_number()), (Fraction(1, 8), Fraction(3, 16), D.get_midi_number()),
            (Fraction(3, 16), Fraction(1, 4), D.get_midi_number()),
        ])

    def test_its_length_and_sound_are_checked(self):
        with self.assertRaises(ValueError):
            Held(sound=C, length=0)
        with self.assertRaises(ValueError):
            Held(sound=NOT_A_SOUND, length=Fraction(1, 8))
        with self.assertRaises(ValueError):
            Held(sound=phrase([NOT_A_SOUND]), length=Fraction(1, 8))


if __name__ == '__main__':
    unittest.main()
