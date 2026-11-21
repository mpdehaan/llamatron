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
"""internal_tools/make_video_tutorial.py, one quick check of its main path: the recording starts before the tracker runs and stops once it quits. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'make_video_tutorial.py'
MODULE_NAME = 'make_video_tutorial'
HELLO_WORLD = str(pathlib.Path(__file__).resolve().parent.parent.parent / 'examples' / 'learning' / '01_hello_world.yml')
VIDEO_FILE = '01_hello_world_tutorial.mov'
SUBTITLES_FILE = '01_hello_world_tutorial.srt'
SAID = 'First we open a demo.'
ENDED = 2
A_WINDOW = 7
A_DEVICE = 'loopback'
A_PACE = 0.0
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
