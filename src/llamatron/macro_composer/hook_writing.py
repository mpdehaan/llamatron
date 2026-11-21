# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a song's hook and the body of its chorus are written: a way of writing and a few gauges, each from 0 to 9.

A hook is one bar of three to seven notes, counted in eight units, that a song is known by. A behavior says what kind of
figure the bar is, and the gauges say how much its rhythm repeats, how few its notes are, how far it leaps, how high its top
sits, how long its last note is held and how far off the beat it starts. Whatever the gauges say, some things always hold:
the bar has at most four pitches within a sixth and one leap at most, and it ends on a long note or a silence.

The body of a chorus is its lines that are not the hook. Its gauges say how much a line reuses the hook's rhythm, how much
silence ends a line, how near the hook's top a line climbs, how settled a line's ending is, and whether a line that returns
answers the line before it note for note.

A genre gives a behavior and where each gauge stands, and a song changes any of them.
"""

import itertools

from llamatron.macro_composer import hook_kinds

# The habits a style or a song says its hook and its chorus's body are written by.
HOOK_WRITING = 'hook_writing'
BODY_WRITING = 'body_writing'
BEHAVIOR = 'behavior'
GAUGES = 'gauges'
# The behaviors of a hook: one or two pitches whose rhythm does the work; up and back; a leap to the top and a fall by step; a
# short cell, a silence and the cell again; one shape said again a step higher.
CHANT = 'chant'
ARCH = 'arch'
LEAP_AND_FALL = 'leap and fall'
CALL = 'call'
LADDER = 'ladder'
BEHAVIORS = (CHANT, ARCH, LEAP_AND_FALL, CALL, LADDER)
DEFAULT_BEHAVIOR = ARCH
# A hook's gauges.
CATCHINESS = 'catchiness'
SIMPLICITY = 'simplicity'
LEAP = 'leap'
HEIGHT = 'height'
HOLD = 'hold'
BOUNCE = 'bounce'
HOOK_GAUGES = {CATCHINESS: 7, SIMPLICITY: 6, LEAP: 4, HEIGHT: 7, HOLD: 6, BOUNCE: 3}
# The gauges that change a hook of each behavior: a chant and a ladder have no leap.
HOOK_GAUGES_OF = {
    CHANT: (CATCHINESS, SIMPLICITY, HEIGHT, HOLD, BOUNCE),
    ARCH: (CATCHINESS, SIMPLICITY, LEAP, HEIGHT, HOLD, BOUNCE),
    LEAP_AND_FALL: (CATCHINESS, SIMPLICITY, LEAP, HEIGHT, HOLD, BOUNCE),
    CALL: (CATCHINESS, SIMPLICITY, LEAP, HEIGHT, HOLD, BOUNCE),
    LADDER: (CATCHINESS, SIMPLICITY, LEAP, HEIGHT, HOLD, BOUNCE),
}
# The gauges of a chorus's body.
SAMENESS = 'sameness'
SPACE = 'space'
LIFT = 'lift'
RESOLVE = 'resolve'
CALL_AND_ANSWER = 'call_and_answer'
BODY_GAUGES = {SAMENESS: 6, SPACE: 5, LIFT: 5, RESOLVE: 6, CALL_AND_ANSWER: 6}
LOWEST = 0
HIGHEST = 9
UNITS = hook_kinds.UNITS
# A hook has this many notes, the fewest where Simplicity is highest.
FEWEST_NOTES = 3
MOST_NOTES = 7
# The last note is held this many units, and a note of one unit is followed by a silence, so that the bar always ends in a long note or a silence.
SHORTEST_HOLD = 1
LONGEST_HOLD = 4
SHORTEST_TAIL = 2
# A note before the last lasts no more than this many units.
LONGEST_SHORT_NOTE = 3
# From this far up the Bounce gauge the bar starts a unit after the beat.
LATE_START_FROM = 7
LATE_START = 1
# A leap is of this many places: none low on the Leap gauge, a skip in its middle, and a leap high on it.
SKIP_FROM = 4
LEAP_FROM = 7
STEP = 1
SKIP = 2
WIDE = 3
DEEPEST = hook_kinds.DEEPEST
# How many of the rhythms nearest what the gauges ask a take chooses among, so that another take is another rhythm.
RHYTHM_DECK = 4
# From this far up the Catchiness gauge a chant stays on one pitch.
ONE_PITCH_FROM = 7
# A call's cell is of three notes low on the Simplicity gauge and of two from this far up it, the two lasting two units
# where the last note is held long, from this far up the Hold gauge, else three.
SHORT_CELL_FROM = 5
SHORT_CELL = (1, 1)
BUSY_CELL = (1, 1, 1)
CELLS_OF_TWO = ((1, 2), (2, 1))
CALL_GAP = 1
# A ladder's cell is of this many notes, each cell a step above the one before.
LADDER_CELLS = (2, 3)
# The farthest below its top a ladder starts, in places of the style's ladder, since its rungs may be wide.
LADDER_DEEPEST = 5
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


def share(position):
    """A gauge's position as a share from 0, its lowest, to 1, its highest."""
    return (position - LOWEST) / (HIGHEST - LOWEST)


