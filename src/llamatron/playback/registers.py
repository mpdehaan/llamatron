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

"""The song's registers as a scene plays: what each step sets them to and adds to them, and the values each step sees.

The registers are shared by every track, but each track's clip is played on its own. So a scene
is played twice. First every clip is played with a RegisterRecorder, which notes what each step
sets and adds and when, the same way the scene's length is found. A step's sets come before its
adds. A RegisterTimeline then applies those
changes in time order, and at the same moment in track order, starting from the values the scene
starts with. Then every clip is played again with a RegisterReader, so each step sees the values
at its own moment, after its own change. Registers only change pitches and velocities and whether
a note sounds, never when anything plays or what a step sets or adds (a condition or probability silences a note and never a change), so both plays go
through exactly the same changes.
"""

from bisect import bisect_right
from typing import NamedTuple

from llamatron.composition.file_format import REGISTER_NAMES

# What a step sees while a clip is only played to find its changes.
NO_VALUE = 0
# A place after every track's, for the values once every track has made its change at a moment.
LAST_PLACE = float('inf')
# No register counting the other way, which is how a song starts.
NOT_TURNED = frozenset()
# What happens at one moment happens in this order: the scene's own sets and adds, each clip's as its pattern starts over, in
# track order, and then the steps', in track order. A clip's place is its track's, this far before every step's.
SCENE_PLACE = float('-inf')
CLIPS_BEFORE_STEPS = 1000000
# The place a clip reads the registers from as its pattern starts over: after every clip's own change then, before any step's.
AS_A_PASS_STARTS = -1
NO_CHANGES = {}
# How far before a track's own change at a moment its step reads the registers to decide whether the clip goes on.
BEFORE_OWN_CHANGE = 0.5
# When a scene's own changes happen: as it starts.
SCENE_START = 0


class RegisterChange(NamedTuple):
    """What one step sets the registers to and adds to them: at a time in its scene, from the track at a place in the song."""

    time: object
    place: int
    sets: dict
    adds: dict


def starting_values(registers):
    """Return every register's default, as the registers start when rendering starts.

    registers is the song's Register for each name.
    """
    return {name: registers[name].get_default() for name in REGISTER_NAMES}


def with_resets(*, values, registers, names):
    """Return register values with the named registers set back to their defaults, as a scene that resets them starts."""
    values = dict(values)
    for name in names:
        values[name] = registers[name].get_default()
    return values


class Turned:
    """Which of the registers that reverse are counting the other way, kept by whoever keeps their values, and the one way anything is added to a register.

    A register is turned when an add or a subtraction takes it past an end, and counts forward
    again once the other end is passed, or when anything sets it or resets it.
    """

    __slots__ = ('_registers', '_reversing', '_turned')

    def __init__(self, *, registers, turned):
        self._registers = registers
        self._reversing = frozenset(name for name, register in registers.items() if register.reverses())
        self._turned = set(turned) if self._reversing else NOT_TURNED

    def forward(self, name):
        """Put a register back to counting forward, as a set or a reset does."""
        if name in self._turned:
            self._turned.discard(name)

    def added(self, *, name, value, amount, chooser):
        """Return a register's value with an amount added, as its Reset behavior has it, noting which way it then counts."""
        register = self._registers[name]
        if name not in self._reversing:
            return register.added(value=value, amount=amount, chooser=chooser)
        result, turned = register.reversed(value=value, amount=amount, turned=name in self._turned)
        if turned:
            self._turned.add(name)
        else:
            self._turned.discard(name)
        return result

    def names(self):
        return frozenset(self._turned)


class RegisterTimeline:
    """The values of every register through one scene, from what its steps add to them.

    Changes are RegisterChanges, applied in time order, and at the same time in track order.
    """

    __slots__ = ('_start', '_moments', '_values', '_turned')

    def __init__(self, *, registers, start, changes, chooser=None, turned=NOT_TURNED):
        """chooser draws the random values of a register whose Reset behavior picks one, and turned names the registers that reverse and are counting the other way as the scene starts."""
        self._start = dict(start)
        self._moments = []
        self._values = []
        values = dict(start)
        turned = Turned(registers=registers, turned=turned)
        for change in sorted(changes, key=_moment_of):
            for name, value in change.sets.items():
                values[name] = registers[name].held(value)
                turned.forward(name)
            for name, amount in change.adds.items():
                values[name] = turned.added(name=name, value=values[name], amount=amount, chooser=chooser)
            self._moments.append((change.time, change.place))
            self._values.append(dict(values))
        self._turned = turned.names()

    def end_turned(self):
        """Return the names of the registers that reverse and are counting the other way once the scene is over, which the next scene starts with."""
        return self._turned

    def values_at(self, *, time, place):
        """Return every register's value as a track at a place sees it at a time, after any change it makes then."""
        found = bisect_right(self._moments, (time, place))
        return self._values[found - 1] if found else self._start

    def changes_within(self, *, start, end):
        """Return (time, values) for each moment from start to before end at which a register changed, the values being those after every change made then, in time order."""
        found = []
        for (time, _), values in zip(self._moments, self._values):
            if start <= time < end:
                if found and found[-1][0] == time:
                    found[-1] = (time, values)
                else:
                    found.append((time, values))
        return found

    def values_after(self, time):
        """Return every register's value once every change made at a time, by every track, is done."""
        found = bisect_right(self._moments, (time, LAST_PLACE))
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

    def at_step(self, *, time, sets, adds):
        """Note what a step sets the registers to and adds to them at a time in the scene, and return the values it sees."""
        if sets or adds:
            self._changes.append(RegisterChange(time, self._place, sets, adds))
        return no_values()

    def at_pass(self, *, time, sets, adds):
        """Note what a clip sets the registers to and adds to them as its pattern starts over at a time in the scene, and return None: nothing is known of the values yet."""
        if sets or adds:
            self._changes.append(RegisterChange(time, self._place - CLIPS_BEFORE_STEPS, sets, adds))
        return None

    def before_step(self, time):
        """Return None: nothing is known of the values while a clip is only played to count changes that depend on none of them."""
        return None

    def is_counting(self):
        """Return true: a clip played to count its changes plays every note, as if neither probability nor a condition silenced one, so that what an arpeggiator adds for its notes is counted the same in every take."""
        return True

    def get_changes(self):
        """Return every change noted, as RegisterChanges."""
        return list(self._changes)


