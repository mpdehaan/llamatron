# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The field of a generator's progression: its chords as numerals in the song's scale, like I V vi IV, which ENTER opens in the
chord editor."""

import functools

from llamatron.interface.forms.nodes import Field
from llamatron.interface.pages import places
from llamatron.model.values.progressions import roman_numeral
from llamatron.user_strings import legends, marks


def numerals_text(*, progression, scale):
    """Return a progression's chords as numerals in a scale, like I V vi IV, as its field and its list page show them."""
    numerals = []
    for degree, accidental in zip(progression.get_chords(), progression.get_accidentals()):
        numerals.append(roman_numeral(scale=scale, degree=degree, accidental=accidental))
    return marks.MSG_NUMERALS_SEPARATOR.join(numerals)


def song_scale(song):
    """Return a song's scale, or None when it has none."""
    name = song.get_scale_name()
    if name is None:
        return None
    return song.get_setlist().get_named_scale(name)


def progression_field(*, page, label):
    """Return the field of the progression of the generator a page shows, ENTER opening it in the chord editor."""
    return Field(
        label=label, value=functools.partial(_numerals_on, page), adjust=None, enter=functools.partial(_open_chords, page),
        enter_what=legends.What.EDIT,
    )


def _numerals_on(page):
    """Return the numerals of the progression of the generator a page shows, in the current song's scale."""
    return numerals_text(progression=page.settings(), scale=song_scale(page.document().song()))


def _open_chords(page):
    """Open the chord editor on the progression of the generator a page shows."""
    page.open_part(places.CHORDS, section=page.SECTION)
