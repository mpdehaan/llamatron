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
"""What the Glide, Shorten, Rush and Drag editors share: a generator's name, its step, its own amounts, its row of steps, which Enter opens in the step row editor, and its Restart."""

from llamatron.composition.generator_settings import StepRowSetting
from llamatron.strings.labels import MSG_STEP_LABEL, MSG_STEPS_LABEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_PATTERN_STEP_SHOWN, MSG_STEP_OFF, MSG_TOGGLE_ON
from llamatron.tui.screens.field import Field, NameField, NumberField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.time_field import time_field
from llamatron.tui import keybindings


def steps_text(values):
    """Return a row of steps on one line, the dot for a step that's on and a point for one that's off, like ● . ● ."""
    return ' '.join(MSG_TOGGLE_ON if value else MSG_STEP_OFF for value in values)


class StepRowGeneratorEditor(ShowsNamedItem, FieldPage):
    """What the Glide, Shorten, Rush and Drag editors share: name, step, the generator's own amounts, the row of steps, and Restart."""

    KEYS = keybindings.StepRowGeneratorEditor
    KIND = None
    # The page that edits the generator's row of steps.
    STEPS_EDITOR = None

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def generator(self):
        return self.document().song().get_generator_settings(kind=self.KIND, name=self.item)

    def store(self, *, setting, value):
        self.document().set_generator_setting(section=self.SECTION, name=self.item, setting=setting, value=value)

    def amount_fields(self):
        """Return the fields of the generator's own amounts."""
        raise NotImplementedError

    def percent_field(self, *, label, setting, current, default, lowest, highest):
        return NumberField(page=self, label=label, number=current, lowest=lowest, highest=highest,
                           set=lambda number: self.store(setting=setting, value=None if number == default else number), clear=lambda: self.store(setting=setting, value=None))

    def fields(self):
        generator = self.generator()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(page=self, label=MSG_STEP_LABEL, written=generator.get_step(), first=MSG_PATTERN_STEP_SHOWN, store=lambda value: self.store(setting=StepRowSetting.STEP, value=value)),
            *self.amount_fields(),
            Field(label=MSG_STEPS_LABEL, value=lambda: steps_text(self.generator().get_steps()), adjust=None,
                  enter=lambda: self.show_page(self.STEPS_EDITOR(holder=self.holder, name=self.item)), enter_what=What.EDIT),
            restart_field(self),
        ]
