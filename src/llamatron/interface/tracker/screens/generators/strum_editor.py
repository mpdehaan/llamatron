# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Strum editor page: one Strum generator's name and its strum, which wins over a clip's and its track's."""

from llamatron.engine.generators import strum as strum_plugin
from llamatron.engine.generators.strum import strings as strum_strings
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.strum_fields import strum_fields
from llamatron.interface.tracker.screens.shared.field import NameField
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.restart_field import restart_field
from llamatron.user_strings import help as help_text, labels, messages


class StrumEditor(GeneratorEditor, FieldPage):

    """The page that edits a Strum generator, which spreads a chord's notes as a strum."""

    KEYS = keybindings.StrumEditor
    HELP = help_text.HELP_STRUM_EDITOR
    SECTION = strum_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=strum_strings.MSG_LABEL)

    def fields(self):
        strum = self.settings()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            *strum_fields(
                page=self, value=strum.get_strum_setting, prefixed=False,
                store=lambda part, value: self.store(setting=part, value=value),
            ),
            restart_field(self),
        ]
