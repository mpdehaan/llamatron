# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Voice leading: its list page and its editor, with the range shown in the set's octave labels."""

from llamatron.engine.generators.voice_leading import settings as voice_leading_settings
from llamatron.model.schema.file_format import GeneratorKind, Section
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.voice_leading_editor import VoiceLeadingEditor
from llamatron.user_strings import labels
from tests.support import ui_testing
from tests.support.ui_testing import UITest

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
        return self.document.song().get_generator_settings(kind=GeneratorKind.VOICE_LEADING, name=ui_testing.SMOOTH)

    async def test_the_lowest_octave_never_passes_the_highest(self):
        await self.select_field(labels.MSG_LOWEST_OCTAVE_LABEL)
        await self.press(*[keybindings.VoiceLeadingEditor.MORE] * (voice_leading_settings.DEFAULT_VOICING_HIGHEST_OCTAVE - voice_leading_settings.DEFAULT_VOICING_LOWEST_OCTAVE + 1))
        self.assertEqual(self.voicing().get_lowest_octave(), voice_leading_settings.DEFAULT_VOICING_HIGHEST_OCTAVE)

    async def test_the_highest_octave_steps_down_and_bksp_puts_it_back(self):
        await self.select_field(labels.MSG_HIGHEST_OCTAVE_LABEL)
        await self.press(keybindings.VoiceLeadingEditor.LESS)
        self.assertEqual(self.voicing().get_highest_octave(), voice_leading_settings.DEFAULT_VOICING_HIGHEST_OCTAVE - 1)
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.voicing().get_highest_octave(), voice_leading_settings.DEFAULT_VOICING_HIGHEST_OCTAVE)

    async def test_keep_the_root_in_the_bass_turns_on_and_off(self):
        await self.select_field(labels.MSG_ROOT_IN_BASS_LABEL)
        await self.press(keybindings.VoiceLeadingEditor.TOGGLE)
        self.assertTrue(self.voicing().keeps_root_in_bass())
        await self.press(keybindings.VoiceLeadingEditor.TOGGLE)
        self.assertFalse(self.voicing().keeps_root_in_bass())
