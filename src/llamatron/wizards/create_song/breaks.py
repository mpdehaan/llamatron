# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Drum breaks: a bar of drums played as one thing, a kick, a snare and a cymbal written together, where a style's other ways
of playing choose each drum apart. Each is named by its feel and written for this program, in the manner of a kind of break
and no record's strokes. A break may be cut up: its bar taken as slices, some of them swapped for others, the more the further
the cut goes, as a break is rearranged on a sampler.
"""

from llamatron.music_theory.composing import notation
from llamatron.wizards.create_song import wizard_names

# A bar's hits, sixteen to the bar: loud, soft or none.
L = notation.LOUD
S = notation.SOFT
O = notation.NONE
KICK = 'kick'
SNARE = 'snare'
HAT = 'hat'
OPEN = 'open'
RIDE = 'ride'
STEPS_IN_BAR = 16
TUMBLING = 'tumbling break'
SHUFFLING = 'shuffling break'
STUTTERING = 'stuttering break'
ROLLING = 'rolling break'
LAZY = 'lazy break'
DRIVING = 'driving break'
BREAKS = {
    # The kick answers itself late in the bar, and quiet snare notes fall between the loud ones.
    TUMBLING: {
        KICK: [L, O, O, O, O, O, O, O, O, O, L, L, O, O, O, O],
        SNARE: [O, O, O, O, L, O, O, S, O, S, O, O, L, O, O, S],
        HAT: [L, O, L, O, L, O, L, O, L, O, L, O, L, O, L, O],
    },
    # The kick lands off the beat twice, under a ride that leans on the beat.
    SHUFFLING: {
        KICK: [L, O, O, L, O, O, O, O, O, O, L, O, O, L, O, O],
        SNARE: [O, O, O, O, L, O, S, O, O, S, O, S, L, O, O, O],
        RIDE: [L, O, S, O, L, O, S, O, L, O, S, O, L, O, S, O],
    },
    # Two kicks at the start, and the snare trips over itself at the end, where the hat opens.
    STUTTERING: {
        KICK: [L, L, O, O, O, O, L, O, O, O, L, O, O, O, O, O],
        SNARE: [O, O, O, O, L, O, O, O, O, O, O, O, L, S, S, O],
        HAT: [L, O, L, O, L, O, L, O, L, O, L, O, L, O, O, O],
        OPEN: [O, O, O, O, O, O, O, O, O, O, O, O, O, O, L, O],
    },
    # Quiet snare notes all through, over a hat in sixteenths.
    ROLLING: {
        KICK: [L, O, O, O, O, O, L, O, O, L, O, O, O, O, O, O],
        SNARE: [O, O, S, O, L, O, O, S, O, O, S, O, L, O, S, S],
        HAT: [L, S, L, S, L, S, L, S, L, S, L, S, L, S, L, S],
    },
    # Few hits and much room, the hat opening once.
    LAZY: {
        KICK: [L, O, O, O, O, O, O, L, O, O, O, O, O, O, L, O],
        SNARE: [O, O, O, O, L, O, O, O, O, O, O, S, L, O, O, O],
        HAT: [L, O, S, O, L, O, O, O, L, O, S, O, L, O, S, O],
        OPEN: [O, O, O, O, O, O, L, O, O, O, O, O, O, O, O, O],
    },
    # A busy kick under a loud, even hat.
    DRIVING: {
        KICK: [L, O, L, O, O, O, O, L, O, O, L, O, O, O, O, L],
        SNARE: [O, O, O, O, L, O, O, O, O, S, O, O, L, O, O, S],
        HAT: [L, O, L, O, L, O, L, O, L, O, L, O, L, O, L, O],
    },
}
# A slice is an eighth note of the bar.
STEPS_IN_SLICE = 2
SLICES = STEPS_IN_BAR // STEPS_IN_SLICE


def break_names():
    """The breaks there are, in the order they are offered."""
    return list(BREAKS)


def sliced(*, bars, slice_at):
    """What every drum of a bar plays in one slice."""
    return {piece: hits[slice_at * STEPS_IN_SLICE:(slice_at + 1) * STEPS_IN_SLICE] for piece, hits in bars.items()}


def cut_up(*, bars, cut, dice):
    """A break's bar with as many of its slices swapped for others of its slices as the cut says, every drum cut alike, the
    first slice left so that the bar still starts as the break does. The least cut is the break as written. Each slice cut
    is a different one, and what takes its place never sounds the same as what was there, so a further cut is always heard."""
    order = list(range(SLICES))
    for target in dice.sample(range(1, SLICES), cut - wizard_names.LEAST_CUT):
        unlike = [slice_at for slice_at in range(SLICES) if sliced(bars=bars, slice_at=slice_at) != sliced(bars=bars, slice_at=target)]
        if unlike:
            order[target] = dice.choice(unlike)
    return {piece: _reordered(hits=hits, order=order) for piece, hits in bars.items()}


def _reordered(*, hits, order):
    """Return one drum's hits with its slices played in a new order."""
    return [hit for slice_at in order for hit in _slice_of(hits=hits, slice_at=slice_at)]


def _slice_of(*, hits, slice_at):
    """Return the hits of one slice of a bar."""
    return hits[slice_at * STEPS_IN_SLICE:(slice_at + 1) * STEPS_IN_SLICE]
