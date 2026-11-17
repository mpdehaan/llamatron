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

"""The song wizard's Listen: a part of the song as it would be made, heard through FluidSynth's stand-in and thrown away."""

from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT
from llamatron.strings.errors import ERR_WIZARD_CANNOT_LISTEN
from llamatron.strings.labels import MSG_WIZARD_HOOKS_BRANCH, MSG_WIZARD_LINES_LABEL, MSG_WIZARD_MELODY_BRANCH
from llamatron.strings.messages import MSG_STOPPED, MSG_WIZARD_LISTEN_RIFF, MSG_WIZARD_LISTEN_HOOK, MSG_WIZARD_LISTEN_SECTION, MSG_WIZARD_LISTEN_TUNE, MSG_WIZARD_LISTENING
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from tests.tui.test_tui_playback import PlaybackTest

GENRE = 'rock'
SUBGENRE = 'arena rock'
A_WHILE = 2.0
A_LONG_WHILE = 120.0
FIRST_SECTION = 'intro'
FIRST_SECTION_NUMBER = 1
A_VERSE = 'verse-1'
A_VERSE_NUMBER = 2
DRUM_CHANNEL_BYTE = 9
CHANNEL_MASK = 0x0F
THE_HOOK_AND_THE_DRUMS = 2


class TestWizardListening(PlaybackTest):
    """L (Listen) on the wizard's Hooks and Melody panels and on a section."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.Page.WIZARD)
        choices = self.app.screen.choices()
        choices.set_genre(GENRE)
        choices.set_subgenre(SUBGENRE)
        await self.press(Key.DOWN, Key.UP)

    def preview(self):
        return self.app.made_preview()

    async def go_to(self, name):
        wizard = self.app.screen
        wizard.tree_place = [branch.name() for _, branch in wizard.rows()].index(name)
        await self.press(Key.DOWN, Key.UP)

    async def let_the_preview_play(self, seconds):
        self.clock.advance(seconds)
        self.preview().tick()
        if self.preview().player() is not None:
            self.preview().player().sender().send_due()
        self.app.screen.draw()
        await self.pilot.pause()

    def channels_heard(self):
        return {data[0] & CHANNEL_MASK for data in self.note_ons(FLUIDSYNTH_PORT)}

    async def test_the_hook_is_heard_over_the_drums_again_and_again_and_stops(self):
        await self.go_to(MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertIn(MSG_WIZARD_LISTENING.format(what=MSG_WIZARD_LISTEN_HOOK), self.text())
        self.assertEqual(self.preview().playing(), MSG_WIZARD_LISTEN_HOOK)
        await self.let_the_preview_play(A_WHILE)
        self.assertTrue(self.note_ons(FLUIDSYNTH_PORT))
        # The hook's player and the drums under it, and nobody else.
        self.assertEqual(len(self.channels_heard()), THE_HOOK_AND_THE_DRUMS)
        self.assertIn(DRUM_CHANNEL_BYTE, self.channels_heard())
        await self.let_the_preview_play(A_LONG_WHILE)
        self.assertEqual(self.preview().playing(), MSG_WIZARD_LISTEN_HOOK)
        await self.press(keybindings.WizardPage.STOP_LISTENING)
        self.assertIn(MSG_STOPPED, self.text())
        self.assertIsNone(self.preview().playing())

    async def test_the_tune_is_heard_from_the_melody_panel(self):
        await self.go_to(MSG_WIZARD_MELODY_BRANCH)
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertEqual(self.preview().playing(), MSG_WIZARD_LISTEN_TUNE)

    async def test_a_section_is_heard_once_with_everybody_in_it(self):
        await self.go_to(FIRST_SECTION)
        await self.press(keybindings.WizardPage.LISTEN)
        what = MSG_WIZARD_LISTEN_SECTION.format(number=FIRST_SECTION_NUMBER, name=FIRST_SECTION)
        self.assertEqual(self.preview().playing(), what)
        await self.let_the_preview_play(A_WHILE)
        self.assertIn(DRUM_CHANNEL_BYTE, self.channels_heard())
        # The section ends and nothing follows it.
        await self.let_the_preview_play(A_LONG_WHILE)
        await self.let_the_preview_play(A_WHILE)
        self.assertIsNone(self.preview().playing())

    async def test_a_choice_stops_what_was_heard(self):
        await self.go_to(MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.LISTEN)
        self.app.screen.choosing(self.app.screen.choices().set_song_plan)(True)
        self.assertIsNone(self.preview().playing())

    async def test_closing_the_wizard_stops_what_was_heard(self):
        await self.go_to(MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.LISTEN, keybindings.WizardPage.CLOSE)
        self.assertIsNone(self.preview().playing())

    async def test_the_lines_dialog_plays_the_section_s_tune_and_stops_when_it_closes(self):
        await self.go_to(A_VERSE)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_LINES_LABEL)
        await self.press(Key.ENTER, keybindings.LinesDialog.LISTEN)
        what = MSG_WIZARD_LISTEN_SECTION.format(number=A_VERSE_NUMBER, name=A_VERSE)
        self.assertEqual(self.preview().playing(), what)
        await self.let_the_preview_play(A_WHILE)
        self.assertTrue(self.note_ons(FLUIDSYNTH_PORT))
        # A change to a line stops what was heard, since it is no longer what the lines make.
        await self.press(keybindings.LinesDialog.LONGER)
        self.assertIsNone(self.preview().playing())
        await self.press(keybindings.LinesDialog.LISTEN, keybindings.LinesDialog.CLOSE)
        self.assertIsNone(self.preview().playing())

    async def test_with_the_hook_off_the_hooks_panel_plays_the_riff(self):
        choices = self.app.screen.choices()
        choices.set_hook(False)
        await self.go_to(MSG_WIZARD_HOOKS_BRANCH)
        self.assertNotIn(keybindings.WizardPage.LISTEN, self.app.screen.shown_keys())
        choices.set_riff(players=choices.riff_players_offered()[0])
        await self.press(Key.DOWN, Key.UP)
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertEqual(self.preview().playing(), MSG_WIZARD_LISTEN_RIFF)

    async def test_without_fluidsynth_listen_is_refused(self):
        self.fluidsynth_installed = False
        await self.go_to(MSG_WIZARD_HOOKS_BRANCH)
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertIn(ERR_WIZARD_CANNOT_LISTEN, self.text())
        self.assertIsNone(self.preview().playing())

    async def test_the_tracker_s_own_set_is_left_alone(self):
        before = self.document.setlist().to_data()
        await self.go_to(FIRST_SECTION)
        await self.press(keybindings.WizardPage.LISTEN)
        await self.let_the_preview_play(A_WHILE)
        self.assertEqual(self.document.setlist().to_data(), before)
