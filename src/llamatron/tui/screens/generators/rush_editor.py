# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Rush editor: a Rush's name, step, amount, row of steps and Restart."""

from llamatron.composition import generator_settings
from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import StepRowSetting
from llamatron.strings import help as help_text, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.rush_steps_editor import RushStepsEditor
from llamatron.tui.screens.generators.step_row_generator_editor import StepRowGeneratorEditor


class RushEditor(StepRowGeneratorEditor):

    """The page that edits a Rush generator, which plays notes early, step by step."""

    KEYS = keybindings.RushEditor
    HELP = help_text.HELP_RUSH_EDITOR
    SECTION = Section.RUSHES
    KIND = GeneratorKind.RUSH
    STEPS_EDITOR = RushStepsEditor
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_RUSH_LABEL)

    def amount_fields(self):
        return [self.number_field(label=labels.MSG_RUSH_AMOUNT_LABEL, setting=StepRowSetting.AMOUNT, current=self.settings().get_amount(), default=generator_settings.DEFAULT_RUSH)]
