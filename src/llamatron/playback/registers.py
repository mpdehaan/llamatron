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

"""The song's registers as a scene plays: what each step adds to them, and the values each step sees.

The registers are shared by every track, but each track's clip is played on its own. So a scene
is played twice. First every clip is played with a RegisterRecorder, which notes what each step
adds and when, the same way the scene's length is found. A RegisterTimeline then applies those
changes in time order, and at the same moment in track order, starting from the values the scene
starts with. Then every clip is played again with a RegisterReader, so each step sees the values
at its own moment, after its own change. Registers only change pitches and velocities, never
when anything plays, so both plays go through exactly the same steps.
"""

from bisect import bisect_right
from typing import NamedTuple

from llamatron.composition.file_format import REGISTER_NAMES

# What a step sees while a clip is only played to find its changes.
NO_VALUE = 0


class RegisterChange(NamedTuple):
    """What one step adds to the registers: at a time in its scene, from the track at a place in the song."""

    time: object
    place: int
    adds: dict


def starting_values(registers):
    """Return every register's default, as the registers start when rendering starts.

    registers is the song's Register for each name.
    """
    return {name: registers[name].get_default() for name in REGISTER_NAMES}


def with_resets(values, registers, names):
    """Return register values with the named registers set back to their defaults, as a scene that resets them starts."""
    values = dict(values)
    for name in names:
        values[name] = registers[name].get_default()
    return values


class RegisterTimeline:
    """The values of every register through one scene, from what its steps add to them.

    Changes are RegisterChanges, applied in time order, and at the same time in track order.
    """

    __slots__ = ('_start', '_moments', '_values')

    def __init__(self, registers, start, changes):
        self._start = dict(start)
        self._moments, self._values = [], []
        values = dict(start)
        for change in sorted(changes, key=_moment_of):
            for name, amount in change.adds.items():
                values[name] = registers[name].added(values[name], amount)
            self._moments.append((change.time, change.place))
            self._values.append(dict(values))

    def values_at(self, time, place):
        """Return every register's value as a track at a place sees it at a time, after any change it makes then."""
        found = bisect_right(self._moments, (time, place))
        return self._values[found - 1] if found else self._start

    def end_values(self):
        """Return every register's value once the scene is over, which the next scene starts with."""
        return self._values[-1] if self._values else self._start


class RegisterRecorder:
    """Stands in for the registers while a clip is played to find what it adds to the registers.

    Every step sees no value, which doesn't matter, because registers never change when a step plays.
    """

    __slots__ = ('_place', '_changes')

    def __init__(self, place):
        self._place = place
        self._changes = []

    def at_step(self, time, adds):
        """Note what a step adds to the registers at a time in the scene, and return the values it sees."""
        if adds:
            self._changes.append(RegisterChange(time, self._place, adds))
        return no_values()

    def get_changes(self):
        """Return every change noted, as RegisterChanges."""
        return list(self._changes)


class RegisterReader:
    """The registers as one track's steps see them, from its scene's RegisterTimeline."""

    __slots__ = ('_timeline', '_place')

    def __init__(self, timeline, place):
        self._timeline = timeline
        self._place = place

    def at_step(self, time, adds):
        """Return the values a step sees at a time in the scene. What it adds is already in the timeline."""
        return self._timeline.values_at(time, self._place)


def no_values():
    """Return a value of nothing for every register."""
    return dict.fromkeys(REGISTER_NAMES, NO_VALUE)


def _moment_of(change):
    """Return when a change happens, as (time, track place), which is the order changes apply in."""
    return change.time, change.place
