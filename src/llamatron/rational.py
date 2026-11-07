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

"""Exact numbers for lengths and times: a numerator over a denominator, so that three triplets make exactly a quarter.

The standard library's Fraction does this too, but it's written for every kind of number, so
each operation checks what it was given against several types and rebuilds the result through
a constructor that checks again. Rendering does hundreds of thousands of these operations, and
Rational does only what llamatron asks of a number: arithmetic and comparison with another
Rational or a whole number, hashing, rounding and conversion. That makes it about twice as fast
per operation, and it gives exactly the same answers, which test_rational.py checks against
Fraction. Mixed with a float it gives a float, as Fraction does, so floats only get in where the
Clip API accepts them, and exact_length turns those back into Rationals.

Rationals are immutable. numerator and denominator are read directly, like Fraction's, with
the denominator always positive and the two always in lowest terms.
"""

import math
import sys
from fractions import Fraction

MSG_CANT_MAKE = 'expected a whole number, a fraction, a float or text like 5/16, got {value!r}'
MSG_DIVIDE_BY_ZERO = 'division by zero'
# The denominator of a whole number.
WHOLE = 1
# The kinds of value a Rational can be made from, besides another Rational.
NUMBER_TYPES = (int, Fraction, float, str)
# How Python hashes numbers, so that equal values hash the same whatever their type.
HASH_MODULUS = sys.hash_info.modulus
HASH_INF = sys.hash_info.inf
# Python's hash never returns -1, which means an error, so it uses -2 instead.
HASH_ERROR = -1
HASH_INSTEAD_OF_ERROR = -2


def _reduced(numerator, denominator):
    """Return a Rational in lowest terms from a numerator and a positive denominator.

    Every operation ends here, so it stays as short as it can: one gcd, and the two fields set.
    """
    divisor = math.gcd(numerator, denominator)
    if divisor != 1:
        numerator //= divisor
        denominator //= divisor
    rational = object.__new__(Rational)
    rational.numerator = numerator
    rational.denominator = denominator
    return rational


