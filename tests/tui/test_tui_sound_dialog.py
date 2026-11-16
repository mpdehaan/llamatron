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
"""The Instruments page, the instrument editor, the Instrument field on the track editor and the main screen's Real Time switch."""
"""The Sound dialog: General MIDI's families as rows, each opening a flyout of its sounds, the search of every sound, and a sound tried with L."""

import unittest

from llamatron.composition.file_format import FLUIDSYNTH_DEVICE, PatternSetting, Row
from llamatron.composition.limits import GM_FAMILY_SIZE, MAX_GM_SOUND, MIN_GM_SOUND
from llamatron.exporters.midi_arrangement import DRUM_CHANNEL_BYTE
from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT
from llamatron.realtime.timeline import NOTE_ON, PROGRAM_CHANGE
from llamatron.strings.errors import ERR_NOTHING_TO_TRY_A_SOUND_WITH, ERR_PREVIEW_DEVICE_NOT_CONNECTED, ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED, ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE
from llamatron.strings.labels import MSG_GM_FAMILIES, MSG_GM_SOUND_LABEL, MSG_GM_SOUNDS
from llamatron.strings.legends import MSG_LISTEN_WHAT
from llamatron.strings.marks import MSG_FLYOUT_CHOSEN, MSG_FLYOUT_CLOSED, MSG_NONE_SHOWN, MSG_SEARCH_SHOWN, MSG_SOUND_FOUND
from llamatron.tui import keybindings
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.keys import Key
from llamatron.tui.pattern_preview import PREVIEW_CHANNEL_BYTE, TRIAL_VELOCITY, trial_pattern
from llamatron.tui.screens.set.instrument_editor import InstrumentEditor, sound_families, sound_text
from llamatron.tui.screens.shared.sound_trial import HITS, HITS_STEP, MAJOR_STEPS, NOTES_IN_OCTAVE, USUAL_OCTAVE, hits_of, run_of
from llamatron.tui.drawing import Box, SPACE
from tests.tui.test_tui_playback import KIND_MASK, SYNTH_PORT, PatternPreviewTest

SYNTH = 'synth'
PREVIEW = 'monitor'
NOT_CONNECTED = 'No Such Port'
A_SOUND_NAME = 'Banjo'
A_SOUND = MSG_GM_SOUNDS.index(A_SOUND_NAME) + MIN_GM_SOUND
ITS_FAMILY = (A_SOUND - MIN_GM_SOUND) // GM_FAMILY_SIZE
NOT_A_SOUND = 'zzzz'
A_ROOT = 9
MINOR_STEPS = (0, 2, 3, 5, 7, 8, 10)
AN_OCTAVE = 2
A_DRUM = 38
MIDDLE_C = 48
C_SHARP = 49
SHARP = '#'
# A trial is played through a moment at a time, for no longer than a while.
A_MOMENT = 0.05
MOMENTS_IN_A_WHILE = 600


