# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Groove field that the Scene page and the track editor share: take the groove from above, play straight, or name one.

A scene's or a track's groove choice is None to take the song's (or, for a track, the scene's or
the song's), False to play straight whatever else chooses, or the name of a groove. Left and
right step through those in that order, Enter picks from a list, and Bksp goes back to None.
"""

from llamatron.interface.forms.nodes import Field
from llamatron.interface.forms.text import sorted_names
from llamatron.user_strings import labels, legends, marks

# The first two choices, before the names: take the groove from above, and off.
TAKE_FROM_ABOVE = None
OFF = False


def groove_choice_field(*, page, title, choice, inherited_option, inherited_shown, choose, clear_what):
    """Return the Groove field for a scene or a track, whose current choice is None, False or a name."""
    names = sorted_names(page.document().get_setlist().get_groove_names())
    choices = [TAKE_FROM_ABOVE, OFF, *names]

    def shown():
        if choice is TAKE_FROM_ABOVE:
            return inherited_shown
        if choice is OFF:
            return marks.MSG_GROOVE_OFF_SHOWN
        return choice

    def place_of(value):
        return next(place for place, candidate in enumerate(choices) if candidate is value or candidate == value and isinstance(value, str))

    def adjust(offset):
        choose(choices[max(min(place_of(choice) + offset, len(choices) - 1), 0)])

    def pick():
        options = [inherited_option, labels.MSG_GROOVE_OFF_OPTION, *names]
        page.ask_choice(title=title, options=options, current=place_of(choice), then=lambda place: choose(choices[place]))

    return Field(label=labels.MSG_GROOVE_LABEL, value=shown, adjust=adjust, enter=pick, enter_what=legends.What.CHOOSE, clear=lambda: choose(TAKE_FROM_ABOVE), clear_what=clear_what)
