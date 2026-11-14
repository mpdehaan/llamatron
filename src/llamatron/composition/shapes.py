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
"""Shapes: how many of a clip's notes play, how loud and how long, each a percentage ramping over time, set on a scene, a clip or a generator.

The user's design of 2026-11-11. Density keeps a share of the notes, the strongest places in the
bar first; Swell scales their velocity; Articulate scales how long each note sounds. Each runs
from its start to its end percentage over its span, which is the whole scene or clip unless its
over says a length, and then holds, repeats or bounces back. A part left blank is 100%, so a
song that sets none of it plays as it always has.
"""

from typing import NamedTuple

from llamatron.composition.corrections import LEFT_OUT
from llamatron.composition.file_format import SHAPE_THENS, SHAPES, Shape, ShapePart, shape_setting
from llamatron.composition.checks import time_length
from llamatron.composition.limits import MAX_ARTICULATE, MAX_DENSITY, MAX_SWELL, MIN_ARTICULATE, MIN_DENSITY, MIN_SWELL
from llamatron.composition.setting import Checked, Choice, WholeNumber
from llamatron.strings.errors import ERR_BAD_SHAPE_PERCENT, ERR_BAD_SHAPE_THEN

# The lowest and highest percentage of each shape.
SHAPE_LIMITS = {Shape.DENSITY: (MIN_DENSITY, MAX_DENSITY), Shape.SWELL: (MIN_SWELL, MAX_SWELL), Shape.ARTICULATE: (MIN_ARTICULATE, MAX_ARTICULATE)}
# What a part left blank plays as: every note, as loud and as long as written.
UNCHANGED = 100
NO_ACCENT = 0


class ShapeValues(NamedTuple):
    """One shape as set somewhere: its start and end percentages, its over (a length in whole notes, or None for the whole span), its then, and a Swell generator's accent."""

    start: int
    end: int
    over: object
    then: str
    accent: int


def shape_part_settings(*, shape, named):
    """Return the descriptions of one shape's four parts, named by named(part)."""
    lowest, highest = SHAPE_LIMITS[shape]
    return [
        WholeNumber(name=named(ShapePart.START), lowest=lowest, highest=highest, error=ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(ShapePart.END), lowest=lowest, highest=highest, error=ERR_BAD_SHAPE_PERCENT),
        Checked(name=named(ShapePart.OVER), check=time_length),
        Choice(name=named(ShapePart.THEN), choices=SHAPE_THENS, default=LEFT_OUT, error=ERR_BAD_SHAPE_THEN),
    ]


def shape_settings():
    """Return the descriptions of every shape's settings a scene or a clip holds, like density_start, in the order a file writes them."""
    return [setting for shape in SHAPES for setting in shape_part_settings(shape=shape, named=lambda part, shape=shape: shape_setting(shape=shape, part=part))]


def shape_values(*, settings, shape, accent=NO_ACCENT):
    """Return a shape as a scene's or a clip's settings hold it, or None when neither its start nor its end is set."""
    start = settings.get(shape_setting(shape=shape, part=ShapePart.START))
    end = settings.get(shape_setting(shape=shape, part=ShapePart.END))
    if start is None and end is None:
        return None
    return ShapeValues(
        UNCHANGED if start is None else start, UNCHANGED if end is None else end, settings.get(shape_setting(shape=shape, part=ShapePart.OVER)),
        settings.get(shape_setting(shape=shape, part=ShapePart.THEN)) or SHAPE_THENS[0], accent,
    )
