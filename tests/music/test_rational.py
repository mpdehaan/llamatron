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

"""Rational gives exactly the answers Fraction gives, for everything the program asks of a number."""

import math
import operator
import unittest
from fractions import Fraction

from llamatron.support.rational import Rational
from llamatron.strings.errors import ERR_CANT_MAKE

# A sweep of values: the lengths a song uses, halves of them, thirds, negatives and zero.
NUMERATORS = range(-5, 6)
DENOMINATORS = [1, 2, 3, 4, 7, 16, 128]
WHOLE_NUMBERS = range(-5, 6)
FLOATS = [0.25, 0.1, -1.5, 2.0, 1 / 3]
# The operations the program uses on two numbers, and on a number and a whole number.
ARITHMETIC = [operator.add, operator.sub, operator.mul, operator.truediv, operator.floordiv]
COMPARISONS = [operator.eq, operator.ne, operator.lt, operator.le, operator.gt, operator.ge]
# limit_denominator's limit, as exact_length uses it.
FINEST = 1_000_000
WRITTEN = ['5/16', '2', '0', '-3/4', '0.5']
NOT_A_NUMBER = [None, [1, 2]]
NOT_A_WRITTEN_NUMBER = 'three'
MANY_DIGITS = 3

# Names the tests give to their own things, and other values they use.
FIVE_SIXTEENTHS = '5/16'


def rationals():
    """Return every value in the sweep as a Rational, with the Fraction it should equal."""
    return [(Rational(numerator, denominator), Fraction(numerator, denominator))
            for numerator in NUMERATORS for denominator in DENOMINATORS]


