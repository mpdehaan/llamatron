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
from llamatron.music.note import MAX_OCTAVE, MIN_OCTAVE
from llamatron.strings.help import HELP_VOICE_LEADING_EDITOR
from llamatron.strings.labels import Crumb, MSG_HIGHEST_OCTAVE_LABEL, MSG_LOWEST_OCTAVE_LABEL, MSG_ROOT_IN_BASS_LABEL, MSG_VOICE_LEADING_LABEL
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.field import NameField, Toggle
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.octave_field import octave_field
from llamatron.tui.screens.shows_named_item import ShowsNamedItem


class VoiceLeadingEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.VoiceLeadingEditor
    HELP = HELP_VOICE_LEADING_EDITOR
    SECTION = Section.VOICE_LEADINGS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_VOICE_LEADING_LABEL)

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
                page=self, label=MSG_LOWEST_OCTAVE_LABEL, current=voicing.get_lowest_octave, lowest=lambda: MIN_OCTAVE, highest=voicing.get_highest_octave,
                default=DEFAULT_VOICING_LOWEST_OCTAVE, set_octave=lambda octave: self.store(setting=VoiceLeadingSetting.LOWEST_OCTAVE, value=octave),
            ),
            octave_field(
                page=self, label=MSG_HIGHEST_OCTAVE_LABEL, current=voicing.get_highest_octave, lowest=voicing.get_lowest_octave, highest=lambda: MAX_OCTAVE,
                default=DEFAULT_VOICING_HIGHEST_OCTAVE, set_octave=lambda octave: self.store(setting=VoiceLeadingSetting.HIGHEST_OCTAVE, value=octave),
            ),
            Toggle(label=MSG_ROOT_IN_BASS_LABEL, on=voicing.keeps_root_in_bass(), set=lambda on: self.store(setting=VoiceLeadingSetting.ROOT_IN_BASS, value=on or None)),
            restart_field(self),
        ]
