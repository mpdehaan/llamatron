# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How loud a scene or a clip plays: a velocity that holds, and a ramp in and a ramp out.

Each is a percentage of the velocity a note is written with, so that accents and soft notes keep
their proportions. The velocity is the level the notes play at; a ramp in counts its bars from
the start and a ramp out counts its bars back from the end, and an end of a ramp left blank is
the velocity, which the ramps start from and return to. A clip's own values win over its
scene's, one field at a time. Everything left blank, the notes play as written.
"""

from typing import NamedTuple

from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import RampPart, RampWay, VelocitySetting
from llamatron.model.schema.setting import WholeNumber
from llamatron.user_strings import errors

# What a velocity left blank everywhere plays as: every note as loud as written.
AS_WRITTEN = 100
# The settings that count bars, where every other one is a percentage.
BAR_COUNTS = (VelocitySetting.IN_OVER, VelocitySetting.OUT_OVER)
HALF = 2


class VelocityRamp(NamedTuple):
    """One velocity ramp as it plays: the percentage it starts from, the percentage it reaches, the bars it takes, and whether the bars are the clip's own, counted over the clip's play, where a scene's are counted over the scene's."""

    start: int
    end: int
    over: int
    of_clip: bool


class Velocity(NamedTuple):
    """How loud a clip plays: the percentage that holds, and its ramp in and ramp out, each a VelocityRamp or None."""

    level: int
    ramp_in: object
    ramp_out: object

    def changes_nothing(self):
        """Return whether every note plays as written."""
        return self.level == AS_WRITTEN and self.ramp_in is None and self.ramp_out is None

    def typical(self):
        """Return the percentage that stands for the whole of it, for weighing one scene against another: the middle of a ramp, or the level."""
        ramp = self.ramp_in or self.ramp_out
        if ramp is None:
            return self.level
        return (ramp.start + ramp.end) / HALF


def velocity_setting_descriptions():
    """Return the descriptions of the velocity settings a scene or a clip holds, in the order a file writes them."""
    descriptions = []
    for name in file_format.VELOCITY_SETTINGS:
        if name in BAR_COUNTS:
            descriptions.append(WholeNumber(name=name, lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, error=errors.ERR_BAD_RAMP_BARS))
        else:
            descriptions.append(WholeNumber(name=name, lowest=limits.MIN_VELOCITY_PERCENT, highest=limits.MAX_VELOCITY_PERCENT, error=errors.ERR_BAD_SHAPE_PERCENT))
    return descriptions


def velocity_of(*, scene_settings, clip_settings=None):
    """Return how loud a clip plays, as a Velocity, from its scene's settings and its own, the clip's winning field by field; with no clip, how loud the scene plays.

    A ramp plays when it has its bars and a start or an end. The end left blank is the level.
    """
    own = clip_settings or {}

    def taken(name):
        if own.get(name) is None:
            return scene_settings.get(name)
        return own[name]

    def ramp_part(way, part):
        return taken(file_format.VELOCITY_RAMP_SETTINGS[(way, part)])
    level = taken(VelocitySetting.LEVEL)
    if level is None:
        level = AS_WRITTEN
    ramps = {}
    for way in file_format.RAMP_WAYS:
        start = ramp_part(way, RampPart.START)
        end = ramp_part(way, RampPart.END)
        over = ramp_part(way, RampPart.OVER)
        if over is None or (start is None and end is None):
            ramps[way] = None
            continue
        # A blank end of a ramp is the level.
        if start is None:
            start = level
        if end is None:
            end = level
        of_clip = own.get(file_format.VELOCITY_RAMP_SETTINGS[(way, RampPart.OVER)]) is not None
        ramps[way] = VelocityRamp(start, end, over, of_clip)
    return Velocity(level, ramps[RampWay.IN], ramps[RampWay.OUT])
