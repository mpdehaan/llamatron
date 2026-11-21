# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Swell editor page: one Swell generator's settings."""

from llamatron.model.vocabulary.file_format import GeneratorKind, Section, Shape
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.shape_editor import ShapeEditor
from llamatron.user_strings import help as help_text, labels, messages


class SwellEditor(ShapeEditor):

    """The page that edits a Swell generator: how loud a clip's notes play, over time."""

    KEYS = keybindings.SwellEditor
    HELP = help_text.HELP_SWELL_EDITOR
    SECTION = Section.SWELLS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    KIND = GeneratorKind.SWELL
    SHAPE = Shape.SWELL
    LABEL = labels.MSG_SHAPE_NAMES[Shape.SWELL]
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_SHAPE_NAMES[Shape.SWELL])
    HAS_ACCENT = True
