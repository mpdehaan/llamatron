# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where a screen's selection is, and what a search typed into a list keeps: the parts of a page's behaviour that draw nothing.

A page or a dialog holds a Cursor for each thing an arrow moves, and a Search where typing narrows a
list. Both know nothing of what is drawn, so the rules every cursor keeps, stopping at each end and
staying on a row a search still shows, are written once and are tested without a screen.
"""

from llamatron.tui import keys
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.keys import Key
from llamatron.user_strings import errors

FIRST_PLACE = 0
NOTHING_TYPED = ''


class NoSuchPlace(LookupError):
    """A screen was asked the way to something its cursor cannot reach."""

    def __init__(self, *, screen, target):
        super().__init__(errors.ERR_NO_SUCH_PLACE.format(screen=type(screen).__name__, target=target))


def key_between(*, here, there, back=Key.UP, forward=Key.DOWN):
    """Return the key that takes a cursor one place nearer another place, or None when it is there."""
    if here == there:
        return None
    return back if there < here else forward


def place_of(*, screen, names, target):
    """Return the place of a target among a screen's names, or raise NoSuchPlace."""
    if target not in names:
        raise NoSuchPlace(screen=screen, target=target)
    return names.index(target)


class Cursor:
    """A place among a number of places, counted from 0, which the arrows move and which stops at either end."""

    __slots__ = ('_place',)

    def __init__(self, *, place=FIRST_PLACE):
        self._place = place

    def get_place(self):
        return self._place

    def set_place(self, place):
        self._place = place

    def is_on(self, place):
        return self._place == place

    def is_on_one_of(self, places):
        return self._place in places

    def move(self, *, name, count):
        """Go one place back for Up or Left and one forward for Down or Right, among count places, stopping at either end."""
        self._place = cursor_moved(place=self._place, name=name, count=count)

    def shift(self, offset):
        """Go on by an offset, as the cursor does when what it is on is carried or a row is put in above it."""
        self._place += offset

    def keep_within(self, count):
        """Come back inside count places, as after rows were removed."""
        self._place = max(min(self._place, count - 1), FIRST_PLACE)

    def move_among(self, *, name, places):
        """Go to the place before or after it among the places given, in their order, as among the rows a search keeps; onto the first of them when it is on none."""
        if not places:
            return
        if self._place not in places:
            self._place = places[0]
            return
        self._place = places[cursor_moved(place=places.index(self._place), name=name, count=len(places))]

    def keep_among(self, places):
        """Stay where it is while that is one of the places given, and otherwise go to the first of them."""
        if places and self._place not in places:
            self._place = places[0]


class Search:
    """What has been typed to narrow a list to the options that contain it, ignoring case."""

    __slots__ = ('_typed',)

    def __init__(self):
        self._typed = NOTHING_TYPED

    def get_typed(self):
        return self._typed

    def clear(self):
        self._typed = NOTHING_TYPED

    def type_key(self, name):
        """Add the character a key types."""
        self._typed += keys.SPACE_CHARACTER if name == Key.SPACE else name

    def erase(self):
        """Take the last character away."""
        self._typed = self._typed[:-1]

    def places_matching(self, options):
        """Return the places of the options whose text contains what was typed: every place when nothing was."""
        return places_matching(options=options, text=self._typed)

    def complete(self, options):
        """Grow what was typed as far as every option still matching agrees from its start, as a shell does."""
        self._typed = completed(options=options, matches=self.places_matching(options), typed=self._typed)


def places_matching(*, options, text):
    """Return the places of the options whose text contains what was typed, ignoring case: every place when nothing was."""
    wanted = text.casefold()
    return [place for place, option in enumerate(options) if wanted in str(option).casefold()]


def completed(*, options, matches, typed):
    """Return what was typed, completed as far as every matching option agrees from its start, like a shell does.

    Matching is by containing, so completion only grows what was typed when every match starts
    with it; otherwise what was typed stays as it is.
    """
    names = [str(options[place]) for place in matches]
    if not names or not all(name.casefold().startswith(typed.casefold()) for name in names):
        return typed
    first = names[0]
    length = len(typed)
    while length < len(first) and all(name.casefold().startswith(first[:length + 1].casefold()) for name in names):
        length += 1
    return first[:length]


def shown_around(*, places, at, room):
    """Return the run of places a list with room for so many shows, keeping the one at the cursor near the middle and the list full at either end."""
    start = max(min(at - room // 2, len(places) - room), FIRST_PLACE)
    return places[start:start + room]
