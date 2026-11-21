# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Operations on a row: an order of places in a collection of notes, each place a whole number below the collection's size.

They are the moves serial music makes with its row, and the same moves turn a phrase so that its repeats evolve. Each returns a
new row and changes nothing.
"""


def backwards(row):
    """The row from its last place to its first."""
    return list(reversed(row))


def upside_down(*, row, size):
    """The row mirrored around its first place: every step up becomes a step down, kept inside the collection."""
    return [(2 * row[0] - place) % size for place in row]


def moved(*, row, by, size):
    """The row with every place moved up by so many places of the collection, going round at its top."""
    return [(place + by) % size for place in row]


def rotated(*, row, by):
    """The row begun so many places later, the places before the start following its end."""
    return row[by % len(row):] + row[:by % len(row)]
