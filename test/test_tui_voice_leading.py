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
"""The tracker's Voice leading: its list page and its editor, with the range shown in the set's octave labels."""

from ui_testing import SMOOTH, UITest
from llamatron.composition.file_format import Section, GeneratorKind
from llamatron.composition.generator_settings import DEFAULT_VOICING_HIGHEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE
from llamatron.strings.labels import MSG_HIGHEST_OCTAVE_LABEL, MSG_LOWEST_OCTAVE_LABEL, MSG_ROOT_IN_BASS_LABEL
from llamatron.tui.keys import Key
from llamatron.tui.screens.voice_leading_editor import VoiceLeadingEditor
from llamatron.tui import keybindings

NEW_ONE = 'close'


class TestVoiceLeadingAdded(UITest):

    async def test_a_new_one_sets_nothing(self):
        name = await self.add_generator(Section.VOICE_LEADINGS)
        self.assertEqual(self.document.song().get_generator_settings(kind=GeneratorKind.VOICE_LEADING, name=name).to_data(), {})


class TestVoiceLeadingEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.VOICE_LEADINGS)
        self.assertIsInstance(self.app.screen, VoiceLeadingEditor)

    def voicing(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.VOICE_LEADING, name=SMOOTH)

    async def test_the_lowest_octave_never_passes_the_highest(self):
        await self.select_field(MSG_LOWEST_OCTAVE_LABEL)
        await self.press(*[keybindings.VoiceLeadingEditor.MORE] * (DEFAULT_VOICING_HIGHEST_OCTAVE - DEFAULT_VOICING_LOWEST_OCTAVE + 1))
        self.assertEqual(self.voicing().get_lowest_octave(), DEFAULT_VOICING_HIGHEST_OCTAVE)

    async def test_the_highest_octave_steps_down_and_bksp_puts_it_back(self):
        await self.select_field(MSG_HIGHEST_OCTAVE_LABEL)
        await self.press(keybindings.VoiceLeadingEditor.LESS)
        self.assertEqual(self.voicing().get_highest_octave(), DEFAULT_VOICING_HIGHEST_OCTAVE - 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.voicing().get_highest_octave(), DEFAULT_VOICING_HIGHEST_OCTAVE)

    async def test_keep_the_root_in_the_bass_turns_on_and_off(self):
        await self.select_field(MSG_ROOT_IN_BASS_LABEL)
        await self.press(keybindings.VoiceLeadingEditor.TOGGLE)
        self.assertTrue(self.voicing().keeps_root_in_bass())
        await self.press(keybindings.VoiceLeadingEditor.TOGGLE)
        self.assertFalse(self.voicing().keeps_root_in_bass())
