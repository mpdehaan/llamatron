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
"""The Sound dialog: General MIDI's families as rows, each opening a flyout of its sounds, the search of every sound, and a sound tried with L."""

import unittest

from llamatron.composition import file_format, limits
from llamatron.composition.file_format import PatternSetting, Row
from llamatron.exporters import midi_arrangement
from llamatron.music.note import NoteName
from llamatron.realtime import fluidsynth, timeline
from llamatron.strings import errors, labels, legends, marks
from llamatron.tui import drawing, keybindings, note_names, pattern_preview
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key
from llamatron.tui.note_names import note_shown, note_typed
from llamatron.tui.pattern_preview import trial_pattern
from llamatron.tui.screens.set.instrument_editor import InstrumentEditor, sound_families, sound_text
from llamatron.tui.screens.shared import sound_trial
from llamatron.tui.screens.shared.sound_trial import hits_of, run_of, SoundTrial
from tests.tui import test_tui_playback
from tests.tui.test_tui_playback import PatternPreviewTest

SYNTH = 'synth'
PREVIEW = 'monitor'
NOT_CONNECTED = 'No Such Port'
A_SOUND_NAME = 'Banjo'
A_SOUND = labels.MSG_GM_SOUNDS.index(A_SOUND_NAME) + limits.MIN_GM_SOUND
ITS_FAMILY = (A_SOUND - limits.MIN_GM_SOUND) // limits.GM_FAMILY_SIZE
NOT_A_SOUND = 'zzzz'
A_ROOT = 9
MINOR_STEPS = (0, 2, 3, 5, 7, 8, 10)
AN_OCTAVE = 2
A_DRUM = 38
MIDDLE_C = 48
C_SHARP = 49
SHARP = '#'
A_TITLE = 'Sound of a piece'
D_FLAT_TYPED = 'db4'
B_TYPED = 'b3'
B_FLAT_TYPED = 'bb3'
# Text that is no note: no octave, no letter of a note, an octave past the highest note, two marks, and nothing.
NOT_NOTES = ('c', 'h3', 'c11', 'c##3', '3', '')
# A trial is played through a moment at a time, for no longer than a while.
A_MOMENT = 0.05
MOMENTS_IN_A_WHILE = 600