def is_position(value):
    return isinstance(value, int) and not isinstance(value, bool) and LOWEST <= value <= HIGHEST


def hook_ways(habits):
    """The behavior and the gauges a hook is written by: the defaults, with what the habits say over them."""
    said = habits.get(HOOK_WRITING) or {}
    return said.get(BEHAVIOR, DEFAULT_BEHAVIOR), {**HOOK_GAUGES, **(said.get(GAUGES) or {})}


def body_ways(habits):
    """The gauges a chorus's body is written by: the defaults, with what the habits say over them."""
    return {**BODY_GAUGES, **((habits.get(BODY_WRITING) or {}).get(GAUGES) or {})}


def leap_size(gauges):
    """How many places the one leap of a hook covers: a step where there is none."""
    if gauges[LEAP] >= LEAP_FROM:
        return WIDE
    return SKIP if gauges[LEAP] >= SKIP_FROM else STEP


def tail_of(gauges):
    """The end of the bar: the last note's length and the silence after it."""
    held = SHORTEST_HOLD + round(share(gauges[HOLD]) * (LONGEST_HOLD - SHORTEST_HOLD))
    return held, max(0, SHORTEST_TAIL - held)


def fillings(*, units, count):
    """Every way of filling some units with so many notes of one to three units each."""
    lengths = range(1, LONGEST_SHORT_NOTE + 1)
    return [filling for filling in itertools.product(lengths, repeat=count) if sum(filling) == units]


def off_the_beat(*, lengths, start):
    """The share of a run of notes that begin off the beat, the beat being every second unit."""
    at = start
    off = 0
    for length in lengths:
        off += at % 2
        at += length
    return off / len(lengths)


def repeating(lengths):
    """The share of a run of notes whose length is the length of the note before, or of the note before that."""
    if len(lengths) < 2:
        return 1.0
    same = sum(1 for place in range(1, len(lengths)) if lengths[place] == lengths[place - 1] or (place > 1 and lengths[place] == lengths[place - 2]))
    return same / (len(lengths) - 1)


def call_rhythm(*, gauges):
    """A call's bar: a short cell, a silence, and the cell again with its last note held to the bar's end."""
    late = LATE_START if gauges[BOUNCE] >= LATE_START_FROM else 0
    if gauges[SIMPLICITY] < SHORT_CELL_FROM:
        cell = BUSY_CELL
    elif gauges[HOLD] >= SHORT_CELL_FROM:
        cell = SHORT_CELL
    else:
        cell = CELLS_OF_TWO[gauges[BOUNCE] % len(CELLS_OF_TWO)]
    left = UNITS - late - 2 * sum(cell) - CALL_GAP
    if left < 0:
        late = 0
        left = UNITS - 2 * sum(cell) - CALL_GAP
    return ([-late] if late else []) + [*cell, -CALL_GAP, *cell[:-1], cell[-1] + left]