class RegisterReader:
    """The registers as one track's steps see them, from its scene's RegisterTimeline."""

    __slots__ = ('_timeline', '_place')

    def __init__(self, *, timeline, place):
        self._timeline = timeline
        self._place = place

    def is_counting(self):
        """Return false: a finished clip's notes are silenced by probability and conditions as they play."""
        return False

    def at_pass(self, *, time, sets, adds):
        """Return the values a clip sees as its pattern starts over at a time in the scene, after every clip's own sets and adds then, which are already in the timeline."""
        return self._timeline.values_at(time=time, place=AS_A_PASS_STARTS)

    def at_step(self, *, time, sets, adds):
        """Return the values a step sees at a time in the scene. What it sets and adds is already in the timeline."""
        return self._timeline.values_at(time=time, place=self._place)

    def before_step(self, time):
        """Return the values as a step is reached at a time in the scene, before the step's own sets and adds, after every earlier track's then."""
        return self._timeline.values_at(time=time, place=self._place - BEFORE_OWN_CHANGE)


class RegisterTrial(RegisterRecorder):
    """Stands in for the registers while a clip whose statements can end it is played to find its changes and its length.

    Such a clip's changes depend on the registers, since a step it never reaches changes
    nothing. So it notes its changes as a RegisterRecorder does, and decides whether it goes
    on from a guess at the scene's timeline. The scene is played again with the timeline its
    changes make until that timeline is the guess (SongRenderer), which it comes to because a
    value at any moment depends only on the changes before it.
    """

    __slots__ = ('_timeline',)

    def __init__(self, *, place, timeline):
        super().__init__(place)
        self._timeline = timeline

    def before_step(self, time):
        """Return the values as a step is reached at a time in the scene, before the step's own sets and adds, by the guess."""
        return self._timeline.values_at(time=time, place=self._place - BEFORE_OWN_CHANGE)


class RegisterSolo(RegisterRecorder):
    """The first guess for a clip whose statements can end it: the clip played as if no other track changed a register.

    It keeps the registers' values itself, from the values its scene starts with, changing
    them by what its own steps set and add. With one track counting, the usual case, the guess
    is already right; where other tracks count too, the trials after it put that right.
    """

    __slots__ = ('_registers', '_values', '_chooser', '_turned')

    def __init__(self, *, place, registers, start, chooser, turned=NOT_TURNED):
        super().__init__(place)
        self._registers = registers
        self._values = dict(start)
        self._chooser = chooser
        self._turned = Turned(registers=registers, turned=turned)

    def at_step(self, *, time, sets, adds):
        self._change(sets=sets, adds=adds)
        return super().at_step(time=time, sets=sets, adds=adds)

    def at_pass(self, *, time, sets, adds):
        self._change(sets=sets, adds=adds)
        return super().at_pass(time=time, sets=sets, adds=adds)

    def before_step(self, time):
        """Return the values as a step is reached, before the step's own sets and adds."""
        return self._values

    def _change(self, *, sets, adds):
        for name, value in sets.items():
            self._values[name] = self._registers[name].held(value)
            self._turned.forward(name)
        for name, amount in adds.items():
            self._values[name] = self._turned.added(name=name, value=self._values[name], amount=amount, chooser=self._chooser)


def scene_change(*, sets, adds):
    """Return what a scene itself sets the registers to and adds to them as it starts, before anything else at that moment, or None when it does neither."""
    return RegisterChange(SCENE_START, SCENE_PLACE, sets, adds) if sets or adds else None


def no_values():
    """Return a value of nothing for every register."""
    return dict.fromkeys(REGISTER_NAMES, NO_VALUE)


def _moment_of(change):
    """Return when a change happens, as (time, track place), which is the order changes apply in."""
    return change.time, change.place
