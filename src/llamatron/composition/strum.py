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
"""Strum: a chord's notes sounding one after another, as a guitarist's pick crosses the strings.

A track's strum holds for every clip on it, a clip's own wins over its track's, and a Strum
generator in a clip's chain wins over both. Each is in force once its direction is set; a clip's
direction of off strums nothing, whatever its track says. Each part left blank takes its default:
the normal spread, no fade, no loose timing, and every string on an upstroke.
"""

from typing import NamedTuple

from llamatron.composition import corrections, file_format, limits
from llamatron.composition.file_format import strum_setting, StrumDirection, StrumPart, StrumSpread, UpstrokeStrings
from llamatron.composition.setting import Choice, WholeNumber
from llamatron.strings import errors

# How many milliseconds apart each spread sounds two strings: a hand's speed, whatever the tempo.
SPREAD_MILLISECONDS = {StrumSpread.TIGHT: 2, StrumSpread.CRISP: 4, StrumSpread.NORMAL: 8, StrumSpread.LOOSE: 15, StrumSpread.RAKE: 30, StrumSpread.HARP: 70}
DEFAULT_SPREAD = StrumSpread.NORMAL
NO_FADE = 0
NO_LOOSE_TIMING = 0
DEFAULT_UPSTROKE_STRINGS = UpstrokeStrings.ALL
# How many of the top notes an upstroke catches, by its setting; all of them for ALL.
UPSTROKE_COUNTS = {UpstrokeStrings.TOP_3: 3, UpstrokeStrings.TOP_4: 4}


class StrumValues(NamedTuple):
    """A strum as set somewhere, every part filled in: its direction, its spread in milliseconds, its fade and loose timing as percentages, and how many top notes an upstroke catches, or None for all."""

    direction: str
    milliseconds: int
    fade: int
    loose_timing: int
    upstroke_count: object


def strum_part_settings(named):
    """Return the descriptions of a strum's five parts, each named by named(part)."""
    def choice(part, choices):
        return Choice(name=named(part), choices=choices, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE)
    return [
        choice(StrumPart.DIRECTION, file_format.STRUM_DIRECTIONS),
        choice(StrumPart.SPREAD, file_format.STRUM_SPREADS),
        WholeNumber(name=named(StrumPart.FADE), lowest=limits.MIN_STRUM_PERCENT, highest=limits.MAX_STRUM_FADE, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=named(StrumPart.LOOSE_TIMING), lowest=limits.MIN_STRUM_PERCENT, highest=limits.MAX_LOOSE_TIMING, error=errors.ERR_BAD_SHAPE_PERCENT),
        choice(StrumPart.UPSTROKE_STRINGS, file_format.UPSTROKE_STRINGS),
    ]


def strum_settings():
    """Return the descriptions of a track's or a clip's strum settings, like strum_spread, in the order a file writes them."""
    return strum_part_settings(strum_setting)


def strum_values(value):
    """Return a strum, from value(part) for each of its parts, or None when its direction is blank and it leaves the strum to the level below."""
    direction = value(StrumPart.DIRECTION)
    if direction is None:
        return None
    spread = value(StrumPart.SPREAD) or DEFAULT_SPREAD
    fade = value(StrumPart.FADE)
    loose = value(StrumPart.LOOSE_TIMING)
    upstroke = value(StrumPart.UPSTROKE_STRINGS) or DEFAULT_UPSTROKE_STRINGS
    return StrumValues(direction, SPREAD_MILLISECONDS[spread], NO_FADE if fade is None else fade, NO_LOOSE_TIMING if loose is None else loose, UPSTROKE_COUNTS.get(upstroke))


def strums_at_all(strum):
    """Return whether a strum in force strums anything, which a direction of off doesn't."""
    return strum is not None and strum.direction != StrumDirection.OFF

