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

"""The order a clip plays its list of patterns in on each pass through the list.

Every order plays every entry of the list exactly once a pass, so that a pass lasts as long
whatever the order: only which pattern comes next changes. The names are a pattern's directions,
each meaning for whole patterns what the direction means for steps.
"""

from llamatron.composition.file_format import PatternOrder


def ordered_patterns(*, names, order, place, rolls):
    """Return a clip's patterns in the order one pass plays them: place is the pass, counted from 0, and rolls the random generator the drawn orders use."""
    names = list(names)
    backward = list(reversed(names))
    if order == PatternOrder.REVERSE_A:
        return [*names[:1], *reversed(names[1:])]
    if order == PatternOrder.REVERSE_B:
        return backward
    if order == PatternOrder.ALTERNATE:
        return backward if is_return_pass(place) else names
    if order == PatternOrder.PENDULUM:
        # The way back starts on the pattern before the last, which has just played, and the last then closes the pass.
        return [*backward[1:], *backward[:1]] if is_return_pass(place) else names
    if order == PatternOrder.RANDOM:
        rolls.shuffle(names)
        return names
    if order == PatternOrder.FIRST_THEN_RANDOM:
        rest = names[1:]
        rolls.shuffle(rest)
        return [*names[:1], *rest]
    return names


def is_return_pass(place):
    """Return whether a pass is one that comes back: every second pass, the first going out."""
    return place % 2 == 1
