# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Swell editor page: one Swell generator's settings."""

from llamatron.engine.generators import swell as swell_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.shape_editor import ShapeEditor
from llamatron.model.schema.file_format import Shape
from llamatron.user_strings import help as help_text, labels, messages


class SwellEditor(ShapeEditor):

    """The page that edits a Swell generator: how loud a clip's notes play, over time."""

    KEYS = keybindings.SwellEditor
    HELP = help_text.HELP_SWELL_EDITOR
    SECTION = swell_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    KIND = swell_plugin.NAME
    SHAPE = Shape.SWELL
    LABEL = labels.MSG_SHAPE_NAMES[Shape.SWELL]
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_SHAPE_NAMES[Shape.SWELL])
    HAS_ACCENT = True
