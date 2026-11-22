# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Restart field every generator's editor ends its own settings with: when the generator starts over, every clip, on new scene or whole song."""

import functools

from llamatron.interface.tracker.screens.shared.field import ChoiceField
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Restart
from llamatron.user_strings import labels



def restart_field(page):
    """Return the Restart field of the generator a page shows, whose settings it gives by settings() and keeps by store()."""
    current = page.settings().get_restart()
    return ChoiceField(
        page=page, label=labels.MSG_RESTART_LABEL, choices=file_format.RESTARTS, current=current, names=[labels.MSG_RESTART_NAMES[choice] for choice in file_format.RESTARTS],
        shown=labels.MSG_RESTART_NAMES[current],
        set=functools.partial(_store_restart, page=page),
    )


def _store_restart(chosen, *, page):
    """Keep when the generator starts over, left out of the file for every clip."""
    if chosen == Restart.EVERY_CLIP:
        chosen = None
    page.store(setting=file_format.GENERATOR_RESTART, value=chosen)
