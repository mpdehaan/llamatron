# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker shows a value as text, shared by its pages. How a new thing is named is in model/objects/naming.py."""

from llamatron.math.rational import Rational
from llamatron.model.objects.naming import name_order
from llamatron.user_strings import marks

SECONDS_PER_MINUTE = 60
# A whole number has this denominator.
WHOLE = 1


def fraction(value):
    """Return a duration from a file as an exact fraction."""
    return Rational(str(value))


def sorted_names(names):
    """Return names in the order a picker shows them, by name ignoring case, a number at a name's end read as a number, as a list's S key sorts, leaving the set's own order alone."""
    return sorted(names, key=name_order)


def plain_number(number):
    """Return an exact number as a whole number if it is one, and otherwise as a decimal, for showing and nudging."""
    return int(number) if number.denominator == WHOLE else float(number)


def tempo_text(tempo):
    """Return a tempo as text, like 120 or 120.5."""
    return str(plain_number(tempo))


def clock(seconds):
    """Return seconds as minutes and seconds, like 3:05, or dashes if they aren't known."""
    if seconds is None:
        return marks.MSG_NO_TIME
    total = int(round(seconds))
    return marks.MSG_CLOCK.format(minutes=total // SECONDS_PER_MINUTE, seconds=total % SECONDS_PER_MINUTE)
