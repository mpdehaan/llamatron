# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The fields of a section's fade in the song wizard, shown on a section's panel and on the Intro panel: whether the section
fades, the velocity it fades from or to, and the bars the fade takes."""

import functools

from llamatron.interface.forms.nodes import NumberField, Toggle
from llamatron.user_strings import labels, legends
from llamatron.wizards.create_song import wizard_names

# A fade takes at least the section's first bar.
FIRST_BAR = 1


def fade_field(*, branch, place, field):
    """Return a field of a section's fade, named for the fade's way: the switch, Fade in where the section opens the song and
    Fade out where the section closes it; the level, the velocity the fade starts from or ends at; or the bars the fade
    takes, the first of the section for a fade in and the last for a fade out. The level and the bars show what a fade takes
    until they are given, and Bksp gives each back."""
    choices = branch.get_choices()
    page = branch.get_page()
    section = choices.section(place)
    fade = section.fade()
    label = labels.MSG_WIZARD_FADE_LABELS[fade.way()][field]
    own = section.own(field=field)
    set_own = page.refusing(functools.partial(give_section_own, choices=choices, place=place, field=field))
    if field == wizard_names.SONG_PLAN_FADES:
        return Toggle(label=label, on=bool(own), set=set_own)
    usual = section.from_plan(field=field)
    if field == wizard_names.FADE_LEVEL:
        lowest = wizard_names.FADED
        highest = wizard_names.LOUDEST_FADE_LEVEL
    else:
        lowest = FIRST_BAR
        highest = section.bars()
    now = usual
    if own is not None:
        now = min(own, highest)
    clear = {}
    if own is not None:
        clear = dict(clear=functools.partial(set_own, None), clear_what=legends.MSG_TUNE_USUAL_WHAT)
    return NumberField(page=page, label=label, number=own, start=usual, shown=_fade_said(field=field, now=now), lowest=lowest,
                       highest=highest, set=set_own, **clear)


def _fade_said(*, field, now):
    """Return what a fade's level or length says: the velocity it starts from or ends at, or the bars it takes."""
    if field == wizard_names.FADE_LEVEL:
        return labels.MSG_WIZARD_FADE_VELOCITY.format(value=now)
    if now == 1:
        return labels.MSG_WIZARD_FADE_ONE_BAR
    return labels.MSG_WIZARD_FADE_BARS.format(value=now)


def give_section_own(value, *, choices, place, field):
    """Give a section a value of its own for a field, or give the field back with None."""
    section = choices.section(place)
    section.set_own(field=field, value=value)