class TestSoundTrialNotes(unittest.TestCase):
    """What a sound is tried with, and the pattern written to play it."""

    def test_a_run_goes_up_an_octave_of_the_scale_from_the_root_and_back_down(self):
        run = run_of(root=A_ROOT, steps=MINOR_STEPS, octave=AN_OCTAVE)
        low = AN_OCTAVE * sound_trial.NOTES_IN_OCTAVE + A_ROOT
        up = [low + step for step in MINOR_STEPS] + [low + sound_trial.NOTES_IN_OCTAVE]
        self.assertEqual(run, up + up[-2::-1])
        self.assertEqual(run_of()[0], sound_trial.USUAL_OCTAVE * sound_trial.NOTES_IN_OCTAVE)
        self.assertEqual(len(run_of()), 2 * len(sound_trial.MAJOR_STEPS) + 1)

    def test_a_drum_is_hit_four_times(self):
        self.assertEqual(hits_of(A_DRUM), [A_DRUM] * sound_trial.HITS)

    def test_the_trials_pattern_holds_each_note_by_name_and_octave_a_step_each(self):
        data = trial_pattern(numbers=[MIDDLE_C, C_SHARP], step_size=sound_trial.HITS_STEP)
        self.assertEqual(data[PatternSetting.STEPS], 2)
        self.assertEqual(data[PatternSetting.STEP_SIZE], sound_trial.HITS_STEP)
        self.assertTrue(data[PatternSetting.DRUM])
        self.assertEqual(data[Row.DEGREE], ['C', 'C'])
        self.assertEqual(data[Row.ACCIDENTAL], [None, SHARP])
        self.assertEqual(data[Row.OCTAVE], [MIDDLE_C // sound_trial.NOTES_IN_OCTAVE] * 2)
        self.assertEqual(data[Row.VELOCITY], [pattern_preview.TRIAL_VELOCITY] * 2)


class TestSoundDialog(PatternPreviewTest):
    """The Sound dialog, opened from the Instrument page's GM sound field."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(SYNTH)
        await self.press(keybindings.MainPage.INSTRUMENTS, Key.ENTER)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        await self.select_field(labels.MSG_GM_SOUND_LABEL)
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
        self.assertEqual([name for name, _ in families], labels.MSG_GM_FAMILIES)
        self.assertEqual([sound for _, sounds in families for _, sound in sounds], list(range(limits.MIN_GM_SOUND, limits.MAX_GM_SOUND + 1)))
        for _, sounds in families:
            self.assertEqual(len(sounds), limits.GM_FAMILY_SIZE)
        self.assertEqual(sound_families(numbered=True)[0][1][0][0], sound_text(limits.MIN_GM_SOUND))

    async def test_it_opens_on_none_above_the_families_each_drawn_as_a_button(self):
        shown = self.text()
        self.assertIn(marks.MSG_NONE_SHOWN, shown)
        for family in labels.MSG_GM_FAMILIES[:4]:
            self.assertIn(marks.MSG_FLYOUT_CLOSED.format(name=family), shown)
        self.assertEqual(self.dialog.cursor.get_place(), 0)

    async def test_a_familys_flyout_opens_and_enter_takes_a_sound_which_the_family_then_shows(self):
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN)
        self.assertEqual(self.dialog.flyout, 0)
        for name in labels.MSG_GM_SOUNDS[:limits.GM_FAMILY_SIZE]:
            self.assertIn(name, self.text())
        await self.press(Key.DOWN, keybindings.SoundDialog.CHOOSE)
        self.assertEqual(self.instrument().get_gm_sound(), limits.MIN_GM_SOUND + 1)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.cursor.get_place(), 1)
        self.assertIn(marks.MSG_FLYOUT_CHOSEN.format(name=labels.MSG_GM_FAMILIES[0], chosen=sound_text(limits.MIN_GM_SOUND + 1)), self.text())
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
        self.document.change(self.document.setlist().get_instrument(SYNTH).set_gm_sound, A_SOUND)
        await self.press(Key.ESCAPE, Key.ENTER)
        self.assertEqual(self.app.screen.cursor.get_place(), 1 + ITS_FAMILY)
        await self.press(*[Key.UP] * (1 + ITS_FAMILY), keybindings.SoundDialog.CHOOSE)
        self.assertIsNone(self.instrument().get_gm_sound())

    async def test_the_cursor_stops_at_the_first_and_the_last_row_and_in_the_flyout(self):
        await self.press(Key.UP)
        self.assertEqual(self.dialog.cursor.get_place(), 0)
        await self.press(*[Key.DOWN] * (len(labels.MSG_GM_FAMILIES) + 3))
        self.assertEqual(self.dialog.cursor.get_place(), len(labels.MSG_GM_FAMILIES))
        self.assertIn(marks.MSG_FLYOUT_CLOSED.format(name=labels.MSG_GM_FAMILIES[-1]), self.text())
        await self.press(keybindings.SoundDialog.OPEN, *[Key.DOWN] * (limits.GM_FAMILY_SIZE + 2))
        self.assertEqual(self.dialog.flyout_place, limits.GM_FAMILY_SIZE - 1)
        await self.press(keybindings.SoundDialog.CHOOSE)
        self.assertEqual(self.instrument().get_gm_sound(), limits.MAX_GM_SOUND)

    async def test_a_search_finds_a_sound_in_any_family_and_enter_opens_its_flyout_on_it(self):
        await self.find(A_SOUND_NAME.lower())
        self.assertTrue(self.dialog.takes_text())
        shown = self.text()
        self.assertIn(marks.MSG_SEARCH_SHOWN.format(text=A_SOUND_NAME.lower()), shown)
        self.assertIn(marks.MSG_SOUND_FOUND.format(sound=sound_text(A_SOUND), group=labels.MSG_GM_FAMILIES[ITS_FAMILY]), shown)
        self.assertNotIn(marks.MSG_FLYOUT_CLOSED.format(name=labels.MSG_GM_FAMILIES[0]), shown)
        await self.press(keybindings.SoundDialog.FIND)
        self.assertFalse(self.dialog.takes_text())
        self.assertEqual((self.dialog.flyout, self.dialog.flyout_place), (ITS_FAMILY, (A_SOUND - limits.MIN_GM_SOUND) % limits.GM_FAMILY_SIZE))
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
        self.assertIn(marks.MSG_FLYOUT_CLOSED.format(name=labels.MSG_GM_FAMILIES[0]), self.text())
        await self.find(NOT_A_SOUND)
        await self.press(keybindings.SoundDialog.FIND)
        self.assertIsNotNone(self.dialog.typed)
        self.assertIsNone(self.dialog.flyout)

    async def test_l_tries_the_sound_under_the_cursor_as_a_run_once_and_l_again_or_a_move_stops_it(self):
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN, Key.DOWN)
        self.assertIn(legends.MSG_LISTEN_WHAT, self.text())
        await self.press(keybindings.SoundDialog.LISTEN)
        sound = limits.MIN_GM_SOUND + 1
        self.assertEqual(self.preview().playing_sound(), sound)
        self.play_through()
        sent = [list(data) for _, data in self.outputs[fluidsynth.FLUIDSYNTH_PORT].sent]
        self.assertIn([timeline.PROGRAM_CHANGE | pattern_preview.PREVIEW_CHANNEL_BYTE, sound - limits.MIN_GM_SOUND], sent)
        self.assertEqual([data[1] for data in self.note_ons(fluidsynth.FLUIDSYNTH_PORT)], run_of())
        self.assertEqual({data[0] for data in self.note_ons(fluidsynth.FLUIDSYNTH_PORT)}, {timeline.NOTE_ON | pattern_preview.PREVIEW_CHANNEL_BYTE})
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
        self.assertIn(legends.MSG_LISTEN_WHAT, self.text())
        await self.press(keybindings.SoundDialog.LISTEN)
        self.assertIsNone(self.preview().playing_sound())
        self.assertIn(errors.ERR_NOTHING_TO_TRY_A_SOUND_WITH, self.text())
        await self.press(Key.DOWN)
        self.assertNotIn(errors.ERR_NOTHING_TO_TRY_A_SOUND_WITH, self.text())

    async def test_without_fluidsynth_a_sound_is_tried_on_the_songs_preview_instrument_which_is_sent_no_sound(self):
        self.fluidsynth_installed = False
        self.document.add_instrument(PREVIEW)
        self.document.change(self.document.setlist().get_instrument(PREVIEW).set_device, test_tui_playback.SYNTH_PORT)
        self.document.change(self.document.song().set_preview_instrument_name, PREVIEW)
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN, keybindings.SoundDialog.LISTEN)
        self.assertEqual(self.preview().playing_sound(), limits.MIN_GM_SOUND)
        self.play_through()
        self.assertEqual([data[1] for data in self.note_ons(test_tui_playback.SYNTH_PORT)], run_of())
        self.assertNotIn(timeline.PROGRAM_CHANGE, [data[0] & test_tui_playback.KIND_MASK for _, data in self.outputs[test_tui_playback.SYNTH_PORT].sent])
        self.assertEqual(self.fluidsynth.starts, 0)

    async def test_a_preview_instrument_that_cannot_sound_says_why(self):
        self.fluidsynth_installed = False
        self.document.add_instrument(PREVIEW)
        self.document.change(self.document.song().set_preview_instrument_name, PREVIEW)
        await self.press(Key.DOWN, keybindings.SoundDialog.OPEN, keybindings.SoundDialog.LISTEN)
        self.assertIn(errors.ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE.format(name=PREVIEW), drawing.SPACE.join(self.text().replace(Box.HEAVY_BAR, drawing.SPACE).split()))
        self.document.change(self.document.setlist().get_instrument(PREVIEW).set_device, NOT_CONNECTED)
        await self.press(keybindings.SoundDialog.LISTEN)
        self.assertEqual(self.preview().sound_refusal(), errors.ERR_PREVIEW_DEVICE_NOT_CONNECTED.format(name=PREVIEW, device=NOT_CONNECTED))
        self.document.change(self.document.setlist().get_instrument(PREVIEW).set_device, file_format.FLUIDSYNTH_DEVICE)
        self.assertEqual(self.preview().sound_refusal(), errors.ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED.format(name=PREVIEW))
        self.fluidsynth_installed = True
        self.assertIsNone(self.preview().sound_refusal())

    async def test_a_drum_of_the_kit_is_tried_on_the_drum_channel_with_no_sound_chosen(self):
        await self.press(Key.ESCAPE)
        self.preview().play_sound(numbers=hits_of(A_DRUM), step_size=sound_trial.HITS_STEP, sound=None, key=A_DRUM)
        self.play_through()
        self.assertEqual([list(data[:2]) for data in self.note_ons(fluidsynth.FLUIDSYNTH_PORT)], [[timeline.NOTE_ON | midi_arrangement.DRUM_CHANNEL_BYTE, A_DRUM]] * sound_trial.HITS)
        self.assertNotIn(timeline.PROGRAM_CHANGE | midi_arrangement.DRUM_CHANNEL_BYTE, [data[0] for _, data in self.outputs[fluidsynth.FLUIDSYNTH_PORT].sent])


class TestNoteNames(unittest.TestCase):
    """A MIDI note shown by name and octave, and a typed name read back."""

    def test_a_note_is_shown_by_its_name_and_octave_a_black_key_as_a_sharp(self):
        self.assertEqual(note_shown(MIDDLE_C), marks.MSG_NOTE_NAME_SHOWN.format(name=NoteName.C, octave=MIDDLE_C // sound_trial.NOTES_IN_OCTAVE))
        self.assertEqual(note_shown(C_SHARP), marks.MSG_NOTE_NAME_SHOWN.format(name=NoteName.C_SHARP, octave=C_SHARP // sound_trial.NOTES_IN_OCTAVE))

    def test_every_note_typed_as_shown_is_that_note_in_capitals_or_not(self):
        for note in range(note_names.LOWEST_NOTE, note_names.HIGHEST_NOTE + 1):
            self.assertEqual(note_typed(note_shown(note)), note)
            self.assertEqual(note_typed(note_shown(note).lower()), note)

    def test_a_flat_is_the_note_below_and_b_alone_is_the_note_b(self):
        self.assertEqual(note_typed(D_FLAT_TYPED), C_SHARP)
        self.assertEqual(note_typed(B_TYPED), MIDDLE_C - 1)
        self.assertEqual(note_typed(B_FLAT_TYPED), MIDDLE_C - 2)

    def test_what_is_no_note_there_is_reads_as_none(self):
        for text in NOT_NOTES:
            self.assertIsNone(note_typed(text), text)


class TestSoundDialogNoteRow(PatternPreviewTest):
    """The Note row of a Sound dialog whose asker's sounds play on one note."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.answers = []
        self.dialog = None

    async def open(self, *, note, current=None):
        self.dialog = SoundDialog(title=A_TITLE, groups=sound_families(), top=[(marks.MSG_NONE_SHOWN, None)], current=current, note=note,
                                  trial=SoundTrial(page=self.app.screen, played=lambda sound: None if sound is None else (hits_of(self.dialog.note), sound_trial.HITS_STEP, sound)))
        self.app.push_screen(self.dialog, self.answers.append)
        await self.settle()

    async def to_note_row(self):
        await self.press(*[Key.DOWN] * (len(labels.MSG_GM_FAMILIES) + 1))

    async def test_the_note_row_stays_in_view_under_the_list_and_a_dialog_given_no_note_has_none(self):
        await self.open(note=MIDDLE_C)
        self.assertIn(marks.MSG_SOUND_NOTE_ROW.format(note=note_shown(MIDDLE_C)), self.text())
        self.assertNotIn(labels.MSG_GM_FAMILIES[-1], self.text())
        await self.to_note_row()
        self.assertIn(labels.MSG_GM_FAMILIES[-1], self.text())
        self.assertIn(marks.MSG_SOUND_NOTE_ROW.format(note=note_shown(MIDDLE_C)), self.text())
        self.assertTrue(self.dialog.on_note_row())
        await self.press(Key.ESCAPE)
        self.assertEqual(self.answers, [None])
        await self.open(note=None)
        self.assertNotIn(marks.MSG_SOUND_NOTE_ROW.format(note=note_shown(MIDDLE_C)), self.text())
        await self.to_note_row()
        self.assertFalse(self.dialog.on_note_row())
        self.assertFalse(self.dialog.takes_text())

    async def test_the_note_is_stepped_between_the_lowest_and_the_highest_and_a_sound_taken_answers_with_it(self):
        await self.open(note=note_names.HIGHEST_NOTE - 1)
        await self.to_note_row()
        await self.press(*[keybindings.SoundDialog.NOTE_MORE] * 3)
        self.assertEqual(self.dialog.note, note_names.HIGHEST_NOTE)
        await self.press(Key.ESCAPE)
        await self.open(note=note_names.LOWEST_NOTE + 1)
        await self.to_note_row()
        await self.press(*[keybindings.SoundDialog.NOTE_LESS] * 3)
        self.assertEqual(self.dialog.note, note_names.LOWEST_NOTE)
        await self.press(Key.UP, keybindings.SoundDialog.OPEN, keybindings.SoundDialog.CHOOSE)
        self.assertEqual(self.answers[-1], (limits.MAX_GM_SOUND - limits.GM_FAMILY_SIZE + 1, note_names.LOWEST_NOTE))

    async def test_a_note_is_typed_by_name_and_set_with_enter_and_enter_again_takes_the_sound_the_dialog_opened_on(self):
        await self.open(note=MIDDLE_C, current=A_SOUND)
        await self.to_note_row()
        await self.type(D_FLAT_TYPED)
        self.assertIn(marks.MSG_SOUND_NOTE_TYPED.format(text=D_FLAT_TYPED), self.text())
        await self.press(keybindings.SoundDialog.ERASE)
        self.assertIn(marks.MSG_SOUND_NOTE_TYPED.format(text=D_FLAT_TYPED[:-1]), self.text())
        await self.type(D_FLAT_TYPED[-1])
        await self.press(keybindings.SoundDialog.TAKE_NOTE)
        self.assertEqual(self.dialog.note, C_SHARP)
        self.assertEqual(self.answers, [])
        await self.press(keybindings.SoundDialog.TAKE_NOTE)
        self.assertEqual(self.answers, [(A_SOUND, C_SHARP)])

    async def test_what_is_typed_and_is_no_note_is_refused_and_moving_away_drops_what_was_typed(self):
        await self.open(note=MIDDLE_C)
        await self.to_note_row()
        await self.type(NOT_NOTES[0])
        await self.press(keybindings.SoundDialog.TAKE_NOTE)
        self.assertEqual(self.dialog.note, MIDDLE_C)
        self.assertIn(errors.ERR_NOT_A_NOTE_NAME.format(text=NOT_NOTES[0]), drawing.SPACE.join(self.text().replace(Box.HEAVY_BAR, drawing.SPACE).split()))
        await self.type(D_FLAT_TYPED)
        await self.press(Key.UP, Key.DOWN)
        self.assertIn(marks.MSG_SOUND_NOTE_ROW.format(note=note_shown(MIDDLE_C)), self.text())

    async def test_l_tries_a_sound_on_the_note_the_row_shows(self):
        await self.open(note=MIDDLE_C)
        await self.to_note_row()
        await self.press(keybindings.SoundDialog.NOTE_MORE, *[Key.UP] * len(labels.MSG_GM_FAMILIES), keybindings.SoundDialog.OPEN, keybindings.SoundDialog.LISTEN)
        self.assertEqual(self.preview().playing_sound(), limits.MIN_GM_SOUND)
        for _ in range(MOMENTS_IN_A_WHILE):
            self.clock.advance(A_MOMENT)
            self.preview().tick()
            if self.preview().player() is None:
                break
            self.preview().player().sender().send_due()
        self.assertEqual([data[1] for data in self.note_ons(fluidsynth.FLUIDSYNTH_PORT)], hits_of(C_SHARP))
