# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the things a set holds are named: a copy's name, a name nothing has yet, and the name a scale takes from its root and kind.

The tracker names what it adds and copies with these, and so does the MIDI import, which names
what it makes so that it sits among what the set has.
"""

import re

from llamatron.composition import named_scale
from llamatron.user_strings import names

# The number a duplicate of a name with no number gets: the name the user picked counts as the first, and is never renamed.
FIRST_COPY_NUMBER = 2
# The number the first new thing of a kind gets.
FIRST_NEW_NUMBER = 1
# In a sort, a name that ends in no number comes before the same words with one.
NO_NUMBER_FIRST = 0
NUMBERED_AFTER = 1
# A name that ends in a number, like verse-1, name1 or bass 2, which a duplicate counts up from: its words, whatever joins the
# number to them, and the number, as the three named groups of the pattern below. The words may themselves end in a number
# where something joins the last number to them, as in treble 1-2; with nothing between, the words end in no digit.
BASE_GROUP = 'base'
JOINT_GROUP = 'joint'
NUMBER_GROUP = 'number'
TRAILING_NUMBER = re.compile(rf'^(?P<{BASE_GROUP}>.+?)(?P<{JOINT_GROUP}>[\s_-]+|(?<=[^\d\s_-]))(?P<{NUMBER_GROUP}>\d+)$')


def words(name):
    """Return a name the file writes with underscores, like reverse_a, as words for the screen."""
    return str(name).replace(named_scale.MEMBER_WORD_GAP, named_scale.WORD_GAP)


def suggested_word(text):
    """Return text as the tracker writes a name it makes up itself: lowercase, an underscore where a space would be."""
    return str(text).strip().lower().replace(named_scale.WORD_GAP, named_scale.MEMBER_WORD_GAP)


def same_name(*, one, other):
    """Return whether two names are one name: names are compared without regard to capitals, and kept as typed."""
    return str(one).casefold() == str(other).casefold()


def is_taken(*, name, taken):
    """Return whether a name is one of the names taken, without regard to capitals."""
    return str(name).casefold() in {str(other).casefold() for other in taken}


def default_scale_name(*, root, kind):
    """Return the name a scale gets from its root and kind, like C_major or F#_harmonic_minor: lowercase with underscores, as every
    name the tracker makes, but for the note's name, which keeps its capital, the one exception."""
    return names.MSG_DEFAULT_SCALE_NAME.format(root=root, kind=suggested_word(words(kind)))


def legacy_scale_name(*, root, kind):
    """Return the name a scale got from its root and kind before names were lowercase, like C Major, which older files hold."""
    return names.MSG_LEGACY_SCALE_NAME.format(root=root, kind=words(kind).title())


def is_default_scale_name(*, name, root, kind):
    """Return whether a scale's name is the one its root and kind would give it, now or in an older file, in any case, so that it still says what the scale is."""
    return same_name(one=name, other=default_scale_name(root=root, kind=kind)) or same_name(one=name, other=legacy_scale_name(root=root, kind=kind))


def unique_name(*, base, taken):
    """Return a name that's not in use: the name wanted when it's free, and otherwise the duplicate's name counted up from it."""
    if not is_taken(name=base, taken=taken):
        return base
    return copy_name(name=base, taken=taken)


def copy_name(*, name, taken):
    """Return the name for a duplicate of something: a name with no number gets a dash and 2, like bass-2, since the
    name the user picked is the first; a name that already ends in a number counts up from it and keeps whatever joins the number
    to it, so bass-2 gives bass-3, name1 gives name2 and bass 2 gives bass 3, never a number after a number. The number goes on
    until the name is free."""
    base, joint, number = split_trailing_number(name)
    if number is None:
        joint = names.MSG_NUMBER_JOINT
        number = FIRST_COPY_NUMBER - 1
    number = max(FIRST_COPY_NUMBER, number + 1)
    while is_taken(name=base + joint + str(number), taken=taken):
        number += 1
    return base + joint + str(number)


def new_name(*, word, taken):
    """Return the name for a new thing of a kind: its word, a dash and a number, like pattern-1, the number one more
    than the highest any name of that word ends in, so that a new thing never takes the name of one just deleted and the newest
    has the highest number."""
    highest = FIRST_NEW_NUMBER - 1
    for other in taken:
        base, _, number = split_trailing_number(str(other))
        if number is not None and same_name(one=base, other=word):
            highest = max(highest, number)
    return names.MSG_NUMBERED_NAME.format(base=word, number=highest + 1)


def split_part_names(*, name, count, taken):
    """Return the names of the patterns a pattern is split into: its name, the word split and a number, like p1-split-1, counted on
    from the highest such name in use, so that splitting again takes no name of an earlier split."""
    word = names.MSG_SPLIT_BASE.format(name=name)
    first = split_trailing_number(new_name(word=word, taken=taken))[-1]
    return [names.MSG_NUMBERED_NAME.format(base=word, number=first + part) for part in range(count)]


def split_trailing_number(name):
    """Return a name's words, what joins its number to them and the number it ends in, like ("verse", "-", 1), or the name, None and None if it ends in none."""
    found = TRAILING_NUMBER.match(name)
    if found is None:
        return name, None, None
    return found.group(BASE_GROUP), found.group(JOINT_GROUP), int(found.group(NUMBER_GROUP))


def name_order(name):
    """Return what names are sorted by, everywhere the tracker sorts them: the words ignoring capitals, then
    the number a name ends in read as a number, so that verse-2 comes before verse-10, a name with no number before both."""
    base, _, number = split_trailing_number(str(name))
    if number is None:
        return (base.lower(), NO_NUMBER_FIRST, NO_NUMBER_FIRST, str(name).lower())
    return (base.lower(), NUMBERED_AFTER, number, str(name).lower())


def name_in_copied_group(*, name, old, new):
    """Return a pattern's name for its copy in a copied group: the new group's name at the front, in place of
    the old group's name where that was at the front, and joined with an underscore otherwise; nothing else of the name changes."""
    if old and name.lower().startswith(old.lower()):
        return new + name[len(old):]
    return new + named_scale.MEMBER_WORD_GAP + name
