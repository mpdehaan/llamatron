# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Density editor page: one Density generator's settings."""

from llamatron.model.schema.file_format import GeneratorKind, Section, Shape
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.shape_editor import ShapeEditor
from llamatron.user_strings import help as help_text, labels, messages


class DensityEditor(ShapeEditor):

    """The page that edits a Density generator: how many of a clip's notes sound, over time."""

    KEYS = keybindings.DensityEditor
    HELP = help_text.HELP_DENSITY_EDITOR
    SECTION = Section.DENSITIES
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    KIND = GeneratorKind.DENSITY
    SHAPE = Shape.DENSITY
    LABEL = labels.MSG_SHAPE_NAMES[Shape.DENSITY]
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_SHAPE_NAMES[Shape.DENSITY])
    HAS_ACCENT = False
