# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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
