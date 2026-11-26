# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A table of what a generator does in each kind of section the song's scenes have, as a Musician's: a row a kind, under a
caption, its Plays switched with Space and its Played stepped with [ and ] or picked with ENTER; Left and Right move between
them. A kind the generator holds a setting for stays, so that the setting is seen and kept."""

import functools

from llamatron.interface.forms.nodes import CaptionedTableRow, Field, TableRow, Toggle
from llamatron.model.schema import file_format
from llamatron.user_strings import legends, marks


def section_table(*, page, view):
    """Return the table's rows, the first drawing the caption and the columns' headings, or none where no kind is shown."""
    kinds = _kinds_shown(page=page, view=view)
    widths = _widths(view)
    rows = []
    for place, kind in enumerate(kinds):
        cells = [_plays_cell(page=page, view=view, kind=kind), _played_cell(page=page, view=view, kind=kind)]
        label = kind
        if place == 0:
            rows.append(CaptionedTableRow(label=label, cells=cells, widths=widths, caption=view.caption, headings=[view.plays_label, view.played_label]))
        else:
            rows.append(TableRow(label=label, cells=cells, widths=widths))
    return rows


def store_section(*, page, view, kind, name, value):
    """Keep what a kind of section has of its own, left out where it is what a section does unasked."""
    if value == view.defaults[name]:
        value = None
    page.document().change_set(page.settings().set_section_own, section=kind, name=name, value=value)


def _kinds_shown(*, page, view):
    """Return the kinds of section the table shows: those the song's scenes are, and those the generator has settings for, in the
    order kinds of section are listed."""
    used = {scene.get_section() for scene in page.document().song().get_scenes()}
    return [kind for kind in file_format.SECTION_KINDS if kind in used or _is_set(page=page, view=view, kind=kind)]


def _is_set(*, page, view, kind):
    """Return whether the generator holds a setting of its own for a kind of section."""
    settings = page.settings()
    return any(settings.get_section_own(section=kind, name=name) is not None for name in view.defaults)


def _widths(view):
    """Return each column's width: the room of its heading or its widest value, so that the columns never move."""
    plays = max(len(view.plays_label), len(marks.MSG_TOGGLE_ON), len(marks.MSG_FIELD_TOGGLE_OFF))
    played = max(len(view.played_label), *[len(choice) for choice in view.played_choices])
    return [plays, played]


def _plays_cell(*, page, view, kind):
    """Return whether the generator plays in a kind of section, switched with Space or ENTER."""
    on = page.settings().get_for(section=kind, name=view.plays)
    store = functools.partial(store_section, page=page, view=view, kind=kind, name=view.plays)
    return Toggle(label=view.plays_label, on=on, set=lambda chosen: store(value=chosen))


def _played_cell(*, page, view, kind):
    """Return how the part is played in a kind of section, stepped or picked; nothing to choose where it sits out."""
    settings = page.settings()
    if not settings.get_for(section=kind, name=view.plays):
        return Field(label=view.played_label, value=lambda: marks.MSG_SITS_OUT_SHOWN, adjust=None)
    choices = list(view.played_choices)
    store = functools.partial(store_section, page=page, view=view, kind=kind, name=view.played)

    def current():
        return page.settings().get_for(section=kind, name=view.played)

    def step(offset):
        place = max(min(choices.index(current()) + offset, len(choices) - 1), 0)
        store(value=choices[place])

    def picked():
        page.pick(title=view.played_label, values=choices, shown=choices, current=current(), then=lambda chosen: store(value=chosen))
    return Field(label=view.played_label, value=current, adjust=step, enter=picked, enter_what=legends.What.CHOOSE)
