# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Voice leading editor page: one voice leading's name, the octaves its chords stay within, and whether the root stays in the bass."""

from llamatron.model.objects import generator_settings
from llamatron.model.objects.generator_settings import VoiceLeadingSetting
from llamatron.model.values import note
from llamatron.model.vocabulary.file_format import Section
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import NameField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.tui.screens.shared.octave_field import octave_field
from llamatron.user_strings import help as help_text, labels, messages


class VoiceLeadingEditor(GeneratorEditor, FieldPage):

    """The page that edits Voice leading, which voices each chord nearest the one before."""

    KEYS = keybindings.VoiceLeadingEditor
    HELP = help_text.HELP_VOICE_LEADING_EDITOR
    SECTION = Section.VOICE_LEADINGS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_VOICE_LEADING_LABEL)

    def fields(self):
        voicing = self.settings()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            octave_field(
                page=self, label=labels.MSG_LOWEST_OCTAVE_LABEL, current=voicing.get_lowest_octave, lowest=lambda: note.MIN_OCTAVE, highest=voicing.get_highest_octave,
                default=generator_settings.DEFAULT_VOICING_LOWEST_OCTAVE, set_octave=lambda octave: self.store(setting=VoiceLeadingSetting.LOWEST_OCTAVE, value=octave),
            ),
            octave_field(
                page=self, label=labels.MSG_HIGHEST_OCTAVE_LABEL, current=voicing.get_highest_octave, lowest=voicing.get_lowest_octave, highest=lambda: note.MAX_OCTAVE,
                default=generator_settings.DEFAULT_VOICING_HIGHEST_OCTAVE, set_octave=lambda octave: self.store(setting=VoiceLeadingSetting.HIGHEST_OCTAVE, value=octave),
            ),
            Toggle(label=labels.MSG_ROOT_IN_BASS_LABEL, on=voicing.keeps_root_in_bass(), set=lambda on: self.store(setting=VoiceLeadingSetting.ROOT_IN_BASS, value=on or None)),
            restart_field(self),
        ]
