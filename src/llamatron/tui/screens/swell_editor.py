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
"""The Swell editor page: one Swell generator's settings."""

from llamatron.composition.file_format import GeneratorKind, Section, Shape
from llamatron.strings.help import HELP_SWELL_EDITOR
from llamatron.strings.labels import Crumb, MSG_SHAPE_NAMES
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui.screens.shape_editor import ShapeEditor
from llamatron.tui import keybindings


class SwellEditor(ShapeEditor):

    KEYS = keybindings.SwellEditor
    HELP = HELP_SWELL_EDITOR
    SECTION = Section.SWELLS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    KIND = GeneratorKind.SWELL
    SHAPE = Shape.SWELL
    LABEL = MSG_SHAPE_NAMES[Shape.SWELL]
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_SHAPE_NAMES[Shape.SWELL])
    HAS_ACCENT = True
