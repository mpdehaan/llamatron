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
"""How the tracker shows a value as text, shared by its pages. How a new thing is named is in composition/naming.py."""

from llamatron.support.rational import Rational
from llamatron.strings.marks import MSG_CLOCK, MSG_NO_TIME

SECONDS_PER_MINUTE = 60
# A whole number has this denominator.
WHOLE = 1


def fraction(value):
    """Return a duration from a file as an exact fraction."""
    return Rational(str(value))


def sorted_names(names):
    """Return names in the order a picker shows them, alphabetical ignoring case, as a list's S key sorts, leaving the set's own order alone."""
    return sorted(names, key=lambda name: str(name).lower())


def plain_number(number):
    """Return an exact number as a whole number if it is one, and otherwise as a decimal, for showing and nudging."""
    return int(number) if number.denominator == WHOLE else float(number)


def tempo_text(tempo):
    """Return a tempo as text, like 120 or 120.5."""
    return str(plain_number(tempo))


def clock(seconds):
    """Return seconds as minutes and seconds, like 3:05, or dashes if they aren't known."""
    if seconds is None:
        return MSG_NO_TIME
    total = int(round(seconds))
    return MSG_CLOCK.format(minutes=total // SECONDS_PER_MINUTE, seconds=total % SECONDS_PER_MINUTE)
