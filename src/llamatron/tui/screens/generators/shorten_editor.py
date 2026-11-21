# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Shorten editor: a Shorten's name, step, amount, row of steps and Restart."""

from llamatron.composition import generator_settings
from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import StepRowSetting
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.shorten_steps_editor import ShortenStepsEditor
from llamatron.tui.screens.generators.step_row_generator_editor import StepRowGeneratorEditor
from llamatron.user_strings import help as help_text, labels, messages


class ShortenEditor(StepRowGeneratorEditor):

    """The page that edits a Shorten generator, which makes notes shorter, step by step."""

    KEYS = keybindings.ShortenEditor
    HELP = help_text.HELP_SHORTEN_EDITOR
    SECTION = Section.SHORTENS
    KIND = GeneratorKind.SHORTEN
    STEPS_EDITOR = ShortenStepsEditor
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_SHORTEN_LABEL_NAME)

    def amount_fields(self):
        return [self.number_field(label=labels.MSG_SHORTEN_LABEL, setting=StepRowSetting.SHORTEN, current=self.settings().get_shorten(), default=generator_settings.DEFAULT_SHORTEN)]
