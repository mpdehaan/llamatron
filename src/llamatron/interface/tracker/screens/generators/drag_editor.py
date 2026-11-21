# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Drag editor: a Drag's name, step, amount, row of steps and Restart."""

from llamatron.engine.generators import drag as drag_plugin
from llamatron.engine.generators.drag import model as drag_model, strings as drag_strings
from llamatron.engine.generators.step_row import StepRowSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.drag_steps_editor import DragStepsEditor
from llamatron.interface.tracker.screens.generators.step_row_generator_editor import StepRowGeneratorEditor
from llamatron.user_strings import help as help_text, labels, messages


class DragEditor(StepRowGeneratorEditor):

    """The page that edits a Drag generator, which plays notes late, step by step."""

    KEYS = keybindings.DragEditor
    HELP = help_text.HELP_DRAG_EDITOR
    SECTION = drag_plugin.SECTION
    KIND = drag_plugin.NAME
    STEPS_EDITOR = DragStepsEditor
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=drag_strings.MSG_LABEL)

    def amount_fields(self):
        return [self.number_field(label=labels.MSG_DRAG_AMOUNT_LABEL, setting=StepRowSetting.AMOUNT, current=self.settings().get_amount(), default=drag_model.DEFAULT_DRAG)]
