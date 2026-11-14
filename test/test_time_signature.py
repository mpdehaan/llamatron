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
"""TimeSignature: beats over a note value, which beat is which, and what it refuses."""

import unittest
from fractions import Fraction

from llamatron.music.time_signature import MAX_BEATS, MIN_BEATS, TimeSignature, is_time_signature

# Time signatures the tests use, written as a file writes them.
COMMON_TIME = '4/4'
WALTZ = '3/4'
COMPOUND_DUPLE = '6/8'
COMPOUND_QUADRUPLE = '12/8'
CUT_TIME = '2/2'
THREE_EIGHT = '3/8'
SEVEN_SIXTEEN = '7/16'
# Things that aren't time signatures.
NOT_SIGNATURES = ['4', '4/5', '0/4', '4/0', '33/4', 'four/four', '', ' 4/4', '4/4 ', '4//4', '-4/4', '4.0/4']


class TestTimeSignature(unittest.TestCase):

    def test_it_reads_and_writes_its_text(self):
        for text in [COMMON_TIME, WALTZ, COMPOUND_DUPLE, CUT_TIME, SEVEN_SIXTEEN]:
            with self.subTest(text=text):
                signature = TimeSignature.from_text(text)
                self.assertEqual(signature.to_text(), text)
                self.assertTrue(is_time_signature(text))

    def test_the_beats_and_unit_are_the_two_numbers(self):
        signature = TimeSignature.from_text(COMPOUND_DUPLE)
        self.assertEqual((signature.get_beats(), signature.get_unit()), (6, 8))
        self.assertEqual(signature, TimeSignature(beats=6, unit=8))
        self.assertEqual(hash(signature), hash(TimeSignature(beats=6, unit=8)))
        self.assertNotEqual(signature, TimeSignature.from_text(WALTZ))

    def test_the_limits_are_the_constants(self):
        self.assertTrue(is_time_signature(f'{MIN_BEATS}/4'))
        self.assertTrue(is_time_signature(f'{MAX_BEATS}/4'))
        self.assertFalse(is_time_signature(f'{MAX_BEATS + 1}/4'))
        self.assertFalse(is_time_signature(f'{MIN_BEATS - 1}/4'))

    def test_it_refuses_what_is_not_a_time_signature(self):
        for text in NOT_SIGNATURES:
            with self.subTest(text=text):
                self.assertFalse(is_time_signature(text))
                with self.assertRaises(ValueError):
                    TimeSignature.from_text(text)
        with self.assertRaises(ValueError):
            TimeSignature(beats=4, unit=5)
        self.assertFalse(is_time_signature(None))
        self.assertFalse(is_time_signature(4))

    def test_the_beat_is_the_unit_note_except_in_compound_meters_where_it_is_three_of_them(self):
        expected = {
            COMMON_TIME: Fraction(1, 4), WALTZ: Fraction(1, 4), CUT_TIME: Fraction(1, 2), THREE_EIGHT: Fraction(1, 8),
            COMPOUND_DUPLE: Fraction(3, 8), COMPOUND_QUADRUPLE: Fraction(3, 8), SEVEN_SIXTEEN: Fraction(1, 16),
        }
        for text, beat in expected.items():
            with self.subTest(text=text):
                signature = TimeSignature.from_text(text)
                self.assertEqual(signature.beat_length(), beat)
                self.assertEqual(signature.is_compound(), text in (COMPOUND_DUPLE, COMPOUND_QUADRUPLE))

    def test_a_bar_lasts_its_beats_over_its_unit(self):
        self.assertEqual(TimeSignature.from_text(COMMON_TIME).bar_length(), 1)
        self.assertEqual(TimeSignature.from_text(WALTZ).bar_length(), Fraction(3, 4))
        self.assertEqual(TimeSignature.from_text(COMPOUND_DUPLE).bar_length(), Fraction(3, 4))

    def test_which_times_start_a_beat(self):
        common = TimeSignature.from_text(COMMON_TIME)
        sixteenths = [Fraction(step, 16) for step in range(16)]
        self.assertEqual([step for step, time in enumerate(sixteenths) if common.starts_a_beat(time)], [0, 4, 8, 12])
        compound = TimeSignature.from_text(COMPOUND_DUPLE)
        self.assertEqual([step for step, time in enumerate(sixteenths) if compound.starts_a_beat(time)], [0, 6, 12])
        # Triplet sixteenths: three to a beat.
        twelfths = [Fraction(step, 12) for step in range(12)]
        self.assertEqual([step for step, time in enumerate(twelfths) if common.starts_a_beat(time)], [0, 3, 6, 9])
        # A time that isn't on a beat at all.
        self.assertFalse(common.starts_a_beat(Fraction(3, 16)))
