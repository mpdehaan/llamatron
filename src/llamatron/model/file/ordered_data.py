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
        if not isinstance(second, dict) or list(first) != list(second):
            return False
        for key in first:
            if not same_in_order(first=first[key], second=second[key]):
                return False
        return True
    if isinstance(first, list):
        if not isinstance(second, list) or len(first) != len(second):
            return False
        for one, other in zip(first, second):
            if not same_in_order(first=one, second=other):
                return False
        return True
    return first == second
