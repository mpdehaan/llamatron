# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Rush steps page: a Rush's row of steps, each on or off."""

from llamatron.engine.generators import rush as rush_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.step_row_editor import StepRowEditor
from llamatron.user_strings import labels


class RushStepsEditor(StepRowEditor):

    """The editor of a Rush generator's row of steps, how early each step plays."""

    KEYS = keybindings.RushStepsEditor
    SECTION = rush_plugin.SECTION
    KIND = rush_plugin.NAME
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