class TestRationalAgreesWithFraction(unittest.TestCase):

    def assertSame(self, *, rational, fraction):
        """Check a Rational has a Fraction's value, in lowest terms, with the same hash."""
        self.assertEqual((rational.numerator, rational.denominator), (fraction.numerator, fraction.denominator))
        self.assertEqual(rational, fraction)
        self.assertEqual(hash(rational), hash(fraction))

    def test_it_is_made_in_lowest_terms_from_two_whole_numbers(self):
        for rational, fraction in rationals():
            with self.subTest(fraction=fraction):
                self.assertSame(rational=rational, fraction=fraction)
        self.assertSame(rational=Rational(3, -6), fraction=Fraction(3, -6))

    def test_it_is_made_from_whole_numbers_fractions_floats_and_text(self):
        for whole in WHOLE_NUMBERS:
            self.assertSame(rational=Rational(whole), fraction=Fraction(whole))
        for number in FLOATS:
            self.assertSame(rational=Rational(number), fraction=Fraction(number))
        for text in WRITTEN:
            self.assertSame(rational=Rational(text), fraction=Fraction(text))
        for _, fraction in rationals():
            self.assertSame(rational=Rational(fraction), fraction=fraction)
        one = Rational(1, 3)
        self.assertIs(Rational(one), one)

    def test_anything_else_is_refused(self):
        for value in NOT_A_NUMBER:
            with self.subTest(value=value):
                with self.assertRaises(TypeError) as raised:
                    Rational(value)
                self.assertEqual(str(raised.exception), ERR_CANT_MAKE.format(value=value))
        # Text that isn't a number raises what Fraction raises, which reading a song file catches.
        with self.assertRaises(ValueError):
            Rational(NOT_A_WRITTEN_NUMBER)
        with self.assertRaises(ZeroDivisionError):
            Rational(1, 0)

    def test_arithmetic_with_another_rational(self):
        for left, left_fraction in rationals():
            for right, right_fraction in rationals():
                for operation in ARITHMETIC:
                    if right == 0 and operation in (operator.truediv, operator.floordiv):
                        continue
                    with self.subTest(left=left_fraction, right=right_fraction, operation=operation.__name__):
                        self.assertEqual(operation(left, right), operation(left_fraction, right_fraction))

    def test_arithmetic_with_a_whole_number_on_either_side(self):
        for rational, fraction in rationals():
            for whole in WHOLE_NUMBERS:
                for operation in ARITHMETIC:
                    with self.subTest(rational=fraction, whole=whole, operation=operation.__name__):
                        if whole != 0:
                            self.assertEqual(operation(rational, whole), operation(fraction, whole))
                        if operation is operator.truediv and rational != 0:
                            self.assertEqual(operation(whole, rational), operation(whole, fraction))
                        elif operation in (operator.add, operator.sub, operator.mul):
                            self.assertEqual(operation(whole, rational), operation(whole, fraction))

    def test_arithmetic_with_a_fraction_on_either_side_gives_a_rational(self):
        for rational, fraction in rationals():
            for other, other_fraction in rationals():
                for operation in ARITHMETIC:
                    if other == 0 and operation in (operator.truediv, operator.floordiv):
                        continue
                    with self.subTest(left=fraction, right=other_fraction, operation=operation.__name__):
                        self.assertEqual(operation(rational, other_fraction), operation(fraction, other_fraction))
                        if rational != 0 or operation not in (operator.truediv, operator.floordiv):
                            self.assertEqual(operation(other_fraction, rational), operation(other_fraction, fraction))
        self.assertIsInstance(Rational(1, 2) + Fraction(1, 3), Rational)
        self.assertIsInstance(Fraction(1, 3) + Rational(1, 2), Rational)
        self.assertEqual(Fraction(Rational(5, 16)), Fraction(5, 16))

    def test_division_by_zero_is_refused(self):
        with self.assertRaises(ZeroDivisionError):
            Rational(1, 2) / Rational(0)
        with self.assertRaises(ZeroDivisionError):
            Rational(1, 2) / 0
        with self.assertRaises(ZeroDivisionError):
            1 / Rational(0)

    def test_arithmetic_with_a_float_gives_a_float_as_fraction_does(self):
        for rational, fraction in rationals():
            for number in FLOATS:
                for operation in (operator.add, operator.sub, operator.mul, operator.truediv):
                    with self.subTest(rational=fraction, number=number, operation=operation.__name__):
                        self.assertEqual(operation(rational, number), operation(fraction, number))
                        if rational != 0 or operation is not operator.truediv:
                            self.assertEqual(operation(number, rational), operation(number, fraction))

    def test_comparisons_with_rationals_whole_numbers_floats_and_fractions(self):
        for left, left_fraction in rationals():
            others = [(right, right_fraction) for right, right_fraction in rationals()]
            others += [(whole, whole) for whole in WHOLE_NUMBERS]
            others += [(number, number) for number in FLOATS]
            others += [(right_fraction, right_fraction) for _, right_fraction in rationals()]
            for right, right_value in others:
                for comparison in COMPARISONS:
                    with self.subTest(left=left_fraction, right=right_value, comparison=comparison.__name__):
                        self.assertEqual(comparison(left, right), comparison(left_fraction, right_value))
                        self.assertEqual(comparison(right, left), comparison(right_value, left_fraction))

    def test_sign_truth_and_absolute_value(self):
        for rational, fraction in rationals():
            with self.subTest(fraction=fraction):
                self.assertEqual(-rational, -fraction)
                self.assertEqual(+rational, fraction)
                self.assertEqual(abs(rational), abs(fraction))
                self.assertEqual(bool(rational), bool(fraction))

    def test_rounding_and_conversion(self):
        for rational, fraction in rationals():
            with self.subTest(fraction=fraction):
                self.assertEqual(round(rational), round(fraction))
                self.assertEqual(round(rational, MANY_DIGITS), round(fraction, MANY_DIGITS))
                self.assertEqual(math.floor(rational), math.floor(fraction))
                self.assertEqual(math.ceil(rational), math.ceil(fraction))
                self.assertEqual(math.trunc(rational), math.trunc(fraction))
                self.assertEqual(int(rational), int(fraction))
                self.assertEqual(float(rational), float(fraction))
                self.assertTrue(math.isfinite(rational))

    def test_a_half_rounds_to_the_even_neighbour(self):
        self.assertEqual(round(Rational(1, 2)), 0)
        self.assertEqual(round(Rational(3, 2)), 2)
        self.assertEqual(round(Rational(-1, 2)), 0)
        self.assertEqual(round(Rational(-3, 2)), -2)

    def test_limit_denominator_tidies_a_float(self):
        third = 1 / 3
        self.assertSame(rational=Rational(third).limit_denominator(FINEST), fraction=Fraction(third).limit_denominator(FINEST))
        self.assertEqual(Rational(third).limit_denominator(FINEST), Rational(1, 3))

    def test_equal_values_hash_the_same_so_they_can_share_a_dictionary(self):
        for rational, fraction in rationals():
            with self.subTest(fraction=fraction):
                self.assertEqual(hash(rational), hash(fraction))
                self.assertEqual(hash(rational), hash(float(fraction)) if float(fraction) == fraction else hash(rational))
        self.assertEqual(hash(Rational(3)), hash(3))
        self.assertEqual(len({Rational(1, 2), Fraction(1, 2), 0.5}), 1)

    def test_it_sorts_sums_and_takes_the_smallest_like_fraction(self):
        values = [rational for rational, _ in rationals()]
        fractions = [fraction for _, fraction in rationals()]
        self.assertEqual(sorted(values), sorted(fractions))
        self.assertEqual(sum(values, Rational(0)), sum(fractions, Fraction(0)))
        self.assertEqual(min(values), min(fractions))
        self.assertEqual(max(values), max(fractions))

    def test_text_is_written_like_a_song_file_length(self):
        self.assertEqual(str(Rational(5, 16)), FIVE_SIXTEENTHS)
        self.assertEqual(str(Rational(2)), '2')
        self.assertEqual(repr(Rational(5, 16)), 'Rational(5, 16)')
        self.assertTrue(Rational(2).is_whole())
        self.assertFalse(Rational(5, 16).is_whole())

    def test_it_cannot_be_changed(self):
        with self.assertRaises(AttributeError):
            Rational(1, 2).something = 1
