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
"""The Drag editor: a Drag's name, step, amount, row of steps and Restart."""

from llamatron.composition import generator_settings, limits
from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import StepRowSetting
from llamatron.strings import help as help_text, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.drag_steps_editor import DragStepsEditor
from llamatron.tui.screens.generators.step_row_generator_editor import StepRowGeneratorEditor


class DragEditor(StepRowGeneratorEditor):

    KEYS = keybindings.DragEditor
    HELP = help_text.HELP_DRAG_EDITOR
    SECTION = Section.DRAGS
    KIND = GeneratorKind.DRAG
    STEPS_EDITOR = DragStepsEditor
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_DRAG_LABEL)

    def amount_fields(self):
        return [self.percent_field(label=labels.MSG_DRAG_AMOUNT_LABEL, setting=StepRowSetting.AMOUNT, current=self.generator().get_amount(), default=generator_settings.DEFAULT_DRAG,
                                   lowest=generator_settings.NO_RUSH_OR_DRAG, highest=limits.MAX_RUSH_OR_DRAG)]
