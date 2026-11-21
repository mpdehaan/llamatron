# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Restart field every generator's editor ends its own settings with: when the generator starts over, every clip, on new scene or whole song."""

from llamatron.interface.tracker.screens.shared.field import ChoiceField
from llamatron.model.schema import file_format, generator_plugins
from llamatron.model.schema.file_format import Restart
from llamatron.user_strings import labels

# Each named section's generator kind, the other way round from NAMED_GENERATORS.
KINDS_BY_SECTION = {section: kind for kind, section in generator_plugins.sections_by_name().items()}


def restart_field(page):
    """Return the Restart field of the generator a page of one named generator shows, by its SECTION and its item."""
    settings = page.document().song().get_generator_settings(kind=KINDS_BY_SECTION[page.SECTION], name=page.item)
    current = settings.get_restart()
    return ChoiceField(
        page=page, label=labels.MSG_RESTART_LABEL, choices=file_format.RESTARTS, current=current, names=[labels.MSG_RESTART_NAMES[choice] for choice in file_format.RESTARTS],
        shown=labels.MSG_RESTART_NAMES[current],
        set=lambda chosen: page.document().change_set(page.document().generator(section=page.SECTION, name=page.item).set_setting, name=file_format.GENERATOR_RESTART, value=None if chosen == Restart.EVERY_CLIP else chosen),
    )
