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
"""The Density editor page: one Density generator's settings."""

from llamatron.composition.file_format import GeneratorKind, Section, Shape
from llamatron.strings.help import HELP_DENSITY_EDITOR
from llamatron.strings.labels import Crumb, MSG_SHAPE_NAMES
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui.screens.shape_editor import ShapeEditor
from llamatron.tui import keybindings


class DensityEditor(ShapeEditor):

    KEYS = keybindings.DensityEditor
    HELP = HELP_DENSITY_EDITOR
    SECTION = Section.DENSITIES
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    KIND = GeneratorKind.DENSITY
    SHAPE = Shape.DENSITY
    LABEL = MSG_SHAPE_NAMES[Shape.DENSITY]
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_SHAPE_NAMES[Shape.DENSITY])
    HAS_ACCENT = False
