# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Drag steps page: a Drag's row of steps, each on or off."""

from llamatron.engine.generators import drag as drag_plugin
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.step_row_editor import StepRowEditor
from llamatron.user_strings import labels


class DragStepsEditor(StepRowEditor):

    """The editor of a Drag generator's row of steps, how late each step plays."""

    KEYS = keybindings.DragStepsEditor
    SECTION = drag_plugin.SECTION
    KIND = drag_plugin.NAME
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
