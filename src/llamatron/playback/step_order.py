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

from llamatron.composition.file_format import FORWARD


class StepOrder:
    """Remembers where a clip is in each list of steps, carrying on across its repeats.

    Directions that choose as they go, like random, take their choices from a random generator
    made from the song's seed, so a render is always the same.
    """

    def __init__(self, choices):
        self._choices = choices
        self._places = {}

    def next_step(self, key, count, direction):
        """Return the next step to play from a list of count steps, for the list that key names."""
        key = (*key, direction)
        order = _walk_order(count, direction)
        if order is not None:
            taken = self._places.get(key, 0)
            self._places[key] = taken + 1
            return order[taken % len(order)]
        if direction == 'random':
            return self._choices.randrange(count)
        if key not in self._places:
            self._places[key] = 0
            return 0
        chance = self._choices.random()
        if direction == 'brownian':
            move = 1 if chance < 0.5 else (-1 if chance < 0.75 else 0)
        else:
            move = 1 if chance < 0.5 else -1
        self._places[key] = (self._places[key] + move) % count
        return self._places[key]


def _walk_order(count, direction):
    """Return the steps of a direction that repeats exactly, or None if it's chosen as it goes."""
    forward, backward = list(range(count)), list(range(count - 1, -1, -1))
    if direction == FORWARD:
        return forward
    if direction == 'reverse_a':
        return [0, *backward[:-1]]
    if direction == 'reverse_b':
        return backward
    if direction == 'alternate':
        return forward + backward
    if direction == 'pendulum':
        return forward + backward[1:-1]
    return None
