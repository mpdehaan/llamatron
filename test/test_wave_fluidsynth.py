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

"""The WAV export (exporters/wave_fluidsynth.py): only the tracks that play through FluidSynth, played by FluidSynth, normalized, with nothing left behind.

No real FluidSynth runs: a stand-in writes a WAV file where FluidSynth would, and keeps what it was handed.
"""

import contextlib
import io
import os
import pathlib
import tempfile
import unittest
import wave
from types import SimpleNamespace
from unittest import mock

import mido
import numpy

from llamatron.composition.file_format import FLUIDSYNTH_DEVICE
from llamatron.exporters import wave_fluidsynth
from llamatron.exporters.exporter import ExportKind
from llamatron.exporters.exports import EXPORT_KINDS, EXPORT_LABELS
from llamatron.exporters.wave_fluidsynth import MIDI_FILE, WaveFluidSynth
from llamatron.exporters.wave_level import peak_sample
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings.errors import ERR_CANT_EXPORT_TITLE, ERR_FLUIDSYNTH_RENDER_FAILED, ERR_NO_FLUIDSYNTH_TRACKS, ERR_WAV_NEEDS_FLUIDSYNTH
from llamatron.strings.labels import MSG_EXPORT_CHOICES
from llamatron.strings.messages import MSG_EXPORTED, MSG_WAV_EXPORT_NOTE, MSG_WAV_EXPORT_TITLE
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from ui_testing import DRUMS, LEAD, UITest, a_song, fixed_text

FLUID = 'fluid'
KEYS = 'keys'
OTHER_PORT = 'IAC Driver Bus 1'
VIOLIN = 41
NAME = 'my_set_untitled'
SET_FILE = 'my_set.yml'
# What the stand-in writes: a second of quiet stereo, loudest at this sample, for the normalizing to raise.
FRAME_RATE = 8000
QUIET_PEAK = 1000
STEREO = 2
FAILED = 1
FLUIDSYNTH_SAYS = 'fluidsynth: error: no audio'
INSTALLED = 'llamatron.exporters.wave_fluidsynth.is_installed'
TRACKER_INSTALLED = 'llamatron.tui.screens.everywhere.fluidsynth_installed'
PROGRAM_CHANGE = 'program_change'
READ_BYTES = 'rb'
WRITE_BYTES = 'wb'
SAMPLE_BYTES = 2
# FluidSynth's option naming the WAV file it writes.
WRITES_TO = '-F'
# Within a sample of what the arithmetic says, after rounding to whole samples.
ROUNDING = 1


def song_with_instruments():
    """Return a document whose lead plays through FluidSynth with a violin and whose drums play through a MIDI port."""
    document = a_song()
    for name, device in ((FLUID, FLUIDSYNTH_DEVICE), (KEYS, OTHER_PORT)):
        document.add_instrument(name)
        document.set_instrument_device(name=name, device=device)
    document.set_instrument_gm_sound(name=FLUID, sound=VIOLIN)
    document.set_track_instrument(name=LEAD, instrument=FLUID)
    document.set_track_instrument(name=DRUMS, instrument=KEYS)
    return document


class StandInFluidSynth:
    """Writes a quiet WAV file where FluidSynth would, keeping the MIDI file it was handed and where that was, or fails as FluidSynth can."""

    __slots__ = ('midi', 'midi_folder', 'fails')

    def __init__(self, *, fails=False):
        self.midi = None
        self.midi_folder = None
        self.fails = fails

    def __call__(self, command, **named):
        midi_path = command[-1]
        self.midi_folder = os.path.dirname(midi_path)
        self.midi = mido.MidiFile(midi_path)
        if self.fails:
            return SimpleNamespace(returncode=FAILED, stdout='', stderr=FLUIDSYNTH_SAYS)
        samples = numpy.zeros(FRAME_RATE * STEREO, dtype=numpy.int16)
        samples[1] = QUIET_PEAK
        with wave.open(command[command.index(WRITES_TO) + 1], WRITE_BYTES) as file:
            file.setnchannels(STEREO)
            file.setsampwidth(SAMPLE_BYTES)
            file.setframerate(FRAME_RATE)
            file.writeframes(samples.tobytes())
        return SimpleNamespace(returncode=0, stdout='', stderr='')