class TestSoundTrialNotes(unittest.TestCase):
    """What a sound is tried with, and the pattern written to play it."""

    def test_a_run_goes_up_an_octave_of_the_scale_from_the_root_and_back_down(self):
        run = run_of(root=A_ROOT, steps=MINOR_STEPS, octave=AN_OCTAVE)
        low = AN_OCTAVE * NOTES_IN_OCTAVE + A_ROOT
        up = [low + step for step in MINOR_STEPS] + [low + NOTES_IN_OCTAVE]
        self.assertEqual(run, up + up[-2::-1])
        self.assertEqual(run_of()[0], USUAL_OCTAVE * NOTES_IN_OCTAVE)
        self.assertEqual(len(run_of()), 2 * len(MAJOR_STEPS) + 1)

    def test_a_drum_is_hit_four_times(self):
        self.assertEqual(hits_of(A_DRUM), [A_DRUM] * HITS)

    def test_the_trials_pattern_holds_each_note_by_name_and_octave_a_step_each(self):
        data = trial_pattern(numbers=[MIDDLE_C, C_SHARP], step_size=HITS_STEP)
        self.assertEqual(data[PatternSetting.STEPS], 2)
        self.assertEqual(data[PatternSetting.STEP_SIZE], HITS_STEP)
        self.assertTrue(data[PatternSetting.DRUM])
        self.assertEqual(data[Row.DEGREE], ['C', 'C'])
        self.assertEqual(data[Row.ACCIDENTAL], [None, SHARP])
        self.assertEqual(data[Row.OCTAVE], [MIDDLE_C // NOTES_IN_OCTAVE] * 2)
        self.assertEqual(data[Row.VELOCITY], [TRIAL_VELOCITY] * 2)


class TestSoundDialog(PatternPreviewTest):
    """The Sound dialog, opened from the Instrument page's GM sound field."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(SYNTH)
        await self.press(keybindings.MainPage.INSTRUMENTS, Key.ENTER)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        await self.select_field(MSG_GM_SOUND_LABEL)
        await self.press(Key.ENTER)
        self.dialog = self.app.screen
        self.assertIsInstance(self.dialog, SoundDialog)

    def instrument(self):
        return self.document.setlist().get_instrument(SYNTH)

    def play_through(self):
        """Move the clock on a little at a time until the trial has played through, ticking the preview as its timer would and sending what is due."""
        for _ in range(MOMENTS_IN_A_WHILE):
            self.clock.advance(A_MOMENT)
            self.preview().tick()
            if self.preview().player() is None:
                return
            self.preview().player().sender().send_due()

    async def find(self, text):
        await self.press(keybindings.SoundDialog.SEARCH)
        await self.type(text)

    def test_every_family_holds_its_eight_sounds_and_together_they_are_all_of_general_midi(self):
        families = sound_families()
        self.assertEqual([name for name, _ in families], MSG_GM_FAMILIES)
        self.assertEqual([sound for _, sounds in families for _, sound in sounds], list(range(MIN_GM_SOUND, MAX_GM_SOUND + 1)))
        for _, sounds in families:
            self.assertEqual(len(sounds), GM_FAMILY_SIZE)
        self.assertEqual(sound_families(numbered=True)[0][1][0][0], sound_text(MIN_GM_SOUND))

    async def test_it_opens_on_none_above_the_families_each_drawn_as_a_button(self):
        shown = self.text()
        self.assertIn(MSG_NONE_SHOWN, shown)
        for family in MSG_GM_FAMILIES[:4]:
            self.assertIn(MSG_FLYOUT_CLOSED.format(name=family), shown)
        self.assertEqual(self.dialog.place, 0)

    async def test_a_familys_flyout_opens_and_enter_takes_a_sound_which_the_family_then_shows(self):
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN)
        self.assertEqual(self.dialog.flyout, 0)
        for name in MSG_GM_SOUNDS[:GM_FAMILY_SIZE]:
            self.assertIn(name, self.text())
        await self.press(Key.DOWN, keybindings.SoundDialog.CHOOSE)
        self.assertEqual(self.instrument().get_gm_sound(), MIN_GM_SOUND + 1)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.place, 1)
        self.assertIn(MSG_FLYOUT_CHOSEN.format(name=MSG_GM_FAMILIES[0], chosen=sound_text(MIN_GM_SOUND + 1)), self.text())
        # The flyout opens on the sound the instrument has.
        await self.press(keybindings.SoundDialog.OPEN)
        self.assertEqual(self.app.screen.flyout_place, 1)

    async def test_esc_and_left_close_the_flyout_with_nothing_taken_and_esc_again_cancels(self):
        for close in (Key.ESCAPE, Key.LEFT):
            await self.press(Key.DOWN, keybindings.SoundDialog.OPEN)
            self.assertIsNotNone(self.dialog.flyout)
            await self.press(close)
            self.assertIsNone(self.dialog.flyout)
            self.assertIs(self.app.screen, self.dialog)
            await self.press(Key.UP)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        self.assertIsNone(self.instrument().get_gm_sound())

    async def test_none_takes_the_sound_away(self):
        self.document.set_instrument_gm_sound(name=SYNTH, sound=A_SOUND)
        await self.press(Key.ESCAPE, Key.ENTER)
        self.assertEqual(self.app.screen.place, 1 + ITS_FAMILY)
        await self.press(*[Key.UP] * (1 + ITS_FAMILY), keybindings.SoundDialog.CHOOSE)
        self.assertIsNone(self.instrument().get_gm_sound())

    async def test_the_cursor_stops_at_the_first_and_the_last_row_and_in_the_flyout(self):
        await self.press(Key.UP)
        self.assertEqual(self.dialog.place, 0)
        await self.press(*[Key.DOWN] * (len(MSG_GM_FAMILIES) + 3))
        self.assertEqual(self.dialog.place, len(MSG_GM_FAMILIES))
        self.assertIn(MSG_FLYOUT_CLOSED.format(name=MSG_GM_FAMILIES[-1]), self.text())
        await self.press(keybindings.SoundDialog.OPEN, *[Key.DOWN] * (GM_FAMILY_SIZE + 2))
        self.assertEqual(self.dialog.flyout_place, GM_FAMILY_SIZE - 1)
        await self.press(keybindings.SoundDialog.CHOOSE)
        self.assertEqual(self.instrument().get_gm_sound(), MAX_GM_SOUND)

    async def test_a_search_finds_a_sound_in_any_family_and_enter_opens_its_flyout_on_it(self):
        await self.find(A_SOUND_NAME.lower())
        self.assertTrue(self.dialog.takes_text())
        shown = self.text()
        self.assertIn(MSG_SEARCH_SHOWN.format(text=A_SOUND_NAME.lower()), shown)
        self.assertIn(MSG_SOUND_FOUND.format(sound=sound_text(A_SOUND), group=MSG_GM_FAMILIES[ITS_FAMILY]), shown)
        self.assertNotIn(MSG_FLYOUT_CLOSED.format(name=MSG_GM_FAMILIES[0]), shown)
        await self.press(keybindings.SoundDialog.FIND)
        self.assertFalse(self.dialog.takes_text())
        self.assertEqual((self.dialog.flyout, self.dialog.flyout_place), (ITS_FAMILY, (A_SOUND - MIN_GM_SOUND) % GM_FAMILY_SIZE))
        await self.press(keybindings.SoundDialog.CHOOSE)
        self.assertEqual(self.instrument().get_gm_sound(), A_SOUND)

    async def test_a_search_is_erased_completed_and_left_with_esc_and_one_that_finds_nothing_takes_nothing(self):
        await self.find(A_SOUND_NAME[:3].lower())
        await self.press(keybindings.SoundDialog.COMPLETE)
        await self.press(keybindings.SoundDialog.ERASE)
        self.assertTrue(self.dialog.typed)
        await self.press(Key.ESCAPE)
        self.assertIsNone(self.dialog.typed)
        self.assertIs(self.app.screen, self.dialog)
        self.assertIn(MSG_FLYOUT_CLOSED.format(name=MSG_GM_FAMILIES[0]), self.text())
        await self.find(NOT_A_SOUND)
        await self.press(keybindings.SoundDialog.FIND)
        self.assertIsNotNone(self.dialog.typed)
        self.assertIsNone(self.dialog.flyout)

    async def test_l_tries_the_sound_under_the_cursor_as_a_run_once_and_l_again_or_a_move_stops_it(self):
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN, Key.DOWN)
        self.assertIn(MSG_LISTEN_WHAT, self.text())
        await self.press(keybindings.SoundDialog.LISTEN)
        sound = MIN_GM_SOUND + 1
        self.assertEqual(self.preview().playing_sound(), sound)
        self.play_through()
        sent = [list(data) for _, data in self.outputs[FLUIDSYNTH_PORT].sent]
        self.assertIn([PROGRAM_CHANGE | PREVIEW_CHANNEL_BYTE, sound - MIN_GM_SOUND], sent)
        self.assertEqual([data[1] for data in self.note_ons(FLUIDSYNTH_PORT)], run_of())
        self.assertEqual({data[0] for data in self.note_ons(FLUIDSYNTH_PORT)}, {NOTE_ON | PREVIEW_CHANNEL_BYTE})
        # Played once: the run does not come round again.
        self.assertIsNone(self.preview().playing_sound())
        # The set is untouched by the trial.
        self.assertIsNone(self.instrument().get_gm_sound())
        await self.press(keybindings.SoundDialog.LISTEN)
        self.assertEqual(self.preview().playing_sound(), sound)
        await self.press(keybindings.SoundDialog.STOP_LISTENING)
        self.assertIsNone(self.preview().playing_sound())
        await self.press(keybindings.SoundDialog.LISTEN, Key.DOWN)
        self.assertIsNone(self.preview().playing_sound())
        await self.press(keybindings.SoundDialog.LISTEN, keybindings.SoundDialog.CHOOSE)
        self.assertIsNone(self.preview().playing_sound())
        self.assertEqual(self.instrument().get_gm_sound(), sound + 1)

    async def test_nothing_is_tried_on_none_or_on_a_familys_row(self):
        await self.press(keybindings.SoundDialog.LISTEN)
        self.assertIsNone(self.preview().playing_sound())
        await self.press(Key.DOWN, keybindings.SoundDialog.LISTEN)
        self.assertIsNone(self.preview().playing_sound())

    async def test_without_fluidsynth_or_a_preview_instrument_l_says_what_to_do_until_the_next_key(self):
        self.fluidsynth_installed = False
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN)
        self.assertIn(MSG_LISTEN_WHAT, self.text())
        await self.press(keybindings.SoundDialog.LISTEN)
        self.assertIsNone(self.preview().playing_sound())
        self.assertIn(ERR_NOTHING_TO_TRY_A_SOUND_WITH, self.text())
        await self.press(Key.DOWN)
        self.assertNotIn(ERR_NOTHING_TO_TRY_A_SOUND_WITH, self.text())

    async def test_without_fluidsynth_a_sound_is_tried_on_the_songs_preview_instrument_which_is_sent_no_sound(self):
        self.fluidsynth_installed = False
        self.document.add_instrument(PREVIEW)
        self.document.set_instrument_device(name=PREVIEW, device=SYNTH_PORT)
        self.document.set_preview_instrument_name(PREVIEW)
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN, keybindings.SoundDialog.LISTEN)
        self.assertEqual(self.preview().playing_sound(), MIN_GM_SOUND)
        self.play_through()
        self.assertEqual([data[1] for data in self.note_ons(SYNTH_PORT)], run_of())
        self.assertNotIn(PROGRAM_CHANGE, [data[0] & KIND_MASK for _, data in self.outputs[SYNTH_PORT].sent])
        self.assertEqual(self.fluidsynth.starts, 0)

    async def test_a_preview_instrument_that_cannot_sound_says_why(self):
        self.fluidsynth_installed = False
        self.document.add_instrument(PREVIEW)
        self.document.set_preview_instrument_name(PREVIEW)
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN, keybindings.SoundDialog.LISTEN)
        self.assertIn(ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE.format(name=PREVIEW), SPACE.join(self.text().replace(Box.HEAVY_BAR, SPACE).split()))
        self.document.set_instrument_device(name=PREVIEW, device=NOT_CONNECTED)
        await self.press(keybindings.SoundDialog.LISTEN)
        self.assertEqual(self.preview().sound_refusal(), ERR_PREVIEW_DEVICE_NOT_CONNECTED.format(name=PREVIEW, device=NOT_CONNECTED))
        self.document.set_instrument_device(name=PREVIEW, device=FLUIDSYNTH_DEVICE)
        self.assertEqual(self.preview().sound_refusal(), ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED.format(name=PREVIEW))
        self.fluidsynth_installed = True
        self.assertIsNone(self.preview().sound_refusal())

    async def test_a_drum_of_the_kit_is_tried_on_the_drum_channel_with_no_sound_chosen(self):
        await self.press(Key.ESCAPE)
        self.preview().play_sound(numbers=hits_of(A_DRUM), step_size=HITS_STEP, sound=None, key=A_DRUM)
        self.play_through()
        self.assertEqual([list(data[:2]) for data in self.note_ons(FLUIDSYNTH_PORT)], [[NOTE_ON | DRUM_CHANNEL_BYTE, A_DRUM]] * HITS)
        self.assertNotIn(PROGRAM_CHANGE | DRUM_CHANNEL_BYTE, [data[0] for _, data in self.outputs[FLUIDSYNTH_PORT].sent])
