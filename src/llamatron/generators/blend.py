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

from enum import Enum, auto
from fractions import Fraction
from math import isfinite

from llamatron.support.length import ZERO, Length
from llamatron.support.rational import Rational
from llamatron.generators.base import ClipGenerator
from llamatron.music.sound import DEGREE, HELD, HELD_SOUND, KIND, LENGTH, PARTS, PHRASE, Sound
from llamatron.grid.clip import Clip
from llamatron.strings.errors import ERR_BAD_AMOUNT, ERR_DEGREE_NEEDS_SCALE, ERR_LENGTHS_DIFFER, ERR_NOT_A_CLIP, ERR_NOT_A_MODE

# How far a blend has moved to its target, as a percentage.
NONE_OF_THE_TARGET = 0
ALL_OF_THE_TARGET = 100
# The amount's fraction is rounded to this, so that a float amount like 33.3 behaves.
AMOUNT_PRECISION = 1_000_000
# Where a clip starts, and the middle of a span, as a fraction of its length.
START = Rational(0)
HALF = 2
AMOUNT_TYPES = (int, float, Rational, Fraction)


class BlendMode(Enum):
    """Where the target comes in from as Blend moves one clip towards another."""

    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


def _check_mode(mode):
    if not isinstance(mode, BlendMode):
        raise ValueError(ERR_NOT_A_MODE.format(value=mode))


def _check_target(target):
    if not isinstance(target, Clip):
        raise ValueError(ERR_NOT_A_CLIP.format(value=target))


def _check_amount(amount):
    # bool is a subclass of int, but True is not a real amount.
    if not _is_amount(amount):
        raise ValueError(ERR_BAD_AMOUNT.format(value=amount, lowest=NONE_OF_THE_TARGET, highest=ALL_OF_THE_TARGET))


def _is_amount(amount):
    """Return whether an amount is a finite percentage from 0 to 100, not counting true and false."""
    return type(amount) in AMOUNT_TYPES and isfinite(amount) and NONE_OF_THE_TARGET <= amount <= ALL_OF_THE_TARGET


def _concrete(clip):
    """Return a copy of a clip with degrees turned into notes of its own scale.

    Slices from two songs can't share one scale, so degrees have to be settled here.
    """
    sounds = [_settled(position=position, scale=clip.get_scale()) for position in clip.get_sounds()]
    return Clip(sounds=sounds, length=clip.get_length(), note_length=clip.get_note_length())


def _settled(*, position, scale):
    """Return a sound with any degree in it, including inside a held sound, turned into a note of a scale."""
    kind = position[KIND]
    if kind == HELD:
        return (HELD, position[LENGTH], _settled(position=position[HELD_SOUND], scale=scale))
    if kind == PHRASE:
        return (PHRASE, position[LENGTH], tuple([_settled(position=part, scale=scale) for part in position[PARTS]]))
    if kind != DEGREE:
        return position
    if scale is None:
        raise ValueError(ERR_DEGREE_NEEDS_SCALE.format(degree=Sound.position(position)))
    return Sound.settled(position, scale)


class Blend(ClipGenerator):
    """Moves a clip towards a target clip of the same total length.

    An amount of 0 plays this clip, and 100 plays the target. LEFT, RIGHT and MIDDLE bring in the
    target from one side, from the other, or from the center out, with the amount setting how
    much of the clip's length it covers. There's no randomness, and the edges move to the nearest
    note in this clip, so its notes aren't cut.
    """

    __slots__ = ('_target', '_amount', '_mode')

    def __init__(self, *, target, amount, mode=BlendMode.LEFT):
        _check_target(target)
        _check_amount(amount)
        _check_mode(mode)
        self._target = target
        self._amount = amount
        self._mode = mode

    def get_amount(self):
        return self._amount

    def set_amount(self, amount):
        _check_amount(amount)
        self._amount = amount

    def _generate(self, clip):
        total = clip.total_length()
        if self._target.total_length() != total:
            raise ValueError(ERR_LENGTHS_DIFFER.format(first=total, second=self._target.total_length()))
        return self._sweep(source=_concrete(clip), target=_concrete(self._target), total=total), clip.get_length()

    def region(self, clip):
        """Return where the target plays in the result, from start to end in whole notes."""
        total = clip.total_length()
        source = _concrete(clip)
        share = total * Rational(self._amount).limit_denominator(AMOUNT_PRECISION) / ALL_OF_THE_TARGET
        if self._mode is BlendMode.LEFT:
            start = START
            end = share
        elif self._mode is BlendMode.RIGHT:
            start = total - share
            end = total
        else:
            start = (total - share) / HALF
            end = (total + share) / HALF
        # The edges are the same for both ends, so they are found once.
        edges = _note_starts(source=source, total=total)
        start = Length.rational(_closest(edges=edges, time=Length.of(start)))
        end = Length.rational(_closest(edges=edges, time=Length.of(end)))
        if end <= start:
            return (START, START) if share < total else (START, total)
        return start, end

    def _sweep(self, *, source, target, total):
        start, end = self.region(source)
        if end <= start:
            return source.get_sounds()
        if start == START and end == total:
            return target.get_sounds()
        sounds = []
        if start > START:
            sounds += source.section(start=START, end=start).get_sounds()
        sounds += target.section(start=start, end=end).get_sounds()
        if end < total:
            sounds += source.section(start=end, end=total).get_sounds()
        return sounds

def _note_starts(*, source, total):
    """Return where each note of a clip starts, and its start and end, which a blend's edges can move to, as pairs."""
    edges = [ZERO, Length.of(total)]
    now = ZERO
    for position in source.played_sounds():
        edges.append(now)
        now = Length.add(now, position[LENGTH])
    return edges


def _closest(*, edges, time):
    """Return the edge nearest a time, which is the start of the note closest to it, choosing the earlier of two that are equally near."""
    nearest = None
    least = None
    for edge in edges:
        apart = Length.distance(edge, time)
        if nearest is None or Length.less(apart, least) or (apart == least and Length.less(edge, nearest)):
            nearest = edge
            least = apart
    return nearest
