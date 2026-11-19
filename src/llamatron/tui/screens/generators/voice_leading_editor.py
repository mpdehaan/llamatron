# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The Voice leading editor page: one voice leading's name, the octaves its chords stay within, and whether the root stays in the bass."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import DEFAULT_VOICING_HIGHEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE, VoiceLeadingSetting
from llamatron.music import note
from llamatron.strings import help as help_text, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import NameField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.octave_field import octave_field
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem


class VoiceLeadingEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.VoiceLeadingEditor
    HELP = help_text.HELP_VOICE_LEADING_EDITOR
    SECTION = Section.VOICE_LEADINGS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_VOICE_LEADING_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def voicing(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.VOICE_LEADING, name=self.item)

    def store(self, *, setting, value):
        self.document().set_generator_setting(section=Section.VOICE_LEADINGS, name=self.item, setting=setting, value=value)

    def fields(self):
        voicing = self.voicing()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            octave_field(
                page=self, label=labels.MSG_LOWEST_OCTAVE_LABEL, current=voicing.get_lowest_octave, lowest=lambda: note.MIN_OCTAVE, highest=voicing.get_highest_octave,
                default=DEFAULT_VOICING_LOWEST_OCTAVE, set_octave=lambda octave: self.store(setting=VoiceLeadingSetting.LOWEST_OCTAVE, value=octave),
            ),
            octave_field(
                page=self, label=labels.MSG_HIGHEST_OCTAVE_LABEL, current=voicing.get_highest_octave, lowest=voicing.get_lowest_octave, highest=lambda: note.MAX_OCTAVE,
                default=DEFAULT_VOICING_HIGHEST_OCTAVE, set_octave=lambda octave: self.store(setting=VoiceLeadingSetting.HIGHEST_OCTAVE, value=octave),
            ),
            Toggle(label=labels.MSG_ROOT_IN_BASS_LABEL, on=voicing.keeps_root_in_bass(), set=lambda on: self.store(setting=VoiceLeadingSetting.ROOT_IN_BASS, value=on or None)),
            restart_field(self),
        ]
