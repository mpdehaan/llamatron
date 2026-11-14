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
"""Euclidean rhythms: so many hits spread as evenly as can be over so many steps, which mask a clip so that only the notes starting on a hit play, the user's design of 2026-11-11.

A track's mask holds for every clip on it, and a Euclid generator in a clip's chains masks on top
of it: masks stack, so a note plays only where every mask has a hit. A mask is in force once its
hits are set; its steps are a bar of sixteenths unless set, its rotation moves the rhythm that many
steps later, and its step is the clip's pattern's step size unless set.
"""

from typing import NamedTuple

from llamatron.composition.checks import time_length
from llamatron.composition.file_format import EuclidPart, NamedRhythm, euclid_setting
from llamatron.composition.limits import DEFAULT_EUCLID_STEPS, MAX_EUCLID, MIN_EUCLID, NO_ROTATION
from llamatron.composition.setting import Checked, WholeNumber
from llamatron.strings.errors import ERR_BAD_SHAPE_PERCENT

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
        WholeNumber(name=named(EuclidPart.HITS), lowest=MIN_EUCLID, highest=MAX_EUCLID, error=ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(EuclidPart.STEPS), lowest=MIN_EUCLID, highest=MAX_EUCLID, error=ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(EuclidPart.ROTATE), lowest=NO_ROTATION, highest=MAX_EUCLID - 1, error=ERR_BAD_SHAPE_PERCENT),
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
    return EuclidValues(hits, DEFAULT_EUCLID_STEPS if steps is None else steps, NO_ROTATION if rotate is None else rotate, value(EuclidPart.STEP))


def rhythm(*, hits, steps, rotate=NO_ROTATION):
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
    return hits_and_misses[-shift:] + hits_and_misses[:-shift] if shift else hits_and_misses