class TestWaveFluidSynth(unittest.TestCase):

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.folder = scratch.name
        self.document = song_with_instruments()
        patcher = mock.patch(INSTALLED, return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def exporter(self):
        return WaveFluidSynth(directory=self.folder, grid=SongRenderer(self.document.song()).render(), name=NAME)

    def test_the_grid_says_which_tracks_play_through_fluidsynth(self):
        columns = {column.get_name(): column for column in SongRenderer(self.document.song()).render().get_columns()}
        self.assertTrue(columns[LEAD].plays_through_fluidsynth())
        self.assertFalse(columns[DRUMS].plays_through_fluidsynth())

    def test_only_the_tracks_through_fluidsynth_are_played_with_their_sound_and_nothing_is_left_behind(self):
        render = StandInFluidSynth()
        self.exporter().export(render=render)
        names = [track.name for track in render.midi.tracks]
        self.assertIn(LEAD, names)
        self.assertNotIn(DRUMS, names)
        lead = next(track for track in render.midi.tracks if track.name == LEAD)
        self.assertEqual([message.program for message in lead if message.type == PROGRAM_CHANGE], [VIOLIN - 1])
        self.assertFalse(os.path.exists(render.midi_folder))
        self.assertEqual(os.listdir(self.folder), [WaveFluidSynth.FILE.format(name=NAME)])
        self.assertNotIn(MIDI_FILE, os.listdir(self.folder))

    def test_the_wav_file_is_normalized_to_a_peak_one_decibel_below_full_scale(self):
        exporter = self.exporter()
        exporter.export(render=StandInFluidSynth())
        with wave.open(exporter.path(), READ_BYTES) as file:
            samples = numpy.frombuffer(file.readframes(file.getnframes()), dtype=numpy.int16)
        self.assertAlmostEqual(int(numpy.abs(samples.astype(numpy.int32)).max()), peak_sample(), delta=ROUNDING)

    def test_fluidsynth_not_installed_or_no_track_through_it_is_refused_before_anything_is_written(self):
        with mock.patch(INSTALLED, return_value=False), self.assertRaises(ValueError) as refused:
            self.exporter().export(render=StandInFluidSynth())
        self.assertEqual(str(refused.exception), ERR_WAV_NEEDS_FLUIDSYNTH)
        self.document.set_track_instrument(name=LEAD, instrument=None)
        with self.assertRaises(ValueError) as refused:
            self.exporter().export(render=StandInFluidSynth())
        self.assertEqual(str(refused.exception), ERR_NO_FLUIDSYNTH_TRACKS)
        self.assertEqual(os.listdir(self.folder), [])

    def test_a_muted_track_is_left_out_as_every_arrangement_export_leaves_it(self):
        self.document.set_track_mute(name=LEAD, muted=True)
        with self.assertRaises(ValueError):
            self.exporter().export(render=StandInFluidSynth())

    def test_fluidsynth_failing_is_told_and_still_leaves_nothing_behind(self):
        render = StandInFluidSynth(fails=True)
        with self.assertRaises(ValueError) as refused:
            self.exporter().export(render=render)
        self.assertEqual(str(refused.exception), ERR_FLUIDSYNTH_RENDER_FAILED.format(problem=FLUIDSYNTH_SAYS))
        self.assertFalse(os.path.exists(render.midi_folder))

    def test_a_wav_file_already_there_is_never_written_over(self):
        exporter = self.exporter()
        pathlib.Path(exporter.path()).write_text(NAME)
        render = StandInFluidSynth()
        with contextlib.redirect_stdout(io.StringIO()):
            exporter.export(render=render)
        self.assertIsNone(render.midi)
        self.assertEqual(pathlib.Path(exporter.path()).read_text(), NAME)


class TestWaveExportInTheTracker(UITest):
    """Choosing WAV (FluidSynth) in the export dialog says that only the tracks through FluidSynth are in it, or that FluidSynth isn't installed."""

    def make_app(self):
        self.document = song_with_instruments()
        self.document.save(path=SET_FILE)
        return super().make_app()

    async def choose_wav(self):
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options[EXPORT_KINDS.index(ExportKind.WAV)], MSG_EXPORT_CHOICES[EXPORT_KINDS.index(ExportKind.WAV)])
        await self.press(*([Key.DOWN] * EXPORT_KINDS.index(ExportKind.WAV)), Key.ENTER)

    async def test_the_note_is_shown_first_and_yes_exports(self):
        with mock.patch(TRACKER_INSTALLED, return_value=True), mock.patch(INSTALLED, return_value=True), \
                mock.patch.object(wave_fluidsynth.subprocess, 'run', side_effect=StandInFluidSynth()):
            await self.choose_wav()
            self.assertIsInstance(self.app.screen, ConfirmDialog)
            self.assertIn(MSG_WAV_EXPORT_TITLE, self.text())
            self.assertIn(MSG_WAV_EXPORT_NOTE, self.app.screen.messages)
            await self.press(keybindings.ConfirmDialog.YES)
        self.assertIn(fixed_text(MSG_EXPORTED), self.text())
        self.assertIn(EXPORT_LABELS[ExportKind.WAV], self.text())
        self.assertTrue(os.path.exists(WaveFluidSynth.FILE.format(name=NAME)))

    async def test_no_writes_nothing(self):
        with mock.patch(TRACKER_INSTALLED, return_value=True):
            await self.choose_wav()
            await self.press(keybindings.ConfirmDialog.NO)
        self.assertFalse(os.path.exists(WaveFluidSynth.FILE.format(name=NAME)))

    async def test_fluidsynth_not_installed_is_told_and_nothing_is_written(self):
        with mock.patch(TRACKER_INSTALLED, return_value=False):
            await self.choose_wav()
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(ERR_CANT_EXPORT_TITLE, self.text())
        self.assertIn(ERR_WAV_NEEDS_FLUIDSYNTH, self.app.screen.messages)
        self.assertFalse(os.path.exists(WaveFluidSynth.FILE.format(name=NAME)))


if __name__ == '__main__':
    unittest.main()
