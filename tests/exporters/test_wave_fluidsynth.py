# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The WAV export (exporters/wave_fluidsynth.py): only the tracks that play through FluidSynth, played by FluidSynth, normalized, with nothing left behind.

No real FluidSynth runs: a stand-in writes a WAV file where FluidSynth would, and keeps what it was handed.
"""

import contextlib
import io
import mido
import numpy
import os
import pathlib
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import wave

from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.exporters import exports, wave_fluidsynth
from llamatron.exporters.exporter import ExportKind
from llamatron.exporters.wave_fluidsynth import WaveFluidSynth
from llamatron.exporters.wave_level import peak_sample
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.export_dialog import ExportDialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.keys import Key
from llamatron.model.schema import file_format
from llamatron.realtime.devices.fluidsynth import FluidSynthInstallation
from llamatron.user_strings import errors, messages
from tests.interface.tracker.test_tui_exporting import export_keys
from tests.support import ui_testing
from tests.support.ui_testing import a_song, fixed_text, UITest

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
INSTALLED = 'llamatron.realtime.devices.fluidsynth.installed'
# Where a stand-in FluidSynth and its SoundFont are said to be, which the stand-in render never looks at.
STAND_IN_SYNTH = FluidSynthInstallation('fluidsynth', 'soundfont.sf2')
TRACKER_INSTALLED = 'llamatron.interface.tracker.transport.installed'
TRACKER_PORT_NAMES = 'llamatron.interface.tracker.transport.output_port_names'
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
    for name, device in ((FLUID, file_format.FLUIDSYNTH_DEVICE), (KEYS, OTHER_PORT)):
        document.add_instrument(name)
        document.change_set(document.get_setlist().get_instrument(name).set_device, device)
    document.change_set(document.get_setlist().get_instrument(FLUID).set_gm_sound, VIOLIN)
    document.set_track_instrument(name=ui_testing.LEAD, instrument=FLUID)
    document.set_track_instrument(name=ui_testing.DRUMS, instrument=KEYS)
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

    def exporter(self, *, synth=STAND_IN_SYNTH):
        return WaveFluidSynth(directory=self.folder, grid=SongRealizer(self.document.song()).render(), name=NAME, synth=synth)

    def test_the_grid_says_which_tracks_play_through_fluidsynth(self):
        columns = {column.get_name(): column for column in SongRealizer(self.document.song()).render().get_columns()}
        self.assertTrue(columns[ui_testing.LEAD].plays_through_fluidsynth())
        self.assertFalse(columns[ui_testing.DRUMS].plays_through_fluidsynth())

    def test_only_the_tracks_through_fluidsynth_are_played_with_their_sound_and_nothing_is_left_behind(self):
        render = StandInFluidSynth()
        self.exporter().export(render=render)
        names = [track.name for track in render.midi.tracks]
        self.assertIn(ui_testing.LEAD, names)
        self.assertNotIn(ui_testing.DRUMS, names)
        lead = next(track for track in render.midi.tracks if track.name == ui_testing.LEAD)
        self.assertEqual([message.program for message in lead if message.type == PROGRAM_CHANGE], [VIOLIN - 1])
        self.assertFalse(os.path.exists(render.midi_folder))
        self.assertEqual(os.listdir(self.folder), [WaveFluidSynth.FILE.format(name=NAME)])
        self.assertNotIn(wave_fluidsynth.MIDI_FILE, os.listdir(self.folder))

    def test_the_wav_file_is_normalized_to_a_peak_one_decibel_below_full_scale(self):
        exporter = self.exporter()
        exporter.export(render=StandInFluidSynth())
        with wave.open(exporter.path(), READ_BYTES) as file:
            samples = numpy.frombuffer(file.readframes(file.getnframes()), dtype=numpy.int16)
        self.assertAlmostEqual(int(numpy.abs(samples.astype(numpy.int32)).max()), peak_sample(), delta=ROUNDING)

    def test_fluidsynth_not_installed_or_no_track_through_it_is_refused_before_anything_is_written(self):
        with self.assertRaises(ValueError) as refused:
            self.exporter(synth=None).export(render=StandInFluidSynth())
        self.assertEqual(str(refused.exception), errors.ERR_WAV_NEEDS_FLUIDSYNTH)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=None)
        with self.assertRaises(ValueError) as refused:
            self.exporter().export(render=StandInFluidSynth())
        self.assertEqual(str(refused.exception), errors.ERR_NO_FLUIDSYNTH_TRACKS)
        self.assertEqual(os.listdir(self.folder), [])

    def test_a_muted_track_is_left_out_as_every_arrangement_export_leaves_it(self):
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_mute, True)
        with self.assertRaises(ValueError):
            self.exporter().export(render=StandInFluidSynth())

    def test_fluidsynth_failing_is_told_and_still_leaves_nothing_behind(self):
        render = StandInFluidSynth(fails=True)
        with self.assertRaises(ValueError) as refused:
            self.exporter().export(render=render)
        self.assertEqual(str(refused.exception), errors.ERR_FLUIDSYNTH_RENDER_FAILED.format(problem=FLUIDSYNTH_SAYS))
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
        # The drums' port is said to be connected, so that opening the set warns of no silent instrument whatever ports this
        # computer lists at the moment: the test is of the export, not of the ports the machine has.
        ports = mock.patch(TRACKER_PORT_NAMES, return_value=[OTHER_PORT])
        ports.start()
        self.addCleanup(ports.stop)
        return super().make_app()

    async def choose_wav(self):
        await self.press(Key.CTRL_X)
        self.assertIsInstance(self.app.screen, ExportDialog)
        await self.press(*export_keys(ExportKind.WAV))

    async def test_the_note_is_shown_first_and_yes_exports(self):
        with mock.patch(TRACKER_INSTALLED, return_value=True), mock.patch(INSTALLED, return_value=True), \
                mock.patch.object(wave_fluidsynth.subprocess, 'run', side_effect=StandInFluidSynth()):
            await self.choose_wav()
            self.assertIsInstance(self.app.screen, ConfirmDialog)
            self.assertIn(messages.MSG_WAV_EXPORT_TITLE, self.text())
            self.assertIn(messages.MSG_WAV_EXPORT_NOTE, self.app.screen.messages)
            await self.press(*ui_testing.ANSWER_YES)
        self.assertIn(fixed_text(messages.MSG_EXPORTED), self.text())
        self.assertIn(exports.EXPORT_LABELS[ExportKind.WAV], self.text())
        self.assertTrue(os.path.exists(WaveFluidSynth.FILE.format(name=NAME)))

    async def test_no_writes_nothing(self):
        with mock.patch(TRACKER_INSTALLED, return_value=True):
            await self.choose_wav()
            await self.press(ui_testing.ANSWER_NO)
        self.assertFalse(os.path.exists(WaveFluidSynth.FILE.format(name=NAME)))

    async def test_fluidsynth_not_installed_is_told_and_nothing_is_written(self):
        with mock.patch(TRACKER_INSTALLED, return_value=False):
            await self.choose_wav()
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(errors.ERR_CANT_EXPORT_TITLE, self.text())
        self.assertIn(errors.ERR_WAV_NEEDS_FLUIDSYNTH, self.app.screen.messages)
        self.assertFalse(os.path.exists(WaveFluidSynth.FILE.format(name=NAME)))


if __name__ == '__main__':
    unittest.main()
