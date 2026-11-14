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
"""Length does on pairs of whole numbers exactly what Fraction does, for everything a render asks of a length."""

import itertools
import unittest
from fractions import Fraction

from llamatron.support.length import FINEST_LENGTH, ZERO, Length
from llamatron.support.rational import Rational

# A sweep of values: the lengths a song uses, thirds, sevenths, negatives and zero.
NUMERATORS = range(-5, 6)
DENOMINATORS = [1, 2, 3, 4, 7, 16, 128]
# How many times over a length is taken, and how many notes share one.
COUNTS = range(0, 6)
SHARES = range(1, 6)
# Floats that aren't exact, and the fraction each one means.
TWELFTH = Fraction(1, 12)
INEXACT_FLOATS = {1 / 12: TWELFTH, 1 / 3: Fraction(1, 3), 0.1: Fraction(1, 10), 0.25: Fraction(1, 4)}
WHOLE_NUMBERS = range(-3, 4)
# Two lengths that Python's own comparison of tuples puts the wrong way round.
HALF = (1, 2)
THIRD = (1, 3)
# A length finer than any a song has, as a float's rounding error is.
TOO_FINE = Rational(1, FINEST_LENGTH * 3)


def pairs():
    """Return every value in the sweep as a pair in lowest terms, with the Fraction it should equal."""
    found = {}
    for numerator in NUMERATORS:
        for denominator in DENOMINATORS:
            fraction = Fraction(numerator, denominator)
            found[(fraction.numerator, fraction.denominator)] = fraction
    return list(found.items())


def two_pairs():
    """Return every two values of the sweep, each with its Fraction."""
    return itertools.product(pairs(), repeat=2)


class TestLengthAgreesWithFraction(unittest.TestCase):

    def assertSame(self, *, pair, fraction):
        """Check a pair is a Fraction's value in lowest terms, with its denominator above zero."""
        self.assertEqual(pair, (fraction.numerator, fraction.denominator))

    def test_a_number_becomes_the_pair_that_says_it(self):
        for pair, fraction in pairs():
            with self.subTest(fraction=fraction):
                rational = Rational(fraction.numerator, fraction.denominator)
                self.assertSame(pair=Length.exact(rational), fraction=fraction)
                self.assertSame(pair=Length.exact(fraction), fraction=fraction)
                self.assertSame(pair=Length.of(rational), fraction=fraction)
        for number in WHOLE_NUMBERS:
            with self.subTest(number=number):
                self.assertSame(pair=Length.exact(number), fraction=Fraction(number))

    def test_an_inexact_float_becomes_the_length_it_means(self):
        for number, fraction in INEXACT_FLOATS.items():
            with self.subTest(number=number):
                self.assertSame(pair=Length.exact(number), fraction=fraction)

    def test_three_inexact_twelfths_make_exactly_a_quarter(self):
        twelfth = Length.exact(1 / 12)
        self.assertSame(pair=Length.total([twelfth, twelfth, twelfth]), fraction=Fraction(1, 4))

    def test_a_number_finer_than_any_length_is_tidied_and_only_of_takes_it_as_it_is(self):
        self.assertEqual(Length.exact(TOO_FINE), ZERO)
        self.assertEqual(Length.of(TOO_FINE), (TOO_FINE.numerator, TOO_FINE.denominator))

    def test_a_pair_becomes_the_rational_that_says_it(self):
        for pair, fraction in pairs():
            with self.subTest(fraction=fraction):
                rational = Length.rational(pair)
                self.assertIs(type(rational), Rational)
                self.assertEqual(rational, fraction)

    def test_adding_and_subtracting(self):
        for (first, first_fraction), (second, second_fraction) in two_pairs():
            with self.subTest(first=first, second=second):
                self.assertSame(pair=Length.add(first, second), fraction=first_fraction + second_fraction)
                self.assertSame(pair=Length.subtract(first, second), fraction=first_fraction - second_fraction)

    def test_multiplying_two_lengths(self):
        for (first, first_fraction), (second, second_fraction) in two_pairs():
            with self.subTest(first=first, second=second):
                self.assertSame(pair=Length.multiplied(first, second), fraction=first_fraction * second_fraction)

    def test_a_length_a_whole_number_of_times_over(self):
        for pair, fraction in pairs():
            for count in COUNTS:
                with self.subTest(pair=pair, count=count):
                    self.assertSame(pair=Length.times(pair, count), fraction=fraction * count)

    def test_a_length_shared_among_a_whole_number(self):
        for pair, fraction in pairs():
            for share in SHARES:
                with self.subTest(pair=pair, share=share):
                    self.assertSame(pair=Length.shared(pair, share), fraction=fraction / share)

    def test_how_many_whole_times_one_length_goes_into_another(self):
        for (first, first_fraction), (second, second_fraction) in two_pairs():
            if second_fraction > 0:
                with self.subTest(first=first, second=second):
                    self.assertEqual(Length.whole_times(first, second), first_fraction // second_fraction)

    def test_which_of_two_lengths_is_shorter(self):
        for (first, first_fraction), (second, second_fraction) in two_pairs():
            with self.subTest(first=first, second=second):
                self.assertEqual(Length.less(first, second), first_fraction < second_fraction)
                self.assertEqual(Length.at_most(first, second), first_fraction <= second_fraction)
                self.assertSame(pair=Length.shorter(first, second), fraction=min(first_fraction, second_fraction))
                self.assertSame(pair=Length.longer(first, second), fraction=max(first_fraction, second_fraction))

    def test_the_shorter_and_the_longer_of_two_equal_lengths_is_the_first(self):
        first = (1, 4)
        second = tuple([1, 4])
        self.assertIs(Length.shorter(first, second), first)
        self.assertIs(Length.longer(first, second), first)

    def test_the_longest_and_the_total_of_many(self):
        swept = pairs()
        for size in (1, 2, 5):
            for start in range(0, len(swept) - size, 7):
                some = swept[start:start + size]
                with self.subTest(some=some):
                    self.assertSame(pair=Length.longest([pair for pair, _ in some]), fraction=max(fraction for _, fraction in some))
                    self.assertSame(pair=Length.total([pair for pair, _ in some]), fraction=sum(fraction for _, fraction in some))

    def test_the_total_of_none_is_no_time_at_all(self):
        self.assertEqual(Length.total([]), ZERO)

    def test_whether_a_length_is_longer_than_nothing(self):
        for pair, fraction in pairs():
            with self.subTest(pair=pair):
                self.assertEqual(Length.is_positive(pair), fraction > 0)

    def test_how_far_apart_two_times_are(self):
        for (first, first_fraction), (second, second_fraction) in two_pairs():
            with self.subTest(first=first, second=second):
                self.assertSame(pair=Length.distance(first, second), fraction=abs(first_fraction - second_fraction))


class TestPairsAreNotComparedAsTuples(unittest.TestCase):
    """Why every ordering goes through Length: Python compares tuples one number at a time."""

    def test_python_puts_a_half_before_a_third_and_length_does_not(self):
        self.assertLess(HALF, THIRD)
        self.assertFalse(Length.less(HALF, THIRD))
        self.assertTrue(Length.less(THIRD, HALF))

    def test_equal_lengths_are_equal_pairs(self):
        self.assertEqual(Length.add((1, 4), (1, 4)), HALF)
        self.assertEqual(Length.exact(Rational(2, 4)), HALF)


if __name__ == '__main__':
    unittest.main()
