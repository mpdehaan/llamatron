# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The field of a Guitarify's bar of strokes: its ready-made name, or that it is someone's own, and ENTER opening the bar editor."""

import functools

from llamatron.engine.generators.guitarify.schema import ready_bar_matching
from llamatron.interface.forms.nodes import Field
from llamatron.interface.pages import places
from llamatron.user_strings import labels, legends, marks


def bar_shown(guitar):
    """Return a Guitarify's bar on one line: its ready-made name, or that it is someone's own, how many cells and how long each."""
    ready = ready_bar_matching(cell=guitar.get_cell(), strokes=guitar.get_bar(), accents=guitar.get_accents())
    name = labels.MSG_OWN_BAR
    if ready is not None:
        name = labels.MSG_READY_BAR_NAMES[ready]
    return marks.MSG_GUITAR_BAR_SHOWN.format(name=name, count=len(guitar.get_bar()), cell=guitar.get_cell())


def guitar_bar_field(*, page, label):
    """Return the field of the bar of strokes of the Guitarify a page shows, ENTER opening it in the bar editor."""
    return Field(label=label, value=lambda: bar_shown(page.settings()), enter=functools.partial(page.open_part, places.GUITAR_BAR), enter_what=legends.What.EDIT)
