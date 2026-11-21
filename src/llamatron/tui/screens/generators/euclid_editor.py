# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Euclid editor page: one Euclid generator's name and its rhythm, a mask painted on clips on top of their track's."""

from rich.text import Text

from llamatron.composition.file_format import EuclidPart, Section
from llamatron.strings import help as help_text, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.drawing import Style
from llamatron.tui.screens.generators.euclid_fields import drawn_rhythm, euclid_fields, pick_rhythm
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor


class EuclidEditor(GeneratorEditor, FieldPage):

    """The page that edits a Euclidean mask, which keeps the notes on an even spread of a bar's steps."""

    KEYS = keybindings.EuclidEditor
    HELP = help_text.HELP_EUCLID_EDITOR
    SECTION = Section.EUCLIDS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_EUCLID_LABEL)

    def fields(self):
        return [NameField(value=lambda: self.item, rename=self.rename), *euclid_fields(page=self, value=self.settings().get_euclid_setting, store=lambda part, value: self.store(setting=part, value=value), prefixed=False), restart_field(self)]

    def page_keys(self):
        if self.field().label == labels.MSG_EUCLID_PART_LABELS[EuclidPart.HITS]:
            return [self.bind(self.KEYS.PICK_RHYTHM, action=lambda: pick_rhythm(page=self, store=lambda part, value: self.store(setting=part, value=value)))]
        return []

    def remarks(self, width):
        mask = self.settings().get_euclid()
        return [] if mask is None else [Text(drawn_rhythm(hits=mask.hits, steps=mask.steps, rotate=mask.rotate), style=Style.DIM)]
