# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Euclidean rhythms: so many hits spread as evenly as can be over so many steps, which mask a clip so that only the notes starting on a hit play.

A track's mask holds for every clip on it, and a Euclid generator in a clip's chains masks on top
of it: masks stack, so a note plays only where every mask has a hit. A mask is in force once its
hits are set; its steps are a bar of sixteenths unless set, its rotation moves the rhythm that many
steps later, and its step is the clip's pattern's step size unless set.
"""

from typing import NamedTuple

from llamatron.model.file.checks import time_length
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import euclid_setting, EuclidPart, NamedRhythm
from llamatron.model.schema.setting import Checked, WholeNumber
from llamatron.user_strings import errors

# The named rhythms, each its hits and steps, in the order the picker offers them.
NAMED_RHYTHMS = {
    NamedRhythm.TRESILLO: (3, 8), NamedRhythm.CINQUILLO: (5, 8), NamedRhythm.KHAFIF_E_RAMAL: (2, 5), NamedRhythm.AKSAK: (4, 9),
    NamedRhythm.VENDA: (5, 12), NamedRhythm.BEMBE: (7, 12), NamedRhythm.SAMBA: (7, 16), NamedRhythm.BOSSA_NOVA: (5, 16),
}
HIT = True
MISS = False


class EuclidValues(NamedTuple):
    """A mask as set somewhere: its hits, steps and rotation, and its step as written, or None for the pattern's step size."""

    hits: int
    steps: int
    rotate: int
    step: object


def euclid_part_settings(named):
    """Return the descriptions of a mask's four parts, each named by named(part)."""
    return [
        WholeNumber(name=named(EuclidPart.HITS), lowest=limits.MIN_EUCLID, highest=limits.MAX_EUCLID, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(EuclidPart.STEPS), lowest=limits.MIN_EUCLID, highest=limits.MAX_EUCLID, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(EuclidPart.ROTATE), lowest=limits.NO_ROTATION, highest=limits.MAX_EUCLID - 1, error=errors.ERR_BAD_SHAPE_PERCENT),
        Checked(name=named(EuclidPart.STEP), check=time_length),
    ]


def euclid_settings():
    """Return the descriptions of a track's mask settings, like euclid_hits, in the order a file writes them."""
    return euclid_part_settings(euclid_setting)


def euclid_values(value):
    """Return a mask from value(part) for each of its parts, or None when its hits are blank and it masks nothing."""
    hits = value(EuclidPart.HITS)
    if hits is None:
        return None
    steps = value(EuclidPart.STEPS)
    rotate = value(EuclidPart.ROTATE)
    if steps is None:
        steps = limits.DEFAULT_EUCLID_STEPS
    if rotate is None:
        rotate = limits.NO_ROTATION
    return EuclidValues(hits, steps, rotate, value(EuclidPart.STEP))


def rhythm(*, hits, steps, rotate=limits.NO_ROTATION):
    """Return a Euclidean rhythm as a hit or a miss for each step, Bjorklund's way, so that 3 over 8 is X..X..X. and 5 over 8 X.XX.XX., moved rotate steps later.

    Hits past the steps hit every step.
    """
    hits = min(hits, steps)
    groups = [[HIT] for _ in range(hits)]
    rest = [[MISS] for _ in range(steps - hits)]
    while len(rest) > 1:
        paired = min(len(groups), len(rest))
        groups, rest = [groups[place] + rest[place] for place in range(paired)], (groups[paired:] or rest[paired:])
    hits_and_misses = [step for group in groups + rest for step in group]
    shift = rotate % steps
    if not shift:
        return hits_and_misses
    return hits_and_misses[-shift:] + hits_and_misses[:-shift]
