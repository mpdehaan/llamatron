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
"""The Shorten editor: a Shorten's name, step, amount, row of steps and Restart."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import DEFAULT_SHORTEN, StepRowSetting
from llamatron.composition.limits import MAX_SHORTEN, MIN_SHORTEN
from llamatron.strings.labels import MSG_SHORTEN_LABEL
from llamatron.strings.help import HELP_SHORTEN_EDITOR
from llamatron.strings.labels import Crumb, MSG_SHORTEN_LABEL_NAME
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.shorten_steps_editor import ShortenStepsEditor
from llamatron.tui.screens.step_row_generator_editor import StepRowGeneratorEditor


class ShortenEditor(StepRowGeneratorEditor):

    KEYS = keybindings.ShortenEditor
    HELP = HELP_SHORTEN_EDITOR
    SECTION = Section.SHORTENS
    KIND = GeneratorKind.SHORTEN
    STEPS_EDITOR = ShortenStepsEditor
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_SHORTEN_LABEL_NAME)

    def amount_fields(self):
        return [self.percent_field(label=MSG_SHORTEN_LABEL, setting=StepRowSetting.SHORTEN, current=self.generator().get_shorten(), default=DEFAULT_SHORTEN,
                                   lowest=MIN_SHORTEN, highest=MAX_SHORTEN)]
