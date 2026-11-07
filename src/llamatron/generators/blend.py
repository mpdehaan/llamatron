# llamatron: a Python language and framework for producing MIDI clips.
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

from llamatron.rational import Rational
from llamatron.generators.base import ClipGenerator, exact_length
from llamatron.held import Held, is_phrase, phrase
from llamatron.note import Degree
from llamatron.clip_grid import Clip, _Validated

# How far a blend has moved to its target, as a percentage.
NONE_OF_THE_TARGET, ALL_OF_THE_TARGET = 0, 100
# The amount's fraction is rounded to this, so that a float amount like 33.3 behaves.
AMOUNT_PRECISION = 1_000_000
# Where a clip starts, and the middle of a span, as a fraction of its length.
START = Rational(0)
HALF = 2
AMOUNT_TYPES = (int, float, Rational, Fraction)

MSG_NOT_A_MODE = 'expected a BlendMode, got {value!r}'
MSG_NOT_A_CLIP = 'expected a Clip, got {value!r}'
MSG_BAD_AMOUNT = 'invalid amount: {value!r} (must be from {lowest} to {highest})'
MSG_DEGREE_NEEDS_SCALE = "{degree!r} needs a scale, but the clip has none"
MSG_LENGTHS_DIFFER = 'the clips must be the same length, but they last {first} and {second}'


class BlendMode(Enum):
    """Where the target comes in from as Blend moves one clip towards another."""

    LEFT = auto()
    RIGHT = auto()
    MIDDLE = auto()


def _check_mode(mode):
    if not isinstance(mode, BlendMode):
        raise ValueError(MSG_NOT_A_MODE.format(value=mode))


def _check_target(target):
    if not isinstance(target, Clip):
        raise ValueError(MSG_NOT_A_CLIP.format(value=target))


def _check_amount(amount):
    # bool is a subclass of int, but True is not a real amount.
    if not _is_amount(amount):
        raise ValueError(MSG_BAD_AMOUNT.format(value=amount, lowest=NONE_OF_THE_TARGET, highest=ALL_OF_THE_TARGET))


def _is_amount(amount):
    """Return whether an amount is a finite percentage from 0 to 100, not counting true and false."""
    return type(amount) in AMOUNT_TYPES and isfinite(amount) and NONE_OF_THE_TARGET <= amount <= ALL_OF_THE_TARGET


def _concrete(clip):
    """Return a copy of a clip with degrees turned into notes of its own scale.

    Slices from two songs can't share one scale, so degrees have to be settled here.
    """
    notes = [_settled(position, clip.scale) for position in clip.notes]
    return Clip(notes=notes, length=clip.length, note_length=clip.note_length)


def _settled(position, scale):
    """Return a position with any degree in it, including inside a Held, turned into a note of a scale."""
    if isinstance(position, Held):
        sound = position.sound
        sound = phrase(_settled(part, scale) for part in sound) if is_phrase(sound) else _settled(sound, scale)
        return Held(sound, position.length)
    if not isinstance(position, Degree):
        return position
    if scale is None:
        raise ValueError(MSG_DEGREE_NEEDS_SCALE.format(degree=position))
    return position.to_note(scale)


class Blend(ClipGenerator):
    """Moves a clip towards a target clip of the same total length.

    An amount of 0 plays this clip, and 100 plays the target. LEFT, RIGHT and MIDDLE bring in the
    target from one side, from the other, or from the center out, with the amount setting how
    much of the clip's length it covers. There's no randomness, and the edges move to the nearest
    note in this clip, so its notes aren't cut.
    """

    __slots__ = ('_target', '_amount', '_mode')

    target = _Validated(_check_target)
    amount = _Validated(_check_amount)
    mode = _Validated(_check_mode)

    def __init__(self, target, amount, mode=BlendMode.LEFT):
        self.target = target
        self.amount = amount
        self.mode = mode

    def _generate(self, clip):
        total = clip.total_length()
        if self.target.total_length() != total:
            raise ValueError(MSG_LENGTHS_DIFFER.format(first=total, second=self.target.total_length()))
        return self._sweep(_concrete(clip), _concrete(self.target), total), clip.length

    def region(self, clip):
        """Return where the target plays in the result, from start to end in whole notes."""
        total = clip.total_length()
        source = _concrete(clip)
        share = total * Rational(self.amount).limit_denominator(AMOUNT_PRECISION) / ALL_OF_THE_TARGET
        if self.mode is BlendMode.LEFT:
            start, end = START, share
        elif self.mode is BlendMode.RIGHT:
            start, end = total - share, total
        else:
            start, end = (total - share) / HALF, (total + share) / HALF
        start, end = self._nearest_edge(source, start, total), self._nearest_edge(source, end, total)
        if end <= start:
            return (START, START) if share < total else (START, total)
        return start, end

    def _sweep(self, source, target, total):
        start, end = self.region(source)
        if end <= start:
            return source.notes
        if start == START and end == total:
            return target.notes
        notes = []
        if start > START:
            notes += source.section(START, start).notes
        notes += target.section(start, end).notes
        if end < total:
            notes += source.section(end, total).notes
        return notes

    def _nearest_edge(self, source, time, total):
        """Return the start of the note in the source closest to a time."""
        return _closest(_note_starts(source, total), time)


def _note_starts(source, total):
    """Return where each note of a clip starts, and its start and end, which a blend's edges can move to."""
    edges = [START, total]
    now = START
    for position in source.played_notes():
        edges.append(now)
        now += exact_length(position.length)
    return edges


def _closest(edges, time):
    """Return the edge nearest a time, choosing the earlier of two that are equally near."""
    return min(edges, key=lambda edge: (abs(edge - time), edge))
