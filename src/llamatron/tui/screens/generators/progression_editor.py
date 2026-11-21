# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Progression editor page: one progression's name, how long each chord lasts, and its chords, which Enter opens in the chord editor."""

from llamatron.composition import file_format
from llamatron.composition.file_format import Section
from llamatron.composition.generator_settings import ProgressionSetting
from llamatron.composition.progressions import roman_numeral
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.chords_editor import ChordsEditor
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.generators.time_field import time_field
from llamatron.tui.screens.shared.field import Field, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


def numerals_text(*, progression, scale):
    """Return a progression's chords as numerals in a scale, like I V vi IV, as its editor and its list page show them."""
    return marks.MSG_NUMERALS_SEPARATOR.join(
        roman_numeral(scale=scale, degree=degree, accidental=accidental) for degree, accidental in zip(progression.get_chords(), progression.get_accidentals()))


def song_scale(song):
    """Return a song's scale, or None when it has none."""
    name = song.get_scale_name()
    return None if name is None else song.get_named_scale(name)


class ProgressionEditor(GeneratorEditor, FieldPage):

    """The page that edits a Progression, the chords a part is moved through."""

    KEYS = keybindings.ProgressionEditor
    HELP = help_text.HELP_PROGRESSION_EDITOR
    SECTION = Section.PROGRESSIONS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_PROGRESSION_LABEL)

    def fields(self):
        progression = self.settings()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(
                page=self, label=labels.MSG_EVERY_LABEL, written=progression.get_every(), first=file_format.ONE_BAR_WRITTEN,
                store=lambda value: self.document().change(self.settings().set_setting, name=ProgressionSetting.EVERY, value=value),
            ),
            Field(label=labels.MSG_CHORDS_LABEL, value=lambda: numerals_text(progression=progression, scale=song_scale(self.document().song())), adjust=None,
                  enter=lambda: self.show_page(ChordsEditor(holder=self.holder, name=self.item)), enter_what=legends.What.EDIT),
            restart_field(self),
        ]
