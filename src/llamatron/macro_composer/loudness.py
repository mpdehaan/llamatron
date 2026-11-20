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
"""How loud a player's notes are: four named levels, a ghost note, a soft note, a normal note and an accent, each a velocity.

A style says a drum's levels as one number, its normal stroke, from which the others follow, or as each level's own number. A
player of notes has a velocity, the normal level, with the others at set distances from it. A song may give a player levels
of its own and may say how far the player's levels lie from the normal one, the player's dynamics: none at the least, where
every note is as loud as the next, and twice the style's distance at the most.
"""

from fractions import Fraction
import functools

from llamatron.macro_composer import notation
from llamatron.macro_composer.notation import clamped

NORMAL = 'normal'
# The levels from the quietest up, as a person is shown them.
LEVELS = (notation.GHOST, notation.SOFT, NORMAL, notation.ACCENT)
# How a drum's other levels follow from its normal stroke.
ACCENT_ABOVE = 12
SOFT_SHARE = Fraction(2, 3)
GHOST_SHARE = Fraction(1, 3)
# How far a note player's other levels lie from the player's velocity.
SOFT_BELOW = 8
GHOST_BELOW = 30
# A player's dynamics, from every note alike to twice the style's distances.
LEAST_DYNAMICS = 0
USUAL_DYNAMICS = 5
MOST_DYNAMICS = 10


def drum_levels(given):
    """A drum's four levels from what a style says of it: its normal stroke alone, or any of its levels by name."""
    if not isinstance(given, dict):
        given = {NORMAL: given}
    normal = given[NORMAL]
    return {notation.GHOST: given.get(notation.GHOST, int(normal * GHOST_SHARE)), notation.SOFT: given.get(notation.SOFT, int(normal * SOFT_SHARE)), NORMAL: normal,
            notation.ACCENT: given.get(notation.ACCENT, clamped(normal + ACCENT_ABOVE))}


def note_levels(velocity):
    """A note player's four levels from the player's velocity."""
    return {notation.GHOST: clamped(velocity - GHOST_BELOW), notation.SOFT: clamped(velocity - SOFT_BELOW), NORMAL: velocity, notation.ACCENT: clamped(velocity + ACCENT_ABOVE)}


@functools.cache
def scaled(*, move, dynamics):
    """A distance from the normal level as a player's dynamics have it."""
    return round(Fraction(move * dynamics, USUAL_DYNAMICS))


def spread(*, levels, dynamics):
    """Levels with each as far from the normal one as a player's dynamics say."""
    normal = levels[NORMAL]
    return {level: clamped(normal + scaled(move=number - normal, dynamics=dynamics)) for level, number in levels.items()}


def with_own(*, levels, own):
    """Levels with the ones a song gives of its own in their places; a normal level of the song's own carries the others with it,
    each as far from it as before, but for those the song also gives."""
    own = {level: number for level, number in (own or {}).items() if level in LEVELS}
    move = own.get(NORMAL, levels[NORMAL]) - levels[NORMAL]
    return {level: own[level] if level in own else clamped(number + move) for level, number in levels.items()}


def in_proportion(*, levels, kit, chosen):
    """A piece's levels moved as the whole kit's were: each level by the share the kit's level was changed by."""
    return {level: clamped(round(Fraction(number * chosen[level], kit[level]))) if kit[level] else number for level, number in levels.items()}
