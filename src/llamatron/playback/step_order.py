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

"""The order a pattern's steps play in, for each of the Cirklon's directions."""

from llamatron.composition.file_format import Direction

# Every list of steps starts at its first step.
FIRST_STEP = 0
# How a step moves in the directions that choose as they go: on, back, or staying put.
MOVE_ON, MOVE_BACK, STAY = 1, -1, 0
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

    def next_step(self, key, count, direction):
        """Return the next step to play from a list of count steps, for the list that key names."""
        key = (*key, direction)
        order = _walk_order(count, direction)
        if order is not None:
            taken = self._places.get(key, FIRST_STEP)
            self._places[key] = taken + 1
            return order[taken % len(order)]
        if direction == Direction.RANDOM:
            return self._choices.randrange(count)
        if key not in self._places:
            self._places[key] = FIRST_STEP
            return FIRST_STEP
        self._places[key] = (self._places[key] + self._chosen_move(direction)) % count
        return self._places[key]

    def _chosen_move(self, direction):
        """Return which way a direction that chooses as it goes moves this time."""
        chance = self._choices.random()
        if chance < CHANCE_OF_MOVING_ON:
            return MOVE_ON
        if direction == Direction.BROWNIAN:
            return MOVE_BACK if chance < CHANCE_OF_MOVING_ON_OR_BACK else STAY
        return MOVE_BACK


def _walk_order(count, direction):
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
