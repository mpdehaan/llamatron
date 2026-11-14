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
"""The Rush editor: a Rush's name, step, amount, row of steps and Restart."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import DEFAULT_RUSH, NO_RUSH_OR_DRAG, StepRowSetting
from llamatron.composition.limits import MAX_RUSH_OR_DRAG
from llamatron.strings.labels import MSG_RUSH_AMOUNT_LABEL
from llamatron.strings.help import HELP_RUSH_EDITOR
from llamatron.strings.labels import Crumb, MSG_RUSH_LABEL
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.rush_steps_editor import RushStepsEditor
from llamatron.tui.screens.step_row_generator_editor import StepRowGeneratorEditor


class RushEditor(StepRowGeneratorEditor):

    KEYS = keybindings.RushEditor
    HELP = HELP_RUSH_EDITOR
    SECTION = Section.RUSHES
    KIND = GeneratorKind.RUSH
    STEPS_EDITOR = RushStepsEditor
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_RUSH_LABEL)

    def amount_fields(self):
        return [self.percent_field(label=MSG_RUSH_AMOUNT_LABEL, setting=StepRowSetting.AMOUNT, current=self.generator().get_amount(), default=DEFAULT_RUSH,
                                   lowest=NO_RUSH_OR_DRAG, highest=MAX_RUSH_OR_DRAG)]
