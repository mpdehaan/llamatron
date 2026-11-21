# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""internal_tools/preview_visualizer.py, one quick check of its main path: it launches the tracker on the mode and quits when the song ends. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import pathlib
import unittest
from unittest import mock

from llamatron.interface.visualizers import modes
from tests.support.ui_testing import a_song

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'preview_visualizer.py'
MODULE_NAME = 'preview_visualizer'
SET_FILE = 'a set.yml'


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPreviewVisualizer(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.shared = self.tool.recorder()

    def test_it_launches_the_tracker_on_the_mode_and_quits_when_the_song_ends(self):
        document = a_song()
        port = self.shared.DEFAULT_DRIVER
        with mock.patch.object(self.tool, 'output_port_names', return_value=[port]), mock.patch.object(self.tool.Document, 'load', return_value=document), \
                mock.patch.object(self.tool, 'LlamatronApp') as app, contextlib.redirect_stdout(io.StringIO()):
            self.tool.preview(path=SET_FILE, driver=port, assignment=None, visualizer=modes.MODES[0].OPTION, shared=self.shared)
        launch = app.call_args.kwargs['launch']
        self.assertEqual(launch.visualizer, modes.MODES[0].OPTION)
        self.assertTrue(launch.quit_when_finished)
        self.assertFalse(launch.for_recording)
        self.assertTrue(document.get_setlist().is_real_time())


if __name__ == '__main__':
    unittest.main()
