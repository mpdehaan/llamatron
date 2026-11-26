# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a form's selection is: a place among a number of places, which the moves move and which stops at either end, and the
way to a place a test or a page asks for by name."""

from llamatron.interface.forms import moves
from llamatron.user_strings import errors

FIRST_PLACE = 0


class NoSuchPlace(LookupError):
    """A screen was asked the way to something its cursor cannot reach."""

    def __init__(self, *, screen, target):
        super().__init__(errors.ERR_NO_SUCH_PLACE.format(screen=type(screen).__name__, target=target))


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
        self._place = moves.moved(place=self._place, name=name, count=count)

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
        self._place = places[moves.moved(place=places.index(self._place), name=name, count=len(places))]

    def keep_among(self, places):
        """Stay where it is while that is one of the places given, and otherwise go to the first of them."""
        if places and self._place not in places:
            self._place = places[0]
