# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Comparing a set's data with the order of its items counted, which a dictionary's == leaves out."""


def same_in_order(*, first, second):
    """Return whether two pieces of a set's data are equal with every dictionary's keys in the same order too.

    A set's named items are a dictionary in the file's order, so moving a pattern or a track up
    or down changes only the order of its keys, which == on dictionaries ignores: the undo
    history and the unsaved mark compare this way so that a move counts as a change. A piece
    shared between the two is the same at once, which keeps the comparison cheap.
    """
    if first is second:
        return True
    if isinstance(first, dict):
        return isinstance(second, dict) and list(first) == list(second) and all(same_in_order(first=first[key], second=second[key]) for key in first)
    if isinstance(first, list):
        return isinstance(second, list) and len(first) == len(second) and all(same_in_order(first=one, second=other) for one, other in zip(first, second))
    return first == second
