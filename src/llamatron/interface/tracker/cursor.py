# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a search typed into a list keeps: the part of a page's behaviour that draws nothing, beside the forms' Cursor
(interface/forms/cursor.py).

A page or a dialog holds a Search where typing narrows a list. It knows nothing of what is drawn, so the rule a cursor keeps,
staying on a row a search still shows, is written once and is tested without a screen.
"""

from llamatron.interface.tracker import keys
from llamatron.interface.tracker.keys import Key

FIRST_PLACE = 0
NOTHING_TYPED = ''


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
