# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Glide steps page: a Glide's row of steps, each on or off."""

from llamatron.model.vocabulary.file_format import GeneratorKind, Section
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.step_row_editor import StepRowEditor
from llamatron.user_strings import labels


class GlideStepsEditor(StepRowEditor):

    """The editor of a Glide generator's row of steps, how far each step glides."""

    KEYS = keybindings.GlideStepsEditor
    SECTION = Section.GLIDES
    KIND = GeneratorKind.GLIDE
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
