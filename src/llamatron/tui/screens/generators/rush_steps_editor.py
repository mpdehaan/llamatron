# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Rush steps page: a Rush's row of steps, each on or off."""

from llamatron.model.schema.file_format import GeneratorKind, Section
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.step_row_editor import StepRowEditor
from llamatron.user_strings import labels


class RushStepsEditor(StepRowEditor):

    """The editor of a Rush generator's row of steps, how early each step plays."""

    KEYS = keybindings.RushStepsEditor
    SECTION = Section.RUSHES
    KIND = GeneratorKind.RUSH
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
