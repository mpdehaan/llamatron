# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Articulate editor page: one Articulate generator's settings."""

from llamatron.composition.file_format import GeneratorKind, Section, Shape
from llamatron.strings import help as help_text, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.shape_editor import ShapeEditor


class ArticulateEditor(ShapeEditor):

    """The page that edits an Articulate generator: how long notes sound by their place in a bar, over time."""

    KEYS = keybindings.ArticulateEditor
    HELP = help_text.HELP_ARTICULATE_EDITOR
    SECTION = Section.ARTICULATES
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    KIND = GeneratorKind.ARTICULATE
    SHAPE = Shape.ARTICULATE
    LABEL = labels.MSG_SHAPE_NAMES[Shape.ARTICULATE]
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_SHAPE_NAMES[Shape.ARTICULATE])
    HAS_ACCENT = False
