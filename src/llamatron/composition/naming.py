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
"""How the things a set holds are named: a copy's name, a name nothing has yet, and the name a scale takes from its root and kind.

The tracker names what it adds and copies with these, and so does the MIDI import, which names
what it makes so that it sits among what the set has.
"""

import re

from llamatron.composition.named_scale import MEMBER_WORD_GAP, WORD_GAP
from llamatron.strings.names import MSG_DEFAULT_SCALE_NAME, MSG_NUMBERED_NAME

FIRST_COPY_NUMBER = 2
# A name that ends in a number after a space, like verse 1, which a copy counts up from.
# A name's words and the number it ends in, as the two named groups of the pattern below.
BASE_GROUP = 'base'
NUMBER_GROUP = 'number'
TRAILING_NUMBER = re.compile(rf'^(?P<{BASE_GROUP}>.*\S)\s+(?P<{NUMBER_GROUP}>\d+)$')


def words(name):
    """Return a name the file writes with underscores, like reverse_a, as words for the screen."""
    return str(name).replace(MEMBER_WORD_GAP, WORD_GAP)


def default_scale_name(*, root, kind):
    """Return the name a scale gets from its root and kind, like C Major or F Harmonic Minor."""
    return MSG_DEFAULT_SCALE_NAME.format(root=root, kind=words(kind).title())


def is_default_scale_name(*, name, root, kind):
    """Return whether a scale's name is the one its root and kind would give it, in any case, so that it still says what the scale is."""
    return name.casefold() == default_scale_name(root=root, kind=kind).casefold()


def unique_name(*, base, taken):
    """Return a name that's not in use, based on another one."""
    if base not in taken:
        return base
    number = FIRST_COPY_NUMBER
    while MSG_NUMBERED_NAME.format(base=base, number=number) in taken:
        number += 1
    return MSG_NUMBERED_NAME.format(base=base, number=number)


def copy_name(*, name, taken):
    """Return the name for a copy of something: the name with the first free number after it, like bass 2.

    A name that already ends in a number counts up from it, so a copy of bass 2 is bass 3, never
    bass 2 2, and a copy of verse 1 is verse 2.
    """
    base, number = split_trailing_number(name)
    number = FIRST_COPY_NUMBER if number is None else max(FIRST_COPY_NUMBER, number + 1)
    while MSG_NUMBERED_NAME.format(base=base, number=number) in taken:
        number += 1
    return MSG_NUMBERED_NAME.format(base=base, number=number)


def split_trailing_number(name):
    """Return a name's words and the number it ends in, like ("verse", 1), or the name and None if it ends in none."""
    found = TRAILING_NUMBER.match(name)
    if found is None:
        return name, None
    return found.group(BASE_GROUP), int(found.group(NUMBER_GROUP))
