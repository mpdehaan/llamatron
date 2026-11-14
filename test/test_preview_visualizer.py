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
"""Tests of the visualizer preview's parts that need no port and no screen: which mode it shows, and that a driver nobody has stops it before the tracker opens."""

import contextlib
import importlib.util
import io
import pathlib
import unittest
from unittest import mock

from llamatron.visualizers.modes import MODES
from ui_testing import a_song

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'preview_visualizer.py'
MODULE_NAME = 'preview_visualizer'
PORT_NAMES = 'preview_visualizer.output_port_names'
NO_SUCH = 'doesnotexist'
SET_FILE = 'a set.yml'
FAILURE = 1


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

    def test_it_shows_the_mode_typed_from_the_list_or_the_only_one_without_asking(self):
        with mock.patch('builtins.input', return_value=str(len(MODES))) as asked, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.tool.ask_for_mode(shared=self.shared), MODES[-1].OPTION)
        self.assertEqual(asked.call_count, 0 if len(MODES) == 1 else 1)
        with mock.patch.object(self.tool, 'MODES', MODES[:1]), mock.patch('builtins.input') as asked:
            self.assertEqual(self.tool.ask_for_mode(shared=self.shared), MODES[0].OPTION)
        asked.assert_not_called()

    def test_a_driver_nobody_has_stops_it_before_the_tracker_opens(self):
        with mock.patch.object(self.tool, 'output_port_names', return_value=[]), mock.patch.object(self.tool, 'LlamatronApp') as app, \
                contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.tool.preview(path=SET_FILE, driver=NO_SUCH, assignment=None, visualizer=MODES[0].OPTION, shared=self.shared)
        self.assertEqual(code, FAILURE)
        app.assert_not_called()
        self.assertIn(NO_SUCH, stderr.getvalue())

    def test_it_launches_the_tracker_on_the_mode_and_quits_when_the_song_ends(self):
        document = a_song()
        port = self.shared.DEFAULT_DRIVER
        with mock.patch.object(self.tool, 'output_port_names', return_value=[port]), mock.patch.object(self.tool.Document, 'load', return_value=document), \
                mock.patch.object(self.tool, 'LlamatronApp') as app, contextlib.redirect_stdout(io.StringIO()):
            self.tool.preview(path=SET_FILE, driver=port, assignment=None, visualizer=MODES[0].OPTION, shared=self.shared)
        launch = app.call_args.kwargs['launch']
        self.assertEqual(launch.visualizer, MODES[0].OPTION)
        self.assertTrue(launch.quit_when_finished)
        self.assertFalse(launch.for_recording)
        self.assertTrue(document.setlist().is_real_time())


if __name__ == '__main__':
    unittest.main()
