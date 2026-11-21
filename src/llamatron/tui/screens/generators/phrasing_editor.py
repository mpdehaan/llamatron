# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Phrasing editor: how long a line is, how the lines breathe, and a table of what each kind of section does of its own."""

from llamatron.engine.generators.phrasing import generator as phrasing_values, settings as phrasing_settings
from llamatron.engine.generators.phrasing.settings import PhrasingSetting
from llamatron.model.schema.file_format import Section
from llamatron.tui import keybindings
from llamatron.tui.screens.shared.field import ChoiceField, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.user_strings import help as help_text, labels, messages


class PhrasingEditor(GeneratorEditor, FieldPage):

    """The page that edits a Phrasing generator, which shapes where a tune's lines breathe."""

    KEYS = keybindings.PhrasingEditor
    HELP = help_text.HELP_PHRASING_EDITOR
    SECTION = Section.PHRASINGS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_PHRASING_LABEL)

    def store(self, *, setting, value):
        """Keep a setting, left out of the file where it is what a Phrasing starts with."""
        self.document().change(self.settings().set_setting, name=setting, value=None if value == phrasing_settings.PHRASING_DEFAULTS[setting] else value)

    def choice(self, *, label, setting, choices, names=None):
        """Return a field that chooses one of a setting's values from a list, shown by its name where its value is not a word."""
        current = self.settings().get_own(setting)
        return ChoiceField(
            page=self, label=label, choices=list(choices), names=names, current=current, shown=None if names is None else names[list(choices).index(current)],
            set=lambda chosen: self.store(setting=setting, value=chosen),
        )

    def fields(self):
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            self.choice(label=labels.MSG_PHRASING_LINE_LABEL, setting=PhrasingSetting.LINE_BARS, choices=phrasing_settings.LINES_IN_BARS, names=[labels.MSG_PHRASING_LINE_NAMES[bars] for bars in phrasing_settings.LINES_IN_BARS]),
            self.choice(label=labels.MSG_PHRASING_BREATH_LABEL, setting=PhrasingSetting.BREATH, choices=phrasing_values.BREATHS),
            self.choice(label=labels.MSG_PHRASING_RISE_LABEL, setting=PhrasingSetting.RISE_AND_FALL, choices=phrasing_values.RISES),
            self.choice(label=labels.MSG_PHRASING_NOTES_LABEL, setting=PhrasingSetting.NOTES, choices=phrasing_values.JOINS),
        ]
