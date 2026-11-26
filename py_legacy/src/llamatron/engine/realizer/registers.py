# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song's draws as a scene plays: what each step draws and resets, and the values each step sees.

The draws are shared by every track, but each track's clip is played on its own. So a scene is played twice. First every clip
is played with a RegisterRecorder, which notes what each step draws and resets and when, the same way the scene's length is
found. A RegisterTimeline then draws them in time order, and at the same moment in track order, from where the draws stand as
the scene starts. Then every clip is played again with a RegisterReader, so each step sees the values at its own moment, after
its own draws. A step draws whether its note sounds or not, and the values only change pitches and velocities and whether a note
sounds, never when anything plays, so both plays go through exactly the same draws. The classes keep the names they had when
the song also had registers.
"""

from bisect import bisect_right
from typing import NamedTuple

from llamatron.model.schema import file_format

# What a step sees while a clip is only played to find its changes.
NO_VALUE = 0
# The place a clip reads the values from as its pattern starts over: before any step's draws.
AS_A_PASS_STARTS = -1
NO_CHANGES = {}
# How far before a track's own change at a moment its step reads the values to decide whether the clip goes on.
BEFORE_OWN_CHANGE = 0.5
# How far before a track's own change a step resets and takes its draws: just before its statements read them.
CONDITION_DRAWS = 0.75
# How far before a track's own change the first step of a pass takes its draws and reads the values: after the step before it
# reads them, which a Restart When can make a step at the same moment, so that a restarting step never reads the next pass's draw.
PASS_START_DRAWS = 0.4
PASS_START_READS = 0.3
# How far before a track's own change a clip resets the draws it resets as it starts: after every track before it, before any of
# its own steps draws. A clip starts with its scene.
CLIP_RESETS = 0.9
CLIP_START = 0
NO_DRAWS = ()


class RegisterChange(NamedTuple):
    """What one step does to the draws: at a time in its scene, from the track at a place in the song, the draws it uses, each
    drawing once, and the draws it resets before it draws (draws.py)."""

    time: object
    place: int
    draws: tuple
    draw_resets: tuple


def starting_values():
    """Return every draw as having drawn nothing yet, as the draws start when rendering starts."""
    return dict.fromkeys(file_format.DRAW_NAMES, NO_VALUE)


class RegisterTimeline:
    """The values of every draw through one scene, from what its steps draw.

    Changes are RegisterChanges, drawn in time order, and at the same time in track order.
    """

    __slots__ = ('_start', '_moments', '_values', '_draws', '_draw_moments', '_taken')

    def __init__(self, *, start, changes, chooser=None, draws=None):
        """chooser draws the values of a draw that chooses at random, and draws is where the song's draws stand as the scene
        starts (a DrawPlay), which the timeline carries on from without changing, or None in a song with no draws."""
        self._start = dict(start)
        self._moments = []
        self._values = []
        values = dict(start)
        self._draws = None
        if draws is not None:
            self._draws = draws.copy()
        # Each moment a draw drew, and where every draw then stood, for the Draws page's lights.
        self._draw_moments = []
        # What each change that drew took, by its moment, which a clip's pass reads as it starts.
        self._taken = {}
        for change in sorted(changes, key=_moment_of):
            if self._draws is not None:
                for name in change.draw_resets:
                    self._draws.reset(name)
                for name in change.draws:
                    values[name] = self._draws.draw(name=name, chooser=chooser)
                if change.draws:
                    self._draw_moments.append((change.time, self._draws.places()))
                    self._taken[(change.time, change.place)] = {name: values[name] for name in change.draws}
            self._moments.append((change.time, change.place))
            self._values.append(dict(values))

    def reads_as(self, other):
        """Return whether a clip reading this timeline reads what it would read from another: the same values at every moment,
        and the same draws taken and standing where they stand."""
        return (self._start, self._moments, self._values, self._draw_moments, self._taken, _places_of(self._draws)) == (
            other._start, other._moments, other._values, other._draw_moments, other._taken, _places_of(other._draws))

    def get_draw_moments(self):
        """Return each moment in the scene at which a draw drew, as (time, the place of every draw's last slot), in time order."""
        return list(self._draw_moments)

    def get_end_draws(self):
        """Return where the song's draws stand once the scene is over, which the next scene starts from, or None in a song with no draws."""
        return self._draws

    def draws_taken(self, *, time, place):
        """Return the values a track at a place drew at a time, by draw name, empty where it drew nothing then."""
        return self._taken.get((time, place), NO_CHANGES)

    def values_at(self, *, time, place):
        """Return every draw's value as a track at a place sees it at a time, after any draw it takes then."""
        found = bisect_right(self._moments, (time, place))
        if not found:
            return self._start
        return self._values[found - 1]

    def end_values(self):
        """Return every draw's value once the scene is over, which the next scene starts with."""
        if not self._values:
            return self._start
        return self._values[-1]


class RegisterRecorder:
    """Stands in for the draws while a clip is played to find what its steps draw.

    Every step sees no value, which doesn't matter, because what a step draws never depends on a value.
    """

    __slots__ = ('_place', '_changes')

    def __init__(self, place):
        self._place = place
        self._changes = []

    def at_step(self, time):
        """Return the values a step sees at a time in the scene: none, while a clip is only played to count its draws."""
        return no_values()

    def at_pass(self, time):
        """Return None: nothing is known of the values as a pass starts while a clip is only played to count its draws."""
        return None

    def before_step(self, time, *, first=False):
        """Return None: nothing is known of the values while a clip is only played to count changes that depend on none of them."""
        return None

    def as_clip_starts(self, draw_resets):
        """Note the draws a clip resets as it starts."""
        self._changes.append(RegisterChange(CLIP_START, self._place - CLIP_RESETS, NO_DRAWS, tuple(draw_resets)))

    def before_statements(self, *, time, draws, draw_resets, first=False):
        """Note the draws a step resets and then takes at a time in the scene, just before its statements read the values; first
        says it is the first step of a pass."""
        self._changes.append(RegisterChange(time, self._place - _draws_place(first), draws, draw_resets))

    def is_counting(self):
        """Return true: a clip played to count its draws plays every note, as if neither probability nor a condition silenced one."""
        return True

    def get_changes(self):
        """Return every change noted, as RegisterChanges."""
        return list(self._changes)


class RegisterReader:
    """The draws' values as one track's steps see them, from its scene's RegisterTimeline."""

    __slots__ = ('_timeline', '_place')

    def __init__(self, *, timeline, place):
        self._timeline = timeline
        self._place = place

    def is_counting(self):
        """Return false: a finished clip's notes are silenced by probability and conditions as they play."""
        return False

    def at_pass(self, time):
        """Return the values a clip sees as its pattern starts over at a time in the scene."""
        values = self._timeline.values_at(time=time, place=AS_A_PASS_STARTS)
        # The pass's first step draws before anything reads the values, and the clip's statements read what it drew.
        taken = self._timeline.draws_taken(time=time, place=self._place - PASS_START_DRAWS)
        if not taken:
            return values
        return {**values, **taken}

    def at_step(self, time):
        """Return the values a step sees at a time in the scene. What it draws is already in the timeline."""
        return self._timeline.values_at(time=time, place=self._place)

    def before_step(self, time, *, first=False):
        """Return the values as a step's statements read them at a time in the scene, after its own draws and every earlier track's then."""
        return self._timeline.values_at(time=time, place=self._place - _reads_place(first))

    def as_clip_starts(self, draw_resets):
        """Do nothing: what the clip resets is already in the timeline."""

    def before_statements(self, *, time, draws, draw_resets, first=False):
        """Do nothing: what a step draws is already in the timeline, and before_step sees it."""


class RegisterTrial(RegisterRecorder):
    """Stands in for the draws while a clip whose statements can end it is played to find its draws and its length.

    Such a clip's draws depend on the values, since a step it never reaches draws nothing. So it notes its draws as a
    RegisterRecorder does, and decides whether it goes on from a guess at the scene's timeline. The scene is played again with the timeline its
    changes make until that timeline is the guess (SongRealizer), which it comes to because a
    value at any moment depends only on the changes before it.
    """

    __slots__ = ('_timeline',)

    def __init__(self, *, place, timeline):
        super().__init__(place)
        self._timeline = timeline

    def before_step(self, time, *, first=False):
        """Return the values as a step's statements read them at a time in the scene, by the guess."""
        return self._timeline.values_at(time=time, place=self._place - _reads_place(first))


class RegisterSolo(RegisterRecorder):
    """The first guess for a clip whose statements can end it: the clip played as if no other track drew.

    It keeps the draws' values itself, from the values its scene starts with, taking each value its steps draw, so that a
    statement reading a draw sees what the step drew. With one track counting, the usual case, the guess is already right; where
    other tracks count too, the trials after it put that right.
    """

    __slots__ = ('_values', '_chooser', '_draws')

    def __init__(self, *, place, start, draws, chooser):
        """start is every draw's value as the scene starts, and draws where the song's draws stand then, or None in a song with
        no draws, which the guess carries on from without changing."""
        super().__init__(place)
        self._values = dict(start)
        self._chooser = chooser
        self._draws = None
        if draws is not None:
            self._draws = draws.copy()

    def before_step(self, time, *, first=False):
        """Return the values as a step's statements read them, after its own draws."""
        return self._values

    def as_clip_starts(self, draw_resets):
        """Note the draws the clip resets as it starts, and reset them."""
        super().as_clip_starts(draw_resets)
        if self._draws is None:
            return
        for name in draw_resets:
            self._draws.reset(name)

    def before_statements(self, *, time, draws, draw_resets, first=False):
        """Note the draws a step resets and takes, and take them, so that the step's statements read what it drew."""
        super().before_statements(time=time, draws=draws, draw_resets=draw_resets, first=first)
        if self._draws is None:
            return
        for name in draw_resets:
            self._draws.reset(name)
        for name in draws:
            self._values[name] = self._draws.draw(name=name, chooser=self._chooser)


def no_values():
    """Return a value of nothing for every draw."""
    return dict.fromkeys(file_format.DRAW_NAMES, NO_VALUE)


def _moment_of(change):
    """Return when a change happens, as (time, track place), which is the order changes apply in."""
    return change.time, change.place


def _places_of(draws):
    """Return where the song's draws stand, or None in a song with no draws."""
    if draws is None:
        return None
    return draws.places()


def _draws_place(first):
    """Return how far before a track's own change a step takes its draws: the first step of a pass after any step before it reads."""
    if first:
        return PASS_START_DRAWS
    return CONDITION_DRAWS


def _reads_place(first):
    """Return how far before a track's own change a step's statements read the values: the first step of a pass after its own draws."""
    if first:
        return PASS_START_READS
    return BEFORE_OWN_CHANGE
