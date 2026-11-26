# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How loud a clip plays: the velocity of its instrument, its track, its scene and itself, and a ramp in and a ramp out.

Each is a percentage of what it scales, so that accents and soft notes keep their proportions: 0
silences, 100 changes nothing, 200 doubles. The velocities stack as gain stages do, each scaling
what the one above gives, so that 0 anywhere silences. A ramp's ends are percentages of that
stacked level: a ramp in counts its bars from the start and a ramp out counts its bars back from
the end, and an end left blank is 100, the level itself. A clip's ramp fields win over its scene's,
one field at a time, since two fades together would fade twice. Everything left blank, the notes
play as written.

What a clip plays is worked out as a percentage of the written velocity, which is what the render
scales each note by.
"""

from typing import NamedTuple

from llamatron.math.rational import Rational
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import RampPart, RampWay, VelocitySetting
from llamatron.model.schema.setting import WholeNumber
from llamatron.user_strings import errors

# What a clip plays at, as a percentage of each note's written velocity, when nothing changes it, and what a velocity left
# blank scales by.
AS_WRITTEN = 100
# The settings that count bars, where every other one is a percentage.
BAR_COUNTS = (VelocitySetting.IN_OVER, VelocitySetting.OUT_OVER)
HALF = 2


class VelocityRamp(NamedTuple):
    """One velocity ramp as it plays: the percentage it starts from, the percentage it reaches, the bars it takes, and whether the bars are the clip's own, counted over the clip's play, where a scene's are counted over the scene's."""

    start: object
    end: object
    over: int
    of_clip: bool


class Velocity(NamedTuple):
    """How loud a clip plays: the percentage that holds, and its ramp in and ramp out, each a VelocityRamp or None."""

    level: object
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


def velocity_of(*, scene_settings, clip_settings=None, outer_levels=()):
    """Return how loud a clip plays, as a Velocity of percentages of the written velocity, from its scene's settings, its own
    and outer_levels, the velocities of its instrument and its track, None where blank; with no clip, how loud the scene plays.

    The levels stack, each scaling the others. A ramp plays when it has its bars and a start or an end, each a percentage of
    the stacked level, an end left blank being the level itself; a clip's ramp fields win over its scene's, field by field.
    """
    own = clip_settings or {}
    level = Rational(AS_WRITTEN)
    for percent in (*outer_levels, scene_settings.get(VelocitySetting.LEVEL), own.get(VelocitySetting.LEVEL)):
        level = scaled(level=level, percent=percent)
    ramps = {}
    for way in file_format.RAMP_WAYS:
        ramps[way] = _ramp_of(way=way, level=level, scene_settings=scene_settings, own=own)
    return Velocity(level, ramps[RampWay.IN], ramps[RampWay.OUT])


def scaled(*, level, percent):
    """Return a level scaled by a percentage, or as it is for a percentage left blank."""
    if percent is None:
        return level
    return level * Rational(percent, AS_WRITTEN)


def _ramp_of(*, way, level, scene_settings, own):
    """Return one ramp of a clip as it plays, a VelocityRamp of percentages of the written velocity, or None where it has no bars or neither end."""

    def taken(part):
        name = file_format.VELOCITY_RAMP_SETTINGS[(way, part)]
        if own.get(name) is None:
            return scene_settings.get(name)
        return own[name]
    start = taken(RampPart.START)
    end = taken(RampPart.END)
    over = taken(RampPart.OVER)
    if over is None or (start is None and end is None):
        return None
    of_clip = own.get(file_format.VELOCITY_RAMP_SETTINGS[(way, RampPart.OVER)]) is not None
    return VelocityRamp(scaled(level=level, percent=start), scaled(level=level, percent=end), over, of_clip)
