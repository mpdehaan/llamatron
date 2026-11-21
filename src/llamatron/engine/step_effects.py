# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the generators that change values as the song plays do to one step a clip plays: added to its velocity, its
probability and its degree, and the scale and root that take the clip's place. A plugin's modulation returns them, and the
pattern player applies them to each step."""

from typing import NamedTuple

NOTHING_ADDED = 0


class StepEffects(NamedTuple):
    """What the modulations a clip hears do to one step: added to its velocity, its probability and its degree, and the scale and root that override the clip's, or None."""

    velocity: int
    probability: int
    degree: int
    scale: object
    root: object


NO_EFFECTS = StepEffects(NOTHING_ADDED, NOTHING_ADDED, NOTHING_ADDED, None, None)


def combined(*, first, second):
    """Return two plugins' effects on one step together: their numbers added, and the second's scale and root winning where it gives one."""
    return StepEffects(first.velocity + second.velocity, first.probability + second.probability, first.degree + second.degree, second.scale or first.scale, second.root or first.root)


def heard_at(*, heard, time):
    """Return what every modulation a clip hears does to a step at a song time: heard is each modulation's play with the
    generators the clip names and where each one's clock starts, as (play, names, origins)."""
    effects = NO_EFFECTS
    for play, names, origins in heard:
        effects_now = play.effects(names=names, time=time, origins=origins)
        effects = effects_now if effects is NO_EFFECTS else combined(first=effects, second=effects_now)
    return effects
