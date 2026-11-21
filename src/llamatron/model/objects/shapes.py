# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shapes: how many of a clip's notes play, how loud and how long, each a percentage ramping over time, set on a scene, a clip or a generator.

Density keeps a share of the notes, the strongest places in the
bar first; Swell scales their velocity; Articulate scales how long each note sounds. Each runs
from its start to its end percentage over its span, which is the whole scene or clip unless its
over says a length, and then holds, repeats or bounces back. A part left blank is 100%, so a
song that sets none of it plays as it always has.
"""

from typing import NamedTuple

from llamatron.model.file import corrections
from llamatron.model.file.checks import time_length
from llamatron.model.vocabulary import file_format, limits
from llamatron.model.vocabulary.file_format import Shape, shape_setting, ShapePart
from llamatron.model.vocabulary.setting import Checked, Choice, WholeNumber
from llamatron.user_strings import errors

# The lowest and highest percentage of each shape.
SHAPE_LIMITS = {Shape.DENSITY: (limits.MIN_DENSITY, limits.MAX_DENSITY), Shape.SWELL: (limits.MIN_SWELL, limits.MAX_SWELL), Shape.ARTICULATE: (limits.MIN_ARTICULATE, limits.MAX_ARTICULATE)}
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
        WholeNumber(name=named(ShapePart.START), lowest=lowest, highest=highest, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(ShapePart.END), lowest=lowest, highest=highest, error=errors.ERR_BAD_SHAPE_PERCENT),
        Checked(name=named(ShapePart.OVER), check=time_length),
        Choice(name=named(ShapePart.THEN), choices=file_format.SHAPE_THENS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_SHAPE_THEN),
    ]


def shape_settings():
    """Return the descriptions of every shape's settings a scene or a clip holds, like density_start, in the order a file writes them."""
    return [setting for shape in file_format.PLACED_SHAPES for setting in shape_part_settings(shape=shape, named=lambda part, shape=shape: shape_setting(shape=shape, part=part))]


def shape_values(*, settings, shape, accent=NO_ACCENT):
    """Return a shape as a scene's or a clip's settings hold it, or None when neither its start nor its end is set."""
    start = settings.get(shape_setting(shape=shape, part=ShapePart.START))
    end = settings.get(shape_setting(shape=shape, part=ShapePart.END))
    if start is None and end is None:
        return None
    return ShapeValues(
        UNCHANGED if start is None else start, UNCHANGED if end is None else end, settings.get(shape_setting(shape=shape, part=ShapePart.OVER)),
        settings.get(shape_setting(shape=shape, part=ShapePart.THEN)) or file_format.SHAPE_THENS[0], accent,
    )
