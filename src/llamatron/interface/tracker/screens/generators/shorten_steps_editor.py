# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Shorten steps page: a Shorten's row of steps, each on or off."""

from llamatron.engine.generators import shorten as shorten_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.step_row_editor import StepRowEditor
from llamatron.user_strings import labels


class ShortenStepsEditor(StepRowEditor):

    """The editor of a Shorten generator's row of steps, how much shorter each step's note plays."""

    KEYS = keybindings.ShortenStepsEditor
    SECTION = shorten_plugin.SECTION
    KIND = shorten_plugin.NAME
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
