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
"""The Glide editor: a Glide's name, step, amount, row of steps and Restart."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import StepRowSetting
from llamatron.strings.labels import MSG_GLIDE_AMOUNT_LABEL
from llamatron.tui.screens.field import ChoiceField

# How far a glide can run into the next note, shortest first.
GLIDE_AMOUNTS = ['1/256', '1/128', '1/64', '1/32', '1/16']
DEFAULT_GLIDE_AMOUNT_WRITTEN = '1/128'
from llamatron.strings.help import HELP_GLIDE_EDITOR
from llamatron.strings.labels import Crumb, MSG_GLIDE_LABEL
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.glide_steps_editor import GlideStepsEditor
from llamatron.tui.screens.step_row_generator_editor import StepRowGeneratorEditor


class GlideEditor(StepRowGeneratorEditor):

    KEYS = keybindings.GlideEditor
    HELP = HELP_GLIDE_EDITOR
    SECTION = Section.GLIDES
    KIND = GeneratorKind.GLIDE
    STEPS_EDITOR = GlideStepsEditor
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_GLIDE_LABEL)

    def amount_fields(self):
        written = self.generator().get_written_glide_amount()
        current = DEFAULT_GLIDE_AMOUNT_WRITTEN if written is None else str(written)
        return [ChoiceField(page=self, label=MSG_GLIDE_AMOUNT_LABEL, choices=GLIDE_AMOUNTS, current=current,
                            set=lambda chosen: self.store(setting=StepRowSetting.GLIDE_AMOUNT, value=None if chosen == DEFAULT_GLIDE_AMOUNT_WRITTEN else chosen))]
