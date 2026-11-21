# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Glide editor: a Glide's name, step, amount, row of steps and Restart."""

from llamatron.engine.generators import glide as glide_plugin
from llamatron.engine.generators.glide import strings as glide_strings
from llamatron.engine.generators.step_row import StepRowSetting
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.user_strings import help as help_text, labels, messages

# How far a glide can run into the next note, shortest first.
GLIDE_AMOUNTS = ['1/256', '1/128', '1/64', '1/32', '1/16']
DEFAULT_GLIDE_AMOUNT_WRITTEN = '1/128'
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.glide_steps_editor import GlideStepsEditor
from llamatron.tui.screens.generators.step_row_generator_editor import StepRowGeneratorEditor


class GlideEditor(StepRowGeneratorEditor):

    """The page that edits a Glide generator, which slides notes into the next, step by step."""

    KEYS = keybindings.GlideEditor
    HELP = help_text.HELP_GLIDE_EDITOR
    SECTION = glide_plugin.SECTION
    KIND = glide_plugin.NAME
    STEPS_EDITOR = GlideStepsEditor
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=glide_strings.MSG_LABEL)

    def amount_fields(self):
        written = self.settings().get_written_glide_amount()
        current = DEFAULT_GLIDE_AMOUNT_WRITTEN if written is None else str(written)
        return [ChoiceField(page=self, label=labels.MSG_GLIDE_AMOUNT_LABEL, choices=GLIDE_AMOUNTS, current=current,
                            set=lambda chosen: self.store(setting=StepRowSetting.GLIDE_AMOUNT, value=None if chosen == DEFAULT_GLIDE_AMOUNT_WRITTEN else chosen))]
