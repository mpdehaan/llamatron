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
"""The Shorten steps page: a Shorten's row of steps, each on or off."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.strings.labels import Crumb
from llamatron.tui import keybindings
from llamatron.tui.screens.step_row_editor import StepRowEditor


class ShortenStepsEditor(StepRowEditor):

    KEYS = keybindings.ShortenStepsEditor
    SECTION = Section.SHORTENS
    KIND = GeneratorKind.SHORTEN
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
