# llamatron: a music program
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
"""The song's draws as it plays: where each draw stands, and the value each use of one takes.

A draw is one process for the whole song, shared by every track, so its uses are counted with the registers' changes
(registers.py): every step that uses a draw notes the use as its clip is played to count its changes, and the scene's timeline
then draws in time order, and at one moment in track order, carrying each draw on from scene to scene.
"""

from llamatron.composition import file_format
from llamatron.composition.file_format import Direction, DrawDirection
from llamatron.playback.step_order import chosen_move, walk_order

# What a draw adds before it has drawn anything, and what a draw with no value in any slot always adds.
NOTHING_DRAWN = 0


class DrawPlay:
    """Where each of the song's four draws stands: how far a draw that repeats exactly has gone, where a draw that chooses as it
    goes is, which slots a serial draw has left this round, and each draw's last value and the slot it came from."""

    __slots__ = ('_draws', '_taken', '_places', '_rounds', '_last')

    def __init__(self, draws):
        """draws is the song's Draw for each name."""
        self._draws = draws
        self._taken = {}
        self._places = {}
        self._rounds = {}
        self._last = {}

    def copy(self):
        """Return the draws standing where these stand, to carry on from without changing these."""
        other = DrawPlay(self._draws)
        other._taken = dict(self._taken)
        other._places = dict(self._places)
        other._rounds = {name: list(left) for name, left in self._rounds.items()}
        other._last = dict(self._last)
        return other

    def values(self):
        """Return each draw's last value, by name, NOTHING_DRAWN for one that has drawn nothing yet."""
        return {name: self._last[name][1] if name in self._last else NOTHING_DRAWN for name in file_format.DRAW_NAMES}

    def places(self):
        """Return the place of the slot each draw last took its value from, by name, for the draws that have drawn."""
        return {name: last[0] for name, last in self._last.items()}

    def last_slot(self, name):
        """Return the place of the slot a draw last took its value from, or None before it has drawn."""
        return self._last[name][0] if name in self._last else None

    def reset(self, name):
        """Send a draw back to its first slot, or a serial draw to a new round. A draw that picks any slot has nothing to reset."""
        self._taken.pop(name, None)
        self._places.pop(name, None)
        self._rounds.pop(name, None)

    def draw(self, *, name, chooser):
        """Take a draw's next value, by its direction, from the slots that hold one, and return it. chooser draws the random choices."""
        draw = self._draws[name]
        filled = draw.filled_places()
        if not filled:
            return NOTHING_DRAWN
        place = filled[self._next_of(name=name, count=len(filled), direction=draw.get_direction(), chooser=chooser)]
        value = draw.get_slots()[place]
        self._last[name] = (place, value)
        return value

    def _next_of(self, *, name, count, direction, chooser):
        """Return which of a draw's count filled slots comes next, counted among the filled slots alone."""
        if direction == DrawDirection.ANY or direction == Direction.RANDOM:
            return chooser.randrange(count)
        if direction == DrawDirection.SERIAL:
            left = self._rounds.get(name) or list(range(count))
            taken = left.pop(chooser.randrange(len(left)))
            self._rounds[name] = left
            return taken
        order = walk_order(count=count, direction=direction)
        if order is not None:
            taken = self._taken.get(name, 0)
            self._taken[name] = taken + 1
            return order[taken % len(order)]
        if name not in self._places:
            self._places[name] = 0
        else:
            self._places[name] = (self._places[name] + chosen_move(direction=direction, choices=chooser)) % count
        return self._places[name]
