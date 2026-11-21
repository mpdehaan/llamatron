# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The bars a tag is made of: a tag's rhythm and how far below its top each note sits.

A bar is counted in eight units. A rhythm is the lengths of its notes, a silence written as a length below zero; a contour is
how far below the top each note sits, the top being none. A song's main hook is written by a behavior and gauges
(hook_writing.py); a tag, the song's second hook, takes one of the choppy rhythms here that the main hook does not have.
"""

UNITS = 8
# The contours of a tag: one note with its neighbour once, and two notes in turn.
CHANT = 'chant'
ROCKING = 'rocking'
# The rhythms: starting after the first beat; three and three and two; even eighths with a gap.
AFTER_ONE = 'after the first beat'
THREE_THREE_TWO = 'three and three and two'
EIGHTHS_WITH_A_GAP = 'eighths with a gap'
RHYTHMS = {
    AFTER_ONE: (-1, 1, 2, 2, 2),
    THREE_THREE_TWO: (2, 1, 2, 1, 2),
    EIGHTHS_WITH_A_GAP: (1, 1, 1, -1, 1, 1, 2),
}
# The farthest below its top a hook goes, in places of the style's ladder, about a sixth.
DEEPEST = 3


def depths_of(*, contour, count):
    """How far below the top each of a bar's notes sits."""
    if contour == CHANT:
        # One note, with its neighbour once, before the last.
        return [1 if place == count - 2 else 0 for place in range(count)]
    return [(place + 1) % 2 for place in range(count)]
