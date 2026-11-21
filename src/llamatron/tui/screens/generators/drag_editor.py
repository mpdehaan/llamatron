# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Drag editor: a Drag's name, step, amount, row of steps and Restart."""

from llamatron.model.objects import generator_settings
from llamatron.model.objects.generator_settings import StepRowSetting
from llamatron.model.schema.file_format import GeneratorKind, Section
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.drag_steps_editor import DragStepsEditor
from llamatron.tui.screens.generators.step_row_generator_editor import StepRowGeneratorEditor
from llamatron.user_strings import help as help_text, labels, messages


class DragEditor(StepRowGeneratorEditor):

    """The page that edits a Drag generator, which plays notes late, step by step."""

    KEYS = keybindings.DragEditor
    HELP = help_text.HELP_DRAG_EDITOR
    SECTION = Section.DRAGS
    KIND = GeneratorKind.DRAG
    STEPS_EDITOR = DragStepsEditor
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_DRAG_LABEL)

    def amount_fields(self):
        return [self.number_field(label=labels.MSG_DRAG_AMOUNT_LABEL, setting=StepRowSetting.AMOUNT, current=self.settings().get_amount(), default=generator_settings.DEFAULT_DRAG)]
