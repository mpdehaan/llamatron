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

"""How two values of a trait's field are compared, each giving a gap from 0, the same, to 1, as different as they can be. A
trait class lists how each of its fields compares in COMPARED, so that one function compares any two traits of a kind, and a
field a measured song leaves unknown (None) is skipped rather than counted as a difference.

Comparing two styles compares their typical values. Fitting a song to a style treats the style as a region, the user's model:
no style is one sound, so a number within the style's spread of its typical value fits wholly, and only the distance past the
spread counts; a set is the style's alternatives, and a song fits by doing what is among them, not by doing all of them; and
grooves fit by the nearest of the style's. A tightness below 1 narrows the spreads, for fitting a homage to the one song it is
written after, a much smaller region than its whole style."""

from dataclasses import dataclass
from math import sqrt

from llamatron.genres.measures.drum_patterns import COMMON_STEPS_PER_BEAT, Voice

# The gap of two values that can't be told apart, and of two that share nothing.
SAME = 0.0
APART = 1.0
# Gaps are rounded to this many places, so that rounding errors don't count as differences.
PLACES = 9


class Compare:
    """The ways a field compares."""

    NUMBER = 'number'
    SET = 'set'
    PATTERN = 'pattern'
    FLAG = 'flag'
    TEXT = 'text'
    CURVE = 'curve'
    ROLES = 'roles'
    GROOVES = 'grooves'
    RANGE = 'range'
    METER = 'meter'


class Unit:
    """What a field's value counts, so that it is shown in words that fit it and held to the bounds it can take."""

    SHARE = 'share'
    PER_HUNDRED = 'per hundred'
    LEVELS = 'levels'
    COUNT = 'count'
    PER_BEAT = 'per beat'
    PER_BAR = 'per bar'
    BEATS = 'beats'
    BARS = 'bars'
    HALF_STEPS = 'half steps'
    BEATS_A_MINUTE = 'beats a minute'
    HUNDREDTHS_OF_A_BEAT = 'hundredths of a beat'
    NAME = 'name'
    NAMES = 'names'
    SOUNDS = 'sounds'
    GROOVES = 'grooves'


# The lowest and highest value a number of each bounded unit can take.
SHARE_BOUNDS = (0.0, 1.0)
PER_HUNDRED_BOUNDS = (0.0, 100.0)
LEVEL_BOUNDS = (0.0, 10.0)
UNIT_BOUNDS = {Unit.SHARE: SHARE_BOUNDS, Unit.PER_HUNDRED: PER_HUNDRED_BOUNDS, Unit.LEVELS: LEVEL_BOUNDS}


@dataclass(slots=True, kw_only=True, frozen=True)
class Field:
    """How one field compares: its way; what its value counts, its unit; for a number the difference counted as wholly apart,
    and the spread either side of a style's typical value that a song still wholly fits; and how much the field counts in its
    trait. A field may name another of its trait (also) that holds a style's other values for it, each as good as the first: a
    period's pieces have a bass that moves in several ways, and no one way is the period's."""

    way: str
    unit: str
    scale: float = 1.0
    spread: float = 0.0
    weight: float = 1.0
    also: str = None


def pattern_gap(*, mine, theirs):
    """Return how unlike two patterns of weights are, by the cosine of their angle, each stretched to the other's length."""
    if not mine or not theirs:
        return SAME if not mine and not theirs else APART
    length = max(len(mine), len(theirs))
    mine = stretched(values=mine, count=length)
    theirs = stretched(values=theirs, count=length)
    size = sqrt(sum(value * value for value in mine)) * sqrt(sum(value * value for value in theirs))
    if size == 0:
        return SAME if sum(mine) == sum(theirs) else APART
    return max(SAME, round(APART - sum(left * right for left, right in zip(mine, theirs)) / size, PLACES))


def groove_gap(*, mine, theirs):
    """Return how unlike two drum grooves are: each voice family (the kick, the backbeat, the cymbals, the rest) compared on a
    common grid of a bar, weighted by how much it carries a groove; a voice one groove has and the other lacks counts fully."""
    mine_voices = voice_families(mine)
    theirs_voices = voice_families(theirs)
    total = 0.0
    weights = 0.0
    for family, weight in FAMILY_WEIGHTS.items():
        left = mine_voices.get(family)
        right = theirs_voices.get(family)
        if not left and not right:
            continue
        total += (APART if not left or not right else pattern_gap(mine=left, theirs=right)) * weight
        weights += weight
    return total / weights if weights else SAME


# The voices of a kit gathered into the families a groove is compared by, so that a snare and a clap on the backbeat, or hats
# and a ride keeping time, count as the same part.
KICK_FAMILY = 'kick'
BACKBEAT_FAMILY = 'backbeat'
CYMBAL_FAMILY = 'cymbals'
OTHER_FAMILY = 'other'
FAMILY_WEIGHTS = {KICK_FAMILY: 2.0, BACKBEAT_FAMILY: 1.5, CYMBAL_FAMILY: 1.2, OTHER_FAMILY: 0.4}
FAMILY_OF_VOICE = {Voice.KICK: KICK_FAMILY, Voice.SNARE: BACKBEAT_FAMILY, Voice.RIM: BACKBEAT_FAMILY, Voice.CLAP: BACKBEAT_FAMILY, Voice.HATS: CYMBAL_FAMILY,
                   Voice.OPEN_HAT: CYMBAL_FAMILY, Voice.RIDE: CYMBAL_FAMILY, Voice.CRASH: OTHER_FAMILY, Voice.TOMS: OTHER_FAMILY, Voice.PERCUSSION: OTHER_FAMILY}


def voice_families(groove):
    """Return a groove's voices merged into their families, one bar on the common grid, each step the loudest of its voices."""
    grid = groove.on_common_grid()
    bar = groove.beats * COMMON_STEPS_PER_BEAT
    result = {}
    for voice, steps in grid.items():
        family = FAMILY_OF_VOICE.get(voice, OTHER_FAMILY)
        folded = [0] * bar
        for place, weight in enumerate(steps):
            folded[place % bar] = max(folded[place % bar], weight)
        merged = result.get(family, [0] * bar)
        result[family] = [max(left, right) for left, right in zip(merged, folded)]
    return {family: tuple(steps) for family, steps in result.items() if any(steps)}


def stretched(*, values, count):
    """Return values stretched or squeezed to count, each taken from its place along the original."""
    if count <= 0 or not values:
        return ()
    return tuple(values[min(len(values) - 1, place * len(values) // count)] for place in range(count))


