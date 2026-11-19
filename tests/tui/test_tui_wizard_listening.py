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

from llamatron.realtime import fluidsynth
from llamatron.strings import errors, labels, messages
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from llamatron.tui.screens.wizard import section_melody_branch
from tests.tui.test_tui_playback import PlaybackTest

GENRE = 'rock'
SUBGENRE = 'arena rock'
A_WHILE = 2.0
A_PART = 'a part'
A_TRACK_NOBODY_HAS = 'nobody'
A_LONG_WHILE = 120.0
FIRST_SECTION = 'intro'
FIRST_SECTION_NUMBER = 1
A_VERSE = 'verse-1'
A_VERSE_NUMBER = 2
DRUM_CHANNEL_BYTE = 9
CHANNEL_MASK = 0x0F
THE_MELODY_ALONE = 1
A_PLAYER_AND_THE_DRUMS = 2


class TestWizardListening(PlaybackTest):
    """L (Listen) on the wizard's panels of the melodies and the riffs and on a section."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.Page.WIZARD)
        choices = self.app.screen.get_choices()
        choices.set_genre(GENRE)
        choices.set_subgenre(SUBGENRE)
        await self.press(Key.DOWN, Key.UP)

    def preview(self):
        return self.app.made_preview()

    async def go_to(self, name):
        wizard = self.app.screen
        wizard.tree_place = [branch.name() for _, branch in wizard.rows()].index(name)
        await self.press(Key.DOWN, Key.UP)

    def hook_kind(self):
        kind, _ = self.app.screen.get_choices().get_hook().hook_line_place()
        return kind

    def hook_heard(self):
        """What Listen calls the melody of the kind of section that says the hook line."""
        return messages.MSG_WIZARD_MELODY_OF.format(kind=self.hook_kind())

    async def go_to_hook(self):
        """Move the tree's cursor to the panel of the melody of the kind of section that says the hook line."""
        wizard = self.app.screen
        wizard.tree_place = [branch.key() for _, branch in wizard.rows()].index(section_melody_branch.MELODY_KEY.format(kind=self.hook_kind()))
        await self.press(Key.DOWN, Key.UP)

    async def let_the_preview_play(self, seconds):
        self.clock.advance(seconds)
        self.preview().tick()
        if self.preview().get_player() is not None:
            self.preview().get_player().get_sender().send_due()
        self.app.screen.draw()
        await self.pilot.pause()

    def channels_heard(self):
        return {data[0] & CHANNEL_MASK for data in self.note_ons(fluidsynth.FLUIDSYNTH_PORT)}

    async def test_a_melody_is_heard_alone_with_no_drums_under_it_again_and_again_and_stops(self):
        await self.go_to_hook()
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertIn(messages.MSG_WIZARD_LISTENING.format(what=self.hook_heard()), self.text())
        self.assertEqual(self.preview().playing(), self.hook_heard())
        await self.let_the_preview_play(A_WHILE)
        self.assertTrue(self.note_ons(fluidsynth.FLUIDSYNTH_PORT))
        # The melody's player and nobody else: the drums are heard with Listen With Band.
        self.assertEqual(len(self.channels_heard()), THE_MELODY_ALONE)
        self.assertNotIn(DRUM_CHANNEL_BYTE, self.channels_heard())
        await self.let_the_preview_play(A_LONG_WHILE)
        self.assertEqual(self.preview().playing(), self.hook_heard())
        await self.press(keybindings.WizardPage.STOP_LISTENING)
        self.assertIn(messages.MSG_STOPPED, self.text())
        self.assertIsNone(self.preview().playing())

    async def test_a_part_that_is_no_melody_is_heard_over_the_drums_and_a_player_with_no_clip_is_refused(self):
        choices = self.app.screen.get_choices()
        setlist, name = choices.made_for_listening()
        scene = choices.get_hook().hook_scene()
        self.preview().play_line(setlist=setlist, name=name, index=scene, track=choices.tune_player(), what=A_PART)
        await self.let_the_preview_play(A_WHILE)
        self.assertEqual(len(self.channels_heard()), A_PLAYER_AND_THE_DRUMS)
        self.assertIn(DRUM_CHANNEL_BYTE, self.channels_heard())
        self.preview().stop()
        with self.assertRaises(ValueError):
            self.preview().play_line(setlist=setlist, name=name, index=scene, track=A_TRACK_NOBODY_HAS, what=A_PART)
        self.assertIsNone(self.preview().playing())

    async def test_the_tune_is_heard_from_the_melody_panel(self):
        await self.go_to(labels.MSG_WIZARD_MELODY_BRANCH)
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertEqual(self.preview().playing(), messages.MSG_WIZARD_LISTEN_TUNE)

    async def test_a_section_is_heard_once_with_everybody_in_it(self):
        await self.go_to(FIRST_SECTION)
        await self.press(keybindings.WizardPage.LISTEN)
        what = messages.MSG_WIZARD_LISTEN_SECTION.format(number=FIRST_SECTION_NUMBER, name=FIRST_SECTION)
        self.assertEqual(self.preview().playing(), what)
        await self.let_the_preview_play(A_WHILE)
        self.assertIn(DRUM_CHANNEL_BYTE, self.channels_heard())
        # The section ends and nothing follows it.
        await self.let_the_preview_play(A_LONG_WHILE)
        await self.let_the_preview_play(A_WHILE)
        self.assertIsNone(self.preview().playing())

    async def test_a_choice_stops_what_was_heard(self):
        await self.go_to_hook()
        await self.press(keybindings.WizardPage.LISTEN)
        self.app.screen.choosing(self.app.screen.get_choices().set_song_plan)(True)
        self.assertIsNone(self.preview().playing())

    async def test_closing_the_wizard_stops_what_was_heard(self):
        await self.go_to_hook()
        await self.press(keybindings.WizardPage.LISTEN, keybindings.WizardPage.CLOSE)
        self.assertIsNone(self.preview().playing())

    async def test_a_riff_nobody_plays_yet_is_heard_from_the_riffs_panel(self):
        wizard = self.app.screen
        choices = wizard.get_choices()
        role = choices.riff_instruments()[0]
        riff = choices.add_riff(role=role)
        await self.go_to(labels.MSG_WIZARD_RIFFS_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        self.assertNotIn(keybindings.WizardPage.LISTEN, wizard.shown_keys())
        wizard.app.open_field_sections.add(choices.role_title(role))
        wizard.go_to_field(riff)
        await self.press(Key.DOWN, Key.UP)
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertEqual(self.preview().playing(), riff)

    async def test_without_fluidsynth_listen_is_refused(self):
        self.fluidsynth_installed = False
        await self.go_to_hook()
        await self.press(keybindings.WizardPage.LISTEN)
        self.assertIn(errors.ERR_WIZARD_CANNOT_LISTEN, self.text())
        self.assertIsNone(self.preview().playing())

    async def test_the_tracker_s_own_set_is_left_alone(self):
        before = self.document.get_setlist().to_data()
        await self.go_to(FIRST_SECTION)
        await self.press(keybindings.WizardPage.LISTEN)
        await self.let_the_preview_play(A_WHILE)
        self.assertEqual(self.document.get_setlist().to_data(), before)
