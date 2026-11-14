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
"""Lengths and times as plain pairs of whole numbers, for what a render makes for every step and every note.

A Rational is an object, and a render that makes one for every sum makes tens of thousands of
them to keep a few thousand. Here a length is a tuple, (numerator, denominator), always in lowest
terms with the denominator above zero, so (1, 16) is a sixteenth, and Length is a class of static
methods that does the arithmetic on such pairs without making anything but the pair that is the
answer. Rational stays what the rest of the program uses: the objects a set file stores, a clip's
own length, an exporter's times and every test.

Two pairs are equal exactly when they are the same length, since both are in lowest terms, so
== and != are safe. Which is longer is never asked with <, which compares tuples one number at
a time and would say a half is less than a third: every ordering goes through Length.less and
the methods beside it.
"""

import math

from llamatron.support.rational import Rational

# No time at all, which is also where a clip starts.
ZERO = (0, 1)
# The denominator of a whole number.
WHOLE = 1
# The largest denominator an exact length can have: anything finer is a float's rounding error.
FINEST_LENGTH = 1_000_000
# Looked up once here rather than on the module for every operation.
_gcd = math.gcd


class Length:
    """Arithmetic on lengths held as pairs. Nothing here makes an object: each answer is a pair, a whole number or true or false."""

    __slots__ = ()

    @staticmethod
    def exact(value):
        """Return a number as a pair: a Rational or a whole number as it is, and a float as the nearest length no finer than FINEST_LENGTH.

        Lengths like 1/12 are slightly inexact as floats, so without the rounding three of them
        would fall just short of a quarter note and leave a tiny extra note or rest.
        """
        kind = type(value)
        if kind is Rational and value.denominator <= FINEST_LENGTH:
            return (value.numerator, value.denominator)
        if kind is int:
            return (value, WHOLE)
        tidied = Rational(value).limit_denominator(FINEST_LENGTH)
        return (tidied.numerator, tidied.denominator)

    @staticmethod
    def of(rational):
        """Return a Rational as a pair, exactly as it is."""
        return (rational.numerator, rational.denominator)

    @staticmethod
    def rational(pair):
        """Return a pair as a Rational, for whoever wants a number: a clip's own length, an exporter's times and the tests."""
        return Rational(pair[0], pair[1])

    @staticmethod
    def add(first, second):
        """Return the sum of two lengths."""
        denominator = first[1]
        if denominator == second[1]:
            numerator = first[0] + second[0]
        else:
            numerator = first[0] * second[1] + second[0] * denominator
            denominator *= second[1]
        divisor = _gcd(numerator, denominator)
        if divisor == 1:
            return (numerator, denominator)
        return (numerator // divisor, denominator // divisor)

    @staticmethod
    def subtract(first, second):
        """Return the first length less the second, which is below zero when the second is the longer."""
        denominator = first[1]
        if denominator == second[1]:
            numerator = first[0] - second[0]
        else:
            numerator = first[0] * second[1] - second[0] * denominator
            denominator *= second[1]
        divisor = _gcd(numerator, denominator)
        if divisor == 1:
            return (numerator, denominator)
        return (numerator // divisor, denominator // divisor)

    @staticmethod
    def times(pair, count):
        """Return a length a whole number of times over."""
        numerator = pair[0] * count
        denominator = pair[1]
        divisor = _gcd(numerator, denominator)
        if divisor == 1:
            return (numerator, denominator)
        return (numerator // divisor, denominator // divisor)

    @staticmethod
    def shared(pair, count):
        """Return a length shared equally among a whole number above zero, as a ratchet shares a gate among its notes."""
        numerator = pair[0]
        denominator = pair[1] * count
        divisor = _gcd(numerator, denominator)
        if divisor == 1:
            return (numerator, denominator)
        return (numerator // divisor, denominator // divisor)

    @staticmethod
    def multiplied(first, second):
        """Return one length multiplied by another, as a gate is by what its dot makes of it."""
        numerator = first[0] * second[0]
        denominator = first[1] * second[1]
        divisor = _gcd(numerator, denominator)
        if divisor == 1:
            return (numerator, denominator)
        return (numerator // divisor, denominator // divisor)

    @staticmethod
    def whole_times(first, second):
        """Return how many whole times the second length goes into the first, rounding down, as a time is counted in steps."""
        return (first[0] * second[1]) // (second[0] * first[1])

    @staticmethod
    def less(first, second):
        """Return whether the first length is shorter than the second."""
        return first[0] * second[1] < second[0] * first[1]

    @staticmethod
    def at_most(first, second):
        """Return whether the first length is no longer than the second."""
        return first[0] * second[1] <= second[0] * first[1]

    @staticmethod
    def shorter(first, second):
        """Return the shorter of two lengths, and the first when they are the same."""
        return second if second[0] * first[1] < first[0] * second[1] else first

    @staticmethod
    def longer(first, second):
        """Return the longer of two lengths, and the first when they are the same."""
        return second if first[0] * second[1] < second[0] * first[1] else first

    @staticmethod
    def longest(pairs):
        """Return the longest of some lengths, of which there is at least one."""
        best = None
        for pair in pairs:
            if best is None or best[0] * pair[1] < pair[0] * best[1]:
                best = pair
        return best

    @staticmethod
    def total(pairs):
        """Return the sum of any number of lengths, which is no time at all for none."""
        numerator = 0
        denominator = 1
        for pair in pairs:
            if denominator == pair[1]:
                numerator += pair[0]
            else:
                numerator = numerator * pair[1] + pair[0] * denominator
                denominator *= pair[1]
                divisor = _gcd(numerator, denominator)
                if divisor != 1:
                    numerator //= divisor
                    denominator //= divisor
        divisor = _gcd(numerator, denominator)
        if divisor == 1:
            return (numerator, denominator)
        return (numerator // divisor, denominator // divisor)

    @staticmethod
    def is_positive(pair):
        """Return whether a length is longer than nothing."""
        return pair[0] > 0

    @staticmethod
    def distance(first, second):
        """Return how far apart two times are, whichever comes first."""
        apart = Length.subtract(first, second)
        return (-apart[0], apart[1]) if apart[0] < 0 else apart
