# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Density editor page: one Density generator's settings."""

from llamatron.engine.generators import density as density_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.shape_editor import ShapeEditor
from llamatron.model.schema.file_format import Shape
from llamatron.user_strings import help as help_text, labels, messages


class DensityEditor(ShapeEditor):

    """The page that edits a Density generator: how many of a clip's notes sound, over time."""

    KEYS = keybindings.DensityEditor
    HELP = help_text.HELP_DENSITY_EDITOR
    SECTION = density_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    KIND = density_plugin.NAME
    SHAPE = Shape.DENSITY
    LABEL = labels.MSG_SHAPE_NAMES[Shape.DENSITY]
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_SHAPE_NAMES[Shape.DENSITY])
    HAS_ACCENT = False
