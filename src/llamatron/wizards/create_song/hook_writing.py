# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a style's habits say a song's hook and the body of its chorus are written: the hook's behavior and gauges, which
music_theory/hooks/hook_bars.py writes the bar from, and the gauges of the chorus's body.

The body of a chorus is its lines that are not the hook. Its gauges say how much a line reuses the hook's rhythm, how much
silence ends a line, how near the hook's top a line climbs, how settled a line's ending is, and whether a line that returns
answers the line before it note for note. A genre gives a behavior and where each gauge stands, and a song changes any of them.
"""

from llamatron.music_theory.hooks import hook_bars
from llamatron.wizards.create_song import wizard_names

BEHAVIOR = 'behavior'
GAUGES = 'gauges'
DEFAULT_BEHAVIOR = hook_bars.ARCH
HOOK_GAUGES = {hook_bars.CATCHINESS: 7, hook_bars.SIMPLICITY: 6, hook_bars.LEAP: 4, hook_bars.HEIGHT: 7, hook_bars.HOLD: 6, hook_bars.BOUNCE: 3}
# The gauges of a chorus's body.
SAMENESS = 'sameness'
SPACE = 'space'
LIFT = 'lift'
RESOLVE = 'resolve'
CALL_AND_ANSWER = 'call_and_answer'
BODY_GAUGES = {SAMENESS: 6, SPACE: 5, LIFT: 5, RESOLVE: 6, CALL_AND_ANSWER: 6}
# How the bar after a hook's answers it, by the Catchiness gauge: on a plainer rhythm low on the gauge, on the hook's own
# rhythm from its middle, and from high on it with the hook's own notes a place lower.
SAME_RHYTHM_FROM = 4
SAME_NOTES_FROM = 8
# The most silence a line of a chorus's body ends in, in units, at the top of the Space gauge.
MOST_SPACE = 4
# How far under the hook's floor a line of the body is held at the bottom of the Lift gauge, in places.
LIFT_ROOM = 2
# From this far up the Resolve gauge a line's ending settles on a note of its chord, and from this far up Call and answer a
# line that returns keeps its notes and changes its ending alone.
SETTLED_FROM = 5
ANSWERS_FROM = 5


def hook_ways(habits):
    """The behavior and the gauges a hook is written by: the defaults, with what the habits say over them."""
    said = habits.get(wizard_names.HOOK_WRITING) or {}
    return said.get(BEHAVIOR, DEFAULT_BEHAVIOR), {**HOOK_GAUGES, **(said.get(GAUGES) or {})}


def body_ways(habits):
    """The gauges a chorus's body is written by: the defaults, with what the habits say over them."""
    return {**BODY_GAUGES, **((habits.get(wizard_names.BODY_WRITING) or {}).get(GAUGES) or {})}
