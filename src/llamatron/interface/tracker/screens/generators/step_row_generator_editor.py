# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What the Glide, Shorten, Rush and Drag editors share: a generator's name, its step, its own amounts, its row of steps, which Enter opens in the step row editor, and its Restart."""

from llamatron.engine.generators.step_row import StepRowSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.restart_field import restart_field
from llamatron.interface.tracker.screens.generators.time_field import time_field
from llamatron.interface.tracker.screens.shared.field import Field, NameField
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.user_strings import labels, legends, marks


def steps_text(values):
    """Return a row of steps on one line, the dot for a step that's on and a point for one that's off, like ● . ● ."""
    return ' '.join(marks.MSG_TOGGLE_ON if value else marks.MSG_STEP_OFF for value in values)


class StepRowGeneratorEditor(GeneratorEditor, FieldPage):
    """What the Glide, Shorten, Rush and Drag editors share: name, step, the generator's own amounts, the row of steps, and Restart."""

    KEYS = keybindings.StepRowGeneratorEditor
    KIND = None
    # The page that edits the generator's row of steps.
    STEPS_EDITOR = None

    def amount_fields(self):
        """Return the fields of the generator's own amounts."""
        raise NotImplementedError

    def fields(self):
        generator = self.settings()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(page=self, label=labels.MSG_STEP_LABEL, written=generator.step_row().get_step(), first=marks.MSG_PATTERN_STEP_SHOWN, store=lambda value: self.store(setting=StepRowSetting.STEP, value=value)),
            *self.amount_fields(),
            Field(label=labels.MSG_STEPS_LABEL, value=lambda: steps_text(self.settings().step_row().get_steps()), adjust=None,
                  enter=lambda: self.show_page(self.STEPS_EDITOR(holder=self.holder, name=self.item)), enter_what=legends.What.EDIT),
            restart_field(self),
        ]
