# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The order a clip plays its list of patterns in on each pass through the list.

Every order plays every entry of the list exactly once a pass, so that a pass lasts as long
whatever the order: only which pattern comes next changes. The names are a pattern's directions,
each meaning for whole patterns what the direction means for steps.
"""

from llamatron.model.vocabulary.file_format import PatternOrder


def ordered_patterns(*, names, order, place, rolls):
    """Return a clip's patterns in the order one pass plays them: place is the pass, counted from 0, and rolls the random generator the drawn orders use."""
    names = list(names)
    backward = list(reversed(names))
    if order == PatternOrder.REVERSE_A:
        return [*names[:1], *reversed(names[1:])]
    if order == PatternOrder.REVERSE_B:
        return backward
    if order == PatternOrder.ALTERNATE:
        return backward if is_return_pass(place) else names
    if order == PatternOrder.PENDULUM:
        # The way back starts on the pattern before the last, which has just played, and the last then closes the pass.
        return [*backward[1:], *backward[:1]] if is_return_pass(place) else names
    if order == PatternOrder.RANDOM:
        rolls.shuffle(names)
        return names
    if order == PatternOrder.FIRST_THEN_RANDOM:
        rest = names[1:]
        rolls.shuffle(rest)
        return [*names[:1], *rest]
    return names


def is_return_pass(place):
    """Return whether a pass is one that comes back: every second pass, the first going out."""
    return place % 2 == 1
