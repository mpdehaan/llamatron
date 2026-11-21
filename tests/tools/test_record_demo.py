# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""internal_tools/record_demo.py, one quick check of its main path: a take is the splash the lead in the song the lead out the splash again the hold and a margin or the limit. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from llamatron.interface.tracker import launch as launch_values
from llamatron.interface.visualizers import modes
from llamatron.model.schema import file_format
from llamatron.realtime.devices import fluidsynth
from tests.support import ui_testing
from tests.support.ui_testing import a_song

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'record_demo.py'
MODULE_NAME = 'record_demo'
PORT = 'IAC Driver Bus 1'
OTHER_PORT = 'Some Synth'
PORTS = [OTHER_PORT, PORT]
A_SONG_SECONDS = 30.0
SMALL_LIMIT = 5.0
DEVICE_ID = 'blackhole-id'
WINDOW = 72
REGION_ARGUMENT = '10,20,300,200'
SET_PATH = 'a set.yml'
# What the stand-ins for screencapture and avconvert write, to tell the trimmed video from the one recorded.
VIDEO_BYTES = b'recorded'
TRIMMED_BYTES = b'trimmed'
RECORDED_BYTES = b'recorded'
PART_BYTES = b'part'
A_VIDEO = 'take.mov'
A_FAILURE = 'no room'
# The argument that limits how long a command may run.
TIMEOUT = 'timeout'
RECORDED_SECONDS = 60
# screencapture's flag for how many seconds it records.
SUCCEEDED = 0
FLUID = 'fluid'


class StandInRecording:
    """Stands in for the screen recording: notes where it records and writes the video when stopped."""

    __slots__ = ('path',)
    made = []

    def __init__(self, *, path, window, audio_device, region=None):
        self.path = path
        StandInRecording.made.append((window, audio_device, region))

    def stop(self):
        pathlib.Path(self.path).write_bytes(VIDEO_BYTES)
        return SUCCEEDED


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class TestRecordDemo(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.document = a_song()
        # A take waits SETTLE_SECONDS on black before the tracker starts, which the tests don't wait for.
        settling = mock.patch.object(self.tool.time, 'sleep')
        self.slept = settling.start()
        self.addCleanup(settling.stop)

    def test_a_take_is_the_splash_the_lead_in_the_song_the_lead_out_the_splash_again_the_hold_and_a_margin_or_the_limit(self):
        expected = launch_values.SPLASH_SECONDS + launch_values.LEAD_IN_SECONDS + A_SONG_SECONDS + launch_values.LEAD_OUT_SECONDS + launch_values.SPLASH_SECONDS + self.tool.HOLD_SECONDS + self.tool.MARGIN_SECONDS
        self.assertEqual(self.tool.take_seconds(song_seconds=A_SONG_SECONDS, max_seconds=self.tool.DEFAULT_MAX_SECONDS), expected)
        self.assertEqual(self.tool.take_seconds(song_seconds=A_SONG_SECONDS, max_seconds=SMALL_LIMIT), SMALL_LIMIT)

    def visualizer_take(self, *, staged, path=SET_PATH, scroll=True, scroll_text=None, announce=False):
        """Record a take of the last visualizer mode, chosen when asked, with everything it runs replaced, and return what the tracker was launched with."""
        # A take gives the set's tracks instruments, so each take is of a set no take has touched.
        self.document = a_song()
        devices = [(DEVICE_ID, self.tool.DEFAULT_AUDIO_DEVICE)]
        region = mock.Mock()
        region.argument.return_value = REGION_ARGUMENT
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(self.tool, 'RECORDINGS', folder), \
                mock.patch.object(self.tool, 'output_port_names', return_value=PORTS), mock.patch.object(self.tool, 'audio_devices', return_value=devices), \
                mock.patch.object(self.tool, 'terminal_window_id', return_value=WINDOW), mock.patch.object(self.tool.Document, 'load', return_value=self.document), \
                mock.patch.object(self.tool, 'cells_region', return_value=region), mock.patch.object(self.tool.subprocess, 'run') as trim, \
                mock.patch.object(self.tool, 'LlamatronApp') as app, \
                mock.patch('builtins.input', return_value=str(len(modes.MODES) + 1)), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            trim.side_effect = lambda command, **named: pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)
            self.tool.record(path=path, driver=PORT, audio_device=self.tool.DEFAULT_AUDIO_DEVICE, assignment=None, max_seconds=SMALL_LIMIT, window_id=None,
                             go=True, ask_view=True, staged=staged, recording=StandInRecording, scroll=scroll, scroll_text=scroll_text, announce=announce)
        return app.call_args.kwargs['launch']

    def trimmed(self, *, folder, side_effect):
        """Trim a video in a folder with a stand-in for avconvert, and return the video's path and what the trim answered or raised."""
        video = os.path.join(folder, A_VIDEO)
        pathlib.Path(video).write_bytes(RECORDED_BYTES)
        with mock.patch.object(self.tool.subprocess, 'run', side_effect=side_effect):
            try:
                return video, self.tool.trim_end(video=video, recorded_seconds=RECORDED_SECONDS)
            except KeyboardInterrupt as stopped:
                return video, stopped

    def write_trimmed(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)

    def write_part_and_stop(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(PART_BYTES)
        raise KeyboardInterrupt

    def write_part_and_fail(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(PART_BYTES)
        raise OSError(A_FAILURE)

    def write_part_and_run_too_long(self, command, **named):
        pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(PART_BYTES)
        raise subprocess.TimeoutExpired(cmd=command, timeout=named[TIMEOUT])

    def record_with_fluidsynth(self, *, installed=True, output=None, outputs=()):
        """Record a take with --fluidsynth, every program it runs replaced, and return the exit code, what the tracker was launched with, what was printed and the device FluidSynth was sent to."""
        devices = [(DEVICE_ID, self.tool.DEFAULT_AUDIO_DEVICE)]
        printed = io.StringIO()
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(self.tool, 'RECORDINGS', folder), mock.patch.dict(os.environ), \
                mock.patch.object(self.tool, 'is_installed', return_value=installed), mock.patch.object(self.tool, 'output_port_names', return_value=[]) as ports, \
                mock.patch.object(self.tool, 'fluidsynth_outputs', return_value=list(outputs)), \
                mock.patch.object(self.tool, 'audio_devices', return_value=devices), mock.patch.object(self.tool, 'terminal_window_id', return_value=WINDOW), \
                mock.patch.object(self.tool.Document, 'load', return_value=self.document), \
                mock.patch.object(self.tool.subprocess, 'run') as trim, mock.patch.object(self.tool, 'LlamatronApp') as app, \
                contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            trim.side_effect = lambda command, **named: pathlib.Path(command[command.index(self.tool.OUTPUT_FLAG) + 1]).write_bytes(TRIMMED_BYTES)
            code = self.tool.record(path=SET_PATH, driver=PORT, audio_device=self.tool.DEFAULT_AUDIO_DEVICE, assignment=None, max_seconds=SMALL_LIMIT,
                                    window_id=None, go=True, fluidsynth=True, fluidsynth_output=output, recording=StandInRecording)
            sent_to = os.environ.get(fluidsynth.AUDIO_DEVICE_VARIABLE)
        ports.assert_not_called()
        return code, app, printed.getvalue(), sent_to

    def give_lead_fluidsynth(self):
        self.document.add_instrument(FLUID)
        self.document.change(self.document.get_setlist().get_instrument(FLUID).set_device, file_format.FLUIDSYNTH_DEVICE)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=FLUID)
