# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The moves a person makes through a form, whatever key makes them: up, down, left and right, and choose.

Each is named as the tracker names the key that makes it, so that a key's name is the move it makes. A cursor stops at every
edge and never goes round from one end to the other (.claude/UX.md): an arrow held down flies to the end and stays there,
which going round would break.
"""

UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'
CHOOSE = 'enter'
# The moves that go one place back, toward the first, where the others go forward.
BACK_MOVES = (UP, LEFT)
ONE_BACK = -1
ONE_FORWARD = 1


def moved(*, place, name, count):
    """Return where a cursor at place goes when a move is made among count places: back for up and left, forward for down and
    right, and stopping at either end."""
    step = ONE_FORWARD
    if name in BACK_MOVES:
        step = ONE_BACK
    return max(min(place + step, count - 1), 0)


def toward(*, here, there, back=UP, forward=DOWN):
    """Return the move that takes a cursor one place nearer another place, or None when it is there."""
    if here == there:
        return None
    return back if there < here else forward
