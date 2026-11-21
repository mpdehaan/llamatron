# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Auto ratchet editor page."""

from llamatron.engine.generators import auto_ratchet as auto_ratchet_plugin
from llamatron.engine.generators.auto_ratchet import strings as auto_ratchet_strings
from llamatron.engine.generators.auto_ratchet.model import AutoRatchetSetting
from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.screens.generators.restart_field import restart_field
from llamatron.interface.tracker.screens.shared.field import Field, NameField
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.shared import counts_text
from llamatron.user_strings import errors, help as help_text, labels, messages


COUNT_SEPARATOR = ','


class AutoRatchetEditor(GeneratorEditor, FieldPage):

    """The page that edits an AutoRatchet, which repeats notes quickly inside their steps."""

    KEYS = keybindings.AutoRatchetEditor
    HELP = help_text.HELP_AUTO_RATCHET_EDITOR
    SECTION = auto_ratchet_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=auto_ratchet_strings.MSG_LABEL)

    def counts(self):
        return self.settings().get_counts()

    def ask_counts(self):
        def answered(text):
            parts = text.replace(COUNT_SEPARATOR, drawing.SPACE).split()
            if not parts or not all(part.isdigit() and int(part) >= 1 for part in parts):
                self.refuse(errors.ERR_BAD_COUNTS)
                return
            self.document().change_set(self.settings().set_setting, name=AutoRatchetSetting.COUNTS, value=[int(part) for part in parts])
        self.ask_text(title=labels.MSG_COUNTS_LABEL, value=counts_text(self.counts()), then=answered)

    def fields(self):
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            Field(label=labels.MSG_COUNTS_LABEL, value=lambda: counts_text(self.counts()), adjust=None, enter=self.ask_counts),
            restart_field(self),
        ]