class Rational:
    """An exact number: Rational(1, 16) is a sixteenth, Rational(3) is three, and Rational('5/16') reads a written length."""

    __slots__ = ('numerator', 'denominator')

    def __new__(cls, value=0, denominator=None):
        if denominator is None:
            return _from_one_value(value)
        if denominator == 0:
            raise ZeroDivisionError(MSG_DIVIDE_BY_ZERO)
        if denominator < 0:
            value, denominator = -value, -denominator
        return _reduced(value, denominator)

    def limit_denominator(self, most):
        """Return the closest Rational whose denominator is at most most, which tidies a float's rounding error."""
        return _from_fraction(Fraction(self.numerator, self.denominator).limit_denominator(most))

    def is_whole(self):
        """Return whether it's a whole number."""
        return self.denominator == WHOLE

    def as_integer_ratio(self):
        """Return the numerator and denominator, which is also how Fraction reads a Rational."""
        return self.numerator, self.denominator

    # Arithmetic. Each method handles another Rational first, which is the common case, then a
    # whole number, then a float, and leaves anything else to the other side. A Fraction is
    # turned into a Rational first, so that the two can be mixed.

    def __add__(self, other):
        kind = type(other)
        if kind is Fraction:
            other = _from_fraction(other)
            kind = Rational
        if kind is Rational:
            if self.denominator == other.denominator:
                return _reduced(self.numerator + other.numerator, self.denominator)
            return _reduced(
                self.numerator * other.denominator + other.numerator * self.denominator,
                self.denominator * other.denominator,
            )
        if kind is int:
            return _reduced(self.numerator + other * self.denominator, self.denominator)
        if kind is float:
            return float(self) + other
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        kind = type(other)
        if kind is Fraction:
            other = _from_fraction(other)
            kind = Rational
        if kind is Rational:
            if self.denominator == other.denominator:
                return _reduced(self.numerator - other.numerator, self.denominator)
            return _reduced(
                self.numerator * other.denominator - other.numerator * self.denominator,
                self.denominator * other.denominator,
            )
        if kind is int:
            return _reduced(self.numerator - other * self.denominator, self.denominator)
        if kind is float:
            return float(self) - other
        return NotImplemented

    def __rsub__(self, other):
        kind = type(other)
        if kind is Fraction:
            return _from_fraction(other) - self
        if kind is int:
            return _reduced(other * self.denominator - self.numerator, self.denominator)
        if kind is float:
            return other - float(self)
        return NotImplemented

    def __mul__(self, other):
        kind = type(other)
        if kind is Fraction:
            other = _from_fraction(other)
            kind = Rational
        if kind is Rational:
            return _reduced(self.numerator * other.numerator, self.denominator * other.denominator)
        if kind is int:
            return _reduced(self.numerator * other, self.denominator)
        if kind is float:
            return float(self) * other
        return NotImplemented

    __rmul__ = __mul__

    def __truediv__(self, other):
        kind = type(other)
        if kind is Fraction:
            other = _from_fraction(other)
            kind = Rational
        if kind is Rational:
            return _divided(self.numerator * other.denominator, self.denominator * other.numerator)
        if kind is int:
            return _divided(self.numerator, self.denominator * other)
        if kind is float:
            return float(self) / other
        return NotImplemented

    def __rtruediv__(self, other):
        kind = type(other)
        if kind is Fraction:
            return _from_fraction(other) / self
        if kind is int:
            return _divided(other * self.denominator, self.numerator)
        if kind is float:
            return other / float(self)
        return NotImplemented

    def __floordiv__(self, other):
        """Return how many whole times other goes into it, as Fraction does: a whole number."""
        kind = type(other)
        if kind is Fraction:
            other = _from_fraction(other)
            kind = Rational
        if kind is Rational:
            return (self.numerator * other.denominator) // (self.denominator * other.numerator)
        if kind is int:
            return self.numerator // (self.denominator * other)
        return NotImplemented

    def __rfloordiv__(self, other):
        kind = type(other)
        if kind is Fraction:
            return _from_fraction(other) // self
        if kind is int:
            return (other * self.denominator) // self.numerator
        return NotImplemented

    def __neg__(self):
        return _reduced(-self.numerator, self.denominator)

    def __pos__(self):
        return self

    def __abs__(self):
        return _reduced(abs(self.numerator), self.denominator)

    def __bool__(self):
        return self.numerator != 0

    # Conversions.

    def __float__(self):
        return self.numerator / self.denominator

    def __int__(self):
        return math.trunc(self)

    def __trunc__(self):
        """Return the whole number towards zero, as int() gives."""
        if self.numerator < 0:
            return -(-self.numerator // self.denominator)
        return self.numerator // self.denominator

    def __floor__(self):
        return self.numerator // self.denominator

    def __ceil__(self):
        return -(-self.numerator // self.denominator)

    def __round__(self, ndigits=None):
        """Return the nearest whole number, with a half going to the even neighbour, as round() does for every number."""
        if ndigits is not None:
            return _from_fraction(round(Fraction(self.numerator, self.denominator), ndigits))
        whole, remainder = divmod(self.numerator, self.denominator)
        if remainder * 2 < self.denominator:
            return whole
        if remainder * 2 > self.denominator:
            return whole + 1
        return whole if whole % 2 == 0 else whole + 1

    # Comparison. Equal values hash the same as ints, floats and Fractions, so that a Rational
    # can be a dictionary key beside them.

    def __eq__(self, other):
        kind = type(other)
        if kind is Rational:
            return self.numerator == other.numerator and self.denominator == other.denominator
        if kind is int:
            return self.denominator == WHOLE and self.numerator == other
        if kind is float or kind is Fraction:
            return Fraction(self.numerator, self.denominator) == other
        return NotImplemented

    def __hash__(self):
        if self.denominator == WHOLE:
            return hash(self.numerator)
        try:
            inverse = pow(self.denominator, -1, HASH_MODULUS)
        except ValueError:
            # The denominator is a multiple of the modulus, which Python hashes like infinity.
            hashed = HASH_INF
        else:
            hashed = hash(hash(abs(self.numerator)) * inverse)
        result = hashed if self.numerator >= 0 else -hashed
        return HASH_INSTEAD_OF_ERROR if result == HASH_ERROR else result

    def __lt__(self, other):
        kind = type(other)
        if kind is Rational:
            return self.numerator * other.denominator < other.numerator * self.denominator
        if kind is int:
            return self.numerator < other * self.denominator
        if kind is float or kind is Fraction:
            return Fraction(self.numerator, self.denominator) < other
        return NotImplemented

    def __le__(self, other):
        kind = type(other)
        if kind is Rational:
            return self.numerator * other.denominator <= other.numerator * self.denominator
        if kind is int:
            return self.numerator <= other * self.denominator
        if kind is float or kind is Fraction:
            return Fraction(self.numerator, self.denominator) <= other
        return NotImplemented

    def __gt__(self, other):
        kind = type(other)
        if kind is Rational:
            return self.numerator * other.denominator > other.numerator * self.denominator
        if kind is int:
            return self.numerator > other * self.denominator
        if kind is float or kind is Fraction:
            return Fraction(self.numerator, self.denominator) > other
        return NotImplemented

    def __ge__(self, other):
        kind = type(other)
        if kind is Rational:
            return self.numerator * other.denominator >= other.numerator * self.denominator
        if kind is int:
            return self.numerator >= other * self.denominator
        if kind is float or kind is Fraction:
            return Fraction(self.numerator, self.denominator) >= other
        return NotImplemented

    # Text, and copying.

    def __repr__(self):
        return f'Rational({self.numerator}, {self.denominator})'

    def __str__(self):
        """Return it the way a song file writes a length: a whole number, or 5/16."""
        if self.denominator == WHOLE:
            return str(self.numerator)
        return f'{self.numerator}/{self.denominator}'

    def __reduce__(self):
        return Rational, (self.numerator, self.denominator)

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self


def _from_one_value(value):
    """Return a Rational from a whole number, a Fraction, a float (exactly, as Fraction does), text like 5/16 or another Rational."""
    kind = type(value)
    if kind is Rational:
        return value
    if kind is int:
        return _reduced(value, WHOLE)
    if kind is Fraction:
        return _from_fraction(value)
    if kind is float:
        numerator, denominator = value.as_integer_ratio()
        return _reduced(numerator, denominator)
    if kind is str:
        return _from_fraction(Fraction(value))
    raise TypeError(MSG_CANT_MAKE.format(value=value))


def _from_fraction(fraction):
    return _reduced(fraction.numerator, fraction.denominator)


def _divided(numerator, denominator):
    """Return a Rational from a division whose denominator can be zero or negative."""
    if denominator == 0:
        raise ZeroDivisionError(MSG_DIVIDE_BY_ZERO)
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    return _reduced(numerator, denominator)