def rhythms_for(*, gauges):
    """The rhythms of a hook's bar nearest what the gauges ask, the nearest first: each the lengths of its notes, a silence
    written as a length below zero."""
    held, silence = tail_of(gauges)
    late = LATE_START if gauges[BOUNCE] >= LATE_START_FROM else 0
    wanted = MOST_NOTES - round(share(gauges[SIMPLICITY]) * (MOST_NOTES - FEWEST_NOTES))
    head_units = UNITS - late - held - silence
    count = max(-(-head_units // LONGEST_SHORT_NOTE), min(wanted - 1, head_units))
    heads = fillings(units=head_units, count=count)
    heads.sort(key=lambda head: (abs(off_the_beat(lengths=head, start=late) - share(gauges[BOUNCE])) + abs(repeating(head) - share(gauges[CATCHINESS])), head))
    return [([-late] if late else []) + [*head, held] + ([-silence] if silence else []) for head in heads[:RHYTHM_DECK]]


def with_leap(*, depths, at, size):
    """A run of depths with one leap of a size into the note at a place: every note before it is lowered, none deeper than the deepest."""
    return [min(DEEPEST, depth + size - STEP) if place < at else depth for place, depth in enumerate(depths)]


def depths_for(*, behavior, gauges, count, turn):
    """How far below the hook's top each of its notes sits. A turn is another form of the same behavior, for another take."""
    size = leap_size(gauges)
    if behavior == CHANT:
        if gauges[CATCHINESS] >= ONE_PITCH_FROM and not turn % 2:
            return [0] * count
        # One pitch with its neighbour once, before the last note or after the first.
        beside = count - 2 if not turn % 2 else 1
        return [1 if place == beside else 0 for place in range(count)]
    if behavior == LEAP_AND_FALL:
        # From below, a leap to the top, and a fall by step; a leap is at least a skip here.
        return [max(size, SKIP)] + [min(DEEPEST, place) for place in range(count - 1)]
    if behavior == CALL:
        half = count // 2
        cell = [min(DEEPEST, (half - 1 - place) * (size if place == 0 and half > 1 else STEP)) for place in range(half)]
        return [*cell, *cell] if not turn % 2 else [*cell, *[max(0, depth - 1) for depth in cell]]
    if behavior == LADDER:
        cell = LADDER_CELLS[turn % len(LADDER_CELLS)]
        rising = [(cell - 1 - place % cell) - place // cell for place in range(count)]
        lowest = min(rising)
        # The Leap gauge is the size of each rung: by step, by a skip, or wider.
        return [min(LADDER_DEEPEST, (depth - lowest) * size) for depth in rising[:-1]] + [0]
    # An arch: up to the top and back, the top in the middle or a note later; the leap, where there is one, is into the top.
    peak = min(count - 2, count // 2 + turn % 2) if count > 2 else 0
    arch = [min(DEEPEST, abs(place - peak)) for place in range(count)]
    return with_leap(depths=arch, at=peak, size=size)


def bar_of(*, behavior, gauges, order, take):
    """A hook's bar at a take: the lengths of its notes and silences, and each note's depth below the top. The order is a
    number of the song's own, which says where among the nearest rhythms its first take starts."""
    if behavior == CALL:
        lengths = call_rhythm(gauges=gauges)
        turn = take
    else:
        nearest = rhythms_for(gauges=gauges)
        lengths = nearest[(order + take) % len(nearest)]
        turn = take // len(nearest)
    count = sum(1 for length in lengths if length > 0)
    depths = depths_for(behavior=behavior, gauges=gauges, count=count, turn=turn)
    return lengths, [depth - min(depths) for depth in depths]


def plainer(lengths):
    """A bar's rhythm made plainer: each two notes joined into one, a silence kept, so that a line on it has fewer and longer notes."""
    plain = []
    held = 0
    joined = 0
    for length in lengths:
        if length < 0:
            if held:
                plain.append(held)
                held = 0
                joined = 0
            plain.append(length)
            continue
        held += length
        joined += 1
        if joined == 2:
            plain.append(held)
            held = 0
            joined = 0
    if held:
        plain.append(held)
    return plain
