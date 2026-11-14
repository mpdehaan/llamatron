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
"""internal_tools/show_keys.py prints the key bindings of tui/keybindings.py: every class's, one class's, or every binding that has one key."""
"""Tests of the video tutorial tool's recording, which need no screen: the screen recording stops when a character is typed into its own terminal, as screencapture does, and the tutorial is recorded from just before the tracker runs until it quits, into recordings/<set>_tutorial.mov."""

import contextlib
import importlib.util
import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'make_video_tutorial.py'
MODULE_NAME = 'make_video_tutorial'
HELLO_WORLD = str(pathlib.Path(__file__).resolve().parent.parent / 'examples' / 'learning' / '01_hello_world.yml')
VIDEO_FILE = '01_hello_world_tutorial.mov'
SUBTITLES_FILE = '01_hello_world_tutorial.srt'
SAID = 'First we open a demo.'
ENDED = 2
A_WINDOW = 7
A_DEVICE = 'loopback'
A_PACE = 0.0
# A stand-in for screencapture: it puts its terminal in raw mode and waits for one character, as screencapture does, then writes the file its last argument names.
STAND_IN = 'import sys, termios, tty; tty.setraw(0, termios.TCSANOW); sys.stdin.read(1); open(sys.argv[-1], "w").write("video")'
# A stand-in that never reads its input, as screencapture does when given a time limit.
DEAF_STAND_IN = 'import time; time.sleep(60)'
A_MOMENT = 0.5
STARTED = 'started'
RAN = 'ran'
STOPPED = 'stopped'
FAILED = 'the tracker failed'


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeRecording:
    """A screen recording that notes when it starts and stops, and writes its file on stop."""

    __slots__ = ('path', 'happened')

    def __init__(self, *, path, happened):
        self.path = path
        self.happened = happened
        happened.append(STARTED)

    def stop(self):
        self.happened.append(STOPPED)
        with open(self.path, 'w') as video:
            video.write(STARTED)
        return 0


class TestScreenRecording(unittest.TestCase):

    def test_typing_a_character_into_its_terminal_stops_the_recording_and_the_file_is_written(self):
        tool = load_script()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, VIDEO_FILE)
            with mock.patch.object(tool, 'SCREENCAPTURE', sys.executable), mock.patch.object(tool, 'CAPTURE_FLAGS', ['-c', STAND_IN]):
                recording = tool.ScreenRecording(path=path, window=A_WINDOW, audio_device=None)
                self.assertIsNone(recording.process.poll())
                self.assertEqual(recording.stop(), 0)
            self.assertTrue(os.path.exists(path))

    def test_the_command_records_the_window_with_the_sound_device_given_and_no_time_limit(self):
        tool = load_script()
        with mock.patch.object(tool.subprocess, 'Popen') as popen, mock.patch.object(tool.os, 'close'), mock.patch.object(tool.pty, 'openpty', return_value=(0, 1)):
            tool.ScreenRecording(path=VIDEO_FILE, window=A_WINDOW, audio_device=A_DEVICE)
            command = popen.call_args.args[0]
        # A time limit would make screencapture ignore the character that stops it.
        self.assertEqual(command, [tool.SCREENCAPTURE, *tool.CAPTURE_FLAGS, '-l', str(A_WINDOW), '-G', A_DEVICE, VIDEO_FILE])

    def test_a_recording_that_does_not_stop_when_told_is_ended_and_says_so(self):
        tool = load_script()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, VIDEO_FILE)
            with mock.patch.object(tool, 'SCREENCAPTURE', sys.executable), mock.patch.object(tool, 'CAPTURE_FLAGS', ['-c', DEAF_STAND_IN]), mock.patch.object(tool, 'STOP_TIMEOUT_SECONDS', A_MOMENT):
                recording = tool.ScreenRecording(path=path, window=A_WINDOW, audio_device=None)
                self.assertIsNone(recording.stop())
            self.assertFalse(os.path.exists(path))


class TestTutorialIsRecorded(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.happened = []
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        patcher = mock.patch.object(self.tool, 'RECORDINGS', self.folder.name)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_app(self, *, fails=False):
        """Return a tracker whose run notes that it ran, or fails, and whose tutorial reports nothing."""
        app = mock.Mock()

        def run():
            self.happened.append(RAN)
            if fails:
                raise RuntimeError(FAILED)
        app.run.side_effect = run
        app.driven.report.return_value = []
        app.driven.problem = None
        app.driven.narrator.said = [(0, SAID)]
        app.driven.started_at = 0
        app.driven.ended_at = ENDED
        return app

    def recording(self, **named):
        return FakeRecording(path=named['path'], happened=self.happened)

    def run_tool(self, *, video=True, app=None):
        with mock.patch.object(self.tool, 'LlamatronApp', return_value=app or self.fake_app()) as made, contextlib.redirect_stdout(io.StringIO()):
            code = self.tool.run(path=HELLO_WORLD, driver=None, audio_device=A_DEVICE, pace=A_PACE, play=False, save_to=None, go=True,
                                 video=video, window_id=A_WINDOW, recording=self.recording)
        return code, made

    def test_the_recording_starts_before_the_tracker_runs_and_stops_once_it_quits(self):
        code, made = self.run_tool()
        self.assertEqual(code, self.tool.SUCCESS)
        self.assertEqual(self.happened, [STARTED, RAN, STOPPED])
        self.assertTrue(os.path.exists(os.path.join(self.folder.name, VIDEO_FILE)))
        # The captions are written beside the video, for YouTube.
        with open(os.path.join(self.folder.name, SUBTITLES_FILE), encoding=self.tool.FILE_ENCODING) as handle:
            self.assertIn(SAID, handle.read())
        self.assertTrue(made.call_args.kwargs['launch'].for_recording)
        # The tracker's time limit ends the recording, since screencapture has none.
        self.assertEqual(made.call_args.kwargs['launch'].max_seconds, self.tool.DEFAULT_MAX_SECONDS)

    def test_the_recording_is_stopped_and_written_even_when_the_tracker_fails(self):
        with self.assertRaises(RuntimeError):
            self.run_tool(app=self.fake_app(fails=True))
        self.assertEqual(self.happened, [STARTED, RAN, STOPPED])

    def test_without_video_nothing_is_recorded_and_the_tracker_opens_without_the_splash(self):
        code, made = self.run_tool(video=False)
        self.assertEqual(code, self.tool.SUCCESS)
        self.assertEqual(self.happened, [RAN])
        self.assertFalse(made.call_args.kwargs['launch'].for_recording)
