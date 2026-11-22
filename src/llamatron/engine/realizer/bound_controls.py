# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The CC values a clip's bound lanes send: a track's CC lane bound to a register sends the register's value as it changes."""

from llamatron.engine.clips.control import Control
from llamatron.math.rational import Rational
from llamatron.model.values import midi

# Where a clip starts, in whole notes.
START = Rational(0)


def bound_controls(*, bound, timeline, own, end):
    """Return the CC values a clip's bound lanes send: each lane's register, as it is at the clip's start and after each change before end, held to a CC value.

    bound holds (CC number, register name) for each lane that has a CC number on the track and a
    register bound to it; a lane with no CC number sends nothing, bound or not. A value is sent
    only when it differs from the last value the lane sent, the clip's own included, and never at
    a moment where the clip sends a value of its own on the lane, which wins.
    """
    moments = _moments(timeline=timeline, end=end)
    controls = []
    for number, name in bound:
        own_values = _own_values(own=own, number=number)
        last = None
        for time, value, is_own in _sent(own_values=own_values, moments=moments, name=name):
            if is_own:
                last = value
            elif time not in own_values and value != last:
                controls.append(Control(time=time, number=number, value=value))
                last = value
    return controls


def _moments(*, timeline, end):
    """Return the registers' values at the clip's start and after each change before end, as (time, values)."""
    moments = [(START, timeline.values_after(START))]
    for moment in timeline.changes_within(start=START, end=end):
        if moment[0] != START:
            moments.append(moment)
    return moments


def _own_values(*, own, number):
    """Return the values a clip sends of its own on a CC number, by time."""
    values = {}
    for control in own:
        if control.get_number() == number:
            values[control.get_time()] = control.get_value()
    return values


def _sent(*, own_values, moments, name):
    """Return what a lane would send, its own values and its register's, as (time, value, whether it's the clip's own), in order."""
    sent = []
    for time, value in own_values.items():
        sent.append((time, value, True))
    for time, values in moments:
        sent.append((time, _cc_value(values[name]), False))
    sent.sort(key=_sent_order)
    return sent


def _sent_order(item):
    """Return when a lane's value is sent, as (time, whether it's the clip's own), so that the clip's own comes after a bound one at the same time and is what holds."""
    return item[0], item[2]


def _cc_value(value):
    """Return a register's value held to what a CC value can be."""
    return max(min(value, midi.MAX_CC_VALUE), midi.MIN_CC_VALUE)
