# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The order a pattern's steps play in, for each of a step sequencer's directions."""

from llamatron.model.vocabulary.file_format import Direction

# Every list of steps starts at its first step.
FIRST_STEP = 0
# How a step moves in the directions that choose as they go: on, back, or staying put.
MOVE_ON = 1
MOVE_BACK = -1
STAY = 0
# Brownian moves on half the time, back a quarter of the time, and stays put the rest. Eitherway
# moves on or back, half the time each.
CHANCE_OF_MOVING_ON = 0.5
CHANCE_OF_MOVING_ON_OR_BACK = 0.75


class StepOrder:
    """Remembers where a clip is in each list of steps, carrying on across its repeats.

    Directions that choose as they go, like random, take their choices from a random generator
    made from the song's seed, so a render is always the same.
    """

    __slots__ = ('_choices', '_places')

    def __init__(self, choices):
        self._choices = choices
        self._places = {}

    def next_steps(self, *, key, count, direction):
        """Return the next count steps to play from a list of count steps, which is one pass, for the list that key names.

        A direction that repeats exactly has its order worked out once for the pass. One that
        chooses as it goes makes its choices one after another, as it would a step at a time.
        """
        order = walk_order(count=count, direction=direction)
        if order is None:
            return [self._chosen_step(key=(*key, direction), count=count, direction=direction) for _ in range(count)]
        key = (*key, direction)
        taken = self._places.get(key, FIRST_STEP)
        self._places[key] = taken + count
        return [order[place % len(order)] for place in range(taken, taken + count)]

    def _chosen_step(self, *, key, count, direction):
        """Return the next step of a direction that chooses as it goes, from where the list that key names was left."""
        if direction == Direction.RANDOM:
            return self._choices.randrange(count)
        if key not in self._places:
            self._places[key] = FIRST_STEP
            return FIRST_STEP
        self._places[key] = (self._places[key] + chosen_move(direction=direction, choices=self._choices)) % count
        return self._places[key]



def chosen_move(*, direction, choices):
    """Return which way a direction that chooses as it goes moves this time, drawn from choices: brownian on half the time, back
    a quarter and staying put the rest; eitherway on or back, half the time each."""
    chance = choices.random()
    if chance < CHANCE_OF_MOVING_ON:
        return MOVE_ON
    if direction == Direction.BROWNIAN:
        return MOVE_BACK if chance < CHANCE_OF_MOVING_ON_OR_BACK else STAY
    return MOVE_BACK


def walk_order(*, count, direction):
    """Return the steps of a direction that repeats exactly, or None if it's chosen as it goes."""
    forward = list(range(count))
    backward = forward[::-1]
    if direction == Direction.FORWARD:
        return forward
    if direction == Direction.REVERSE_A:
        # The first step, then the rest backwards.
        return [forward[0], *backward[:-1]]
    if direction == Direction.REVERSE_B:
        return backward
    if direction == Direction.ALTERNATE:
        return forward + backward
    if direction == Direction.PENDULUM:
        # Forward and back, without playing either end twice.
        return forward + backward[1:-1]
    return None
